# Ocean biochemistry

Ocean biochemistry connects physical climate variability with marine ecosystems. This section analyses four complementary indicators within the selected national exclusive economic zone (EEZ): surface-ocean pH, chlorophyll-a concentration, estimated median phytoplankton size and subsurface dissolved oxygen.

## Open an analysis

<div class="dashboard-grid">

<a href="a_oceanic_pH.html" class="dashboard-card ocean">
  <h3>Ocean acidification: pH</h3>
  <p>Examine mean surface pH, spatial and temporal change, seasonal variability, point values and relationships with ENSO.</p>
</a>

<a href="b_chlorophyll.html" class="dashboard-card ocean">
  <h3>Chlorophyll-a</h3>
  <p>Analyse satellite chlorophyll-a as an indicator of phytoplankton abundance and marine productivity.</p>
</a>

<a href="c_phytoplankton.html" class="dashboard-card ocean">
  <h3>Phytoplankton size</h3>
  <p>Explore estimated median phytoplankton size, its trends, seasonal cycle and ENSO-related patterns.</p>
</a>

<a href="d_dissolved_o2.html" class="dashboard-card ocean">
  <h3>Dissolved oxygen</h3>
  <p>Assess subsurface oxygen concentration, spatial change, seasonal variability and climate modulation.</p>
</a>

</div>

## Workflow

All four notebooks use the common national site configuration in `data/sites/palau.json`, resolve paths from the CIndRA repository root and mask gridded observations to the configured Palau EEZ. They present a consistent sequence of mean conditions, trends, seasonal and annual variability, EEZ averages, the configured point and ENSO composites.

The cached input datasets are stored under `data/biochemistry/`; figures are written to `matrix_cc/figures/`.

```{note}
Biogeochemical indicators are derived from complementary satellite and model products. Differences in source, depth, spatial resolution and observational coverage should be considered when comparing indicators.
```

## Context

Ocean pH reflects acidification associated with uptake of atmospheric carbon dioxide. Chlorophyll-a is commonly used as a proxy for phytoplankton abundance, while phytoplankton size provides additional information about food-web structure. Subsurface oxygen is an indicator of marine habitat quality and the risk of hypoxic conditions. These variables can also respond to ENSO-driven changes in circulation, mixing, upwelling and air–sea exchange.
