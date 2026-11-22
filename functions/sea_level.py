"""Sea-level calculations for the CIndRA National and Regional notebooks.

Ported from the SLIndRA repository (github.com/asgenz23/SLIndRA), which in
turn derives from the PICCM_SeaLevel workflows, and adapted to the CIndRA
conventions:

- paths are resolved from the repository root and configs live in
  ``data/sites/sea_level/<site>.json``;
- EEZ boundaries come from ``data/regional/Pacific_EEZs/Pacific_EEZs.shp``;
- tide-gauge data are UHSLC Fast Delivery files cached in ``data/sea_level``;
- satellite altimetry is the CMEMS L4 DUACS 0.125° product (daily for
  National, monthly for Regional analyses).

Units: UHSLC ``sea_level`` is in mm; CMEMS ``sla`` is in m. Functions state
the unit they return. A *storm year* runs from 1 May to 30 April and is
labelled by the calendar year in which it starts (``2015`` = May 2015 – April
2016), matching the ENSO-year convention used by :func:`detect_enso_events`.
"""

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import requests
import xarray as xr
from scipy import stats

from data_downloaders import download_oni_index, download_uhslc_data
from site_common import (  # noqa: F401  (re-exported for notebooks)
    build_output_filename,
    build_site_tag,
    save_dict_json,
    save_site_config,
)
from site_common import save_table_to_csv as _save_table_to_csv
from sst import normalise_name, polygon_mask

ONI_URL = "https://psl.noaa.gov/data/correlation/oni.data"
UHSLC_METADATA_URL = "https://uhslc.soest.hawaii.edu/data/meta.geojson"
UHSLC_DATUM_URL = (
    "https://uhslc.soest.hawaii.edu/stations/TIDES_DATUMS/fd/LST/fd{id:03d}/"
    "datumTable_{id:03d}_mm_GMT.csv"
)
CMEMS_DAILY_DATASET = "cmems_obs-sl_glo_phy-ssh_my_allsat-l4-duacs-0.125deg_P1D"
CMEMS_MONTHLY_DATASET = "cmems_obs-sl_glo_phy-ssh_my_allsat-l4-duacs-0.125deg_P1M-m"
ALTIMETRY_REFERENCE_PERIOD = ("1993-01-01", "2012-12-31")  # DUACS DT2021 SLA reference
NTDE_PERIOD = ("1983-01-01", "2001-12-31")  # US National Tidal Datum Epoch
MINOR_FLOOD_THRESHOLD_CM = 30  # cm above MHHW
COMPLETENESS_THRESHOLD = 0.75


# =========================
# Configuration and paths
# =========================
def find_repo_root(start=None):
    """Return the CIndRA root (directory holding ``functions/sea_level.py``)."""
    start = Path(start or Path.cwd()).resolve()
    for candidate in [start, *start.parents]:
        if (candidate / "functions" / "sea_level.py").is_file():
            return candidate
    raise FileNotFoundError("Could not locate the CIndRA repository root.")


def sea_level_config_path(repo_root, site_key):
    """Path of the sea-level site configuration for ``site_key``."""
    safe = "_".join("".join(ch.lower() if ch.isalnum() else " " for ch in str(site_key)).split())
    return Path(repo_root) / "data" / "sites" / "sea_level" / f"{safe}.json"


def load_site_config(config_path):
    """Load a sea-level site configuration written by ``00_sea_level_setup``."""
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(
            f"Sea-level site config not found: {config_path}. Run "
            "notebooks/historical/National/sea_level/00_sea_level_setup.ipynb first."
        )
    return pd.read_json(config_path, typ="series").to_dict()


def save_table_to_csv(table_df, output_dir, filename, index=False):
    """Save a table (default ``index=False``) and return the written path."""
    return _save_table_to_csv(table_df, output_dir, filename, index=index)


def resolve_eez(country, eez_file):
    """Return the dissolved EEZ GeoDataFrame and geometry for ``country``."""
    eezs = gpd.read_file(eez_file).to_crs(4326)
    target = normalise_name(country)
    names = eezs["Country"].map(normalise_name)
    matches = eezs[names == target]
    if matches.empty:
        suggestions = sorted(eezs.loc[names.str.contains(target.split()[0], regex=False), "Country"].unique())
        raise ValueError(f"No EEZ match for {country!r}. Suggestions: {suggestions}")
    eez = matches.dissolve(by="Country").reset_index()
    return eez, eez.geometry.iloc[0]


def eez_bounds_360(geometry):
    """EEZ bounds ``(west, east, south, north)`` in 0–360° longitude."""
    polygons = list(geometry.geoms) if geometry.geom_type == "MultiPolygon" else [geometry]
    lons = np.concatenate([np.asarray(p.exterior.coords)[:, 0] for p in polygons]) % 360
    lats = np.concatenate([np.asarray(p.exterior.coords)[:, 1] for p in polygons])
    return float(lons.min()), float(lons.max()), float(lats.min()), float(lats.max())


def eez_mask(geometry, lon, lat):
    """Grid-cell-centre EEZ mask on ``(latitude, longitude)`` for any lon convention."""
    lon_180 = ((np.asarray(lon) + 180) % 360) - 180
    mask = polygon_mask(geometry, lon_180, np.asarray(lat))
    return xr.DataArray(mask.values, coords={"latitude": lat, "longitude": lon}, dims=("latitude", "longitude"))


# =========================
# Data access
# =========================
def get_CMEMS_data(
    data_dir,
    minlon=125,
    maxlon=140,
    minlat=0,
    maxlat=15,
    start_date_str="1993-01-01T00:00:00",
    end_date_str="2025-04-30T23:59:59",
):
    """Download (or reuse) daily CMEMS L4 SLA/ADT for a box and return its path.

    Credentials must already be configured with ``copernicusmarine login``.
    """
    import copernicusmarine

    output_filename = f"cmems_L4_SSH_0.125deg_{start_date_str[0:4]}_{end_date_str[0:4]}.nc"
    output_path = Path(data_dir) / output_filename
    if output_path.exists():
        print(f"Using cached CMEMS file: {output_path}")
        return output_path

    copernicusmarine.subset(
        dataset_id=CMEMS_DAILY_DATASET,
        variables=["adt", "sla"],
        minimum_longitude=minlon,
        maximum_longitude=maxlon,
        minimum_latitude=minlat,
        maximum_latitude=maxlat,
        start_datetime=start_date_str,
        end_datetime=end_date_str,
        output_directory=data_dir,
        output_filename=output_filename,
    )
    if not output_path.exists():
        raise FileNotFoundError(f"CMEMS download finished but file was not found: {output_path}")
    return output_path


def cmems_file_covers(path, bounds):
    """True when the NetCDF at ``path`` covers ``(west, east, south, north)`` (0–360)."""
    path = Path(path)
    if not path.exists():
        return False
    with xr.open_dataset(path) as ds:
        lon = ds.longitude % 360
        return bool(
            lon.min() <= bounds[0] + 0.125
            and lon.max() >= bounds[1] - 0.125
            and ds.latitude.min() <= bounds[2] + 0.125
            and ds.latitude.max() >= bounds[3] - 0.125
        )


def get_cmems_monthly_pacific(
    data_dir,
    extent=(125.0, 245.0, -35.0, 35.0),
    start="1993-01-01",
    end="2024-12-31",
    coarsen=2,
    force_download=False,
):
    """Download monthly CMEMS L4 SLA over the Pacific and cache it as NetCDF.

    The 0.125° monthly product is block-averaged by ``coarsen`` (2 → 0.25°)
    to keep the cache small. Returns the path of the cached file whose
    ``sla`` variable is in metres relative to the 1993–2012 mean.
    """
    import copernicusmarine

    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    resolution = 0.125 * coarsen
    output_path = data_dir / f"cmems_L4_SLA_monthly_{resolution:g}deg_pacific_{start[:4]}_{end[:4]}.nc"
    if output_path.exists() and not force_download:
        print(f"Using cached CMEMS monthly file: {output_path}")
        return output_path

    west, east, south, north = extent
    ds = copernicusmarine.open_dataset(
        dataset_id=CMEMS_MONTHLY_DATASET,
        variables=["sla"],
        minimum_longitude=west,
        maximum_longitude=east,
        minimum_latitude=south,
        maximum_latitude=north,
        start_datetime=start,
        end_datetime=end,
    )
    sla = ds["sla"]
    if coarsen and coarsen > 1:
        sla = sla.coarsen(latitude=coarsen, longitude=coarsen, boundary="trim").mean()
    sla = sla.astype("float32")
    sla.attrs.update(units="m", long_name="Sea level anomaly (CMEMS L4 DUACS, monthly mean)")
    out = sla.to_dataset(name="sla").assign_coords(longitude=sla.longitude % 360)
    temporary = output_path.with_suffix(".nc.part")
    out.to_netcdf(temporary, encoding={"sla": {"zlib": True, "complevel": 4}})
    temporary.replace(output_path)
    return output_path


def get_uhslc_metadata(metadata_url=UHSLC_METADATA_URL, timeout=60):
    """Return a DataFrame describing every UHSLC Fast Delivery station."""
    response = requests.get(metadata_url, timeout=timeout)
    response.raise_for_status()
    rows = []
    for feature in response.json().get("features", []):
        props = feature.get("properties", {})
        coords = feature.get("geometry", {}).get("coordinates") or [np.nan, np.nan]
        fd_span = props.get("fd_span") or {}
        rows.append(
            {
                "uhslc_id": props.get("uhslc_id"),
                "name": props.get("name"),
                "country": props.get("country"),
                "lon": float(coords[0]),
                "lat": float(coords[1]),
                "fd_start": pd.to_datetime(fd_span.get("oldest")),
                "fd_end": pd.to_datetime(fd_span.get("latest")),
            }
        )
    return pd.DataFrame(rows)


def get_uhslc_datum(uhslc_id, datum_name):
    """Return a tidal datum value (mm, station datum) and the full datum table."""
    datum_table = pd.read_csv(UHSLC_DATUM_URL.format(id=int(uhslc_id)))
    datum_value = datum_table.loc[datum_table["Name"] == datum_name, "Value"].values[0]
    return float(datum_value), datum_table


def station_series(rsl, variable="sea_level"):
    """Return one UHSLC station variable as a 1-D time series (drops ``record_id``)."""
    da = rsl[variable]
    if "record_id" in da.dims:
        da = da.isel(record_id=0)
    return da


def station_attr(rsl, name):
    """Return a scalar station attribute (``station_name``, ``lat`` …) as Python type."""
    value = rsl[name]
    if "record_id" in value.dims:
        value = value.isel(record_id=0)
    value = value.values.item()
    return value.decode() if isinstance(value, bytes) else value


# =========================
# Site selection
# =========================
def _haversine_km(lon1, lat1, lon2, lat2):
    """Great-circle distance in km between two lon/lat points."""
    lon1, lat1, lon2, lat2 = (np.radians(np.asarray(v, dtype=float)) for v in (lon1, lat1, lon2, lat2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def select_uhslc_station(
    site_lon,
    site_lat,
    station_country_filter=None,
    selected_uhslc_id=None,
    selected_station_name=None,
    metadata_url=UHSLC_METADATA_URL,
):
    """Select a UHSLC station by id, name or proximity.

    Priority: ``selected_uhslc_id`` → ``selected_station_name`` → nearest
    station (optionally restricted to ``station_country_filter``).
    Returns a dict including ``options_df`` with all candidate stations.
    """
    meta = get_uhslc_metadata(metadata_url)
    meta["distance_km"] = _haversine_km(site_lon, site_lat, meta["lon"].values, meta["lat"].values)
    if station_country_filter:
        target = normalise_name(station_country_filter)
        meta = meta[meta["country"].fillna("").map(normalise_name).str.contains(target, regex=False)]
    if meta.empty:
        raise ValueError(f"No UHSLC stations found for country filter: {station_country_filter}")
    meta = meta.sort_values("distance_km").reset_index(drop=True)

    if selected_uhslc_id is not None:
        chosen = meta[meta["uhslc_id"] == int(selected_uhslc_id)]
        reason = "selected_uhslc_id"
    elif selected_station_name is not None:
        chosen = meta[meta["name"].fillna("").str.lower() == selected_station_name.strip().lower()]
        reason = "selected_station_name"
    else:
        chosen = meta.iloc[:1]
        reason = "nearest_station"
    if chosen.empty:
        raise ValueError("Requested UHSLC station not found among the candidates.")
    row = chosen.iloc[0]
    return {
        "options_df": meta[["uhslc_id", "name", "country", "distance_km", "lon", "lat", "fd_start", "fd_end"]].round({"distance_km": 1}),
        "selection_reason": reason,
        "distance_km": float(row["distance_km"]),
        "uhslc_id": int(row["uhslc_id"]),
        "station": row["name"],
        "station_country": row["country"],
        "lon": float(row["lon"]),
        "lat": float(row["lat"]),
    }


def prepare_site_data(site_config, repo_root):
    """Resolve the station and EEZ, pre-download inputs and return the config.

    Downloads UHSLC daily and hourly files, checks the ONI service and makes
    sure a daily CMEMS file covers the EEZ (plus ``cmems_padding_degrees``).
    Paths stored in the config are relative to ``repo_root``.
    """
    repo_root = Path(repo_root)
    cfg = dict(site_config)
    selection = select_uhslc_station(
        site_lon=float(cfg["site_lon"]),
        site_lat=float(cfg["site_lat"]),
        station_country_filter=cfg.get("station_country_filter"),
        selected_uhslc_id=cfg.get("selected_uhslc_id"),
        selected_station_name=cfg.get("selected_station_name"),
    )
    cfg.update(
        selected_uhslc_id=selection["uhslc_id"],
        station=selection["station"],
        station_country=selection["station_country"],
        station_lon=selection["lon"],
        station_lat=selection["lat"],
        station_distance_km=round(selection["distance_km"], 2),
        station_selection_reason=selection["selection_reason"],
    )

    sea_level_dir = repo_root / cfg.get("sea_level_data_dir", "data/sea_level")
    download_uhslc_data(sea_level_dir, cfg["selected_uhslc_id"], "daily")
    download_uhslc_data(sea_level_dir, cfg["selected_uhslc_id"], "hourly")
    download_oni_index(ONI_URL)

    _, geometry = resolve_eez(cfg["country"], repo_root / cfg["eez_file"])
    pad = float(cfg.get("cmems_padding_degrees", 1.0))
    west, east, south, north = eez_bounds_360(geometry)
    bounds = cfg.get("cmems_bbox_override") or [west - pad, east + pad, south - pad, north + pad]
    cfg["cmems_bounds"] = [round(float(v), 3) for v in bounds]

    candidate = cfg.get("cmems_file")
    if candidate and cmems_file_covers(repo_root / candidate, bounds):
        cmems_path = repo_root / candidate
    else:
        cmems_path = get_CMEMS_data(
            data_dir=sea_level_dir,
            minlon=bounds[0],
            maxlon=bounds[1],
            minlat=bounds[2],
            maxlat=bounds[3],
            start_date_str=cfg.get("cmems_start_datetime", "1993-01-01T00:00:00"),
            end_date_str=cfg.get("cmems_end_datetime", "2025-04-30T23:59:59"),
        )
    cfg["cmems_file"] = str(Path(cmems_path).resolve().relative_to(repo_root.resolve()))
    return cfg, selection["options_df"]


# =========================
# Trends and statistics
# =========================
def _decimal_years(time):
    t = pd.to_datetime(np.asarray(time))
    return xr.DataArray((t - t[0]).days.values / 365.25, dims="time", coords={"time": time})


def process_trend_with_nan(sea_level_anomaly):
    """Ordinary-least-squares trend that ignores missing values.

    Works for a 1-D series or a gridded field (``time`` first). Returns
    ``(trend_mag, trend_line, trend_rate, p_value, trend_err)`` where
    ``trend_rate`` and ``trend_err`` (standard error) are in input units per
    year and ``trend_mag`` is the fitted change between the first and last
    time steps. The p-value assumes independent residuals and is therefore
    descriptive for autocorrelated daily or monthly data.
    """
    y = sea_level_anomaly.transpose("time", ...)
    if y.sizes.get("time", 0) < 3:
        raise ValueError("At least 3 time steps are required to estimate a trend.")
    t = _decimal_years(y.time)
    valid = y.notnull()
    tv = t.where(valid)
    n = valid.sum("time")
    t_mean = tv.mean("time")
    y_mean = y.mean("time")
    sxx = ((tv - t_mean) ** 2).sum("time")
    slope = ((tv - t_mean) * (y - y_mean)).sum("time") / sxx
    intercept = y_mean - slope * t_mean
    trend_line = slope * t + intercept
    trend_mag = slope * float(t[-1] - t[0])

    resid = y - trend_line
    dof = n - 2
    stderr = np.sqrt((resid**2).sum("time") / dof / sxx)
    t_stat = np.abs(slope / stderr)
    p_value = xr.apply_ufunc(lambda ts, df: 2 * stats.t.sf(ts, df), t_stat, dof.where(dof > 0))
    enough = n > 2
    return (
        trend_mag.where(enough),
        trend_line,
        slope.where(enough),
        p_value.where(enough),
        stderr.where(enough),
    )


def get_trend_info(x, y, timescale="days"):
    """Linear trend metadata for annual flood-count charts (NaNs ignored)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    ok = np.isfinite(x) & np.isfinite(y)
    slope, intercept, _, p_value, _ = stats.linregress(x[ok], y[ok])
    trend_counts = intercept + slope * x
    unit = "days" if timescale == "days" else "hours"
    trend_label = f"Trend {slope:+.2f} {unit}/year (p = {p_value:.3f})"
    linestyle_trend = "-" if p_value < 0.05 else "--"
    return trend_counts, trend_label, linestyle_trend, slope, p_value


def format_with_units(value, unit):
    """Format a numeric value with a unit suffix."""
    return f"{value:.2f} {unit}"


def build_sl_magnitude_results(
    trend_rate_asl,
    trend_rate_rsl,
    trend_mag_asl,
    trend_mag_rsl,
    sla_nearest_lat,
    sla_nearest_lon,
    rsl_lat,
    rsl_lon,
    start_date_str,
    end_date_str,
):
    """Absolute vs relative sea-level change table (inputs in m and m/yr)."""
    rate_asl_mm = 1000 * float(trend_rate_asl)
    rate_rsl_mm = 1000 * float(trend_rate_rsl)
    mag_asl_cm = 100 * float(trend_mag_asl)
    mag_rsl_cm = 100 * float(trend_mag_rsl)
    table = pd.DataFrame(
        {
            "Rate (mm/yr)": [rate_asl_mm, rate_rsl_mm],
            "Rate (in/yr)": [rate_asl_mm / 25.4, rate_rsl_mm / 25.4],
            f"Change {start_date_str[:4]}-{end_date_str[:4]} (cm)": [mag_asl_cm, mag_rsl_cm],
            f"Change {start_date_str[:4]}-{end_date_str[:4]} (in)": [mag_asl_cm / 2.54, mag_rsl_cm / 2.54],
            "Latitude": [float(sla_nearest_lat), float(rsl_lat)],
            "Longitude": [float(sla_nearest_lon), float(rsl_lon)],
        },
        index=["Absolute (altimetry)", "Relative (tide gauge)"],
    ).round(2)
    glue_values = {
        "trend_mmyr_altimetry": rate_asl_mm,
        "trend_mmyr_tide_gauge": rate_rsl_mm,
        "trend_inyr_altimetry": rate_asl_mm / 25.4,
        "trend_inyr_tide_gauge": rate_rsl_mm / 25.4,
        "delta_cm_altimetry": mag_asl_cm,
        "delta_cm_tide_gauge": mag_rsl_cm,
        "delta_in_altimetry": mag_asl_cm / 2.54,
        "delta_in_tide_gauge": mag_rsl_cm / 2.54,
    }
    return table, glue_values


def build_enso_summary_table(slope, nino_1997, nina_1998, r_value, p_value):
    """Summary of the tide-gauge sensitivity to ONI (inputs in m)."""
    rows = [
        ("Sensitivity to ONI", f"{100 * slope:.1f} cm per °C"),
        ("Correlation (r)", f"{r_value:.2f}"),
        ("Explained variance (r²)", f"{r_value ** 2:.2f}"),
        ("p-value (descriptive)", f"{p_value:.3g}"),
        ("Mean anomaly, 1997–98 El Niño", f"{100 * float(nino_1997.mean()):.1f} cm" if nino_1997.size else "no data"),
        ("Mean anomaly, 1998–2001 La Niña", f"{100 * float(nina_1998.mean()):.1f} cm" if nina_1998.size else "no data"),
    ]
    table = pd.DataFrame(rows, columns=["Metric", "Value"])
    return table, table.style.hide(axis="index")


# =========================
# Completeness and storm years
# =========================
def storm_year(time):
    """Storm-year label (May–April, labelled by the starting calendar year)."""
    t = pd.DatetimeIndex(pd.to_datetime(np.asarray(time)))
    return np.where(t.month >= 5, t.year, t.year - 1)


def monthly_mean_with_completeness(series, min_fraction=COMPLETENESS_THRESHOLD):
    """Monthly means keeping only months with ``min_fraction`` of valid samples.

    ``series`` is a 1-D DataArray (daily or hourly). Months below the
    threshold become NaN rather than being dropped or filled.
    """
    s = series.to_series()
    step = s.index.to_series().diff().median()
    per_day = int(round(pd.Timedelta("1D") / step)) if step < pd.Timedelta("1D") else 1
    counts = s.resample("MS").count()
    expected = counts.index.days_in_month * per_day
    monthly = s.resample("MS").mean()
    return monthly.where(counts / expected >= min_fraction)


def annual_completeness(series, by="storm"):
    """Fraction of expected samples present per (storm or calendar) year."""
    s = series.to_series()
    step = s.index.to_series().diff().median()
    per_day = int(round(pd.Timedelta("1D") / step)) if step < pd.Timedelta("1D") else 1
    labels = storm_year(s.index) if by == "storm" else s.index.year
    present = s.notna().groupby(labels).sum()

    def _days_in(year):
        # expected samples always cover the full year, so partial first/last years are flagged
        if by == "storm":
            return pd.date_range(f"{year}-05-01", f"{year + 1}-04-30", freq="D").size
        return pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D").size

    expected = pd.Series({year: _days_in(int(year)) * per_day for year in present.index})
    return (present / expected).clip(upper=1).rename("completeness")


# =========================
# ENSO helpers
# =========================
def detect_enso_events(oni_df):
    """Flag El Niño / La Niña months: ONI beyond ±0.5 °C for ≥5 consecutive months."""
    oni_df = oni_df.copy()
    oni_df["year_storm"] = storm_year(oni_df.index)

    def _flag(condition):
        run_id = (~condition).cumsum()
        run_length = condition.groupby(run_id).transform("sum")
        return condition & (run_length >= 5)

    oni_df["El Nino"] = _flag(oni_df["ONI"] > 0.5)
    oni_df["La Nina"] = _flag(oni_df["ONI"] < -0.5)
    oni_df["ONI Mode"] = np.select([oni_df["El Nino"], oni_df["La Nina"]], ["El Nino", "La Nina"], "Neutral")
    return oni_df


def get_dominant_enso(series):
    """Dominant ENSO mode in a grouped series of ``ONI Mode`` labels."""
    el_nino = (series == "El Nino").sum()
    la_nina = (series == "La Nina").sum()
    if el_nino > la_nina:
        return "El Nino"
    if la_nina > el_nino:
        return "La Nina"
    return "Neutral"


def enso_by_storm_year(enso_events):
    """Dominant ENSO mode and mean ONI per storm year."""
    grouped = enso_events.groupby("year_storm")
    out = grouped["ONI Mode"].agg(get_dominant_enso).to_frame("ONI Mode")
    out["ONI"] = grouped["ONI"].mean()
    return out


# =========================
# Flood frequency
# =========================
def flood_counts_per_storm_year(
    hourly_mhhw_mm,
    threshold_cm=MINOR_FLOOD_THRESHOLD_CM,
    min_fraction=COMPLETENESS_THRESHOLD,
):
    """Minor-flood days and hours per storm year.

    ``hourly_mhhw_mm`` is a 1-D hourly DataArray in mm relative to MHHW.
    A flood day has at least one hourly value above ``threshold_cm``.
    Years whose hourly completeness is below ``min_fraction`` keep their
    counts in ``*_raw`` columns but are NaN in the analysis columns.
    """
    s = hourly_mhhw_mm.to_series()
    labels = pd.Series(storm_year(s.index), index=s.index)
    above = s > threshold_cm * 10
    hours = above.groupby(labels).sum()
    daily_max = s.resample("D").max()
    days = (daily_max > threshold_cm * 10).groupby(storm_year(daily_max.index)).sum()
    completeness = annual_completeness(hourly_mhhw_mm, by="storm")
    years = np.arange(int(labels.min()), int(labels.max()) + 1)
    table = pd.DataFrame(index=pd.Index(years, name="year_storm"))
    table["completeness"] = completeness.reindex(years)
    table["flood_days_raw"] = days.reindex(years)
    table["flood_hours_raw"] = hours.reindex(years)
    ok = table["completeness"] >= min_fraction
    table["flood_days_count"] = table["flood_days_raw"].where(ok)
    table["flood_hours_count"] = table["flood_hours_raw"].where(ok)
    return table.reset_index()


def monthly_flood_day_matrix(hourly_mhhw_mm, threshold_cm, valid_years):
    """Storm-year × month table of flood days, plus a monthly-share row (%)."""
    import calendar

    daily_max = hourly_mhhw_mm.to_series().resample("D").max()
    flood = (daily_max > threshold_cm * 10).astype(float).where(daily_max.notna())
    frame = pd.DataFrame({"flood": flood, "year": storm_year(flood.index), "month": flood.index.month})
    frame = frame[frame["year"].isin(valid_years)]
    matrix = frame.pivot_table(index="year", columns="month", values="flood", aggfunc="sum")
    month_order = [5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3, 4]
    matrix = matrix.reindex(columns=month_order)
    matrix.columns = [calendar.month_abbr[m] for m in month_order]
    matrix.index.name = "Storm Year"
    matrix["Annual"] = matrix.sum(axis=1, min_count=1)
    totals = matrix.sum()
    matrix.loc["Monthly Total (%)"] = 100 * totals / totals["Annual"] if totals["Annual"] else np.nan
    return matrix, list(matrix.columns[:-1])


# =========================
# Rankings
# =========================
def get_top_ten(rsl, mode="max", separation_days=3):
    """Ten highest/lowest hourly levels separated by more than ``separation_days``."""
    series = station_series(rsl).to_series().dropna()
    candidates = series.nlargest(500) if mode == "max" else series.nsmallest(500)
    chosen = []
    for date, value in candidates.items():
        if all(abs((date - d).days) > separation_days for d, _ in chosen):
            chosen.append((date, value))
        if len(chosen) == 10:
            break
    table = pd.DataFrame(chosen, columns=["date", "sea level (m)"])
    table.insert(0, "rank", np.arange(1, len(table) + 1))
    table["date"] = pd.to_datetime(table["date"]).dt.round("h")
    table["station_name"] = station_attr(rsl, "station_name")
    table["type"] = mode
    return table


def get_top_10_table(rsl, oni=None):
    """Top-10 high/low events joined with the ONI value and ENSO mode."""
    table = pd.concat([get_top_ten(rsl, "max"), get_top_ten(rsl, "min")], ignore_index=True)
    if oni is None:
        oni = download_oni_index(ONI_URL)
    enso = detect_enso_events(oni)[["ONI", "ONI Mode"]]
    month_start = table["date"].dt.to_period("M").dt.to_timestamp()
    return table.join(enso.reindex(month_start).reset_index(drop=True))


# =========================
# Regional helpers
# =========================
def pacific_uhslc_stations(extent=(125.0, 245.0, -35.0, 35.0), start="1993-01-01", end="2024-12-31"):
    """UHSLC Fast Delivery stations inside the Pacific window whose span overlaps the period."""
    meta = get_uhslc_metadata()
    meta["lon360"] = meta["lon"] % 360
    west, east, south, north = extent
    inside = meta["lon360"].between(west, east) & meta["lat"].between(south, north)
    overlap = (meta["fd_start"] <= pd.Timestamp(end)) & (meta["fd_end"] >= pd.Timestamp(start))
    return meta[inside & overlap].sort_values("uhslc_id").reset_index(drop=True)


def station_monthly_record(rsl, start, end, min_fraction=COMPLETENESS_THRESHOLD):
    """Monthly mean relative sea level (m) for the period, incomplete months as NaN."""
    daily = station_series(rsl).sel(time=slice(start, end)) / 1000.0
    monthly = monthly_mean_with_completeness(daily, min_fraction)
    full_index = pd.date_range(pd.Timestamp(start).replace(day=1), end, freq="MS")
    return monthly.reindex(full_index)


def series_trend(series):
    """OLS trend of a monthly pandas Series → (rate per year, stderr, p, n)."""
    s = series.dropna()
    if len(s) < 24:
        return np.nan, np.nan, np.nan, len(s)
    t = (s.index - s.index[0]).days.values / 365.25
    res = stats.linregress(t, s.values)
    return res.slope, res.stderr, res.pvalue, len(s)


def regional_station_trends(
    stations,
    sla_monthly,
    data_dir,
    start="1993-01-01",
    end="2024-12-31",
    min_fraction=COMPLETENESS_THRESHOLD,
    min_valid_fraction=0.7,
):
    """Relative (tide gauge) and absolute (nearest altimetry cell) trends per station.

    A station-month is valid when ≥ ``min_fraction`` of its days are present.
    Stations with fewer than ``min_valid_fraction`` valid months in the period
    are kept in the table but flagged ``qc_pass = False``. Altimetry is
    sampled on exactly the same valid months so both trends cover the same
    epoch. Rates are in mm/yr.
    """
    rows, monthly_records = [], {}
    total_months = len(pd.date_range(start, end, freq="MS"))
    sla_lon = sla_monthly.longitude.values
    for _, st in stations.iterrows():
        try:
            rsl = download_uhslc_data(data_dir, int(st["uhslc_id"]), "daily")
        except Exception as exc:  # network or missing file
            rows.append({"uhslc_id": st["uhslc_id"], "name": st["name"], "error": str(exc)})
            continue
        monthly = station_monthly_record(rsl, start, end, min_fraction)
        n_valid = int(monthly.notna().sum())

        point = sla_monthly.sel(latitude=st["lat"], longitude=st["lon"] % 360, method="nearest")
        if not np.isfinite(point.values).any():
            # nearest cell is land-masked: search a 3×3 neighbourhood for the closest ocean cell
            ilat = int(np.abs(sla_monthly.latitude.values - st["lat"]).argmin())
            ilon = int(np.abs(sla_lon - st["lon"] % 360).argmin())
            window = sla_monthly.isel(
                latitude=slice(max(ilat - 2, 0), ilat + 3), longitude=slice(max(ilon - 2, 0), ilon + 3)
            )
            ocean = window.notnull().any("time")
            if bool(ocean.any()):
                stacked = window.where(ocean).stack(cell=("latitude", "longitude")).dropna("cell", how="all")
                dist = np.hypot(stacked.latitude - st["lat"], stacked.longitude - st["lon"] % 360)
                point = stacked.isel(cell=int(dist.argmin()))
        alt = point.to_series()
        alt.index = alt.index.to_period("M").to_timestamp()
        alt = alt.reindex(monthly.index)
        alt_matched = alt.where(monthly.notna())

        tg_rate, tg_err, tg_p, _ = series_trend(monthly)
        alt_rate, alt_err, alt_p, _ = series_trend(alt_matched)
        alt_full_rate, _, alt_full_p, _ = series_trend(alt)
        first = monthly.first_valid_index()
        last = monthly.last_valid_index()
        rows.append(
            {
                "uhslc_id": int(st["uhslc_id"]),
                "name": st["name"],
                "country": st["country"],
                "lon": st["lon"],
                "lat": st["lat"],
                "first_valid_month": first.strftime("%Y-%m") if first is not None else None,
                "last_valid_month": last.strftime("%Y-%m") if last is not None else None,
                "valid_months": n_valid,
                "valid_fraction": round(n_valid / total_months, 3),
                "qc_pass": n_valid / total_months >= min_valid_fraction,
                "tg_trend_mm_yr": 1000 * tg_rate,
                "tg_trend_se_mm_yr": 1000 * tg_err,
                "tg_trend_p": tg_p,
                "alt_trend_mm_yr": 1000 * alt_rate,
                "alt_trend_p": alt_p,
                "alt_full_trend_mm_yr": 1000 * alt_full_rate,
                "alt_minus_tg_mm_yr": 1000 * (alt_rate - tg_rate),
            }
        )
        monthly_records[int(st["uhslc_id"])] = monthly
    table = pd.DataFrame(rows)
    return table, pd.DataFrame(monthly_records)


def regional_flood_days(
    stations,
    data_dir,
    start_year=1993,
    end_year=2024,
    threshold_cm=MINOR_FLOOD_THRESHOLD_CM,
    min_fraction=COMPLETENESS_THRESHOLD,
):
    """Storm-year minor-flood days (> threshold above MHHW) for several stations.

    Returns ``(matrix, info)``: ``matrix`` has stations as rows and storm
    years as columns (NaN when the year is incomplete); ``info`` lists the
    MHHW datum used and any errors.
    """
    matrix, info = {}, []
    for _, st in stations.iterrows():
        uid = int(st["uhslc_id"])
        try:
            rsl = download_uhslc_data(data_dir, uid, "hourly")
            mhhw, _ = get_uhslc_datum(uid, "MHHW")
        except Exception as exc:
            info.append({"uhslc_id": uid, "name": st["name"], "error": str(exc)})
            continue
        hourly = station_series(rsl).sel(time=slice(f"{start_year}-05-01", f"{end_year + 1}-04-30")) - mhhw
        if hourly.count() == 0:
            info.append({"uhslc_id": uid, "name": st["name"], "error": "no hourly data in period"})
            continue
        counts = flood_counts_per_storm_year(hourly, threshold_cm, min_fraction).set_index("year_storm")
        matrix[f"{st['name']} ({uid:03d})"] = counts["flood_days_count"].reindex(range(start_year, end_year + 1))
        info.append({"uhslc_id": uid, "name": st["name"], "mhhw_mm": mhhw, "error": None})
    frame = pd.DataFrame(matrix).T
    frame.columns.name = "Storm year"
    return frame, pd.DataFrame(info)
