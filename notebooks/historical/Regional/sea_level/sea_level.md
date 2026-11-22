# Regional sea level

Regional sea-level workflows combine Pacific-wide satellite altimetry with every UHSLC tide gauge located inside a Pacific EEZ. They show where absolute sea level has risen fastest, how tide-gauge (relative) trends differ because of vertical land motion, how ENSO redistributes sea level across the basin, and how often tide gauges have recorded minor flooding.

## Open the analysis

<div class="dashboard-grid">

<a href="regional_indicators.html" class="dashboard-card ocean regional">
  <h3>Regional sea-level indicators</h3>
  <p>Altimetry trend map with tide-gauge trends, regional-mean sea level, five-year anomalies, ENSO regression and minor-flood days at Pacific tide gauges.</p>
</a>

</div>

```{note}
The notebook downloads monthly CMEMS altimetry for the Pacific window (125°E–115°W, 35°S–35°N) into `data/regional/sea_level/` and UHSLC Fast Delivery records into `data/sea_level/`. It does not use the regional GHCN station dictionary.
```
