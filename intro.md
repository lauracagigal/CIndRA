# CIndRA Climate Indicators

This Jupyter Book contains the National and Regional climate-indicator notebooks maintained in the CIndRA repository. It supports reproducible analysis and capacity building for Pacific Island climate monitoring.

The book is organized into two principal parts:

- **National indicators** — site- and EEZ-based air-temperature, rainfall, tropical-cyclone, sea-surface-temperature, marine-biochemistry and sea-level workflows.
- **Regional indicators** — Pacific-wide atmosphere, tropical-cyclone, sea-surface-temperature, marine-heatwave and marine-biochemistry analyses, plus the regional sea-level placeholder.

Each section exposes the scientific narrative, executable code, stored outputs and links back to the source repository. Data-intensive notebooks are not automatically re-executed during the website build; run them in their documented order to refresh data and figures before publishing.

The complete source repository is available at [github.com/lauracagigal/CIndRA](https://github.com/lauracagigal/CIndRA).

## Explore the book

<div class="dashboard-grid">

<a href="notebooks/historical/National/national.html" class="dashboard-card atmosphere">
  <h3>National indicators</h3>
  <p>Configure an individual Pacific site or EEZ and explore atmosphere, tropical cyclones, ocean temperature, biochemistry and sea level.</p>
</a>

<a href="notebooks/historical/Regional/regional.html" class="dashboard-card regional">
  <h3>Regional indicators</h3>
  <p>Compare climate and ocean conditions across Pacific stations, countries, EEZs and tropical-cyclone subregions.</p>
</a>

<a href="assistant.html" class="dashboard-card cyclone">
  <h3>CIndRA Assistant</h3>
  <p>Learn how the climate-indicator assistant is structured, how to use its specialized skills and how to keep its knowledge current.</p>
</a>

<a href="references.html" class="dashboard-card setup">
  <h3>References</h3>
  <p>Consult the principal datasets, scientific literature and supporting resources used throughout the analyses.</p>
</a>

</div>

```{admonition} Recommended workflow
:class: tip
Run the relevant setup notebook first, execute the indicator notebooks to refresh their outputs, and then build the book with `jupyter-book build .`.
```
