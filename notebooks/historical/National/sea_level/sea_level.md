# Sea level

Sea level is the height of the ocean surface. Rising sea level is a crucial issue for Pacific islands: it increases coastal flooding when combined with tides and waves, drives shoreline erosion that damages built and natural infrastructure, and causes saltwater intrusion into aquifers and agricultural land.

Changes in **absolute** sea level, relative to the Earth's centre, are measured by satellite altimeters (EU Copernicus, NASA/CNES). Changes in **relative** sea level, with respect to the land at a particular location, are measured by tide gauges such as those operated by the University of Hawaii Sea Level Center (UHSLC). Differences between the two arise from vertical land motion, local oceanography and the different spatial scales of the measurements.

Sea level is also highly variable in time. In the western tropical Pacific, the highest levels tend to occur with perigean spring ("king") tides, and ENSO causes large fluctuations: sea level is typically lower during El Niño and higher during La Niña.

## Prepare the analysis

<div class="dashboard-grid">

<a href="00_sea_level_setup.html" class="dashboard-card setup">
  <h3>Sea-level site setup</h3>
  <p>Select the UHSLC tide gauge and EEZ, download tide-gauge records and check the CMEMS altimetry coverage.</p>
</a>

</div>

## Open the indicators

<div class="dashboard-grid">

<a href="a_sea_level_trend.html" class="dashboard-card ocean">
  <h3>Absolute and relative sea-level change</h3>
  <p>Altimetry and tide-gauge trends, EEZ-mean sea level, change maps and the sensitivity to ENSO.</p>
</a>

<a href="b_sea_level_anomaly.html" class="dashboard-card ocean">
  <h3>Sea-level anomalies</h3>
  <p>Detrended storm-year and monthly anomalies at the gauge, period-mean anomaly maps and ENSO phases.</p>
</a>

<a href="c_sea_level_ff.html" class="dashboard-card ocean">
  <h3>Minor flooding</h3>
  <p>Days and hours above 30 cm over MHHW per storm year, trends, monthly distribution and ENSO context.</p>
</a>

<a href="d_sea_level_rankings.html" class="dashboard-card ocean">
  <h3>Extreme sea-level rankings</h3>
  <p>Top-10 highest and lowest hourly sea levels with the ENSO phase of each event.</p>
</a>

</div>

```{note}
Sea level uses its own setup because it relies on a UHSLC tide gauge and CMEMS altimetry rather than the GHCN station of the atmosphere setup. CMEMS downloads require a Copernicus Marine account (`copernicusmarine login`).
```
