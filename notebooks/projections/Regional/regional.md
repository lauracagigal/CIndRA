# Regional projections

The regional projection workflows summarise how the climate of the whole Pacific Islands region is expected to change under the CMIP6 scenarios, using the same data and global warming levels (+1.5, +2.0, +2.5 and +3.0 °C above 1850–1900) as the [national projections](../National/national.md).

Projections are averaged over these spatial units:

* every **Pacific EEZ** (one mean per country), shown as maps of the trend over 2015–2100 and of the change at each warming level;
* **all the EEZs together**, shown as box plots across models at each warming level for air temperature, rainfall, sea surface temperature and marine heatwaves (sea level uses the mean over the whole Pacific window);
* four **ocean regions**, used **only for the biochemical indicators** (pH, aragonite, salinity): North Pacific Subtropical Gyre, Equatorial Upwelling, Western Equatorial Pacific and South Pacific Subtropical Gyre. For these indicators the maps show the gridded field over the whole Pacific window instead of EEZ means, and trends, tables and box plots are computed in the four regions.

## Prepare the regional analysis

<div class="dashboard-grid">

<a href="00_regional_setup.html" class="dashboard-card setup">
  <h3>Regional setup</h3>
  <p>EEZs and ocean regions, warming-level years, and the cached regional means used by every indicator notebook.</p>
</a>

</div>

## Explore the projections

<div class="dashboard-grid">

<a href="air_temperature/air_temperature.html" class="dashboard-card atmosphere">
  <h3>Air temperature</h3>
  <p>Mean, minimum and maximum temperature, warm days and cold nights.</p>
</a>

<a href="rainfall/rainfall.html" class="dashboard-card rainfall">
  <h3>Rainfall</h3>
  <p>Annual totals, dry days, heavy-rainfall days and annual maximum daily rainfall.</p>
</a>

<a href="tropical_cyclones/tropical_cyclones.html" class="dashboard-card cyclone">
  <h3>Tropical cyclones</h3>
  <p>Change in the number of tropical cyclones and in their genesis latitude in four Pacific subregions (CMIP6-HighResMIP).</p>
</a>

<a href="sea_surface_temperature/sea_surface_temperature.html" class="dashboard-card ocean">
  <h3>Sea-surface temperature</h3>
  <p>SST and marine heatwave days per year.</p>
</a>

<a href="biochemistry/biochemistry.html" class="dashboard-card ocean">
  <h3>Ocean biogeochemistry</h3>
  <p>Surface pH, aragonite saturation state and salinity.</p>
</a>

<a href="sea_level/sea_level.html" class="dashboard-card ocean">
  <h3>Sea level</h3>
  <p>IPCC AR6 projected sea-level change and rates of rise (no vertical land motion).</p>
</a>

</div>

Outputs: figures in `outputs/figures/regional_pacific/PRJ_*.png`, tables in `outputs/tables/regional_pacific/PRJ_*.csv`; regional means are cached in `data/projections/regional/`.
