---
name: sea-level
description: Build and maintain the National (tide gauge + EEZ) and Regional (Pacific) historical sea-level analyses — UHSLC Fast Delivery downloads, CMEMS L4 altimetry, absolute vs relative trends, detrended anomalies, minor-flood days above MHHW, extreme-level rankings, the ENSO response and Pacific tide-gauge comparisons. Use for notebooks under National/sea_level or Regional/sea_level and for functions/sea_level.py and functions/sea_level_plotting.py.
---

# Sea level

Ported from SLIndRA (github.com/asgenz23/SLIndRA) / PICCM_SeaLevel. Calculations live in `functions/sea_level.py`, figures in `functions/sea_level_plotting.py`; keep function definitions out of the notebooks.

## National workflow (`notebooks/historical/National/sea_level/`)

Run in order:

1. `00_sea_level_setup.ipynb` — selects the UHSLC station (`selected_uhslc_id`, `selected_station_name` or nearest to `site_lon/site_lat` within `station_country_filter`), resolves the EEZ from `data/regional/Pacific_EEZs/Pacific_EEZs.shp` by `country`, downloads `data/sea_level/d<id>.nc` and `h<id>.nc`, and reuses `cmems_file` when it covers the EEZ plus `cmems_padding_degrees` (otherwise downloads daily CMEMS with `get_CMEMS_data`). Writes `data/sites/sea_level/<site_key>.json` with repo-relative paths and `site_name = <country>_uhslc<id>`.
2. `a_sea_level_trend.ipynb` — absolute (nearest ocean altimetry cell) vs relative (tide gauge) daily trends, EEZ-masked area-weighted monthly altimetry trend, change map, ENSO scatter (detrended, de-seasoned gauge vs ONI).
3. `b_sea_level_anomaly.ipynb` — detrended, de-seasoned anomalies; storm-year mean/min/max; period-mean detrended altimetry maps over the EEZ with the gauge anomaly on the same scale.
4. `c_sea_level_ff.ipynb` — hourly sea level minus the UHSLC MHHW datum; flood days/hours above `flood_threshold_cm` (default 30 cm) per storm year from the year before the tidal epoch to the last complete storm year; ENSO colouring, monthly matrix, decadal means.
5. `d_sea_level_rankings.ipynb` — top-10 highest/lowest hourly levels (m above MHHW), > 3 days apart, with the ONI phase of the event month.

## Regional workflow (`notebooks/historical/Regional/sea_level/regional_indicators.ipynb`)

- Monthly CMEMS `cmems_obs-sl_glo_phy-ssh_my_allsat-l4-duacs-0.125deg_P1M-m`, window `(125, 245, -35, 35)`, 1993–2025, block-averaged to 0.25° and cached as `data/regional/sea_level/cmems_L4_SLA_monthly_0.25deg_pacific_1993_2025.nc` by `get_cmems_monthly_pacific`.
- Tide gauges: `pacific_uhslc_stations` then `sjoin_nearest` against the Pacific EEZs with a 0.5° tolerance (coastal gauges fall just landward of the EEZ baseline; a strict `within` test drops Kwajalein, Pago Pago, Honolulu, Yap, Noumea, …). `regional_station_trends` keeps months with ≥ 75% of days and flags `qc_pass` when ≥ 70% of months are valid; altimetry is sampled at the nearest ocean cell on the same months.
- Outputs: trend map with gauge circles, PICCM-style change map (cm/epoch) with every gauge in the window (`plot_regional_change_map_filled_tide_gauges`), station trend comparison, regional-mean series, five-year anomaly panels (not detrended, relative to 1993–2012), ENSO regression map (cm/°C), minor-flood heatmap (`regional_flood_days`, storm years 1993–2025), and the PICCM station–year flood matrix for 24 long-record gauges ordered north to south, 1983–2025, with aligned regional-total bars (`plot_regional_flood_matrix`; list in `matrix_station_ids`, includes Santa Cruz and Easter outside the map window).
- Does not use `Regional/00_regional_setup.ipynb`.

## Invariants

- Units: UHSLC `sea_level` is mm relative to station datum; CMEMS `sla` is m relative to the 1993–2012 mean. Report trends in mm/yr, changes and anomalies in cm.
- UHSLC NetCDF `record_id` ≠ UHSLC station ID; always use `station_series(rsl)` / `station_attr(rsl, ...)` (selects by position).
- Storm year = May–April labelled by its **starting** year (`storm_year`), the same convention as `detect_enso_events`. Bars are centred on that label.
- Incomplete years/months (< 75% coverage) stay NaN; never count missing data as zero flood days.
- Trend lines: solid when p < 0.05, dashed otherwise. p-values ignore autocorrelation and are descriptive.
- Altimetry minus tide-gauge rate approximates vertical land motion plus representativeness error — do not present it as a geodetic measurement.
- CMEMS needs `copernicusmarine login` outside the notebooks; never store credentials.

## Outputs

- National: `outputs/figures/<site_tag>/` and `outputs/tables/<site_tag>/` with `site_tag = build_site_tag(site_name, station_lon, station_lat)` (e.g. `palau_uhslc007_lat7p329_lon134p450`); matrix figures `F10_SeaLevel_map_*`, `F10_SeaLevel_trends_*`, `F11_Minor_flood_matrix_*` in `matrix_cc/figures/`.
- Regional: `outputs/figures/regional_pacific/SL_regional_*_pacific.png`, `outputs/tables/regional_pacific/SL_regional_*_pacific.csv|json`, and `matrix_cc/figures/F10_SeaLevel_*_regional_pacific.png`, `F11_Minor_flood_regional_pacific.png`.
