"""IPCC AR6 sea-level projections for the regional (Pacific) CIndRA notebooks.

Source: Garner et al. (2021), *IPCC AR6 Sea Level Projections*, Zenodo record
6382554 (Fox-Kemper et al., 2021, AR6 WGI Chapter 9). The default product is
``ar6-regional_novlm-confidence``: total sea-level change **without** vertical
land motion, i.e. the ocean (absolute) contribution, comparable to satellite
altimetry. Values are relative to the 1995–2014 mean (centred on 2005).

The raw files hold every location of a global 1° grid plus the PSMSL tide
gauges. :func:`load_ar6_pacific` downloads them when missing
(``data_downloaders.download_ar6_sea_level_projections``), keeps the Pacific
window, masks land cells, converts the change to cm and caches a small
netCDF under ``data/projections/regional/``.

Map figures reuse the look of the historical regional sea-level maps
(``sea_level_plotting.plot_regional_change_map_filled_tide_gauges`` and
``plot_pacific_sl_field``).
"""

from pathlib import Path

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr

from data_downloaders import ar6_sea_level_file, download_ar6_sea_level_projections

PLATE = ccrs.PlateCarree()
SCENARIO_LABEL = {
    "ssp119": "SSP1-1.9", "ssp126": "SSP1-2.6", "ssp245": "SSP2-4.5",
    "ssp370": "SSP3-7.0", "ssp585": "SSP5-8.5",
}
SCENARIO_COLOR = {
    "ssp119": "#00adcf", "ssp126": "#173c66", "ssp245": "#f79420",
    "ssp370": "#e71d25", "ssp585": "#951b1e",
}  # IPCC AR6 SSP colours
LIKELY = (0.17, 0.83)
GRID_ID_MIN = 1_000_000_000  # AR6 location ids >= 1e9 are grid cells; smaller ids are PSMSL gauges


def ssp_label(scenario):
    return SCENARIO_LABEL.get(scenario, scenario.upper())


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def _in_window(lon360, lat, extent):
    x0, x1, y0, y1 = extent
    return (lon360 >= x0) & (lon360 <= x1) & (lat >= y0) & (lat <= y1)


def ocean_mask(lon, lat, resolution="50m"):
    """Boolean DataArray (lat, lon): True where the cell centre is not on Natural Earth land or Antarctic ice shelves."""
    import cartopy.io.shapereader as shpreader
    import shapely
    from shapely.ops import unary_union

    geoms = []
    for name in ("land", "antarctic_ice_shelves_polys"):  # ice shelves are not ocean for sea-level purposes
        geoms += list(shpreader.Reader(shpreader.natural_earth(resolution, "physical", name)).geometries())
    land = unary_union(geoms)
    lon2d, lat2d = np.meshgrid(np.asarray(lon, float), np.asarray(lat, float))
    on_land = shapely.contains_xy(land, ((lon2d + 180) % 360) - 180, lat2d)
    return xr.DataArray(~on_land, dims=("lat", "lon"), coords={"lat": lat, "lon": lon})


def _read_subset(path, var, quantiles, grid_idx, gauge_idx):
    with xr.open_dataset(path) as ds:
        da = ds[var].sel(quantiles=list(quantiles))
        grid = da.isel(locations=grid_idx).load()
        gauge = da.isel(locations=gauge_idx).load()
    return grid, gauge


def load_ar6_pacific(
    raw_dir,
    cache_file,
    scenarios=("ssp126", "ssp245", "ssp370", "ssp585"),
    extent=(125, 245, -35, 35),
    quantiles=(0.05, 0.17, 0.5, 0.83, 0.95),
    confidence="medium",
    vlm=False,
    overwrite=False,
    force_download=False,
):
    """AR6 projections for the Pacific window, cached as one small netCDF.

    Returns a Dataset with
    ``change`` (cm) and ``rate`` (mm/yr) on (scenario, quantile, year, lat, lon),
    land cells set to NaN, ``lon`` in 0–360°; and ``gauge_change`` /
    ``gauge_rate`` on (scenario, quantile, year, gauge) for the PSMSL tide
    gauges inside the window, with ``gauge_lon``/``gauge_lat``.
    The raw global files are downloaded into ``raw_dir`` when missing.
    """
    cache_file = Path(cache_file)
    if cache_file.is_file() and not overwrite and not force_download:
        cached = xr.load_dataset(cache_file)
        if set(scenarios) <= set(cached.scenario.values) and np.all(np.isin(quantiles, cached["quantile"].values)):
            return cached.sel(scenario=list(scenarios), quantile=list(quantiles))

    paths = download_ar6_sea_level_projections(
        raw_dir, scenarios, kinds=("values", "rates"), confidence=confidence, vlm=vlm, force_download=force_download,
    )

    with xr.open_dataset(paths[(scenarios[0], "values")]) as ref:
        loc = ref.locations.values
        lat = ref.lat.values.astype(float)
        lon360 = ref.lon.values.astype(float) % 360
    inside = _in_window(lon360, lat, extent)
    grid_idx = np.where(inside & (loc >= GRID_ID_MIN))[0]
    gauge_idx = np.where(inside & (loc < GRID_ID_MIN))[0]

    grid_lat, grid_lon = lat[grid_idx], lon360[grid_idx]
    lat_axis, lon_axis = np.unique(grid_lat), np.unique(grid_lon)
    iy, ix = np.searchsorted(lat_axis, grid_lat), np.searchsorted(lon_axis, grid_lon)
    mask = ocean_mask(lon_axis, lat_axis)

    def to_grid(da):
        out = np.full(da.shape[:-1] + (lat_axis.size, lon_axis.size), np.nan)
        out[..., iy, ix] = da.values
        return out

    fields = {"change": [], "rate": [], "gauge_change": [], "gauge_rate": []}
    for scenario in scenarios:
        for kind, var, name, scale in (("values", "sea_level_change", "change", 0.1),
                                       ("rates", "sea_level_change_rate", "rate", 1.0)):
            grid, gauge = _read_subset(paths[(scenario, kind)], var, quantiles, grid_idx, gauge_idx)
            years = grid.years.values
            fields[name].append(scale * to_grid(grid))
            fields[f"gauge_{name}"].append(scale * gauge.values)

    coords = {"scenario": list(scenarios), "quantile": list(quantiles), "year": years}
    grid_dims = ("scenario", "quantile", "year", "lat", "lon")
    gauge_dims = ("scenario", "quantile", "year", "gauge")
    ds = xr.Dataset(
        {
            "change": (grid_dims, np.stack(fields["change"])),
            "rate": (grid_dims, np.stack(fields["rate"])),
            "gauge_change": (gauge_dims, np.stack(fields["gauge_change"])),
            "gauge_rate": (gauge_dims, np.stack(fields["gauge_rate"])),
            "ocean": (("lat", "lon"), mask.values),
        },
        coords={**coords, "lat": lat_axis, "lon": lon_axis, "gauge": loc[gauge_idx].astype(int),
                "gauge_lat": ("gauge", lat[gauge_idx]), "gauge_lon": ("gauge", lon360[gauge_idx])},
    )
    ds["change"] = ds["change"].where(ds["ocean"])
    ds["rate"] = ds["rate"].where(ds["ocean"])
    ds["change"].attrs.update(units="cm", long_name="Sea-level change relative to 1995–2014")
    ds["rate"].attrs.update(units="mm/yr", long_name="Rate of sea-level change")
    ds["gauge_change"].attrs.update(units="cm")
    ds["gauge_rate"].attrs.update(units="mm/yr")
    ds.attrs.update(
        source="IPCC AR6 sea-level projections, Garner et al. (2021), Zenodo 10.5281/zenodo.6382554",
        product=f"{'regional' if vlm else 'regional_novlm'} total, {confidence} confidence",
        vertical_land_motion="included" if vlm else "excluded",
        reference_period="1995-2014",
        extent=list(extent),
    )
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    ds.to_netcdf(cache_file)
    return ds


def load_ar6_global_median(
    raw_dir,
    cache_file,
    scenarios=("ssp126", "ssp245", "ssp370", "ssp585"),
    confidence="medium",
    vlm=False,
    overwrite=False,
    force_download=False,
):
    """Global 1° median sea-level change (cm, 1995–2014 ref.) on (scenario, year, lat, lon), land masked.

    Used for the global context map; cached as float32 in ``cache_file``.
    """
    cache_file = Path(cache_file)
    if cache_file.is_file() and not overwrite and not force_download:
        cached = xr.load_dataset(cache_file)
        if set(scenarios) <= set(cached.scenario.values):
            return cached.sel(scenario=list(scenarios))

    paths = download_ar6_sea_level_projections(
        raw_dir, scenarios, kinds=("values",), confidence=confidence, vlm=vlm, force_download=force_download,
    )
    with xr.open_dataset(paths[(scenarios[0], "values")]) as ref:
        loc = ref.locations.values
        lat = ref.lat.values.astype(float)
        lon = ref.lon.values.astype(float) % 360
    idx = np.where(loc >= GRID_ID_MIN)[0]
    lat_axis, lon_axis = np.unique(lat[idx]), np.unique(lon[idx])
    iy, ix = np.searchsorted(lat_axis, lat[idx]), np.searchsorted(lon_axis, lon[idx])

    fields = []
    for scenario in scenarios:
        with xr.open_dataset(paths[(scenario, "values")]) as ds:
            da = ds["sea_level_change"].sel(quantiles=0.5).isel(locations=idx).load()
        years = da.years.values
        grid = np.full((years.size, lat_axis.size, lon_axis.size), np.nan, dtype="float32")
        grid[:, iy, ix] = 0.1 * da.values
        fields.append(grid)

    ocean = ocean_mask(lon_axis, lat_axis)
    out = xr.Dataset(
        {"change": (("scenario", "year", "lat", "lon"), np.stack(fields)), "ocean": (("lat", "lon"), ocean.values)},
        coords={"scenario": list(scenarios), "year": years, "lat": lat_axis, "lon": lon_axis},
    )
    out["change"] = out["change"].where(out["ocean"])
    out["change"].attrs.update(units="cm", long_name="Median sea-level change relative to 1995–2014")
    out.attrs.update(source="IPCC AR6 sea-level projections, Garner et al. (2021), Zenodo 10.5281/zenodo.6382554",
                     vertical_land_motion="included" if vlm else "excluded", quantile=0.5)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    out.to_netcdf(cache_file)
    return out


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

def area_weights(da):
    return np.cos(np.deg2rad(da.lat)).broadcast_like(da.isel({d: 0 for d in da.dims if d not in ("lat", "lon")}))


def domain_mean(da):
    """Cosine-latitude weighted mean over the ocean cells of the window."""
    w = area_weights(da).where(da.isel({d: 0 for d in da.dims if d not in ("lat", "lon")}).notnull(), 0)
    return da.weighted(w).mean(("lat", "lon"))


def fill_coast(da, cells=2):
    """Extend ocean values into up to ``cells`` masked coastal cells (for maps only; land is drawn on top)."""
    out = da
    for _ in range(cells):
        neighbours = xr.concat([out.shift(lat=1), out.shift(lat=-1), out.shift(lon=1), out.shift(lon=-1)], dim="_n")
        out = out.combine_first(neighbours.mean("_n", skipna=True))
    return out


def linear_trend(da, start=2020, end=2100):
    """OLS slope (per year) of ``da`` along ``year`` between ``start`` and ``end``."""
    sub = da.sel(year=slice(start, end))
    return sub.polyfit("year", 1)["polyfit_coefficients"].sel(degree=1, drop=True)


def region_table(ds, eez, var="change", years=(2050, 2100), decimals=1):
    """Mean of ``var`` over each Pacific EEZ and ocean region (rows) for every scenario, year and quantile.

    Returns a long DataFrame (Region, Scenario, Year, quantile columns). The
    quantiles are averaged cell by cell, which approximates — but is not
    identical to — the quantiles of the area mean.
    """
    import projections_regional as reg

    weights = reg.region_weights(ds.lon.values, ds.lat.values, eez)
    names = reg.region_names(eez)
    rows = []
    for scenario in ds.scenario.values:
        for year in years:
            field = ds[var].sel(scenario=scenario, year=year)
            values = field.values.reshape(field.sizes["quantile"], -1)
            means = reg._weighted_means(values, weights)  # (quantile, region)
            for k, name in enumerate(names):
                row = {"Region": name, "Scenario": ssp_label(scenario), "Year": int(year)}
                row.update({f"q{q:g}": round(float(means[j, k]), decimals) for j, q in enumerate(ds["quantile"].values)})
                rows.append(row)
    return pd.DataFrame(rows)


def likely_range_table(table, year, median="q0.5", low="q0.17", high="q0.83"):
    """Region × scenario table of 'median (low–high)' strings for one year."""
    sub = table[table["Year"] == year].copy()
    sub["value"] = sub.apply(lambda r: f"{r[median]:.0f} ({r[low]:.0f}–{r[high]:.0f})", axis=1)
    out = sub.pivot(index="Region", columns="Scenario", values="value")
    return out.reindex(index=list(dict.fromkeys(sub["Region"])))


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------

def plot_projection_map(
    field,
    pacific,
    title,
    label,
    cmap="RdBu_r",
    vmin=None,
    vmax=None,
    gauges=None,
    gauge_col=None,
    annotation=None,
    contour_levels=None,
    gauge_label="AR6 projection at tide gauge",
    filename=None,
):
    """Pacific map in the style of the historical regional change map.

    Background: gridded projection (``field`` with ``lon``/``lat`` in 0–360°).
    Circles: projection at the AR6/PSMSL tide-gauge locations on the same
    colour scale (``gauges`` DataFrame with ``lon``, ``lat`` and ``gauge_col``).
    ``annotation`` is written in a box at the lower left (e.g. the domain mean).
    """
    projection = ccrs.PlateCarree(central_longitude=180)
    fig, ax = plt.subplots(figsize=(14, 8.5), subplot_kw={"projection": projection})
    field = fill_coast(field)
    mesh = ax.pcolormesh(field.lon, field.lat, field, transform=PLATE, shading="nearest", cmap=cmap,
                         vmin=vmin, vmax=vmax, zorder=1)
    if contour_levels:
        cs = ax.contour(field.lon, field.lat, field, levels=contour_levels, colors="0.25", linewidths=0.6,
                        transform=PLATE, zorder=2)
        ax.clabel(cs, inline=True, fontsize=8, fmt="%g")
    ax.set_extent(pacific.extent, crs=PLATE)
    ax.add_feature(cfeature.LAND, facecolor="0.72", edgecolor="0.3", linewidth=0.4, zorder=3)
    pacific.eez.boundary.plot(ax=ax, transform=PLATE, color="0.35", linewidth=0.4, alpha=0.6, zorder=4)
    gl = ax.gridlines(draw_labels=True, linewidth=0.4, color="0.6", alpha=0.6)
    gl.top_labels = gl.right_labels = False
    ax.set_title(title, fontsize=16, fontweight="bold")

    if gauges is not None and len(gauges):
        ax.scatter(gauges["lon"], gauges["lat"], c=gauges[gauge_col], cmap=cmap, vmin=vmin, vmax=vmax, s=110,
                   edgecolor="k", linewidth=1.0, transform=PLATE, zorder=7, label=gauge_label)
        ax.legend(loc="upper right", fontsize=11, framealpha=0.9).set_zorder(10)
    if annotation:
        ax.text(0.02, 0.04, annotation, transform=ax.transAxes, ha="left", va="bottom", fontsize=12, zorder=8,
                bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="0.4", alpha=0.9))

    cbar = fig.colorbar(mesh, ax=ax, orientation="horizontal", pad=0.07, fraction=0.05, shrink=0.75, extend="both")
    cbar.set_label(label)
    if filename:
        fig.savefig(filename, dpi=200, bbox_inches="tight")
    return fig, ax


def plot_domain_mean_series(mean, title, ylabel, end_year=2150, likely=LIKELY):
    """Median and likely range (17–83 %) of the domain mean for every scenario."""
    fig, ax = plt.subplots(figsize=(11, 6))
    sub = mean.sel(year=slice(None, end_year))
    for scenario in sub.scenario.values:
        s = sub.sel(scenario=scenario)
        color = SCENARIO_COLOR.get(str(scenario), None)
        ax.fill_between(s.year, s.sel(quantile=likely[0]), s.sel(quantile=likely[1]), color=color, alpha=0.15, lw=0)
        ax.plot(s.year, s.sel(quantile=0.5), "-o", ms=4, color=color, lw=2, label=ssp_label(str(scenario)))
    ax.set_xlabel("Year")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(alpha=0.3)
    ax.legend(title="Median (shading: 17–83 % likely range)", loc="upper left", fontsize=11, title_fontsize=11)
    return fig, ax


def plot_global_context_map(
    field,
    extent,
    title,
    label,
    cmap="RdBu_r",
    vmin=None,
    vmax=None,
    annotation=None,
    box_label="Regional analysis window",
    filename=None,
):
    """Global map (Robinson, centred on the Pacific) with the regional analysis window outlined."""
    projection = ccrs.Robinson(central_longitude=180)
    fig, ax = plt.subplots(figsize=(14, 7.5), subplot_kw={"projection": projection})
    ax.set_global()
    field = fill_coast(field)
    mesh = ax.pcolormesh(field.lon, field.lat, field, transform=PLATE, shading="nearest", cmap=cmap,
                         vmin=vmin, vmax=vmax, zorder=1)
    ax.add_feature(cfeature.LAND, facecolor="0.72", edgecolor="0.3", linewidth=0.3, zorder=3)
    ax.coastlines(linewidth=0.3, zorder=4)
    gl = ax.gridlines(draw_labels=True, linewidth=0.4, color="0.6", alpha=0.6)
    gl.top_labels = gl.right_labels = False

    x0, x1, y0, y1 = extent
    n = 200
    box_lon = np.r_[np.linspace(x0, x1, n), np.full(n, x1), np.linspace(x1, x0, n), np.full(n, x0)]
    box_lat = np.r_[np.full(n, y0), np.linspace(y0, y1, n), np.full(n, y1), np.linspace(y1, y0, n)]
    ax.plot(box_lon, box_lat, color="k", linewidth=2.2, transform=PLATE, zorder=6)
    ax.text(x0 + 1.5, y1 + 2, box_label, transform=PLATE, fontsize=12, fontweight="bold", ha="left", va="bottom",
            zorder=7, bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="none", alpha=0.8))
    ax.set_title(title, fontsize=16, fontweight="bold")
    if annotation:
        ax.text(0.01, 0.02, annotation, transform=ax.transAxes, ha="left", va="bottom", fontsize=11, zorder=8,
                bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="0.4", alpha=0.9))
    cbar = fig.colorbar(mesh, ax=ax, orientation="horizontal", pad=0.06, fraction=0.05, shrink=0.75, extend="both")
    cbar.set_label(label)
    if filename:
        fig.savefig(filename, dpi=200, bbox_inches="tight")
    return fig, ax


# Colour scales of the historical regional sea-level maps (notebooks/historical/Regional/sea_level), reused by the
# projection maps so historical and projected maps read the same way: trends and rates on RdYlBu_r from 0 (0–8 mm/yr in
# the historical map), absolute changes on RdBu_r centred on 0 (±25 cm in the historical map). The projection scales
# keep these limits and widen only when the projected values exceed them.
TREND_CMAP, TREND_HIST_MAX = "RdYlBu_r", 8      # mm/yr
CHANGE_CMAP, CHANGE_HIST_MAX = "RdBu_r", 25     # cm


def trend_scale(*values, step=1):
    """(vmin, vmax) for trend/rate maps: 0 to the larger of the historical 8 mm/yr and the data maximum (rounded up)."""
    hi = max(float(np.nanmax(np.asarray(v, dtype=float))) for v in values)
    return 0, max(TREND_HIST_MAX, float(np.ceil(hi / step) * step))


def change_scale(*values, step=5):
    """(vmin, vmax) for absolute-change maps: symmetric around 0, at least the historical ±25 cm (rounded up)."""
    hi = max(float(np.nanmax(np.abs(np.asarray(v, dtype=float)))) for v in values)
    lim = max(CHANGE_HIST_MAX, float(np.ceil(hi / step) * step))
    return -lim, lim


def colour_limits(da, step):
    """Colour range from the data minimum to its maximum, rounded outwards to ``step``, and contour levels inside it."""
    lo = np.floor(float(da.min()) / step) * step
    hi = np.ceil(float(da.max()) / step) * step
    return lo, hi, tuple(np.round(np.arange(lo + step, hi, step), 6))


def plot_projection_grid(
    fields,
    pacific,
    title,
    label,
    cmap="afmhot_r",
    vmin=None,
    vmax=None,
    contour_levels=None,
    gauges=None,
    gauge_values=None,
    gauge_label="Tide gauge, relative (with VLM)",
    annotations=None,
    ncols=2,
    filename=None,
):
    """Grid of Pacific maps (one per entry of ``fields``) in the style of :func:`plot_projection_map`.

    ``fields`` maps a panel title to a 2-D field (``lon``/``lat`` in 0–360°). Optional ``gauges``
    (DataFrame with ``lon``/``lat``) are drawn on every panel coloured by ``gauge_values[panel]``;
    ``annotations[panel]`` is written in a box at the lower left. One shared colour bar.
    """
    import math

    panels = list(fields)
    nrows = math.ceil(len(panels) / ncols)
    projection = ccrs.PlateCarree(central_longitude=180)
    fig, axes = plt.subplots(nrows, ncols, figsize=(8.2 * ncols, 5.0 * nrows + 0.8), squeeze=False,
                             subplot_kw={"projection": projection})
    for ax, panel in zip(axes.flat, panels):
        field = fill_coast(fields[panel])
        mesh = ax.pcolormesh(field.lon, field.lat, field, transform=PLATE, shading="nearest", cmap=cmap,
                             vmin=vmin, vmax=vmax, zorder=1)
        if contour_levels:
            cs = ax.contour(field.lon, field.lat, field, levels=contour_levels, colors="0.25", linewidths=0.55,
                            transform=PLATE, zorder=2)
            ax.clabel(cs, inline=True, fontsize=7, fmt="%g")
        ax.set_extent(pacific.extent, crs=PLATE)
        ax.add_feature(cfeature.LAND, facecolor="0.72", edgecolor="0.3", linewidth=0.4, zorder=3)
        pacific.eez.boundary.plot(ax=ax, transform=PLATE, color="0.35", linewidth=0.4, alpha=0.6, zorder=4)
        gl = ax.gridlines(draw_labels=True, linewidth=0.35, color="0.6", alpha=0.6)
        gl.top_labels = gl.right_labels = False
        ax.set_title(panel, fontsize=14, fontweight="bold")
        if gauges is not None and gauge_values is not None:
            ax.scatter(gauges["lon"], gauges["lat"], c=gauge_values[panel], cmap=cmap, vmin=vmin, vmax=vmax, s=60,
                       edgecolor="k", linewidth=0.8, transform=PLATE, zorder=7, label=gauge_label)
        if annotations and panel in annotations:
            ax.text(0.02, 0.04, annotations[panel], transform=ax.transAxes, ha="left", va="bottom", fontsize=10, zorder=8,
                    bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="0.4", alpha=0.9))
    for ax in axes.flat[len(panels):]:
        ax.remove()
    if gauges is not None and gauge_values is not None:
        axes.flat[0].legend(loc="upper right", fontsize=9, framealpha=0.9).set_zorder(10)
    fig.subplots_adjust(left=0.05, right=0.9, bottom=0.06, top=0.91, wspace=0.1, hspace=0.18)
    fig.suptitle(title, y=0.975, fontsize=15, fontweight="bold")
    cbar = fig.colorbar(mesh, ax=list(axes.flat[: len(panels)]), fraction=0.025, pad=0.03, aspect=35, extend="both")
    cbar.set_label(label)
    if filename:
        fig.savefig(filename, dpi=150, bbox_inches="tight")
    return fig


def plot_global_context_grid(fields, extent, title, label, cmap="afmhot_r", vmin=None, vmax=None, annotations=None,
                             box_label="Regional analysis window", ncols=2, filename=None):
    """Grid of global maps (Robinson, centred on the Pacific) with the regional window outlined."""
    import math

    panels = list(fields)
    nrows = math.ceil(len(panels) / ncols)
    projection = ccrs.Robinson(central_longitude=180)
    fig, axes = plt.subplots(nrows, ncols, figsize=(8.5 * ncols, 4.8 * nrows + 0.8), squeeze=False,
                             subplot_kw={"projection": projection})
    x0, x1, y0, y1 = extent
    n = 200
    box_lon = np.r_[np.linspace(x0, x1, n), np.full(n, x1), np.linspace(x1, x0, n), np.full(n, x0)]
    box_lat = np.r_[np.full(n, y0), np.linspace(y0, y1, n), np.full(n, y1), np.linspace(y1, y0, n)]
    for ax, panel in zip(axes.flat, panels):
        ax.set_global()
        field = fill_coast(fields[panel])
        mesh = ax.pcolormesh(field.lon, field.lat, field, transform=PLATE, shading="nearest", cmap=cmap,
                             vmin=vmin, vmax=vmax, zorder=1)
        ax.add_feature(cfeature.LAND, facecolor="0.72", edgecolor="0.3", linewidth=0.3, zorder=3)
        ax.coastlines(linewidth=0.3, zorder=4)
        ax.gridlines(linewidth=0.4, color="0.6", alpha=0.6)
        ax.plot(box_lon, box_lat, color="k", linewidth=1.8, transform=PLATE, zorder=6)
        ax.text(x0 + 1.5, y1 + 2, box_label, transform=PLATE, fontsize=9, fontweight="bold", ha="left", va="bottom",
                zorder=7, bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor="none", alpha=0.8))
        ax.set_title(panel, fontsize=14, fontweight="bold")
        if annotations and panel in annotations:
            ax.text(0.5, -0.06, annotations[panel], transform=ax.transAxes, ha="center", va="top", fontsize=10)
    for ax in axes.flat[len(panels):]:
        ax.remove()
    fig.subplots_adjust(left=0.03, right=0.9, bottom=0.05, top=0.9, wspace=0.06, hspace=0.25)
    fig.suptitle(title, y=0.975, fontsize=15, fontweight="bold")
    cbar = fig.colorbar(mesh, ax=list(axes.flat[: len(panels)]), fraction=0.025, pad=0.03, aspect=35, extend="both")
    cbar.set_label(label)
    if filename:
        fig.savefig(filename, dpi=150, bbox_inches="tight")
    return fig


def region_change(ds, eez, var="change"):
    """Cos(latitude)-weighted mean of ``var`` over every Pacific EEZ and ocean region, for every scenario,
    quantile and year: DataArray (region, scenario, quantile, year). Quantiles are averaged cell by cell."""
    import projections_regional as reg

    weights = reg.region_weights(ds.lon.values, ds.lat.values, eez)
    names = reg.region_names(eez)
    da = ds[var]
    values = da.transpose("scenario", "quantile", "year", "lat", "lon").values
    flat = values.reshape(-1, values.shape[-2] * values.shape[-1])
    means = reg._weighted_means(flat, weights).reshape(values.shape[:3] + (len(names),))
    return xr.DataArray(np.moveaxis(means, -1, 0), dims=("region", "scenario", "quantile", "year"),
                        coords={"region": names, "scenario": da.scenario.values, "quantile": da["quantile"].values,
                                "year": da.year.values})
