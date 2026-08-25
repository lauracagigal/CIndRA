# Sea-surface temperature

Sea-surface temperature (SST) describes thermal conditions at the ocean surface and is an important indicator of climate change, ENSO variability and stress on marine ecosystems. The national workflow restricts the gridded SST product to a selected Pacific Island country's exclusive economic zone (EEZ).

## Open the analysis

<div class="dashboard-grid">

<a href="a_Mean_Temperature_maps.html" class="dashboard-card ocean">
  <h3>National SST maps and indicators</h3>
  <p>Calculate mean SST, spatial trends, seasonal and annual anomalies, EEZ-area averages, point values and SST patterns associated with ONI categories.</p>
</a>

</div>

## Workflow

The notebook resolves the selected country against the Pacific EEZ shapefile, checks that the SST grid overlaps it and masks cells outside the boundary. Maps and time series therefore describe the selected EEZ rather than an arbitrary rectangular subset.

```{note}
The SST NetCDF must cover the selected EEZ and provide coordinates named `time`, `lat` and `lon`, together with the configured SST variable.
```
