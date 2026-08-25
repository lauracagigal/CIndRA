"""Utilities for national sea-surface-temperature analyses."""

from dataclasses import dataclass
import math
from pathlib import Path
import unicodedata

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.path import Path as MplPath
import numpy as np
import pandas as pd
import xarray as xr


@dataclass(frozen=True)
class SSTRegion:
    """SST data and spatial metadata clipped to one EEZ."""

    country_name: str
    eez: gpd.GeoDataFrame
    geometry: object
    lon_range: tuple[float, float]
    lat_range: tuple[float, float]
    representative_lon: float
    representative_lat: float
    data_raw: xr.Dataset
    data: xr.Dataset
    mask: xr.DataArray


@dataclass(frozen=True)
class PacificSST:
    """Regional SST data and Pacific EEZ boundaries in a common map window."""

    data_raw: xr.Dataset
    data: xr.Dataset
    eez: gpd.GeoDataFrame
    extent: tuple[float, float, float, float]


def normalise_name(value):
    """Return a case- and accent-insensitive name for matching."""
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    return " ".join(text.casefold().replace("_", " ").split())


def polygon_mask(geometry, lon, lat):
    """Return a grid-cell-centre mask for a polygon or multipolygon."""
    xx, yy = np.meshgrid(np.asarray(lon), np.asarray(lat))
    points = np.column_stack([xx.ravel(), yy.ravel()])
    mask = np.zeros(len(points), dtype=bool)
    polygons = list(geometry.geoms) if geometry.geom_type == "MultiPolygon" else [geometry]

    for polygon in polygons:
        inside = MplPath(np.asarray(polygon.exterior.coords)).contains_points(points)
        for hole in polygon.interiors:
            inside &= ~MplPath(np.asarray(hole.coords)).contains_points(points)
        mask |= inside

    return xr.DataArray(
        mask.reshape(xx.shape),
        coords={"lat": lat, "lon": lon},
        dims=("lat", "lon"),
    )


def resolve_eez_sst(
    country,
    eez_file,
    sst_file,
    dataset_id="sst",
    map_padding_degrees=0.5,
):
    """Resolve a country's EEZ, validate SST coverage, and mask the dataset."""
    eezs = gpd.read_file(eez_file).to_crs(4326)
    target = normalise_name(country)
    normalised_countries = eezs["Country"].map(normalise_name)
    matches = eezs[normalised_countries == target].copy()

    if matches.empty:
        suggestions = sorted(
            eezs.loc[
                normalised_countries.str.contains(target, regex=False), "Country"
            ].unique()
        )
        raise ValueError(f"No exact EEZ match for {country!r}. Suggestions: {suggestions}")

    country_name = str(matches["Country"].iloc[0])
    eez = matches.dissolve(by="Country").reset_index()
    geometry = eez.geometry.iloc[0]
    xmin, ymin, xmax, ymax = geometry.bounds
    lon_range = (xmin - map_padding_degrees, xmax + map_padding_degrees)
    lat_range = (ymin - map_padding_degrees, ymax + map_padding_degrees)
    representative_lon, representative_lat = geometry.representative_point().coords[0]

    data_raw = xr.open_dataset(sst_file)
    required = {dataset_id, "time", "lat", "lon"}
    missing = required.difference(set(data_raw.variables) | set(data_raw.coords))
    if missing:
        data_raw.close()
        raise KeyError(f"Missing variables/coordinates: {sorted(missing)}")

    data_raw = data_raw.assign_coords(
        lon=((data_raw.lon + 180) % 360) - 180
    ).sortby("lon")
    data_bbox = data_raw.sel(lon=slice(xmin, xmax), lat=slice(ymin, ymax))
    if data_bbox.lon.size == 0 or data_bbox.lat.size == 0:
        coverage = (
            f"lon {float(data_raw.lon.min()):.3f}..{float(data_raw.lon.max()):.3f}, "
            f"lat {float(data_raw.lat.min()):.3f}..{float(data_raw.lat.max()):.3f}"
        )
        data_raw.close()
        raise ValueError(
            f"{Path(sst_file).name} does not overlap the {country_name} EEZ. "
            f"SST coverage: {coverage}. Select a broader/country-specific NetCDF."
        )

    mask = polygon_mask(geometry, data_bbox.lon, data_bbox.lat)
    if not bool(mask.any()):
        data_raw.close()
        raise ValueError(f"No SST grid-cell centres fall inside the {country_name} EEZ.")

    return SSTRegion(
        country_name=country_name,
        eez=eez,
        geometry=geometry,
        lon_range=lon_range,
        lat_range=lat_range,
        representative_lon=representative_lon,
        representative_lat=representative_lat,
        data_raw=data_raw,
        data=data_bbox.where(mask),
        mask=mask,
    )


def load_pacific_sst(
    sst_file,
    eez_file,
    dataset_id="sst",
    extent=(125.0, 245.0, -35.0, 35.0),
):
    """Load SST over the Pacific map window together with every Pacific EEZ."""
    sst_file = Path(sst_file)
    if not sst_file.is_file():
        raise FileNotFoundError(
            f"SST file not found: {sst_file}. Check the configured NetCDF path."
        )

    data_raw = xr.open_dataset(sst_file)
    required = {dataset_id, "time", "lat", "lon"}
    missing = required.difference(set(data_raw.variables) | set(data_raw.coords))
    if missing:
        data_raw.close()
        raise KeyError(f"Missing variables/coordinates: {sorted(missing)}")

    west, east, south, north = extent
    data_raw = data_raw.assign_coords(lon=data_raw.lon % 360).sortby("lon")
    lat_slice = slice(south, north) if data_raw.lat[0] < data_raw.lat[-1] else slice(north, south)
    data = data_raw.sel(lon=slice(west, east), lat=lat_slice)
    if data.lon.size == 0 or data.lat.size == 0:
        data_raw.close()
        raise ValueError(f"{sst_file.name} does not overlap the requested Pacific extent {extent}.")

    eez = gpd.read_file(eez_file).to_crs(4326)
    return PacificSST(data_raw=data_raw, data=data, eez=eez, extent=tuple(extent))


def compute_sst_trend(data, dataset_id="sst", period=(1982, 2020)):
    """Compute the linear trend of annual mean SST in °C per decade."""
    start, end = period
    field = data[dataset_id].sel(time=slice(str(start), str(end)))
    annual = field.resample(time="YS").mean()
    annual = annual.where(annual.notnull().any(("lat", "lon")), drop=True)
    if annual.time.size < 2:
        raise ValueError(f"At least two annual SST fields are required during {start}–{end}.")
    year = xr.DataArray(
        annual.time.dt.year.astype(float), coords={"time": annual.time}, dims="time"
    )
    trend = xr.cov(annual, year, dim="time") / year.var("time") * 10
    trend.name = "sst_trend"
    trend.attrs.update(units="°C/decade", period=f"{start}–{end}")
    return trend


def compute_djf_decadal_anomalies(
    data,
    dataset_id="sst",
    decades=range(1980, 2021, 10),
    reference_period=(1981, 2020),
    analysis_end=2020,
):
    """Compute mean DJF SST anomalies for each requested decade."""
    monthly = data[dataset_id].resample(time="MS").mean()
    winter_months = monthly.where(monthly.time.dt.month.isin([12, 1, 2]), drop=True)
    djf = winter_months.resample(time="QS-DEC").mean()
    month_count = winter_months.time.resample(time="QS-DEC").count()
    djf = djf.where(month_count == 3, drop=True)
    djf = djf.where(djf.time.dt.month == 12, drop=True)
    season_year = djf.time.dt.year + 1

    ref_start, ref_end = reference_period
    reference = djf.where(
        (season_year >= ref_start) & (season_year <= ref_end), drop=True
    ).mean("time")

    fields = []
    labels = []
    for decade in decades:
        decade_end = min(int(decade) + 9, int(analysis_end))
        selected = djf.where(
            (season_year >= int(decade)) & (season_year <= decade_end), drop=True
        )
        if selected.time.size == 0:
            continue
        fields.append(selected.mean("time") - reference)
        labels.append(f"{decade}s" if decade_end > int(decade) else str(decade))

    if not fields:
        raise ValueError("No complete DJF seasons occur in the requested decades.")
    anomalies = xr.concat(fields, dim=pd.Index(labels, name="decade"))
    anomalies.name = "sst_djf_anomaly"
    anomalies.attrs.update(
        units="°C",
        reference_period=f"DJF {ref_start}–{ref_end}",
    )
    return anomalies


def compute_djf_period_anomalies(
    data,
    dataset_id="sst",
    period_starts=range(1980, 2025, 5),
    period_years=5,
    reference_period=(1981, 2020),
    require_complete=True,
):
    """Compute DJF anomalies for equal-length, non-overlapping year blocks.

    A label such as ``2020–2025`` denotes the half-open interval
    ``[2020, 2025)`` and therefore contains five DJF seasons (2020–2024).
    """
    monthly = data[dataset_id].resample(time="MS").mean()
    winter_months = monthly.where(monthly.time.dt.month.isin([12, 1, 2]), drop=True)
    djf = winter_months.resample(time="QS-DEC").mean()
    month_count = winter_months.time.resample(time="QS-DEC").count()
    djf = djf.where(month_count == 3, drop=True)
    djf = djf.where(djf.time.dt.month == 12, drop=True)
    season_year = djf.time.dt.year + 1

    ref_start, ref_end = reference_period
    reference = djf.where(
        (season_year >= ref_start) & (season_year <= ref_end), drop=True
    ).mean("time")

    fields = []
    labels = []
    for start in period_starts:
        start = int(start)
        stop = start + int(period_years)
        selected = djf.where((season_year >= start) & (season_year < stop), drop=True)
        years_found = np.unique((selected.time.dt.year + 1).values)
        if require_complete and len(years_found) != period_years:
            expected = list(range(start, stop))
            raise ValueError(
                f"DJF block {start}–{stop} requires seasons {expected}, but the "
                f"dataset contains {years_found.tolist()}. Use a source updated "
                f"through at least February {stop - 1}."
            )
        if selected.time.size == 0:
            continue
        fields.append(selected.mean("time") - reference)
        labels.append(f"{start}–{stop}")

    if not fields:
        raise ValueError("No complete DJF seasons occur in the requested periods.")
    anomalies = xr.concat(fields, dim=pd.Index(labels, name="period"))
    anomalies.name = "sst_djf_anomaly"
    anomalies.attrs.update(
        units="°C",
        reference_period=f"DJF {ref_start}–{ref_end}",
        period_years=int(period_years),
    )
    return anomalies


def _setup_pacific_sst_map(ax, pacific, title=None):
    """Apply the regional Pacific extent, land, grid and EEZ outlines."""
    projection = ccrs.PlateCarree()
    ax.set_extent(pacific.extent, crs=projection)
    ax.add_feature(cfeature.LAND, facecolor="0.88", edgecolor="0.35", linewidth=0.4, zorder=3)
    ax.coastlines(linewidth=0.4, zorder=4)
    pacific.eez.boundary.plot(
        ax=ax, transform=projection, color="0.25", linewidth=0.65, zorder=5
    )
    gl = ax.gridlines(draw_labels=True, linewidth=0.35, color="gray", alpha=0.55)
    gl.top_labels = gl.right_labels = False
    if title is not None:
        ax.set_title(str(title), fontsize=11)


def plot_pacific_sst_field(
    field,
    pacific,
    title,
    cmap="RdBu_r",
    vmin=None,
    vmax=None,
    label="SST (°C)",
    filename=None,
):
    """Plot one regional SST field with all Pacific EEZ boundaries."""
    projection = ccrs.PlateCarree(central_longitude=180)
    fig, ax = plt.subplots(figsize=(14, 7.5), subplot_kw={"projection": projection})
    im = ax.pcolormesh(
        field.lon,
        field.lat,
        field,
        transform=ccrs.PlateCarree(),
        shading="auto",
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        zorder=1,
    )
    _setup_pacific_sst_map(ax, pacific, title)
    cbar = fig.colorbar(im, ax=ax, orientation="horizontal", pad=0.08, shrink=0.78, aspect=40)
    cbar.set_label(label)
    if filename:
        fig.savefig(filename, dpi=300, bbox_inches="tight")
    return fig, ax


def plot_pacific_sst_panels(
    array,
    pacific,
    title,
    dim="decade",
    cmap="RdBu_r",
    vmin=-0.5,
    vmax=0.5,
    label="SST anomaly (°C)",
    ncols=2,
    contour_levels=(-0.3, -0.1, 0.0, 0.1, 0.3),
    filename=None,
):
    """Plot regional SST fields as panels with one shared colour bar."""
    values = array[dim].values
    ncols = min(ncols, len(values))
    nrows = math.ceil(len(values) / ncols)
    projection = ccrs.PlateCarree(central_longitude=180)
    fig, axes = plt.subplots(
        nrows,
        ncols,
        figsize=(7.1 * ncols, 4.3 * nrows + 0.6),
        squeeze=False,
        subplot_kw={"projection": projection},
    )
    for ax, value in zip(axes.flat, values):
        field = array.sel({dim: value})
        im = ax.pcolormesh(
            field.lon,
            field.lat,
            field,
            transform=ccrs.PlateCarree(),
            shading="auto",
            cmap=cmap,
            vmin=vmin,
            vmax=vmax,
            zorder=1,
        )
        if contour_levels:
            contours = ax.contour(
                field.lon,
                field.lat,
                field,
                levels=contour_levels,
                colors="0.25",
                linewidths=0.55,
                transform=ccrs.PlateCarree(),
                zorder=2,
            )
            ax.clabel(contours, inline=True, fontsize=7, fmt="%g")
        _setup_pacific_sst_map(ax, pacific, value)
    for ax in axes.flat[len(values) :]:
        ax.remove()

    fig.subplots_adjust(left=0.05, right=0.91, bottom=0.09, top=0.91, wspace=0.12, hspace=0.2)
    fig.suptitle(title, y=0.975, fontsize=14)
    cbar = fig.colorbar(
        im, ax=list(axes.flat[: len(values)]), fraction=0.025, pad=0.035, aspect=35
    )
    cbar.set_label(label)
    if filename:
        fig.savefig(filename, dpi=300, bbox_inches="tight")
    return fig


def setup_map(ax, title, region, projection=None):
    """Apply the shared SST map extent, layers, grid and title."""
    projection = projection or ccrs.PlateCarree()
    ax.set_extent([*region.lon_range, *region.lat_range], crs=projection)
    ax.add_feature(cfeature.LAND, facecolor="0.88", zorder=2)
    ax.coastlines(linewidth=0.6, zorder=3)
    region.eez.boundary.plot(
        ax=ax, color="0.2", linewidth=1.2, transform=projection, zorder=4
    )
    gl = ax.gridlines(draw_labels=True, linewidth=0.3, alpha=0.5)
    gl.top_labels = gl.right_labels = False
    ax.set_title(str(title))


def plot_map(
    field,
    title,
    cmap,
    region,
    vmin=None,
    vmax=None,
    label="SST (°C)",
    filename=None,
):
    """Plot one SST map and optionally save it."""
    projection = ccrs.PlateCarree()
    fig, ax = plt.subplots(figsize=(9, 6), subplot_kw={"projection": projection})
    im = ax.pcolormesh(
        field.lon,
        field.lat,
        field,
        transform=projection,
        shading="auto",
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
    )
    setup_map(ax, title, region, projection)
    fig.colorbar(im, ax=ax, pad=0.04, label=label)
    if filename:
        fig.savefig(filename, dpi=300, bbox_inches="tight")
    return fig, ax


def plot_panels(
    array,
    dim,
    title,
    cmap,
    region,
    vmin=None,
    vmax=None,
    label="SST (°C)",
    ncols=7,
):
    """Plot a faceted SST array with a shared colour bar."""
    values = array[dim].values
    ncols = min(ncols, len(values))
    nrows = math.ceil(len(values) / ncols)
    fig_height = 2.75 * nrows + 0.45
    projection = ccrs.PlateCarree()
    fig, axes = plt.subplots(
        nrows,
        ncols,
        figsize=(2.65 * ncols, fig_height),
        squeeze=False,
        subplot_kw={"projection": projection},
    )

    for ax, value in zip(axes.flat, values):
        field = array.sel({dim: value})
        im = ax.pcolormesh(
            field.lon,
            field.lat,
            field,
            transform=projection,
            shading="auto",
            cmap=cmap,
            vmin=vmin,
            vmax=vmax,
        )
        panel_title = pd.Timestamp(value).year if dim == "time" else value
        setup_map(ax, panel_title, region, projection)

    for ax in axes.flat[len(values) :]:
        ax.remove()

    fig.subplots_adjust(
        left=0.045,
        right=0.92,
        bottom=0.045,
        top=1 - 0.55 / fig_height,
        wspace=0.16,
        hspace=0.24,
    )
    fig.suptitle(title, y=1 - 0.04 / fig_height, fontsize=14)
    cbar = fig.colorbar(
        im,
        ax=list(axes.flat[: len(values)]),
        fraction=0.012,
        pad=0.018,
        aspect=45,
        shrink=0.88,
    )
    cbar.set_label(label, fontsize=9)
    cbar.ax.tick_params(labelsize=8, width=0.5, length=2)
    return fig
