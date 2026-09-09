---
name: data-sources
description: Documents CIndRA data sources including GHCN-Daily, NOAA OISST/ONI/IBTrACS, UHSLC, Copernicus Marine physical and biogeochemical products, and NOAA PIFSC MD50. Use when running a supported download, attribution or unit conversion.
---

## Skill: Data Sources & Attribution

### Daily precipitation and temperature — GHCN-Daily (NOAA NCEI)

- **Country lookup**: `https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-countries.txt` → `GHCN.download_country_codes()`.
- **Station inventory**: `https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-stations.txt` → `GHCN.download_stations_info()`.
- **Element inventory**: `https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-inventory.txt` → `GHCN.download_station_inventory()`.
- **Per-station daily CSVs**: `https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/<station_id>.csv`.
- **Variables in use**: `PRCP` (rainfall), `TMIN`/`TMAX` (temperature) — all stored in tenths of the analysis unit; downloader divides by 10.
- **Units after conversion**: daily rainfall **mm/day**; annual accumulated rainfall **mm/year**; temperature **°C**; `TMEAN = (TMAX + TMIN) / 2` and `diff = TMAX − TMIN` derived in `00_site_setup.ipynb`.
- **Sentinels**: `-9999` → NaN inside `extract_dict_data_var`.
- **Documentation**: `https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/doc/GHCND_documentation.pdf`.
- **Citation**: Menne, M.J., I. Durre, R.S. Vose, B.E. Gleason, and T.G. Houston, 2012. *An overview of the Global Historical Climatology Network-Daily Database.* J. Atmos. Oceanic Technol., 29, 897-910.

### ENSO — NOAA ONI

- **URL**: `https://psl.noaa.gov/data/correlation/oni.data`.
- **Format**: monthly Niño 3.4 anomalies. `-99.9` → NaN (`download_oni_index`).
- **Classification** (via `add_oni_cat` in `ind_setup`):
  - El Niño: ONI ≥ 0.5 (5 consecutive months for official events; plotting uses monthly categories).
  - La Niña: ONI ≤ −0.5.
  - Neutral otherwise.
- **Colours**: El Niño = red, La Niña = blue, Neutral = gray.
- **Citation**: NOAA Climate Prediction Center / Physical Sciences Laboratory.
- **Use in CIndRA**: rainfall, air temperature, sea level, tropical cyclones, SST, marine heatwaves and marine biochemistry. Preserve the classification rule implemented by the relevant notebook; do not mix monthly phase labels and annual dominant-phase composites silently.

### Sea-surface temperature — NOAA OISST v2

- **Regional monthly NetCDF**: `https://downloads.psl.noaa.gov/Datasets/noaa.oisst.v2/sst.mnmean.nc`.
- **Cache**: `data/sea_surface_temperature/sst.mnmean.nc`; `Regional/sea_surface_temperature/regional_indicators.ipynb` downloads it with `urlretrieve`, using a `.part` file before the final rename.
- **Variable/coordinates**: `sst`, `time`, `lat`, `lon`; SST is °C. `load_pacific_sst` converts longitude to 0–360 and subsets `(125, 245, -35, 35)`.
- **National input**: `data/sea_surface_temperature/sst_daily_1981_2024_palau.nc`, a Palau-only daily subset used by `National/sea_surface_temperature/a_Mean_Temperature_maps.ipynb`.
- **Regional periods**: mean/reference climatology 1981–2020; trend 1982–2020; five-year DJF anomaly blocks 1985–1990 through 2015–2020.
- **Citation**: NOAA Physical Sciences Laboratory, NOAA Optimum Interpolation Sea Surface Temperature (OISST) v2.

### Tropical cyclones — NOAA IBTrACS

- **Dataset**: International Best Track Archive for Climate Stewardship, v04r01.
- **URL**: `https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/netcdf/IBTrACS.ALL.v04r01.nc`.
- **Access**: `download_ibtracs(url, basin=...)` in `functions/data_downloaders.py`; use `basin="WP"` for the current National notebooks and `basin=None` for the Regional multi-basin notebook.
- **Cache**: `data/tcs/tcs_WP.nc` or `data/tcs/tcs_ALL.nc`.
- **Variables**: `lon`/`lat` in degrees, `time`, `wmo_wind` in knots, `wmo_pres` in hPa.
- **Missing intensity**: Regional indicators omit missing WMO winds. National radius workflows currently use `fillwinds=True`, which estimates wind from pressure; disclose the estimate.
- **Citation**: Knapp, K.R. et al., International Best Track Archive for Climate Stewardship (IBTrACS), NOAA NCEI. State dataset version and access window.

### Marine biochemistry — Copernicus Marine and NOAA PIFSC

- **Copernicus dataset**: `cmems_mod_glo_bgc_my_0.25deg_P1M-m`, monthly 0.25° global biogeochemical reanalysis.
- **Variables**: `ph` (pH units), `chl` (mg m⁻³), `phyc` (mmol C m⁻³) and `o2` (µmol L⁻¹), using the surface level selected in the notebooks.
- **Regional cache**: `data/regional/biochemistry/copernicus_bgc_pacific_surface_monthly.nc`.
- **Access**: `copernicusmarine.subset`; configure credentials with `copernicusmarine login` outside the notebook and never store credentials in assistant instructions or code.
- **Product page**: `https://data.marine.copernicus.eu/product/GLOBAL_MULTIYEAR_BGC_001_029/description`.
- **NOAA PIFSC MD50**: experimental `md50_exp_2025` median phytoplankton-size product, units µm, from `https://oceanwatch.pifsc.noaa.gov/erddap/info/md50_exp_2025/index.html`; Regional cache `data/regional/biochemistry/MD50_pacific_monthly.nc`.
- Never use a National/Palau subset as a Regional Pacific product.

### Marine heatwaves — NOAA OISST and Hobday method

- Daily NOAA OISST is processed by the repository's `functions/marineHeatWaves.py` implementation.
- Cite the marineHeatWaves implementation and Hobday marine-heatwave method as recorded in the MHW notebooks.
- Detection parameters, climatology period and spatial stride come from the executed notebook and must be reported with results.

### Tide gauge — UHSLC (University of Hawaii Sea Level Center)

- **Portal**: `https://uhslc.soest.hawaii.edu/data/?rq` (Research Quality Data Set).
- **Per-station NetCDF**: daily `d<uhslc_id>.nc`, hourly `h<uhslc_id>.nc` (`uhslc_id` zero-padded to 3 digits, e.g. `d007.nc` for Malakal, Palau), cached under `data/sea_level/`.
- **Lookup helper**: `download_uhslc_data(data_dir, uhslc_id, resolution)` in `data_downloaders.py` — **cache lookup only**, does not download new files (see Hard Rules).
- **Datums**: `get_uhslc_datum(uhslc_id, datum_name)` in `sea_level.py` fetches the live datum table from `https://uhslc.soest.hawaii.edu/stations/TIDES_DATUMS/...` (e.g. `MSL`, `MHHW`).
- **Station discovery**: `select_uhslc_station(...)` in `sea_level.py` queries `https://uhslc.soest.hawaii.edu/data/meta.geojson` and picks the nearest/matching station.
- **Units**: sea level in metres in the raw NetCDF (`sea_level` variable); notebooks convert to cm for reporting (`100 * value`).

### Satellite altimetry — CMEMS (Copernicus Marine Service)

- **Dataset**: `cmems_obs-sl_glo_phy-ssh_my_allsat-l4-duacs-0.125deg_P1D` (global ocean gridded L4, `adt` absolute dynamic topography and `sla` sea level anomaly variables).
- **Access**: the `copernicusmarine` Python package, via `get_CMEMS_data(...)` in `sea_level.py`, which subsets to a bounding box (derived from the site's EEZ shapefile, or `cmems_bbox_override`) and a date range, caching the result as `cmems_L4_SSH_0.125deg_<start_year>_<end_year>.nc` under `data/sea_level/`.
- **Units**: metres in the raw NetCDF; notebooks convert to mm/yr for trends and cm for anomalies/deltas.

### Reference periods / analysis windows

- Rainfall and air-temperature climatology baseline for anomalies: **1961–1990** (WMO standard), stored in site config as `reference_period_start` / `reference_period_end`. Applies to rainfall totals and to mean/min/max temperature anomalies alike.
- In code, slice with `.loc[ref_start:ref_end]` — never pass `"1961:1990"` as a single label to `.loc` on a DatetimeIndex.
- Hot days (TX90p) / cold nights (TN10p) use the same 1961–1990 window as the ETCCDI base period, hardcoded in `temp_func.py` (`BASE_PERIOD_START`/`BASE_PERIOD_END`).
- Sea level has no fixed WMO reference period; each notebook uses the available UHSLC/CMEMS record window (commonly 1993–2022/2025) for trends, and the station's own monthly climatology (not 1961–1990) for anomalies.
- Regional SST uses the 1981–2020 DJF climatology for five-year boreal-winter anomalies; period labels are half-open (`1985–1990` contains winters 1985–1989).

### QC applied in the shared `00_site_setup.ipynb`

1. **Download** — concat requested variables, `dropna()`. Temperature additionally derives `TMEAN`/`diff` when both `TMIN` and `TMAX` are present.
2. **Completeness filter** — `filter_by_time_completeness` with `month_threshold = year_threshold = completeness_threshold` (default 0.75), applied independently to the temperature pickle and the rainfall pickle. Months with < 75% of calendar days observed are dropped; years with < 75% of valid months are dropped.

Rainfall notebooks `b_Consecutive_dry_days.ipynb` and `c_Heavy_rainfall.ipynb` do not apply any additional per-notebook completeness filter — the shared `00_site_setup.ipynb` filter is the only one.

### Hard rules

- Always attribute sources in narrative outputs ("Source: GHCN-Daily station <id>", "Source: NOAA OISST v2", "Source: NOAA IBTrACS v04r01", "Source: NOAA ONI", "Source: UHSLC station <id>", "Source: CMEMS L4 SSH").
- Never invent GHCN station IDs; resolve via site config and `GHCN.get_country_code`. Never invent UHSLC station IDs; resolve via `select_uhslc_station` / the saved site config.
- Always state units: **mm**, **mm/day**, **mm/year**, **°C**, **°C/decade**, **days/year** (rainfall/temperature); **kt**, **cyclones/year**, **ACE/decade** (cyclones); **mm/yr**, **cm** (sea level).
- Never present user-uploaded data as primary without explicit user instruction.
- Do not claim `download_uhslc_data` fetches new data from UHSLC — it only serves an already-cached local file (`data/sea_level/d<id>.nc` / `h<id>.nc`); automatic download was lost in the PICCM_Atmosphere/PICCM_SeaLevel merge and has not been restored.
