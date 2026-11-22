# Sea level

Projected **relative** sea-level rise and minor (high-tide) flooding at the national UHSLC tide gauge, from the IPCC AR6 sea-level projections **with vertical land motion** — the projections used by the [NASA Pacific Flooding Analysis Tool](https://sealevel.nasa.gov/flooding-analysis-tool-pacific-islands/sea-level-rise). The tide gauge is the one configured in the [historical sea-level setup](../../../historical/National/sea_level/00_sea_level_setup.ipynb) (`data/sites/sea_level/<site_key>.json`).

<div class="dashboard-grid">

<a href="a_sea_level_projections.html" class="dashboard-card ocean">
  <h3>Sea-level rise at the tide gauge</h3>
  <p>Observed annual mean sea level and AR6 projections for the SSPs, reported at the +1.5, +2.0, +2.5 and +3.0 °C global warming levels, with the contribution of vertical land motion.</p>
</a>

<a href="b_sea_level_flooding.html" class="dashboard-card ocean">
  <h3>Projected minor flooding</h3>
  <p>Days per year above 30 cm over MHHW: response to sea-level rise, projected flood days and when flooding milestones are reached.</p>
</a>

</div>

```{note}
The AR6 files (~75 MB per scenario) are extracted from the Zenodo archive on first use and deleted once the tide-gauge values are cached in `data/projections/regional/sl_ar6_vlm_medium_locations.nc`.
```
