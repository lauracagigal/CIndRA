---
name: marine-heatwaves
description: Execute the repository-supported National EEZ/point and Regional Pacific marine-heatwave workflows using NOAA OISST and functions/marineHeatWaves.py. Use for MHW events, days, duration, intensity, severity, trends, ENSO anomalies, decadal maps or EEZ summaries.
---

# Marine heatwaves

Use only the implementations in the canonical CIndRA repository:

- `notebooks/historical/National/sea_surface_temperature/c_MHW.ipynb`
- `notebooks/historical/Regional/sea_surface_temperature/mhw_regional.ipynb`
- `functions/marineHeatWaves.py`

The implementation derives from the marineHeatWaves code by Eric Oliver and retains
the references included in the notebooks. Do not replace it with a different package
or reimplement the detector from memory.

## National workflow

For a new National location, run `notebooks/historical/National/00_site_setup.ipynb`
and obtain the user's location/EEZ choice before running MHW analysis. Validate that
the available SST product covers the selected EEZ.

Run the EEZ-wide analysis first. It produces the representative EEZ-average SST/MHW
series, annual indicators and event tables. Only then offer the point analysis; ask
the user for the point or let them select one inside the validated EEZ. Do not choose
a point silently.

## Regional workflow

Use daily NOAA OISST across the configured Pacific extent with all EEZ boundaries.
Respect `horizontal_stride` and report it: stride 8 is a coarse approximately 2°
analysis and is not equivalent to native 0.25° results. Reuse the metrics cache only
when its period, climatology and stride match the current configuration.

Supported outputs include annual MHW days and trends, event frequency, duration and
intensity, five-year anomalies, decadal number/severity/duration maps, ENSO phase maps
and EEZ summaries. Do not produce an MHW quantity absent from these notebooks.

## Scientific invariants

- Use the climatology period declared in the notebook and ensure it lies inside the
  available record.
- Default detection uses the 90th percentile, minimum duration of five days and the
  configured gap-joining parameters.
- ENSO events follow the five-consecutive-month ONI rule.
- ENSO phase anomalies are `phase composite − complete-period mean`, including the
  Neutral panel; they are not differences from Neutral.
- Preserve missing values. Do not treat unavailable grid cells or incomplete years as
  zero-event observations.
- Report units and distinguish event count, MHW days, duration, intensity and category.

## Execution boundary

Locate and execute the relevant notebook/functions before returning values or figures.
If data, dependencies or execution access are unavailable, state the blocker. If the
requested analysis is not one of the supported outputs above, say it is not currently
implemented in CIndRA rather than improvising it.
