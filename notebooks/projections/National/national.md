# National projections

The national projection workflows describe how the climate of an individual Pacific Island country or monitoring site is expected to change under the CMIP6 Shared Socioeconomic Pathways (SSP1-2.6, SSP2-4.5, SSP3-7.0 and SSP5-8.5). Local changes are reported at **global warming levels** (+1.5, +2.0, +2.5 and +3.0 °C above 1850–1900), so that results can be compared across scenarios.

The notebooks use the same site configuration as the historical analysis (`data/sites/<site_key>.json`, created by the [historical site setup](../../historical/National/00_site_setup.ipynb)): set `site_key` at the top of each notebook.

## Prepare a national projection

<div class="dashboard-grid">

<a href="00_warming_levels.html" class="dashboard-card setup">
  <h3>Global warming levels</h3>
  <p>Years at which each SSP scenario reaches +1.5, +2.0, +2.5 and +3.0 °C of global warming (IPCC AR6), shared by all projection notebooks.</p>
</a>

</div>

## Explore the projections

<div class="dashboard-grid">

<a href="air_temperature/surface_temperature.html" class="dashboard-card atmosphere">
  <h3>Air temperature</h3>
  <p>Mean, minimum and maximum temperature, warm days and cold nights.</p>
</a>

<a href="rainfall/rainfall.html" class="dashboard-card rainfall">
  <h3>Rainfall</h3>
  <p>Annual totals, dry days, heavy-rainfall days and annual maximum daily rainfall.</p>
</a>

<a href="tropical_cyclones/tropical_cyclones.html" class="dashboard-card cyclone">
  <h3>Tropical cyclones</h3>
  <p>Illustrative future exposure from a poleward shift of historical tracks.</p>
</a>

<a href="sea_surface_temperature/sea_surface_temperature.html" class="dashboard-card ocean">
  <h3>Sea-surface temperature</h3>
  <p>EEZ-average and site SST, and marine heatwave days by category.</p>
</a>

<a href="biochemistry/biochemistry.html" class="dashboard-card ocean">
  <h3>Ocean biogeochemistry</h3>
  <p>Surface pH, aragonite saturation state and salinity.</p>
</a>

<a href="sea_level/sea_level.html" class="dashboard-card ocean">
  <h3>Sea level</h3>
  <p>AR6 relative sea-level rise at the tide gauge and projected minor-flood days.</p>
</a>

</div>

## Data

| Source | Variables | Location |
|---|---|---|
| CSIRO CMIP6 ensembles on a common 1° Pacific grid | `tas`, `tasmin`, `tasmax`, warm days, cold nights, rainfall indices, SST | `CINDRA_CSIRO_PROJECTIONS_DIR` |
| IPCC AR6 SYR Figure SPM.4 | Global surface temperature | `data/projections/ipcc/` |
| IPCC-WGI AR6 Interactive Atlas | Surface pH (CMIP6 members) | `CINDRA_EXTRA_PROJECTIONS_DIR/data_copernicus` |
| Jiang et al. (2023), NCEI OCADS 0259391 | pH, aragonite, salinity | `CINDRA_EXTRA_PROJECTIONS_DIR/bio/nc` |
| Holbrook et al., Pacific MHW statistics | Marine heatwave days by category | `CINDRA_EXTRA_PROJECTIONS_DIR/marine_heatwaves` |
| IPCC AR6 sea-level projections (Garner et al., 2021; Zenodo 6382554) | Relative sea-level change at tide gauges (with VLM) | `data/projections/sea_level/` (downloaded on demand) |

Default locations are defined in `functions/projections.py`; series extracted for each site are cached in `data/projections/<site_tag>/` and figures are written to `outputs/figures/<site_tag>/PRJ_*.png`.

## Recommended workflow

1. Run [`00_warming_levels.ipynb`](00_warming_levels.ipynb) once.
2. Set `site_key` and run the indicator notebooks.
3. Interpret local values as the spread across models at the year each scenario reaches a warming level; a single year per model is used, so year-to-year variability is part of the spread.
