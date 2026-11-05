"""Data access helpers for the national climate-projection notebooks.

The national projection notebooks (``notebooks/projections/National``) read the
same site configuration as the historical ones (``data/sites/<site_key>.json``)
and extract local multi-model series from these sources:

* CSIRO CMIP6 ensembles on a common 1° Pacific grid (air temperature, rainfall
  and SST), one file per scenario and variable:
  ``ensemble_<ssp>_<stem>_commongrid.nc``.
* IPCC AR6 SYR Figure SPM.4 global surface temperature (global warming levels).
* IPCC-WGI AR6 Interactive Atlas surface pH (``data_copernicus``).
* Jiang et al. (2023) surface ocean carbonate system (``bio/nc``).
* Holbrook et al. Pacific marine-heatwave statistics (``marine_heatwaves``).

Large inputs stay outside the repository. Their locations default to the
paths below and can be overridden with environment variables:

``CINDRA_CSIRO_PROJECTIONS_DIR``  CSIRO ensemble folder.
``CINDRA_EXTRA_PROJECTIONS_DIR``  Folder holding ``data_copernicus``, ``bio`` and
                                  ``marine_heatwaves``.

Extracted site series are cached under ``data/projections/<site_tag>/``.
"""

import os
import pickle
import re
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr
from matplotlib.path import Path as MplPath

from sst import normalise_name

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
PROJECTIONS_DATA_DIR = DATA_DIR / "projections"
EEZ_FILE = DATA_DIR / "regional" / "Pacific_EEZs" / "Pacific_EEZs.shp"
IPCC_FILE = PROJECTIONS_DATA_DIR / "ipcc" / "IPCC-AR6-SYR-SPM4-Panel(a)-LR-F3-3-Panel(a)(linear-graph).xlsx"
WARMING_LEVELS_FILE = PROJECTIONS_DATA_DIR / "warming_levels_ipcc_ar6.pkl"

SCENARIOS = ("ssp126", "ssp245", "ssp370", "ssp585")
WARMING_LEVELS = (1.5, 2.0, 2.5, 3.0)
SCENARIO_COLOR = {"ssp126": "green", "ssp245": "blue", "ssp370": "orange", "ssp585": "red"}

# variable -> (file stem, variable inside the file, monthly-to-annual aggregation)
CSIRO_VARIABLES = {
    "tas": ("tas_year", "tas", None),
    "tasmin": ("tasmin_year", "tasmin", None),
    "tasmax": ("tasmax_year", "tasmax", None),
    "warmdays": ("warmday_year", "warmdays", None),
    "coldnights": ("coldnights_year", "coldnights", None),
    "pr": ("pr_monthsum", "pr", "sum"),
    "yearmax": ("pr_yearmax", "pr", None),
    "dry_days": ("drydays_yearsum", "dry_days", None),
    "heavyraindays": ("heavyraindays_yearsum", "pr", None),
    "tos": ("sst_month", "tos", "mean"),
}
# Count indices use negative fill values over masked cells.
COUNT_VARIABLES = {"warmdays", "coldnights", "dry_days", "heavyraindays"}

IPCC_SCENARIO_COLUMNS = {
    "ssp126": "SSP1_2_6_Mean",
    "ssp245": "SSP2_4_5_Mean",
    "ssp370": "SSP3_7_0_Mean",
    "ssp585": "SSP5_8_5_Mean",
}
OCADS_FILE_NAMES = {"pHT": "pHT", "aragonite": "Aragonite", "salinity": "Salinity"}


# ---------------------------------------------------------------------------
# Paths and site
# ---------------------------------------------------------------------------

def csiro_dir():
    """Folder with the CSIRO ``ensemble_<ssp>_<stem>_commongrid.nc`` files."""
    default = Path.home() / "Library/CloudStorage/OneDrive-Personal/Documents-share/CC-indicators-projections-CSIRO"
    return Path(os.environ.get("CINDRA_CSIRO_PROJECTIONS_DIR", default))


def extra_dir():
    """Folder with the IPCC Atlas pH, carbonate-system and marine-heatwave inputs."""
    default = REPO_ROOT.parents[1] / "CC_indicators" / "data" / "projections"
    return Path(os.environ.get("CINDRA_EXTRA_PROJECTIONS_DIR", default))


def site_cache_dir(site_tag):
    """Return ``data/projections/<site_tag>/``, creating it if needed."""
    path = PROJECTIONS_DATA_DIR / site_tag
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_figure(fig, fig_dir, name, site_tag, dpi=150):
    """Save ``fig`` as ``<fig_dir>/PRJ_<name>_<site_tag>.png`` and return the path."""
    path = Path(fig_dir) / f"PRJ_{name}_{site_tag}.png"
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    return path


def site_eez(country, eez_file=EEZ_FILE):
    """Return the dissolved EEZ geometry of ``country`` from the Pacific EEZ shapefile."""
    eezs = gpd.read_file(eez_file).to_crs(4326)
    matches = eezs[eezs["Country"].map(normalise_name) == normalise_name(country)]
    if matches.empty:
        raise ValueError(f"No EEZ named {country!r} in {eez_file}.")
    return matches.geometry.union_all() if hasattr(matches.geometry, "union_all") else matches.geometry.unary_union


def _lon180(lon):
    return ((np.asarray(lon, dtype=float) + 180) % 360) - 180


def points_in_geometry(geometry, lon, lat):
    """Boolean array (shape of ``lon``) of points inside ``geometry`` in any longitude convention."""
    lon = np.asarray(lon, dtype=float)
    lat = np.asarray(lat, dtype=float)
    points = np.column_stack([_lon180(lon).ravel(), lat.ravel()])
    inside = np.zeros(len(points), dtype=bool)
    polygons = list(geometry.geoms) if geometry.geom_type == "MultiPolygon" else [geometry]
    for polygon in polygons:
        part = MplPath(np.asarray(polygon.exterior.coords)).contains_points(points)
        for hole in polygon.interiors:
            part &= ~MplPath(np.asarray(hole.coords)).contains_points(points)
        inside |= part
    return inside.reshape(lon.shape)


def _nearest_valid_cell(valid, lon2d, lat2d, lon, lat):
    """Flat index of the valid grid cell closest to (lon, lat), wrapping longitude."""
    dlon = (np.asarray(lon2d) - lon + 180) % 360 - 180
    dist = np.hypot(dlon * np.cos(np.deg2rad(lat)), np.asarray(lat2d) - lat)
    dist = np.where(np.asarray(valid), dist, np.inf)
    if not np.isfinite(dist).any():
        raise ValueError("No valid grid cell found.")
    return np.unravel_index(np.argmin(dist), dist.shape)


def _cached(cache_file, overwrite):
    if cache_file is not None and Path(cache_file).is_file() and not overwrite:
        return xr.load_dataset(cache_file)
    return None


def _save(ds, cache_file):
    if cache_file is not None:
        ds.to_netcdf(cache_file)
    return ds


# ---------------------------------------------------------------------------
# CSIRO CMIP6 ensembles
# ---------------------------------------------------------------------------

def _open_csiro(variable, scenario):
    stem, name, how = CSIRO_VARIABLES[variable]
    path = csiro_dir() / f"ensemble_{scenario}_{stem}_commongrid.nc"
    if not path.is_file():
        raise FileNotFoundError(f"{path} not found. Set CINDRA_CSIRO_PROJECTIONS_DIR.")
    da = xr.open_dataset(path)[name]
    if "model" not in da.coords:
        da = da.assign_coords(model=[f"model_{k:02d}" for k in range(da.sizes["model"])])
    return da, how


def _to_annual(da, how, variable):
    """Annual series indexed by ``time`` = 1 January of each year."""
    if "year" in da.dims:
        da = da.rename(year="time")
        da["time"] = pd.to_datetime([f"{int(y)}-01-01" for y in da.time.values])
    elif how == "sum":
        da = da.resample(time="YS").sum(min_count=12)
    else:
        da = da.resample(time="YS").mean()
    da = da.astype("float64")
    if variable in COUNT_VARIABLES:
        da = da.where(da >= 0)
    drop = [c for c in da.coords if c not in da.dims]
    return da.drop_vars(drop)


def extract_point(variable, lon, lat, scenarios=SCENARIOS, cache_file=None, overwrite=False):
    """Multi-model annual series of a CSIRO variable at the valid grid cell nearest to (lon, lat).

    Returns a Dataset with ``variable`` on (scenario, model, time); models missing
    from a scenario are NaN. The selected cell is stored in ``grid_lon``/``grid_lat``.
    """
    cached = _cached(cache_file, overwrite)
    if cached is not None:
        return cached

    lon360 = float(lon) % 360
    series, cell = [], None
    for scenario in scenarios:
        da, how = _open_csiro(variable, scenario)
        if cell is None:
            first = da.isel(model=0, **{da.dims[1]: 0}).notnull().values
            lon2d, lat2d = np.meshgrid(da.lon.values, da.lat.values)
            j, i = _nearest_valid_cell(first, lon2d, lat2d, lon360, float(lat))
            cell = (j, i, float(da.lat[j]), float(da.lon[i]))
        point = da.isel(lat=cell[0], lon=cell[1]).load()
        series.append(_to_annual(point, how, variable).expand_dims(scenario=[scenario]))

    ds = xr.concat(series, dim="scenario", join="outer").to_dataset(name=variable)
    ds.attrs.update(grid_lat=cell[2], grid_lon=cell[3], site_lat=float(lat), site_lon=float(lon), source=str(csiro_dir()))
    return _save(ds, cache_file)


def extract_eez_mean(variable, geometry, scenarios=SCENARIOS, cache_file=None, overwrite=False):
    """Cosine-latitude weighted mean of a CSIRO variable over the grid cells inside ``geometry``."""
    cached = _cached(cache_file, overwrite)
    if cached is not None:
        return cached

    xmin, ymin, xmax, ymax = geometry.bounds
    series, n_cells = [], None
    for scenario in scenarios:
        da, how = _open_csiro(variable, scenario)
        box = da.sel(lat=slice(ymin - 1, ymax + 1))
        lon2d, lat2d = np.meshgrid(box.lon.values, box.lat.values)
        inside = points_in_geometry(geometry, lon2d, lat2d)
        mask = xr.DataArray(inside, coords={"lat": box.lat, "lon": box.lon}, dims=("lat", "lon"))
        cols = np.where(inside.any(axis=0))[0]
        if cols.size == 0:
            raise ValueError("No grid cell of the CSIRO grid falls inside the EEZ.")
        box = box.isel(lon=slice(cols.min(), cols.max() + 1))
        mask = mask.isel(lon=slice(cols.min(), cols.max() + 1))
        weights = np.cos(np.deg2rad(box.lat)).broadcast_like(mask).where(mask, 0)
        mean = box.load().where(mask).weighted(weights).mean(("lat", "lon"))
        series.append(_to_annual(mean, how, variable).expand_dims(scenario=[scenario]))
        n_cells = int(mask.sum())

    ds = xr.concat(series, dim="scenario", join="outer").to_dataset(name=variable)
    ds.attrs.update(n_cells=n_cells, source=str(csiro_dir()))
    return _save(ds, cache_file)


def add_reference(ds, variable, ref_period=("2015", "2035")):
    """Add ``reference`` (scenario-wise multi-model mean over ``ref_period``) and ``<variable>_ref`` (% change)."""
    period = slice(*ref_period)
    ds["reference"] = ds[variable].sel(time=period).mean(("time", "model"))
    ds[f"{variable}_ref"] = (ds[variable] - ds["reference"]) / ds["reference"] * 100
    return ds


# ---------------------------------------------------------------------------
# Global warming levels (IPCC AR6)
# ---------------------------------------------------------------------------

def read_ipcc_global_temperature(xlsx=IPCC_FILE):
    """Historical and projected global surface temperature (°C vs 1850–1900) from IPCC AR6 SYR Fig. SPM.4."""
    hist = pd.read_excel(xlsx, sheet_name="Historical surface temperature ", skiprows=2)
    proj = pd.read_excel(xlsx, sheet_name="Surface temperature", skiprows=2)
    hist.columns = hist.columns.astype(str)
    return hist, proj


def crossing_year(years, values, threshold):
    """Year (linear interpolation) at which ``values`` first reaches ``threshold``; NaN if never."""
    years, values = np.asarray(years, dtype=float), np.asarray(values, dtype=float)
    for k in range(1, len(values)):
        if values[k - 1] < threshold <= values[k]:
            return years[k - 1] + (threshold - values[k - 1]) * (years[k] - years[k - 1]) / (values[k] - values[k - 1])
    return np.nan


def warming_level_years(proj, scenarios=SCENARIOS, levels=WARMING_LEVELS):
    """``{scenario: {level: {"year": datetime64 | nan, "local": level | nan}}}`` from the IPCC mean projections.

    This is the ``scenario_info`` structure expected by ``ind_setup.plotting_projections``.
    """
    info = {}
    for scenario in scenarios:
        info[scenario] = {}
        for level in levels:
            year = crossing_year(proj["Year"], proj[IPCC_SCENARIO_COLUMNS[scenario]], level)
            if np.isnan(year):
                info[scenario][level] = {"year": np.nan, "local": np.nan}
            else:
                info[scenario][level] = {"year": np.datetime64(f"{int(year)}-01-01"), "local": np.float32(level)}
    return info


def save_warming_levels(info, path=WARMING_LEVELS_FILE):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(info, f)
    return path


def load_warming_levels(scenarios=None, path=WARMING_LEVELS_FILE):
    """Load the warming-level dictionary written by ``00_warming_levels.ipynb``, optionally subset to ``scenarios``."""
    if not Path(path).is_file():
        raise FileNotFoundError(f"{path} not found. Run notebooks/projections/National/00_warming_levels.ipynb first.")
    with open(path, "rb") as f:
        info = pickle.load(f)
    return info if scenarios is None else {s: info[s] for s in scenarios if s in info}


# ---------------------------------------------------------------------------
# IPCC Atlas surface pH (CMIP6 members)
# ---------------------------------------------------------------------------

def extract_atlas_ph_point(lon, lat, scenarios=("ssp245", "ssp370", "ssp585"), cache_file=None, overwrite=False):
    """Annual-mean CMIP6 surface pH (IPCC-WGI AR6 Atlas) at the ocean cell nearest to (lon, lat)."""
    cached = _cached(cache_file, overwrite)
    if cached is not None:
        return cached

    names = {"ssp245": "ssp2_4_5", "ssp370": "ssp3_7_0", "ssp585": "ssp5_8_5"}
    series, cell = [], None
    for scenario in scenarios:
        folder = extra_dir() / "data_copernicus" / f"monthly_mean_of_acidity_of_seawater_{names[scenario]}_2015-2099"
        files = sorted(folder.glob("ph_CMIP6_*.nc"))
        if not files:
            raise FileNotFoundError(f"No ph_CMIP6_*.nc in {folder}. Set CINDRA_EXTRA_PROJECTIONS_DIR.")
        da = xr.open_dataset(files[0])["ph"]
        if cell is None:
            lon2d, lat2d = np.meshgrid(da.lon.values, da.lat.values)
            valid = da.isel(member=0, time=0).notnull().values
            cell = _nearest_valid_cell(valid, lon2d, lat2d, _lon180(lon), float(lat))
        point = da.isel(lat=cell[0], lon=cell[1]).load()
        point = point.assign_coords(member=point["gcm_model"].values).rename(member="model")
        annual = point.resample(time="YS").mean().astype("float64")
        annual = annual.drop_vars([c for c in annual.coords if c not in annual.dims])
        series.append(annual.expand_dims(scenario=[scenario]))

    ds = xr.concat(series, dim="scenario", join="outer").to_dataset(name="ph")
    ds.attrs.update(grid_lat=float(da.lat[cell[0]]), grid_lon=float(da.lon[cell[1]]))
    return _save(ds, cache_file)


# ---------------------------------------------------------------------------
# Jiang et al. (2023) surface ocean carbonate system
# ---------------------------------------------------------------------------

def open_ocads(variable, scenario, statistic="median"):
    """Decadal OCADS field (``median`` or ``std``) with a datetime ``time`` axis."""
    name = OCADS_FILE_NAMES[variable]
    path = extra_dir() / "bio" / "nc" / statistic / f"{name}_{statistic}_{scenario}.nc"
    if not path.is_file():
        raise FileNotFoundError(f"{path} not found. Set CINDRA_EXTRA_PROJECTIONS_DIR.")
    ds = xr.open_dataset(path)
    ds["time"] = pd.to_datetime([f"{int(t)}-01-01" for t in ds.time.values])
    return ds


def ocads_site(variable, scenario, lon, lat, half_width=7):
    """Point series, point std and a ±``half_width``-cell map window around the site."""
    median = open_ocads(variable, scenario, "median")
    std = open_ocads(variable, scenario, "std")
    valid = median[variable].isel(time=0).notnull().values
    j, i = _nearest_valid_cell(valid, median.longitude.values, median.latitude.values, float(lon) % 360, float(lat))
    area = median.isel(lat=slice(max(j - half_width, 0), j + half_width), lon=slice(max(i - half_width, 0), i + half_width))
    return median.isel(lat=j, lon=i), std.isel(lat=j, lon=i), area


# ---------------------------------------------------------------------------
# Marine heatwaves (Holbrook et al.)
# ---------------------------------------------------------------------------

def extract_mhw_eez(geometry, region_name, scenarios=("ssp126", "ssp585"), cache_file=None, overwrite=False):
    """EEZ-average MHW days per year and category for each CMIP6 model.

    Reads ``mhw_cats.pac_is.<model>.historical+<ssp>.<member>.nc`` (native model
    grids), averages ``mhw_cats_dpy`` and ``sst_mean`` over ocean cells whose
    centre lies in ``geometry`` (cosine-latitude weights) and returns a Dataset
    on (region, scenario, model, cat, time) as used by the MHW plotting functions.
    """
    cached = _cached(cache_file, overwrite)
    if cached is not None:
        cached["time"] = pd.to_datetime(cached.time.values)
        return cached

    folder = extra_dir() / "marine_heatwaves" / "pac_mhw_stats" / "mhw_cats"
    per_scenario = []
    for scenario in scenarios:
        files = sorted(folder.glob(f"mhw_cats.pac_is.*.historical+{scenario}.*.nc"))
        if not files:
            raise FileNotFoundError(f"No MHW files for {scenario} in {folder}. Set CINDRA_EXTRA_PROJECTIONS_DIR.")
        models, means = [], []
        for path in files:
            model = re.match(r"mhw_cats\.pac_is\.(.+)\.historical\+", path.name).group(1)
            ds = xr.open_dataset(path)[["mhw_cats_dpy", "sst_mean"]]
            lat2d, lon2d = xr.broadcast(ds["lat"], ds["lon"])
            spatial_dims = lat2d.dims
            inside = points_in_geometry(geometry, lon2d.values, lat2d.values)
            if not inside.any():
                continue
            mask = xr.DataArray(inside, dims=spatial_dims)
            weights = np.cos(np.deg2rad(lat2d)).where(mask, 0).fillna(0)
            mean = ds.where(mask).weighted(weights).mean(spatial_dims)
            mean = mean.drop_vars([c for c in mean.coords if c not in mean.dims]).load()
            models.append(model)
            means.append(mean)
        if not means:
            raise ValueError(f"No MHW grid cell falls inside the {region_name} EEZ.")
        per_scenario.append(xr.concat(means, dim="model").assign_coords(model=models).expand_dims(scenario=[scenario]))

    out = xr.concat(per_scenario, dim="scenario", join="outer").expand_dims(region=[region_name])
    out["time"] = pd.to_datetime([f"{int(t)}-01-01" for t in out.time.values])
    return _save(out, cache_file)


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

def save_table(df, tables_dir, name, site_tag, index=False):
    """Save ``df`` as ``<tables_dir>/PRJ_<name>_<site_tag>.csv`` and return the path."""
    path = Path(tables_dir) / f"PRJ_{name}_{site_tag}.csv"
    df.to_csv(path, index=index)
    return path


def _reached(year):
    return isinstance(year, np.datetime64) and not np.isnat(year)


def _spread(values):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return {"Models": 0, "Median": np.nan, "P10": np.nan, "P90": np.nan, "Min": np.nan, "Max": np.nan}
    return {"Models": values.size, "Median": np.median(values), "P10": np.percentile(values, 10),
            "P90": np.percentile(values, 90), "Min": values.min(), "Max": values.max()}


def gwl_summary(ds, variable, scenario_info, scenarios=None, decimals=2):
    """Spread across models of ``variable`` in the year each scenario reaches each warming level."""
    rows = []
    for scenario in scenarios or list(scenario_info):
        for level, info in scenario_info.get(scenario, {}).items():
            year = info["year"]
            values = ds[variable].sel(scenario=scenario).sel(time=year, method="nearest").values if _reached(year) else []
            rows.append({"Scenario": scenario.upper(), "Warming level": f"+{level}°C",
                         "Year": int(str(year)[:4]) if _reached(year) else None, **_spread(values)})
    table = pd.DataFrame(rows).round(decimals)
    table["Year"] = table["Year"].astype("Int64")
    return table


def mhw_gwl_summary(ds_mhw, scenario_info, var="mhw_cats_dpy", decimals=1):
    """Spread across models of MHW days per year in each category at each reached warming level."""
    names = {1: "Moderate", 2: "Strong", 3: "Severe", 4: "Extreme"}
    rows = []
    for scenario, levels in scenario_info.items():
        for level, info in levels.items():
            if not _reached(info["year"]):
                continue
            year_data = ds_mhw[var].isel(region=0).sel(scenario=scenario).sel(time=info["year"], method="nearest")
            for cat in ds_mhw.cat.values:
                rows.append({"Scenario": scenario.upper(), "Warming level": f"+{level}°C", "Year": int(str(info["year"])[:4]),
                             "Category": names.get(int(cat), int(cat)), **_spread(year_data.sel(cat=cat).values)})
    return pd.DataFrame(rows).round(decimals)


def ocads_table(variable, scenarios, lon, lat, decimals=3):
    """Decadal median and standard deviation of an OCADS variable at the site, one column pair per scenario."""
    columns = {}
    for scenario in scenarios:
        point, point_std, _ = ocads_site(variable, scenario, lon, lat)
        columns[f"{scenario.upper()} median"] = point[variable].to_series()
        columns[f"{scenario.upper()} std"] = point_std[variable].to_series()
    table = pd.DataFrame(columns)
    table.index = table.index.year
    table.index.name = "Year"
    return table.round(decimals)


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_fan_chart(ds, variable, scenarios, site_label, ylabel=None, baseline=("2015", "2035"), figsize=(14, 5)):
    """Multi-model fan chart of anomalies vs ``baseline``: median, 25–75 % and 10–90 % bands."""
    fig, ax = plt.subplots(figsize=figsize)
    for scenario in scenarios:
        da = ds[variable].sel(scenario=scenario)
        anom = da - da.sel(time=slice(*baseline)).mean("time")
        q = anom.quantile([0.10, 0.25, 0.50, 0.75, 0.90], dim="model")
        color = SCENARIO_COLOR[scenario]
        ax.fill_between(anom.time, q.sel(quantile=0.10), q.sel(quantile=0.90), color=color, alpha=0.10, linewidth=0)
        ax.fill_between(anom.time, q.sel(quantile=0.25), q.sel(quantile=0.75), color=color, alpha=0.15, linewidth=0)
        ax.plot(anom.time, q.sel(quantile=0.50), color=color, linewidth=1.2, label=scenario)
    ax.axhline(0, color="k", linestyle="--", linewidth=1, alpha=0.6)
    ax.set_title(f"{site_label} – anomalies vs {baseline[0]}–{baseline[1]}\nMulti-model median, 25–75 % and 10–90 % ranges")
    ax.set_xlabel("Year")
    ax.set_ylabel(ylabel or f"{variable} anomaly")
    ax.set_xlim(ds.time.min().values, ds.time.max().values)
    ax.legend(ncol=len(scenarios))
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    return fig, ax
