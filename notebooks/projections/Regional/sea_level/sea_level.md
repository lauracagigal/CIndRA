# Sea level

Projected sea-level rise across the Pacific from the IPCC AR6 sea-level projections (Garner et al., 2021, medium confidence): gridded maps **without vertical land motion** (`ar6-regional_novlm-confidence`, absolute sea level comparable with satellite altimetry) and tide-gauge projections **with vertical land motion** (`ar6-regional-confidence`, relative sea level).

<div class="dashboard-grid">

<a href="regional_indicators.html" class="dashboard-card ocean regional">
  <h3>Regional sea-level projections</h3>
  <p>Maps of absolute change by 2050 and 2100, rates of rise and the 2020–2100 trend for SSP1-2.6 to SSP5-8.5, the regional-mean likely range and EEZ tables.</p>
</a>

<a href="station_projections.html" class="dashboard-card ocean regional">
  <h3>Projections at Pacific tide gauges</h3>
  <p>Relative sea-level rise (AR6 with vertical land motion) at every UHSLC gauge in the Pacific EEZs, for the SSPs and warming levels, and the contribution of land motion.</p>
</a>

<a href="regional_maps_with_stations.html" class="dashboard-card ocean regional">
  <h3>Maps with tide gauges</h3>
  <p>The gridded absolute projections (no VLM) with the relative projections at the tide gauges (with VLM) on the same colour scale, for 2050, 2100 and the 2020–2100 trend.</p>
</a>

</div>

```{note}
If the files are missing, the notebook extracts only the required `total_<ssp>_medium_confidence_{values,rates}.nc` members (~110 MB per scenario) from the 8.7 GB Zenodo archive into `data/projections/sea_level/`, and caches the Pacific subset in `data/projections/regional/`.
```
