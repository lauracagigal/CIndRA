"""Regional (Pacific) analysis of the climate-projection indicators.

Multi-model series are averaged over every Pacific EEZ (``data/regional/Pacific_EEZs``)
and over the four ocean regions of the phytoplankton-size reference figure, then
summarised as

* maps of the per-EEZ linear trend (2015–2100) of the multi-model median,
* maps of the per-EEZ change relative to 2015–2035 at the global warming levels,
* box plots across models at the global warming levels for each ocean region.

Data sources and warming-level years are the ones used by the national projection
notebooks (see ``functions/projections.py``). Regional means are cached under
``data/projections/regional/``.
"""

from pathlib import Path

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr
from cartopy.mpl.gridliner import LATITUDE_FORMATTER, LONGITUDE_FORMATTER
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from matplotlib.patches import Rectangle

import projections as prj

PACIFIC_EXTENT = (120, 252, -40, 35)
REGIONAL_TAG = "pacific"
CACHE_DIR = prj.PROJECTIONS_DATA_DIR / "regional"

# Ocean regions (lon_min, lon_max in 0–360 °E, lat_min, lat_max), approximated from the
# phytoplankton-size reference figure.
REGION_BOXES = {
    "North Pacific Subtropical Gyre": (125, 245, 10, 30),
    "Equatorial Upwelling": (165, 245, -5, 5),
    "Western Equatorial Pacific": (125, 165, -15, 5),
    "South Pacific Subtropical Gyre": (190, 245, -35, -15),
}
BOX_COLOR = "crimson"

# Indicator settings: label, units of the change, percent change or absolute, colour map,
# whether the colour scale is centred on zero.
INDICATORS = {
    "tas": dict(label="Mean temperature", units="°C", percent=False, cmap="Reds", diverging=False),
    "tasmin": dict(label="Minimum temperature", units="°C", percent=False, cmap="Reds", diverging=False),
    "tasmax": dict(label="Maximum temperature", units="°C", percent=False, cmap="Reds", diverging=False),
    "warmdays": dict(label="Warm days", units="days/year", percent=False, cmap="RdBu_r", diverging=True),
    "coldnights": dict(label="Cold nights", units="days/year", percent=False, cmap="RdBu_r", diverging=True),
    "pr": dict(label="Annual rainfall", units="%", percent=True, cmap="BrBG", diverging=True),
    "dry_days": dict(label="Dry days", units="days/year", percent=False, cmap="BrBG_r", diverging=True),
    "heavyraindays": dict(label="Heavy-rainfall days", units="days/year", percent=False, cmap="BrBG", diverging=True),
    "yearmax": dict(label="Annual maximum daily rainfall", units="%", percent=True, cmap="BrBG", diverging=True),
    "tos": dict(label="Sea surface temperature", units="°C", percent=False, cmap="Reds", diverging=False),
    "ph": dict(label="Surface pH", units="pH units", percent=False, cmap="magma", diverging=False),
    "mhw_days": dict(label="Marine heatwave days", units="days/year", percent=False, cmap="YlOrRd", diverging=False),
}


# ---------------------------------------------------------------------------
# Regions
# ---------------------------------------------------------------------------

def load_eez(eez_file=prj.EEZ_FILE):
    """Pacific EEZs dissolved by country (one geometry per ``Country``)."""
    eez = gpd.read_file(eez_file).to_crs(4326)
    return eez.dissolve(by="Country").reset_index()[["Country", "geometry"]]


def region_names(eez):
    return list(eez["Country"]) + list(REGION_BOXES)


def region_weights(lon, lat, eez):
    """Cosine-latitude weights (n_regions, n_cells) of the grid cells inside each EEZ and ocean box.

    ``lon``/``lat`` are 1-D axes of a rectilinear grid or 2-D arrays of a curvilinear
    one; cells are flattened in C order of the (lat, lon) or native 2-D layout.
    """
    lon, lat = np.asarray(lon, dtype=float), np.asarray(lat, dtype=float)
    if lon.ndim == 1:
        lon, lat = np.meshgrid(lon, lat)
    weight = np.cos(np.deg2rad(lat)).ravel()
    masks = [prj.points_in_geometry(geom, lon, lat).ravel() for geom in eez.geometry]
    lon360 = lon.ravel() % 360
    for x0, x1, y0, y1 in REGION_BOXES.values():
        masks.append((lon360 >= x0) & (lon360 <= x1) & (lat.ravel() >= y0) & (lat.ravel() <= y1))
    return np.stack(masks).astype(float) * weight


def _weighted_means(values, weights):
    """Weighted means over cells, ignoring NaN: values (n, n_cells) -> (n, n_regions)."""
    valid = np.isfinite(values)
    num = np.where(valid, values, 0.0) @ weights.T
    den = valid.astype(float) @ weights.T
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, num / den, np.nan)


# ---------------------------------------------------------------------------
# Regional means
# ---------------------------------------------------------------------------

def extract_regional_means(variable, eez, scenarios=prj.SCENARIOS, overwrite=False):
    """CSIRO multi-model annual series averaged over every EEZ and ocean box.

    Returns a Dataset with ``variable`` on (scenario, model, time, region).
    """
    cache_file = CACHE_DIR / f"{variable}_regions.nc"
    cached = prj._cached(cache_file, overwrite)
    if cached is not None:
        return cached

    names, weights, series = region_names(eez), None, []
    for scenario in scenarios:
        da, how = prj._open_csiro(variable, scenario)
        if weights is None:
            weights = region_weights(da.lon.values, da.lat.values, eez)
        time_dim = da.dims[1]
        per_model = []
        for k in range(da.sizes["model"]):
            values = da.isel(model=k).values.astype("float64")
            if variable in prj.COUNT_VARIABLES:
                values[values < 0] = np.nan
            per_model.append(_weighted_means(values.reshape(values.shape[0], -1), weights))
        arr = xr.DataArray(np.stack(per_model), dims=("model", time_dim, "region"),
                           coords={"model": da.model.values, time_dim: da[time_dim].values, "region": names})
        series.append(prj._to_annual(arr, how, variable).expand_dims(scenario=[scenario]))

    ds = xr.concat(series, dim="scenario", join="outer").to_dataset(name=variable)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return prj._save(ds, cache_file)


def extract_atlas_ph_regional(eez, scenarios=("ssp245", "ssp370", "ssp585"), overwrite=False):
    """Annual-mean CMIP6 surface pH (IPCC-WGI AR6 Atlas) averaged over every EEZ and ocean box."""
    cache_file = CACHE_DIR / "ph_regions.nc"
    cached = prj._cached(cache_file, overwrite)
    if cached is not None:
        return cached

    folder_names = {"ssp245": "ssp2_4_5", "ssp370": "ssp3_7_0", "ssp585": "ssp5_8_5"}
    names, series = region_names(eez), []
    for scenario in scenarios:
        folder = prj.extra_dir() / "data_copernicus" / f"monthly_mean_of_acidity_of_seawater_{folder_names[scenario]}_2015-2099"
        da = xr.open_dataset(sorted(folder.glob("ph_CMIP6_*.nc"))[0])["ph"]
        weights = region_weights(da.lon.values, da.lat.values, eez)
        per_member = [_weighted_means(da.isel(member=m).values.astype("float64").reshape(da.sizes["time"], -1), weights)
                      for m in range(da.sizes["member"])]
        arr = xr.DataArray(np.stack(per_member), dims=("model", "time", "region"),
                           coords={"model": da["gcm_model"].values, "time": da.time.values, "region": names})
        series.append(prj._to_annual(arr, "mean", "ph").expand_dims(scenario=[scenario]))

    ds = xr.concat(series, dim="scenario", join="outer").to_dataset(name="ph")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return prj._save(ds, cache_file)


def extract_mhw_regional(eez, scenarios=("ssp126", "ssp585"), overwrite=False):
    """MHW days per year and category (Holbrook et al.) averaged over every EEZ and ocean box.

    Returns a Dataset with ``mhw_cats_dpy`` on (scenario, model, time, cat, region) and
    ``mhw_days`` (all categories) on (scenario, model, time, region).
    """
    cache_file = CACHE_DIR / "mhw_regions.nc"
    cached = prj._cached(cache_file, overwrite)
    if cached is not None:
        cached["time"] = pd.to_datetime(cached.time.values)
        return cached

    import re
    folder = prj.extra_dir() / "marine_heatwaves" / "pac_mhw_stats" / "mhw_cats"
    names, per_scenario = region_names(eez), []
    for scenario in scenarios:
        models, means = [], []
        for path in sorted(folder.glob(f"mhw_cats.pac_is.*.historical+{scenario}.*.nc")):
            ds = xr.open_dataset(path)
            lat2d, lon2d = xr.broadcast(ds["lat"], ds["lon"])
            weights = region_weights(lon2d.values, lat2d.values, eez)
            da = ds["mhw_cats_dpy"].transpose("time", "cat", *lat2d.dims)
            values = da.values.astype("float64").reshape(da.sizes["time"] * da.sizes["cat"], -1)
            mean = _weighted_means(values, weights).reshape(da.sizes["time"], da.sizes["cat"], -1)
            means.append(mean)
            models.append(re.match(r"mhw_cats\.pac_is\.(.+)\.historical\+", path.name).group(1))
            times, cats = ds.time.values, ds.cat.values
        arr = xr.DataArray(np.stack(means), dims=("model", "time", "cat", "region"),
                           coords={"model": models, "time": times, "cat": cats, "region": names})
        per_scenario.append(arr.expand_dims(scenario=[scenario]))

    out = xr.concat(per_scenario, dim="scenario", join="outer").to_dataset(name="mhw_cats_dpy")
    out["time"] = pd.to_datetime([f"{int(t)}-01-01" for t in out.time.values])
    out["mhw_days"] = out["mhw_cats_dpy"].sum("cat", min_count=1)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return prj._save(out, cache_file)


def extract_ocads_regional(variable, eez, scenarios=prj.SCENARIOS, overwrite=False):
    """Decadal OCADS median field (Jiang et al., 2023) averaged over every EEZ and ocean box."""
    cache_file = CACHE_DIR / f"{variable}_ocads_regions.nc"
    cached = prj._cached(cache_file, overwrite)
    if cached is not None:
        return cached

    names, series = region_names(eez), []
    for scenario in scenarios:
        ds = prj.open_ocads(variable, scenario, "median")
        weights = region_weights(ds.longitude.values, ds.latitude.values, eez)
        values = ds[variable].values.astype("float64").reshape(ds.sizes["time"], -1)
        arr = xr.DataArray(_weighted_means(values, weights), dims=("time", "region"),
                           coords={"time": ds.time.values, "region": names})
        series.append(arr.expand_dims(scenario=[scenario]))

    out = xr.concat(series, dim="scenario").to_dataset(name=variable)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return prj._save(out, cache_file)


# ---------------------------------------------------------------------------
# Indicators
# ---------------------------------------------------------------------------

def change_vs_baseline(da, baseline=("2015", "2035"), percent=False):
    """Change of each model relative to its own ``baseline`` mean (absolute or %)."""
    ref = da.sel(time=slice(*baseline)).mean("time")
    return (da - ref) / ref * 100 if percent else da - ref


def trend_per_decade(da, scenarios, period=("2015", "2100")):
    """Linear trend (per decade) of the multi-model median series: DataFrame region × scenario."""
    out = {}
    for scenario in scenarios:
        median = da.sel(scenario=scenario, time=slice(*period)).median("model")
        years = median.time.dt.year.values.astype(float)
        trend = {}
        for region in median.region.values:
            y = median.sel(region=region).values
            ok = np.isfinite(y)
            trend[region] = np.polyfit(years[ok], y[ok], 1)[0] * 10 if ok.sum() > 10 else np.nan
        out[scenario.upper()] = pd.Series(trend)
    return pd.DataFrame(out)


def change_at_levels(change, scenario_info, scenario):
    """Multi-model median change in the year ``scenario`` reaches each warming level: DataFrame region × level."""
    out = {}
    for level, info in scenario_info.get(scenario, {}).items():
        year = info["year"]
        if prj._reached(year):
            out[f"+{level}°C ({str(year)[:4]})"] = change.sel(scenario=scenario).sel(time=year, method="nearest").median("model").to_series()
    return pd.DataFrame(out)


def region_summary(change, scenario_info, scenarios, decimals=2):
    """``prj.gwl_summary`` for each ocean region, stacked with a ``Region`` column."""
    ds = change.to_dataset(name="change")
    tables = [prj.gwl_summary(ds.sel(region=name), "change", scenario_info, scenarios, decimals).assign(Region=name)
              for name in REGION_BOXES]
    table = pd.concat(tables, ignore_index=True)
    return table[["Region"] + [c for c in table.columns if c != "Region"]]


# ---------------------------------------------------------------------------
# Maps
# ---------------------------------------------------------------------------

def _pacific_axes(ax, boxes=True, labels=True):
    ax.set_extent(PACIFIC_EXTENT, crs=ccrs.PlateCarree())
    ax.set_facecolor("#e8f1f6")
    ax.add_feature(cfeature.LAND, facecolor="lightgrey", edgecolor="none", zorder=3)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.3, edgecolor="0.4", zorder=4)
    gl = ax.gridlines(draw_labels=labels, linewidth=0.3, color="gray", alpha=0.5, linestyle="--")
    gl.top_labels = gl.right_labels = False
    gl.xformatter, gl.yformatter = LONGITUDE_FORMATTER, LATITUDE_FORMATTER
    if boxes:
        for x0, x1, y0, y1 in REGION_BOXES.values():
            ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, edgecolor=BOX_COLOR, linewidth=1.2,
                                   linestyle="--", transform=ccrs.PlateCarree(), zorder=6))


def plot_regions_map(eez, figsize=(13, 8)):
    """EEZs and the four ocean regions used in the regional projection analysis."""
    fig = plt.figure(figsize=figsize)
    ax = plt.axes(projection=ccrs.PlateCarree(central_longitude=180))
    _pacific_axes(ax)
    eez.plot(ax=ax, transform=ccrs.PlateCarree(), facecolor="#8fc4e8", edgecolor="#1b4f72", linewidth=0.6, alpha=0.5, zorder=2)
    for name, (x0, x1, y0, y1) in REGION_BOXES.items():
        ax.text(x0 + 1, y1 - 1, name, transform=ccrs.PlateCarree(), color=BOX_COLOR, fontsize=10, fontweight="bold",
                ha="left", va="top", zorder=7)
    ax.set_title("Pacific EEZs and ocean regions")
    return fig, ax


def plot_eez_panels(values, eez, title, colorbar_label, cmap="RdBu_r", diverging=True, ncols=2, figsize=None):
    """One map per column of ``values`` (index = EEZ country) with EEZs coloured by value."""
    panels = list(values.columns)
    nrows = int(np.ceil(len(panels) / ncols))
    figsize = figsize or (8 * ncols, 4.6 * nrows + 1)
    fig, axes = plt.subplots(nrows, ncols, figsize=figsize, squeeze=False,
                             subplot_kw={"projection": ccrs.PlateCarree(central_longitude=180)})
    data = values.loc[values.index.isin(eez["Country"])]
    finite = data.values[np.isfinite(data.values)]
    if finite.size == 0:
        vmin, vmax = -1, 1
    elif diverging:
        lim = np.nanpercentile(np.abs(finite), 98) or 1
        vmin, vmax = -lim, lim
    else:
        vmin, vmax = np.nanpercentile(finite, 2), np.nanpercentile(finite, 98)
    norm = Normalize(vmin=vmin, vmax=vmax)
    cmap = plt.get_cmap(cmap)

    for ax, panel in zip(axes.flat, panels):
        _pacific_axes(ax, boxes=False, labels=False)
        shaded = eez.assign(value=eez["Country"].map(data[panel]))
        has = shaded["value"].notna()
        if (~has).any():  # EEZs without data
            shaded[~has].plot(ax=ax, transform=ccrs.PlateCarree(), facecolor="white", edgecolor="0.5", hatch="///",
                              linewidth=0.4, zorder=2, aspect=None)
        if has.any():
            shaded[has].plot(ax=ax, transform=ccrs.PlateCarree(), color=cmap(norm(shaded.loc[has, "value"].values)),
                             edgecolor="0.3", linewidth=0.4, zorder=2, aspect=None)
        ax.set_title(panel, fontsize=13)
    for ax in list(axes.flat)[len(panels):]:
        ax.set_visible(False)

    cbar = fig.colorbar(ScalarMappable(norm=norm, cmap=cmap), ax=axes.ravel().tolist(), orientation="horizontal",
                        fraction=0.04, pad=0.04, extend="both")
    cbar.set_label(colorbar_label, fontsize=13)
    fig.suptitle(title, fontsize=15, fontweight="bold")
    return fig


def plot_region_lines(ds, variable, scenarios, ylabel, title, figsize=(14, 8)):
    """Decadal series of ``variable`` (no model dimension) in each ocean region, one line per scenario."""
    fig, axes = plt.subplots(2, 2, figsize=figsize, sharex=True)
    for ax, name in zip(axes.flat, REGION_BOXES):
        for scenario in scenarios:
            series = ds[variable].sel(region=name, scenario=scenario)
            ax.plot(series.time, series, marker="o", color=prj.SCENARIO_COLOR[scenario], label=scenario.upper())
        ax.set_title(name, fontsize=12)
        ax.set_ylabel(ylabel)
        ax.grid(alpha=0.3)
    axes.flat[0].legend(fontsize=10)
    fig.suptitle(title, fontsize=14, fontweight="bold")
    plt.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

DECIMALS = {"°C": 2, "%": 1, "days/year": 0, "pH units": 3}


def _slug(text):
    return "_".join(text.lower().split())


def indicator_report(ds, variable, scenario_info, eez, scenarios, map_scenario, fig_dir, tables_dir,
                     name=None, baseline=("2015", "2035"), absolute=False):
    """Trend map, change-at-warming-level map, region box plots and tables for one indicator.

    ``absolute=True`` reports the values themselves (e.g. MHW days) instead of the change
    relative to each model's ``baseline`` mean. Returns ``{figure key: figure}`` and
    ``{table key: DataFrame}``.
    """
    from ind_setup.plotting_projections import get_box_data, plot_global_warming_boxplot

    cfg = INDICATORS[variable]
    name = name or variable
    units = cfg["units"]
    n_f = DECIMALS.get(units, 2)
    values = ds[variable] if absolute else change_vs_baseline(ds[variable], baseline, cfg["percent"])
    what = cfg["label"] if absolute else f"Change in {cfg['label'].lower()} vs {baseline[0]}–{baseline[1]}"
    info = {sc: scenario_info[sc] for sc in scenarios if sc in scenario_info}
    figs, tables = {}, {}

    tables["trend"] = trend_per_decade(values, scenarios)
    figs["trend"] = plot_eez_panels(tables["trend"], eez, f"{cfg['label']}: linear trend 2015–2100 of the multi-model median",
                                    f"{units} per decade", cfg["cmap"], cfg["diverging"])
    save_figure(figs["trend"], fig_dir, f"{name}_trend_eez")
    save_table(tables["trend"].round(n_f + 2), tables_dir, f"{name}_trend_regions")

    tables["levels"] = change_at_levels(values, info, map_scenario)
    figs["levels"] = plot_eez_panels(tables["levels"], eez,
                                     f"{what} at global warming levels ({map_scenario.upper()}, multi-model median)",
                                     f"{'' if absolute else 'Δ '}{cfg['label']} [{units}]", cfg["cmap"], cfg["diverging"])
    save_figure(figs["levels"], fig_dir, f"{name}_gwl_eez_{map_scenario}")
    save_table(tables["levels"].round(n_f + 1), tables_dir, f"{name}_gwl_regions_{map_scenario}")

    ds_values = values.to_dataset(name="value")
    levels = list(prj.WARMING_LEVELS)
    for region in REGION_BOXES:
        ds_region = ds_values.sel(region=region)
        box_data, box_scenarios, positions = get_box_data(ds_region, info, levels, scenarios, "value")
        if not box_data:
            continue
        fig, _ = plot_global_warming_boxplot(box_data, ds_region, positions, box_scenarios, info, levels, "value",
                                             plot_ref=False, n_f=n_f, site_label=region,
                                             ylabel=f"{'' if absolute else 'Δ '}{cfg['label']} [{units}]")
        figs[f"box_{_slug(region)}"] = fig
        save_figure(fig, fig_dir, f"{name}_gwl_{_slug(region)}")

    tables["regions"] = region_summary(values, info, scenarios, decimals=n_f + 1)
    save_table(tables["regions"], tables_dir, f"{name}_gwl_ocean_regions", index=False)
    return figs, tables


def ocads_report(ds, variable, label, units, eez, scenarios, fig_dir, tables_dir, cmap="RdBu_r", start="2020", end="2100"):
    """Per-EEZ change between two decades and ocean-region series for an OCADS variable (no model spread)."""
    figs, tables = {}, {}
    change = ds[variable].sel(time=end).squeeze("time", drop=True) - ds[variable].sel(time=start).squeeze("time", drop=True)
    tables["change"] = change.to_pandas().T.rename(columns=str.upper)
    figs["change"] = plot_eez_panels(tables["change"], eez, f"{label}: change {start}–{end} (median of Earth system models)",
                                     f"Δ {label} [{units}]", cmap, True)
    save_figure(figs["change"], fig_dir, f"{variable}_change_eez")
    save_table(tables["change"].round(4), tables_dir, f"{variable}_change_regions")

    figs["regions"] = plot_region_lines(ds, variable, scenarios, f"{label} [{units}]", f"{label} in the ocean regions (decadal median)")
    save_figure(figs["regions"], fig_dir, f"{variable}_ocean_regions")
    regions = ds[variable].sel(region=list(REGION_BOXES)).to_dataframe().reset_index()
    regions["Year"] = pd.to_datetime(regions["time"]).dt.year
    tables["regions"] = regions.pivot_table(index=["region", "Year"], columns="scenario", values=variable).round(4)
    save_table(tables["regions"], tables_dir, f"{variable}_ocean_regions")
    return figs, tables


def save_figure(fig, fig_dir, name):
    path = Path(fig_dir) / f"PRJ_{name}_{REGIONAL_TAG}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    return path


def save_table(df, tables_dir, name, index=True):
    path = Path(tables_dir) / f"PRJ_{name}_{REGIONAL_TAG}.csv"
    df.to_csv(path, index=index)
    return path
