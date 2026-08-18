# References and data sources

The notebooks document indicator-specific references alongside their calculations. Principal external sources include:

- NOAA Global Historical Climatology Network Daily (GHCN-Daily) for rainfall and surface-air temperature.
- NOAA International Best Track Archive for Climate Stewardship (IBTrACS) for tropical cyclones.
- NOAA Oceanic Niño Index (ONI) for ENSO context.
- University of Hawaii Sea Level Center (UHSLC) tide-gauge records.
- Copernicus Marine Service (CMEMS) satellite-altimetry products.
- ERA5 monthly fields for supported Regional rainfall and temperature backgrounds.

See `assistant/skills/data-sources/SKILL.md` in the repository for URLs, units, cache conventions and attribution guidance.

## Data completeness and quality criteria

Rainfall and air-temperature station data are filtered once during the National or Regional setup workflow, before the cleaned records are cached and used by downstream indicator notebooks. The default `completeness_threshold` is **0.75** and is applied at two levels by `filter_by_time_completeness(...)` in `functions/data_downloaders.py`:

1. A month is retained when observations are available for at least 75% of its calendar days.
2. A year is retained when at least 75% of the months represented in that year pass the monthly criterion.

The filter returns the excluded months and years so that data loss can be inspected rather than hidden. Downstream notebooks should not apply a second completeness filter, because this can make results inconsistent with the cached station record. Partial first or final years still require explicit review, particularly when the input does not contain all 12 months.

For Regional rainfall and temperature analyses, stations are screened for a record span of at least **20 years** before download and must retain at least **20 valid years** after filtering. Regional trend maps use the same 20-year minimum to avoid displaying regressions based on very short records. These are minimum eligibility criteria, not a guarantee that a record is homogeneous or suitable for trend attribution.

Completeness is evaluated separately from observational quality control. Missing values, station relocation, instrument changes, changes in observing practice, duplicated timestamps and long temporal gaps can still affect an otherwise complete record. Station metadata and the lists of excluded months and years should therefore be reviewed before interpreting trends or comparing sites.

## Other methodological conventions

- **Reference periods:** rainfall and air-temperature anomalies normally use 1961–1990. Sea-level analyses use the record window specified in each notebook rather than this climatological baseline.
- **Rainfall thresholds:** a dry day has rainfall below 1 mm, a wet day has rainfall of at least 1 mm, and station-level heavy rainfall is above the 95th percentile of the available `PRCP` record.
- **Temperature extremes:** hot days (TX90p) and cold nights (TN10p) use calendar-day 90th- and 10th-percentile thresholds derived from the 1961–1990 base period.
- **Sea-level flooding:** the canonical minor-flood threshold is 30 cm above mean higher high water (MHHW).
- **Tropical cyclones:** named-storm, cyclone-strength and major/severe thresholds are at least 34, 64 and 96 kt, respectively. Analyses should state how missing wind observations and an incomplete final season are handled.
- **Trend reporting:** report the data source, station or site, analysis window, units, trend rate, p-value when available, reference period and whether the input was raw or completeness-filtered. Statistical significance does not by itself establish physical attribution.
- **Comparability:** station observations and gridded or satellite products provide different representations of climate. Reanalysis and satellite products supply spatial context but should not be described as interchangeable with in-situ station records.

The operational definitions and current defaults are documented in `assistant/CIndRA_role.md`, `assistant/skills/site-setup/SKILL.md`, `assistant/skills/regional-setup/SKILL.md` and the indicator-specific skills under `assistant/skills/`.
