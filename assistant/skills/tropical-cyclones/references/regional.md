# Regional tropical-cyclone workflow

## Entry point and inputs

- Notebook: `notebooks/historical/Regional/tropical_cyclones/regional_indicators.ipynb`.
- Module: `functions/tcs.py`.
- Cache: `data/tcs/tcs_ALL.nc`; call `download_ibtracs(..., basin=None)` because the study spans WP, EP and SP source basins.
- Default window currently uses `START_YEAR=1981`, `END_YEAR=2026`; check whether the final year is complete.

## Pacific subregions

| Region | Latitude | Longitude (0–360°) | System label | Major threshold |
|---|---:|---:|---|---:|
| Western North Pacific | 0–40°N | 120–<180°E | Typhoons | 96 kt |
| Central North Pacific | 0–40°N | 180–220°E | Hurricanes | 96 kt |
| Western South Pacific | 40–0°S | 135–<180°E | Cyclones | 96 kt |
| Central South Pacific | 40–0°S | 180–240°E | Cyclones | 96 kt |

Use `classify_genesis_region` as the single source of truth for exclusive genesis boundaries.

## Metric functions

- `observations_in_region`: tidy valid in-box observations.
- `build_storm_metrics`: genesis year/month/region, complete-track maximum wind and ACE per storm.
- `annual_region_metrics`: cumulative annual named/system/major counts based on maximum in-box wind plus genesis-assigned ACE.
- `monthly_genesis_metrics`: mean annual genesis counts in exclusive intensity classes.
- `spatial_track_density`: mean annual unique storm passages per regular grid cell.

## Figure functions

- `plot_pacific_regions_map`, `plot_genesis_tracks`
- `plot_monthly_intensity_distribution`, `plot_spatial_track_density`
- `plot_period_comparison`, `plot_regional_annual_counts`
- `plot_regional_intensity_counts`, `plot_regional_map_dashboard`, `plot_regional_ace`

Lower-level axes helpers are `plot_annual_counts`, `plot_stacked_annual_counts`, `plot_region_inset`, and `regional_intensity_colors`.

## Output contract

Create `maps_dir = Path("../../../../outputs/figures") / f"regional_{region_key}"` with `region_key="pacific"`. Current canonical figures are:

- `TC_regional_subregions_pacific.png`
- `TC_regional_genesis_tracks_pacific.png`
- `TC_regional_monthly_genesis_pacific.png`
- `TC_regional_track_density_pacific.png`
- `TC_regional_period_comparison_pacific.png`
- `TC_regional_annual_counts_pacific.png`
- `TC_regional_intensity_composition_pacific.png`
- `TC_regional_map_dashboard_pacific.png`
- `TC_regional_ace_pacific.png`

Optional annual CSVs go to `outputs/tables/regional_tropical_cyclones/`.

## Interpretation cautions

- Annual count charts and ACE do not use the same population definition: counts use box entry; ACE uses exclusive genesis.
- The monthly chart uses genesis month and complete-track maximum intensity.
- The density map includes any cyclone passage inside each box, regardless of genesis region, and counts each storm once per 2° cell.
- Period-comparison boxes use the period dictionary supplied by the notebook. Current overlapping 11-year windows repeat boundary years; disclose this or switch to non-overlapping intervals when independence matters.
- Missing WMO winds are omitted in Regional classification rather than pressure-filled.
