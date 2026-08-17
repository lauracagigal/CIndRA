# Regional indicators

Regional workflows describe climate variability and change across Pacific stations, countries, EEZs and tropical-cyclone subregions. They complement the site-based national indicators by showing geographical contrasts and shared patterns across the wider Pacific.

## Prepare the regional data

<div class="dashboard-grid">

<a href="00_regional_setup.html" class="dashboard-card setup">
  <h3>Regional setup</h3>
  <p>Define the Pacific domain and prepare the station dictionary used by the regional air-temperature and rainfall analyses.</p>
</a>

</div>

## Explore the indicators

<div class="dashboard-grid">

<a href="air_temperature/air_temperature.html" class="dashboard-card atmosphere regional">
  <h3>Regional air temperature</h3>
  <p>Compare annual temperature indicators across stations and display spatial patterns over the Pacific.</p>
</a>

<a href="rainfall/rainfall.html" class="dashboard-card rainfall regional">
  <h3>Regional rainfall</h3>
  <p>Compare accumulated rainfall, dryness and heavy-rainfall indicators among stations and climate zones.</p>
</a>

<a href="tropical_cyclones/tropical_cyclones.html" class="dashboard-card cyclone regional">
  <h3>Regional tropical cyclones</h3>
  <p>Explore tracks, genesis seasonality, spatial density, intensity, trends and period differences in four Pacific subregions.</p>
</a>

<a href="regional_plots.html" class="dashboard-card ocean regional">
  <h3>Regional sea level</h3>
  <p>Reserved section for future comparisons of tide gauges, satellite altimetry and regional sea-level variability.</p>
</a>

</div>

## Data flow

Rainfall and air temperature use the multi-station dataset produced by the [regional setup](00_regional_setup.ipynb). Tropical cyclones independently load the all-basin IBTrACS archive and allocate observations to four Pacific subregions. Regional sea level is currently documented as a placeholder for future development.
