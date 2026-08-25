---
name: sea-surface-temperature
description: Build and maintain National EEZ and Regional Pacific sea-surface-temperature analyses, including NOAA OISST download, EEZ masking, spatial means and trends, seasonal or five-year DJF anomalies, and SST/ENSO outputs. Use for notebooks under National or Regional sea_surface_temperature and for functions/sst.py.
---

# Sea-surface temperature

Use `functions/sst.py` for SST loading, EEZ resolution, calculations and maps. Keep function definitions out of the analysis notebooks.

## National workflow

Notebook: `notebooks/historical/National/sea_surface_temperature/a_Mean_Temperature_maps.ipynb`.

- Resolve the selected country against `data/regional/Pacific_EEZs/Pacific_EEZs.shp` with `resolve_eez_sst`.
- Validate the NetCDF variables/coordinates (`sst`, `time`, `lat`, `lon`) and mask grid-cell centres outside the selected EEZ.
- Produce mean and trend maps, seasonal/annual means and anomalies, EEZ-area-weighted series, point analysis, rankings and ONI-category maps.
- The current National input is `data/sea_surface_temperature/sst_daily_1981_2024_palau.nc`; its actual coverage is Palau only, despite being derived from a wider SST product.

## Regional workflow

Notebook: `notebooks/historical/Regional/sea_surface_temperature/regional_indicators.ipynb`.

- The notebook downloads and caches NOAA OISST v2 monthly means from `https://downloads.psl.noaa.gov/Datasets/noaa.oisst.v2/sst.mnmean.nc` as `data/sea_surface_temperature/sst.mnmean.nc`.
- Use `load_pacific_sst` with the Pacific window `(125, 245, -35, 35)` and overlay every EEZ boundary.
- Figure 19 analogue: `compute_sst_trend`, annual-mean linear trend for 1982–2020 in °C/decade, displayed on a fixed −0.10 to 0.30 scale.
- Figure 20 analogue: `compute_djf_period_anomalies`, five-year half-open DJF blocks from `1985–1990` through `2015–2020`, relative to the 1981–2020 DJF climatology. Each block must contain five complete winters.
- Do not route this workflow through `Regional/00_regional_setup.ipynb`; SST is gridded ocean data, not the GHCN multi-station dataset.

## Invariants

- Use a Pacific-centred Cartopy projection and keep SST longitudes in the 0–360 Pacific window for regional plots.
- Labels such as `1985–1990` mean `[1985, 1990)`, exactly five DJF seasons.
- Never present the Palau-only NetCDF as Pacific-wide coverage; use the downloaded NOAA regional file for Regional maps.
- State SST units explicitly: °C, °C/decade or SST anomaly (°C).
