---
name: marine-biochemistry
description: Execute the repository-supported National EEZ and Regional Pacific pH, chlorophyll-a, phytoplankton-size/biomass and dissolved-oxygen workflows. Use for biogeochemical maps, trends, seasonality, time series, ENSO anomalies or EEZ summaries.
---

# Marine biochemistry

Use the current code from `https://github.com/lauracagigal/CIndRA`. Supported
indicators are limited to:

- surface pH: `a_oceanic_pH.ipynb`;
- chlorophyll-a: `b_chlorophyll.ipynb`;
- NOAA PIFSC MD50 median phytoplankton size: `c_phytoplankton.ipynb`;
- Copernicus surface phytoplankton carbon biomass (`phyc`): Regional
  `c2_phytoplankton.ipynb` only;
- dissolved oxygen: `d_dissolved_o2.ipynb`.

National notebooks live under `notebooks/historical/National/biochemistry/` and
Regional notebooks under `notebooks/historical/Regional/biochemistry/`. The shared
Regional template is maintained in `functions/build_regional_biochemistry_notebooks.py`.

## National location rule

For any National location other than the active saved configuration, run
`notebooks/historical/National/00_site_setup.ipynb` first. Present the resolved
location/EEZ and any available choices to the user, obtain their decision, save the
configuration, and validate dataset coverage before analysis. Never replace Palau
coordinates with guessed coordinates directly inside a biochemistry notebook.

## Regional data

- Copernicus Marine dataset: `cmems_mod_glo_bgc_my_0.25deg_P1M-m`, variables `ph`,
  `chl`, `phyc`, `o2`, surface depth. The four notebooks share
  `data/regional/biochemistry/copernicus_bgc_pacific_surface_monthly.nc`.
- NOAA PIFSC experimental MD50: `md50_exp_2025`, cached as
  `data/regional/biochemistry/MD50_pacific_monthly.nc`.
- National subsets must never be used as Regional results. Stop on a missing Regional
  cache/download instead of falling back to Palau data.
- Copernicus credentials are configured outside notebooks with
  `copernicusmarine login`; never request that users paste credentials into chat or code.

## Supported analysis

Execute the corresponding notebook to produce its long-term mean, gridded linear
trend, seasonal climatology/anomalies, area-weighted annual interactive series,
three-panel ENSO anomalies and EEZ summary. Trend lines are solid for `p < 0.05` and
dashed otherwise, with rate and significance in the legend.

ENSO phase panels are La Niña, Neutral and El Niño composites minus the grid-cell mean
over the complete analysis period. Use one symmetric diverging scale centered on zero.
Do not use Neutral as the anomaly reference.

## Interpretation and execution boundary

Always state variable units, source, depth, period, spatial resolution and National EEZ
or Regional scope. MD50 is experimental; Copernicus variables are model/reanalysis
products and must not be described as direct in-situ observations.

Locate and execute repository code before returning a value, table or figure. Do not
derive additional biogeochemical indicators, combine variables into a new index or
invent missing spatial coverage. If the requested output is absent from these
notebooks, say it is not currently supported by CIndRA.
