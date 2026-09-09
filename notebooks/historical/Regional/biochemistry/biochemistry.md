# Regional marine biochemistry

These workflows compare surface-ocean biogeochemical conditions across the Pacific and its EEZs. Each notebook uses the same regional layout: long-term mean, linear trend, seasonal climatology and anomalies, an area-weighted time series, three ENSO-phase anomaly maps relative to the complete-period mean, and an EEZ summary table.

The annual regional series are interactive: move over the figure to inspect values, zoom into a period or hide traces from the legend. The trend is continuous when statistically significant (`p < 0.05`) and dashed otherwise; its rate and significance are reported in the legend.

## Open the analyses

<div class="dashboard-grid">

<a href="a_oceanic_pH.html" class="dashboard-card ocean regional">
  <h3>Oceanic pH</h3>
  <p>Map surface pH, acidification trends, seasonal variability and ENSO modulation.</p>
</a>

<a href="b_chlorophyll.html" class="dashboard-card ocean regional">
  <h3>Chlorophyll-a</h3>
  <p>Explore the regional distribution, trend and climate variability of satellite chlorophyll-a.</p>
</a>

<a href="c_phytoplankton.html" class="dashboard-card ocean regional">
  <h3>Phytoplankton size</h3>
  <p>Compare the experimental median phytoplankton-size indicator across the region and ENSO phases.</p>
</a>

<a href="c2_phytoplankton.html" class="dashboard-card ocean regional">
  <h3>Phytoplankton biomass</h3>
  <p>Analyse Copernicus Marine surface phytoplankton carbon biomass, including trends, full-period ENSO anomalies and EEZ summaries.</p>
</a>

<a href="d_dissolved_o2.html" class="dashboard-card ocean regional">
  <h3>Dissolved oxygen</h3>
  <p>Assess surface dissolved oxygen means, changes, seasonality and EEZ differences.</p>
</a>

</div>

## Regional input data

Pacific-wide NetCDF files are read from `data/regional/biochemistry/`. The MD50 notebook uses the NOAA PIFSC product; pH, chlorophyll-a, phytoplankton biomass and dissolved oxygen share the Copernicus Marine cache. National subsets are never used as regional results. If a download fails, execution stops with a clear error instead of falling back to Palau data.

The Copernicus workflows share `copernicus_bgc_pacific_surface_monthly.nc`; the MD50 workflow uses `MD50_pacific_monthly.nc`. Before the first Copernicus download, configure credentials once with `copernicusmarine login`. Credentials are not stored in the notebooks.

The five regional notebooks share a common template. After changing that template, regenerate them from the repository root with:

```bash
python functions/build_regional_biochemistry_notebooks.py
```
