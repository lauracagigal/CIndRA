"""Regional (Pacific) analysis of the climate-projection indicators.

Multi-model series are averaged over every Pacific EEZ (``data/regional/Pacific_EEZs``),
over all the EEZs together (``ALL_EEZ``) and over the four ocean regions of the
phytoplankton-size reference figure (``REGION_BOXES``), then summarised as

* maps of the per-EEZ linear trend (2015–2100) of the multi-model median,
* maps of the per-EEZ change relative to 2015–2035 at the global warming levels,
* box plots across models at the global warming levels for the summary regions.

The four ocean regions are used only for the biochemical indicators (pH, aragonite,
salinity: ``BIOCHEM_REGIONS``). Every other indicator is summarised over all the EEZs
together (``DEFAULT_REGIONS``). The biochemical maps show the gridded field over the whole
Pacific window instead of EEZ means (``biochem_indicator_report``, ``ocads_report``), and
their trends, tables and box plots cover the four ocean regions only.

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
from matplotlib import patheffects
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
# Ocean regions whose name goes at the right end of the box in the gridded maps.
BOX_LABEL_RIGHT = ("Equatorial Upwelling",)

# Mean over the union of every Pacific EEZ.
ALL_EEZ = "All Pacific EEZs"
# Summary regions (box plots, tables): the ocean regions only for the biochemical indicators.
DEFAULT_REGIONS = (ALL_EEZ,)
BIOCHEM_REGIONS = tuple(REGION_BOXES)

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
    return list(eez["Country"]) + [ALL_EEZ] + list(REGION_BOXES)


def _cached_regions(cache_file, eez, overwrite):
    """Cached regional means, or None when missing, ``overwrite`` or without every current region."""
    cached = prj._cached(cache_file, overwrite)
    if cached is not None and set(region_names(eez)) - set(cached.region.values):
        return None
    return cached


def region_weights(lon, lat, eez):
    """Cosine-latitude weights (n_regions, n_cells) of the grid cells inside each EEZ, all EEZs and each ocean box.

    ``lon``/``lat`` are 1-D axes of a rectilinear grid or 2-D arrays of a curvilinear
    one; cells are flattened in C order of the (lat, lon) or native 2-D layout.
    """
    lon, lat = np.asarray(lon, dtype=float), np.asarray(lat, dtype=float)
    if lon.ndim == 1:
        lon, lat = np.meshgrid(lon, lat)
    weight = np.cos(np.deg2rad(lat)).ravel()
    masks = [prj.points_in_geometry(geom, lon, lat).ravel() for geom in eez.geometry]
    masks.append(np.any(masks, axis=0))  # ALL_EEZ
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
    """CSIRO multi-model annual series averaged over every EEZ, all EEZs and each ocean box.

    Returns a Dataset with ``variable`` on (scenario, model, time, region).
    """
    cache_file = CACHE_DIR / f"{variable}_regions.nc"
    cached = _cached_regions(cache_file, eez, overwrite)
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
    cached = _cached_regions(cache_file, eez, overwrite)
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
    cached = _cached_regions(cache_file, eez, overwrite)
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
    cached = _cached_regions(cache_file, eez, overwrite)
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


def extract_ocads_models_regional(variable, eez, scenarios=prj.SCENARIOS, overwrite=False):
    """Decadal OCADS field of every Earth system model (Jiang et al., 2023, ``bio/nc/ESMs``) averaged
    over every EEZ, all EEZs and each ocean box: Dataset with ``variable`` on (scenario, model, time, region).

    Models without a given scenario are NaN for it.
    """
    cache_file = CACHE_DIR / f"{variable}_ocads_models_regions.nc"
    cached = _cached_regions(cache_file, eez, overwrite)
    if cached is not None and set(scenarios) <= set(cached.scenario.values):
        return cached

    name = prj.OCADS_FILE_NAMES[variable]
    esm_dir = prj.extra_dir() / "bio" / "nc" / "ESMs"
    names, weights, series = region_names(eez), None, []
    for scenario in scenarios:
        per_model = []
        for model_dir in sorted(p for p in esm_dir.iterdir() if p.is_dir()):
            path = model_dir / f"{model_dir.name}_{name}_{scenario}.nc"
            if not path.is_file():
                continue
            ds = xr.open_dataset(path)
            if weights is None:
                weights = region_weights(ds.longitude.values, ds.latitude.values, eez)
            values = ds[variable].values.astype("float64").reshape(ds.sizes["time"], -1)
            times = pd.to_datetime([f"{int(t)}-01-01" for t in ds.time.values])
            per_model.append(xr.DataArray(_weighted_means(values, weights), dims=("time", "region"),
                                          coords={"time": times, "region": names}).expand_dims(model=[model_dir.name]))
        if per_model:
            series.append(xr.concat(per_model, dim="model", join="outer").expand_dims(scenario=[scenario]))

    out = xr.concat(series, dim="scenario", join="outer").to_dataset(name=variable)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return prj._save(out, cache_file)


# ---------------------------------------------------------------------------
# Gridded fields over the Pacific window (biochemical maps)
# ---------------------------------------------------------------------------

def _pacific_window(da):
    """Subset a (lat, lon) field to ``PACIFIC_EXTENT`` with longitudes in 0–360 °E, ascending."""
    x0, x1, y0, y1 = PACIFIC_EXTENT
    da = da.assign_coords(lon=da.lon % 360).sortby("lon").sortby("lat")
    return da.sel(lon=slice(x0, x1), lat=slice(y0, y1))


def extract_atlas_ph_grid(scenarios=("ssp245", "ssp370", "ssp585"), overwrite=False):
    """Annual-mean CMIP6 surface pH (IPCC-WGI AR6 Atlas) of every member on the Pacific window.

    Returns a Dataset with ``ph`` on (scenario, model, time, lat, lon), cached in
    ``data/projections/regional/ph_grid_pacific.nc``.
    """
    cache_file = CACHE_DIR / "ph_grid_pacific.nc"
    cached = prj._cached(cache_file, overwrite)
    if cached is not None and set(scenarios) <= set(cached.scenario.values):
        return cached

    folder_names = {"ssp245": "ssp2_4_5", "ssp370": "ssp3_7_0", "ssp585": "ssp5_8_5"}
    series = []
    for scenario in scenarios:
        folder = prj.extra_dir() / "data_copernicus" / f"monthly_mean_of_acidity_of_seawater_{folder_names[scenario]}_2015-2099"
        da = xr.open_dataset(sorted(folder.glob("ph_CMIP6_*.nc"))[0])["ph"]
        models = da["gcm_model"].values
        da = _pacific_window(da.drop_vars([c for c in da.coords if c not in ("time", "lat", "lon")])).load()
        annual = da.resample(time="YS").mean().rename(member="model").assign_coords(model=models)
        series.append(annual.astype("float32").expand_dims(scenario=[scenario]))

    ds = xr.concat(series, dim="scenario", join="outer").to_dataset(name="ph")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return prj._save(ds, cache_file)


def ocads_grid(variable, scenarios=prj.SCENARIOS):
    """Decadal OCADS median field (Jiang et al., 2023) on the Pacific window: (scenario, time, lat, lon)."""
    fields = []
    for scenario in scenarios:
        ds = prj.open_ocads(variable, scenario, "median")
        da = xr.DataArray(ds[variable].values, dims=("time", "lat", "lon"),
                          coords={"time": ds.time.values, "lat": ds.latitude.values[:, 0], "lon": ds.longitude.values[0]})
        fields.append(_pacific_window(da).expand_dims(scenario=[scenario]))
    return xr.concat(fields, dim="scenario")


def grid_trend_per_decade(da, period=("2015", "2100")):
    """Linear trend (per decade) along ``time`` of every grid cell of a (time, lat, lon) field."""
    sub = da.sel(time=slice(*period))
    years = sub.time.dt.year.values.astype(float)
    values = sub.values.reshape(sub.sizes["time"], -1)
    ok = np.isfinite(values).all(axis=0)
    trend = np.full(values.shape[1], np.nan)
    if ok.any():
        trend[ok] = np.polyfit(years, values[:, ok], 1)[0] * 10
    return xr.DataArray(trend.reshape(sub.sizes["lat"], sub.sizes["lon"]), dims=("lat", "lon"),
                        coords={"lat": sub.lat.values, "lon": sub.lon.values})


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


def region_summary(change, scenario_info, scenarios, decimals=2, regions=DEFAULT_REGIONS):
    """``prj.gwl_summary`` for each summary region, stacked with a ``Region`` column."""
    ds = change.to_dataset(name="change")
    tables = [prj.gwl_summary(ds.sel(region=name), "change", scenario_info, scenarios, decimals).assign(Region=name)
              for name in regions]
    table = pd.concat(tables, ignore_index=True)
    return table[["Region"] + [c for c in table.columns if c != "Region"]]


# ---------------------------------------------------------------------------
# Maps
# ---------------------------------------------------------------------------

def _pacific_axes(ax, boxes=True, labels=True, box_labels=False, box_label_size=9):
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
    if boxes and box_labels:  # region name just above the top edge of each box
        for name, (x0, x1, y0, y1) in REGION_BOXES.items():
            right = name in BOX_LABEL_RIGHT  # avoid overlapping the label of the box to its left
            ax.text(x1 - 0.5 if right else x0 + 0.5, y1 + 0.4, name, transform=ccrs.PlateCarree(), color=BOX_COLOR,
                    fontsize=box_label_size, fontweight="bold", ha="right" if right else "left", va="bottom", zorder=7,
                    path_effects=[patheffects.withStroke(linewidth=2.5, foreground="white")])


def plot_regions_map(eez, figsize=(13, 8)):
    """EEZs and the four ocean regions (biochemical indicators only) of the regional projection analysis."""
    fig = plt.figure(figsize=figsize)
    ax = plt.axes(projection=ccrs.PlateCarree(central_longitude=180))
    _pacific_axes(ax)
    eez.plot(ax=ax, transform=ccrs.PlateCarree(), facecolor="#8fc4e8", edgecolor="#1b4f72", linewidth=0.6, alpha=0.5, zorder=2)
    for name, (x0, x1, y0, y1) in REGION_BOXES.items():
        ax.text(x0 + 1, y1 - 1, name, transform=ccrs.PlateCarree(), color=BOX_COLOR, fontsize=10, fontweight="bold",
                ha="left", va="top", zorder=7)
    ax.set_title("Pacific EEZs and ocean regions (biochemical indicators)")
    return fig, ax


def colour_limits(values, diverging=True):
    """Colour-scale limits of a set of values: ±98th percentile of |values| if ``diverging``, else 2nd–98th percentile."""
    finite = np.asarray(values, dtype=float).ravel()
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return -1, 1
    if diverging:
        lim = np.nanpercentile(np.abs(finite), 98) or 1
        return -lim, lim
    return np.nanpercentile(finite, 2), np.nanpercentile(finite, 98)


def plot_eez_panels(values, eez, title, colorbar_label, cmap="RdBu_r", diverging=True, ncols=2, figsize=None, limits=None):
    """One map per column of ``values`` (index = EEZ country) with EEZs coloured by value."""
    panels = list(values.columns)
    ncols = min(ncols, len(panels)) or 1
    nrows = int(np.ceil(len(panels) / ncols))
    figsize = figsize or (8 * ncols, 4.6 * nrows + 1)
    fig, axes = plt.subplots(nrows, ncols, figsize=figsize, squeeze=False,
                             subplot_kw={"projection": ccrs.PlateCarree(central_longitude=180)})
    data = values.loc[values.index.isin(eez["Country"])]
    vmin, vmax = limits or colour_limits(data.values, diverging)
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


def plot_grid_panels(fields, title, colorbar_label, cmap="RdBu_r", diverging=True, eez=None, ncols=2, figsize=None, limits=None):
    """One map per entry of ``fields`` ({panel title: (lat, lon) DataArray}) over the Pacific window,
    with the four ocean regions outlined and, if given, the EEZ boundaries."""
    panels = list(fields)
    ncols = min(ncols, len(panels)) or 1
    nrows = int(np.ceil(len(panels) / ncols))
    figsize = figsize or (8 * ncols, 4.6 * nrows + 1)
    fig, axes = plt.subplots(nrows, ncols, figsize=figsize, squeeze=False,
                             subplot_kw={"projection": ccrs.PlateCarree(central_longitude=180)})
    vmin, vmax = limits or colour_limits(np.concatenate([np.asarray(f.values).ravel() for f in fields.values()]), diverging)
    norm = Normalize(vmin=vmin, vmax=vmax)
    cmap = plt.get_cmap(cmap)

    for ax, panel in zip(axes.flat, panels):
        _pacific_axes(ax, boxes=True, labels=False, box_labels=True)
        field = fields[panel]
        ax.pcolormesh(field.lon, field.lat, field.values, cmap=cmap, norm=norm, shading="auto",
                      transform=ccrs.PlateCarree(), zorder=1)
        if eez is not None:
            eez.boundary.plot(ax=ax, transform=ccrs.PlateCarree(), color="0.35", linewidth=0.3, zorder=5)
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


def plot_region_series(da, regions, scenarios, ylabel, title, spread=(10, 90), ncols=2, figsize=None):
    """Annual series of the multi-model median in each of ``regions``, one line per scenario, with the
    ``spread`` percentiles across models shaded. ``da`` is on (scenario, model, time, region)."""
    regions = list(regions)
    ncols = min(ncols, len(regions))
    nrows = int(np.ceil(len(regions) / ncols))
    figsize = figsize or ((14, 4.5 * nrows) if ncols > 1 else (12, 6))
    fig, axes = plt.subplots(nrows, ncols, figsize=figsize, sharex=True, squeeze=False)
    for ax, region in zip(axes.flat, regions):
        for scenario in scenarios:
            series = da.sel(region=region, scenario=scenario).dropna("time", how="all")
            color = prj.SCENARIO_COLOR[scenario]
            low, high = (series.quantile(q / 100, dim="model") for q in spread)
            ax.fill_between(series.time.values, low, high, color=color, alpha=0.15, linewidth=0)
            ax.plot(series.time.values, series.median("model"), color=color, linewidth=2, label=scenario.upper())
        if len(regions) > 1:
            ax.set_title(region, fontsize=12)
        ax.set_ylabel(ylabel)
        ax.grid(alpha=0.3)
    for ax in list(axes.flat)[len(regions):]:
        ax.set_visible(False)
    axes.flat[0].legend(fontsize=10, title=f"Median (shading: P{spread[0]}–P{spread[1]})", title_fontsize=10)
    fig.suptitle(title, fontsize=14, fontweight="bold")
    plt.tight_layout()
    return fig


def series_report(ds, variable, label, units, scenarios, fig_dir, tables_dir, regions=DEFAULT_REGIONS, name=None,
                  baseline=("2015", "2035")):
    """Annual series (multi-model median and spread) of the change of ``variable`` relative to each model's
    ``baseline`` mean in ``regions``, and the table of decadal means of the multi-model median per scenario.
    The change removes each model's mean bias, so the shading shows the spread of the projected change."""
    name = name or variable
    da = change_vs_baseline(ds[variable].sel(region=list(regions)), baseline)
    fig = plot_region_series(da, regions, scenarios, f"Δ {label} [{units}]",
                             f"Change in {label.lower()} vs {baseline[0]}–{baseline[1]} – {', '.join(regions)}")
    save_figure(fig, fig_dir, f"{name}_series_{'all_eez' if tuple(regions) == DEFAULT_REGIONS else 'ocean_regions'}")
    median = da.sel(scenario=list(scenarios)).median("model")
    decadal = median.resample(time="10YS").mean().to_dataframe(name=variable).reset_index()
    decadal["Decade"] = pd.to_datetime(decadal["time"]).dt.year
    table = decadal.pivot_table(index=["region", "Decade"], columns="scenario", values=variable).round(3)
    table.columns = [c.upper() for c in table.columns]
    table = _titled(table, f"Change in {label.lower()} vs {baseline[0]}–{baseline[1]} ({units}): decadal mean of the multi-model median")
    save_table(table, tables_dir, f"{name}_series_{'all_eez' if tuple(regions) == DEFAULT_REGIONS else 'ocean_regions'}")
    return fig, table


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

DECIMALS = {"°C": 2, "%": 1, "days/year": 0, "pH units": 3}


def _slug(text):
    return "_".join(text.lower().split())


def indicator_report(ds, variable, scenario_info, eez, scenarios, map_scenario, fig_dir, tables_dir,
                     name=None, baseline=("2015", "2035"), absolute=False, regions=DEFAULT_REGIONS):
    """Trend map, change-at-warming-level map, region box plots and tables for one indicator.

    Box plots and the ``regions`` table cover ``regions`` (all the EEZs together by default).
    Biochemical indicators use ``biochem_indicator_report`` (gridded maps, ocean regions).
    ``absolute=True`` reports the values themselves (e.g. MHW days) instead of the change
    relative to each model's ``baseline`` mean. Returns ``{figure key: figure}`` and
    ``{table key: DataFrame}``.
    """
    cfg = INDICATORS[variable]
    name = name or variable
    units = cfg["units"]
    n_f = DECIMALS.get(units, 2)
    values = ds[variable] if absolute else change_vs_baseline(ds[variable], baseline, cfg["percent"])
    what = cfg["label"] if absolute else f"Change in {cfg['label'].lower()} vs {baseline[0]}–{baseline[1]}"
    info = {sc: scenario_info[sc] for sc in scenarios if sc in scenario_info}
    figs, tables = {}, {}

    tables["trend"] = _titled(trend_per_decade(values, scenarios).round(n_f + 2),
                              f"{cfg['label']}: linear trend 2015–2100 of the multi-model median ({units} per decade), by EEZ")
    figs["trend"] = plot_eez_panels(tables["trend"], eez, f"{cfg['label']}: linear trend 2015–2100 of the multi-model median",
                                    f"{units} per decade", cfg["cmap"], cfg["diverging"])
    save_figure(figs["trend"], fig_dir, f"{name}_trend_eez")
    save_table(tables["trend"], tables_dir, f"{name}_trend_regions")

    # Warming-level maps and tables: one per scenario, on a colour scale shared by all scenarios.
    levels = {sc: change_at_levels(values, info, sc).round(n_f + 1) for sc in scenarios if sc in info}
    levels = {sc: t for sc, t in levels.items() if not t.empty}
    limits = colour_limits(np.concatenate([t.loc[t.index.isin(eez["Country"])].values.ravel() for t in levels.values()]),
                           cfg["diverging"])
    for sc, table in levels.items():
        tables[f"levels_{sc}"] = _titled(table, f"{what} at the global warming levels ({sc.upper()}, multi-model median, {units}), by EEZ")
        figs[f"levels_{sc}"] = plot_eez_panels(table, eez, f"{what} at global warming levels ({sc.upper()}, multi-model median)",
                                               f"{'' if absolute else 'Δ '}{cfg['label']} [{units}]", cfg["cmap"], cfg["diverging"],
                                               limits=limits)
        save_figure(figs[f"levels_{sc}"], fig_dir, f"{name}_gwl_eez_{sc}")
        save_table(table, tables_dir, f"{name}_gwl_regions_{sc}")
    if f"levels_{map_scenario}" in figs:  # figure glued at the top of the notebook
        figs["levels"] = figs[f"levels_{map_scenario}"]

    figs.update(_region_boxplots(values, regions, info, scenarios, n_f, f"{'' if absolute else 'Δ '}{cfg['label']} [{units}]",
                                 fig_dir, name))

    tables["regions"] = _titled(region_summary(values, info, scenarios, decimals=n_f + 1, regions=regions),
                                f"{what} at the global warming levels ({units}): spread across models in {', '.join(regions)}")
    region_tag = "ocean_regions" if tuple(regions) == BIOCHEM_REGIONS else "all_eez"
    save_table(tables["regions"], tables_dir, f"{name}_gwl_{region_tag}", index=False)
    return figs, tables


def _region_boxplots(values, regions, info, scenarios, n_f, ylabel, fig_dir, name):
    """Box plots across models at the global warming levels, one figure per region: {key: figure}."""
    from ind_setup.plotting_projections import get_box_data, plot_global_warming_boxplot

    figs = {}
    ds_values = values.to_dataset(name="value")
    levels = list(prj.WARMING_LEVELS)
    for region in regions:
        ds_region = ds_values.sel(region=region)
        box_data, box_scenarios, positions = get_box_data(ds_region, info, levels, scenarios, "value")
        if not box_data:
            continue
        fig, _ = plot_global_warming_boxplot(box_data, ds_region, positions, box_scenarios, info, levels, "value",
                                             plot_ref=False, n_f=n_f, site_label=region, ylabel=ylabel)
        figs[f"box_{_slug(region)}"] = fig
        save_figure(fig, fig_dir, f"{name}_gwl_{_slug(region)}")
    return figs


def biochem_indicator_report(ds, grid, variable, scenario_info, eez, scenarios, map_scenario, fig_dir, tables_dir,
                             name=None, baseline=("2015", "2035")):
    """Biochemical indicator with model spread (e.g. Atlas pH): gridded maps over the Pacific window,
    and trends, tables and box plots over the four ocean regions.

    ``ds`` holds the regional means (``extract_atlas_ph_regional``), ``grid`` the gridded annual
    fields (``extract_atlas_ph_grid``). Returns ``{figure key: figure}`` and ``{table key: DataFrame}``.
    """
    cfg = INDICATORS[variable]
    name = name or variable
    units = cfg["units"]
    n_f = DECIMALS.get(units, 2)
    regions = list(BIOCHEM_REGIONS)
    values = change_vs_baseline(ds[variable].sel(region=regions), baseline, cfg["percent"])
    grid_change = change_vs_baseline(grid[variable], baseline, cfg["percent"])
    what = f"Δ {cfg['label']} vs {baseline[0]}–{baseline[1]}"
    info = {sc: scenario_info[sc] for sc in scenarios if sc in scenario_info}
    figs, tables = {}, {}

    trends = {sc.upper(): grid_trend_per_decade(grid_change.sel(scenario=sc).median("model")) for sc in scenarios}
    figs["trend"] = plot_grid_panels(trends, f"{cfg['label']}: linear trend 2015–2100 of the multi-model median",
                                     f"{units} per decade", cfg["cmap"], cfg["diverging"], eez=eez)
    save_figure(figs["trend"], fig_dir, f"{name}_trend_map")
    tables["trend"] = _titled(trend_per_decade(values, scenarios).round(n_f + 2),
                              f"{cfg['label']}: linear trend 2015–2100 of the multi-model median ({units} per decade), by ocean region")
    save_table(tables["trend"], tables_dir, f"{name}_trend_ocean_regions")

    # Warming-level maps: one per scenario, on a colour scale shared by all scenarios.
    at_levels = {}
    for sc in scenarios:
        fields = {}
        for level, level_info in info.get(sc, {}).items():
            year = level_info["year"]
            if prj._reached(year):
                fields[f"+{level}°C ({str(year)[:4]})"] = grid_change.sel(scenario=sc).sel(time=year, method="nearest").median("model")
        if fields:
            at_levels[sc] = fields
    limits = colour_limits(np.concatenate([f.values.ravel() for fields in at_levels.values() for f in fields.values()]),
                           cfg["diverging"])
    for sc, fields in at_levels.items():
        figs[f"levels_{sc}"] = plot_grid_panels(fields, f"{what} at global warming levels ({sc.upper()}, multi-model median)",
                                                f"Δ {cfg['label']} [{units}]", cfg["cmap"], cfg["diverging"], eez=eez, limits=limits)
        save_figure(figs[f"levels_{sc}"], fig_dir, f"{name}_gwl_map_{sc}")
    if f"levels_{map_scenario}" in figs:  # figure glued at the top of the notebook
        figs["levels"] = figs[f"levels_{map_scenario}"]

    figs.update(_region_boxplots(values, regions, info, scenarios, n_f, f"Δ {cfg['label']} [{units}]", fig_dir, name))
    tables["regions"] = _titled(region_summary(values, info, scenarios, decimals=n_f + 1, regions=regions),
                                f"{what} at the global warming levels ({units}): spread across models by ocean region")
    save_table(tables["regions"], tables_dir, f"{name}_gwl_ocean_regions", index=False)
    return figs, tables


def ocads_report(ds, variable, label, units, eez, scenarios, fig_dir, tables_dir, cmap="RdBu_r", start="2020", end="2100",
                 ds_models=None, scenario_info=None, baseline=("2020", "2030"), decimals=3):
    """Gridded change between two decades over the Pacific window, and change and decadal series in the
    four ocean regions, for an OCADS variable (median product).

    With ``ds_models`` (``extract_ocads_models_regional``) and ``scenario_info`` it also adds, in the four
    ocean regions, box plots across Earth system models at the global warming levels, the warming-level
    table and the trend of the multi-model median (see ``ocads_model_analysis``).
    """
    figs, tables = {}, {}
    grid = ocads_grid(variable, scenarios)
    grid_change = grid.sel(time=end).squeeze(drop=True) - grid.sel(time=start).squeeze(drop=True)
    figs["change"] = plot_grid_panels({sc.upper(): grid_change.sel(scenario=sc) for sc in scenarios},
                                      f"{label}: change {start}–{end} (median of Earth system models)",
                                      f"Δ {label} [{units}]", cmap, True, eez=eez)
    save_figure(figs["change"], fig_dir, f"{variable}_change_map")

    regional = ds[variable].sel(region=list(BIOCHEM_REGIONS))
    change = regional.sel(time=end).squeeze("time", drop=True) - regional.sel(time=start).squeeze("time", drop=True)
    tables["change"] = _titled(change.to_pandas().T.rename(columns=str.upper).round(4),
                               f"{label}: change {start}–{end} of the median product ({units}), by ocean region")
    save_table(tables["change"], tables_dir, f"{variable}_change_ocean_regions")

    figs["regions"] = plot_region_lines(ds, variable, scenarios, f"{label} [{units}]", f"{label} in the ocean regions (decadal median)")
    save_figure(figs["regions"], fig_dir, f"{variable}_ocean_regions")
    regions = ds[variable].sel(region=list(REGION_BOXES)).to_dataframe().reset_index()
    regions["Year"] = pd.to_datetime(regions["time"]).dt.year
    tables["regions"] = _titled(regions.pivot_table(index=["region", "Year"], columns="scenario", values=variable).round(4),
                                f"{label} by decade in the ocean regions (median product, {units})")
    save_table(tables["regions"], tables_dir, f"{variable}_ocean_regions")

    if ds_models is not None and scenario_info is not None:
        model_figs, model_tables = ocads_model_analysis(ds_models, variable, label, units, scenario_info, scenarios,
                                                        fig_dir, tables_dir, baseline, decimals)
        figs.update(model_figs)
        tables.update(model_tables)
    return figs, tables


def ocads_model_analysis(ds_models, variable, label, units, scenario_info, scenarios, fig_dir, tables_dir,
                         baseline=("2020", "2030"), decimals=3):
    """Warming-level analysis of an OCADS variable across Earth system models in the four ocean regions.

    The decadal series of every model are interpolated linearly to annual values (2020–2100), so the
    warming-level years of the other notebooks can be used, and expressed as the change relative to each
    model's ``baseline`` mean. Returns box plots ({``box_<region>``: figure}) and the tables ``trend``
    (multi-model median, per decade) and ``gwl`` (spread across models at each warming level).
    """
    regions = list(BIOCHEM_REGIONS)
    decadal = ds_models[variable].sel(region=regions)
    years = pd.date_range(str(pd.Timestamp(decadal.time.values[0]).year), str(pd.Timestamp(decadal.time.values[-1]).year), freq="YS")
    annual = decadal.interp(time=years)
    values = change_vs_baseline(annual, baseline)
    info = {sc: scenario_info[sc] for sc in scenarios if sc in scenario_info}
    ylabel = f"Δ {label} [{units}]"

    figs = _region_boxplots(values, regions, info, scenarios, decimals, ylabel, fig_dir, variable)
    tables = {"trend": _titled(trend_per_decade(values, scenarios, period=(str(years[0].year), str(years[-1].year))).round(decimals + 2),
                               f"{label}: linear trend {years[0].year}–{years[-1].year} of the multi-model median ({units} per decade), by ocean region")}
    save_table(tables["trend"], tables_dir, f"{variable}_trend_ocean_regions")
    tables["gwl"] = _titled(region_summary(values, info, scenarios, decimals=decimals + 1, regions=regions),
                            f"Δ {label} vs {baseline[0]}–{baseline[1]} at the global warming levels ({units}): spread across Earth system models by ocean region")
    save_table(tables["gwl"], tables_dir, f"{variable}_gwl_ocean_regions", index=False)
    return figs, tables


def _titled(df, title):
    """Attach a title to a report table (shown by ``show_tables``)."""
    df.attrs["title"] = title
    return df


def show_tables(tables, keys=None):
    """Display the tables of a report in the notebook, each under its title."""
    from IPython.display import Markdown, display

    for key in keys or tables:
        display(Markdown(f"**{tables[key].attrs.get('title', key)}**"))
        display(tables[key])


def save_figure(fig, fig_dir, name):
    path = Path(fig_dir) / f"PRJ_{name}_{REGIONAL_TAG}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    return path


def save_table(df, tables_dir, name, index=True):
    path = Path(tables_dir) / f"PRJ_{name}_{REGIONAL_TAG}.csv"
    df.to_csv(path, index=index)
    return path
