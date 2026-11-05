"""Per-EEZ summary tables for the regional (Pacific) notebooks.

Two flavours, both returning one row per EEZ (``Country`` field of the Pacific EEZ shapefile):

* :func:`grid_eez_summary` -- gridded fields (ERA5, OISST, Copernicus BGC, MHW metrics): the
  cosine-of-latitude weighted mean of each field over the grid-cell centres falling inside each
  EEZ, plus the number of cells used.
* :func:`station_eez_summary` -- GHCN station trends (the per-station summary tables of the
  regional air-temperature / rainfall notebooks): number of stations with a valid trend, mean
  station trend and number of stations whose trend is significant, for each indicator.

:func:`save_eez_table` writes them to ``outputs/tables/regional_<region>/`` so the product matrix
(``matrix_cc/products.js``) can list them.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

PACIFIC_EXTENT = (125, 245, -35, 45)  # lon 0-360, lat -- same as rainfall_regional.PACIFIC_EXTENT


def load_eez(eez_file: str | Path, country_col: str = "Country") -> gpd.GeoDataFrame:
    """Pacific EEZ polygons in EPSG:4326 with a ``Country`` column."""
    eez = gpd.read_file(eez_file).to_crs(4326)
    if country_col != "Country":
        eez = eez.rename(columns={country_col: "Country"})
    return eez[["Country", "geometry"]]


def _coord(da, *names):
    for name in names:
        if name in da.coords:
            return name
    raise KeyError(f"None of {names} is a coordinate of {da.name!r}: {list(da.coords)}")


def grid_eez_summary(
    fields: dict[str, "xr.DataArray"],
    eez: gpd.GeoDataFrame,
    extent: tuple[float, float, float, float] | None = PACIFIC_EXTENT,
    decimals: int = 3,
) -> pd.DataFrame:
    """Area-weighted mean of each 2-D field over every EEZ.

    ``fields`` maps the output column name (e.g. ``'Mean (°C)'``) to a 2-D DataArray on a common
    regular lat/lon grid (coordinate names ``lat``/``latitude`` and ``lon``/``longitude``, longitudes
    in either -180..180 or 0..360). ``extent`` (lon 0-360 min/max, lat min/max) crops the grid
    first so global fields stay fast; pass ``None`` to keep the whole grid.
    """
    first = next(iter(fields.values()))
    lat_name = _coord(first, "latitude", "lat")
    lon_name = _coord(first, "longitude", "lon")
    lats = first[lat_name].values
    lons = first[lon_name].values
    lons360 = np.mod(lons, 360)

    lat_idx = np.arange(lats.size)
    lon_idx = np.arange(lons.size)
    if extent is not None:
        lon_min, lon_max, lat_min, lat_max = extent
        lat_idx = lat_idx[(lats >= lat_min) & (lats <= lat_max)]
        lon_idx = lon_idx[(lons360 >= lon_min) & (lons360 <= lon_max)]

    jj, ii = np.meshgrid(lat_idx, lon_idx, indexing="ij")
    jj, ii = jj.ravel(), ii.ravel()
    lon180 = np.where(lons360[ii] > 180, lons360[ii] - 360, lons360[ii])
    points = gpd.GeoDataFrame(
        {"row": jj, "col": ii}, geometry=gpd.points_from_xy(lon180, lats[jj]), crs=4326,
    )
    joined = gpd.sjoin(points, eez[["Country", "geometry"]], predicate="within", how="inner")

    arrays = {
        name: np.asarray(da.transpose(_coord(da, "latitude", "lat"), _coord(da, "longitude", "lon")).values,
                         dtype=float)
        for name, da in fields.items()
    }
    rows = []
    for country, group in joined.groupby("Country"):
        j, i = group["row"].to_numpy(), group["col"].to_numpy()
        w = np.cos(np.deg2rad(lats[j]))
        row = {"EEZ": country}
        valid_any = np.zeros(j.size, dtype=bool)
        for name, values in arrays.items():
            v = values[j, i]
            good = np.isfinite(v)
            valid_any |= good
            row[name] = np.average(v[good], weights=w[good]) if good.any() else np.nan
        row["Grid cells"] = int(valid_any.sum())
        rows.append(row)
    table = pd.DataFrame(rows, columns=["EEZ", *fields, "Grid cells"])
    return table.sort_values("EEZ").reset_index(drop=True).round(decimals)


def station_eez_summary(
    summary: pd.DataFrame,
    indicators: dict[str, str],
    units: dict[str, str],
    eez_col: str = "eez_country",
    decimals: int = 3,
) -> pd.DataFrame:
    """Per-EEZ aggregation of per-station trends.

    ``summary`` is the per-station table built in the regional notebooks (columns
    ``<indicator>_trend`` and ``<indicator>_significant``). For each indicator in ``indicators``
    (``{column_prefix: short label}``) the table gets the number of stations with a valid trend,
    the mean station trend (in ``units[indicator]``) and the number of significant stations.
    Stations outside every EEZ are dropped.
    """
    df = summary[summary[eez_col].notna()]
    rows = []
    for country, group in df.groupby(eez_col):
        row = {"EEZ": country, "Stations": len(group)}
        for var, label in indicators.items():
            trend = group[f"{var}_trend"]
            valid = trend.notna()
            row[f"{label}: stations with trend"] = int(valid.sum())
            row[f"{label}: mean trend ({units[var]})"] = trend[valid].mean() if valid.any() else np.nan
            row[f"{label}: significant stations"] = int(group.loc[valid, f"{var}_significant"].astype(bool).sum())
        rows.append(row)
    table = pd.DataFrame(rows)
    first_counts = [c for c in table.columns if c.endswith("stations with trend")]
    table = table[table[first_counts].sum(axis=1) > 0]  # EEZs whose stations have no usable trend
    return table.sort_values("EEZ").reset_index(drop=True).round(decimals)


def save_eez_table(table: pd.DataFrame, table_dir: str | Path, filename: str) -> Path:
    """Write ``table`` as CSV under ``table_dir`` (created if needed) and return the path."""
    path = Path(table_dir) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(path, index=False)
    print(f"Saved {len(table)} EEZ rows to {path}")
    return path
