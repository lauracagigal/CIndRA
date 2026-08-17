# National indicators

The national workflows turn observations and gridded climate products into indicators for an individual Pacific Island country or monitoring site. They provide reproducible calculations, figures and contextual information for reporting changes in the atmosphere, tropical cyclones and the ocean.

Select a section below to open its overview and access the corresponding notebooks.

## Prepare a national analysis

<div class="dashboard-grid">

<a href="00_site_setup.html" class="dashboard-card setup">
  <h3>Atmosphere site setup</h3>
  <p>Select the country and station, configure the analysis period, and prepare the daily temperature and rainfall observations shared by the atmosphere indicators.</p>
</a>

<a href="sea_level/0_site_setup.html" class="dashboard-card setup">
  <h3>Sea-level site setup</h3>
  <p>Configure tide-gauge and satellite-altimetry inputs before running the national sea-level indicators.</p>
</a>

</div>

## Explore the indicators

<div class="dashboard-grid">

<a href="air_temperature/surface_temperature.html" class="dashboard-card atmosphere">
  <h3>Air temperature</h3>
  <p>Mean temperature, minimum and maximum temperature, diurnal range, hot days and cold nights.</p>
</a>

<a href="rainfall/rainfall.html" class="dashboard-card rainfall">
  <h3>Rainfall</h3>
  <p>Annual totals, rainfall anomalies, dry days, consecutive dry spells and heavy-rainfall events.</p>
</a>

<a href="tropical_cyclones/tropical_cyclones.html" class="dashboard-card cyclone">
  <h3>Tropical cyclones</h3>
  <p>Nearby cyclone tracks, intensity, seasonality and trends for all systems and severe tropical cyclones.</p>
</a>

<a href="sea_level/sea_level.html" class="dashboard-card ocean">
  <h3>Sea level</h3>
  <p>Relative and absolute sea-level trends, anomalies, minor flooding and rankings of extreme water levels.</p>
</a>

</div>

## Recommended workflow

1. Run the relevant setup notebook to select the site and prepare its data.
2. Execute the indicator notebooks in the order shown in the navigation menu.
3. Review the data-completeness diagnostics before interpreting trends.
4. Save the refreshed notebook outputs and rebuild the book for publication.

```{note}
Air temperature and rainfall share the atmosphere setup. Tropical-cyclone notebooks use the configured site coordinates together with NOAA IBTrACS, while sea level has a separate setup because it uses tide-gauge and satellite products.
```
