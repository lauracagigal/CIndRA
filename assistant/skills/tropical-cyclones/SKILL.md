---
name: tropical-cyclones
description: Analyse, maintain, extend, and explain CIndRA tropical-cyclone workflows using IBTrACS and ONI for National site-vicinity and Regional Pacific-subregion notebooks. Use for cyclone tracks, Saffir-Simpson categories, severe cyclones, annual/monthly counts, trends, ENSO relationships, genesis regions, track density, period comparisons, ACE, cyclone tables and figures, IBTrACS caches, or changes to functions/tcs.py and notebooks/historical/{National,Regional}/tropical_cyclones/.
---

# Tropical Cyclones

Use repository functions for every calculation and published figure. Keep notebooks thin: configure → load/cache → call `functions/tcs.py` → save → display. Add missing reusable logic to `functions/tcs.py`, never as a notebook-local `def`.

## Choose the workflow

- For a cyclone analysis around one configured site, read [references/national.md](references/national.md).
- For Pacific subregions or basin comparisons, read [references/regional.md](references/regional.md).
- For any code change, inspect the current notebook and `functions/tcs.py` before relying on this documentation; preserve user changes in the worktree.

## Core data rules

1. Use NOAA IBTrACS v04r01 NetCDF through `download_ibtracs` in `functions/data_downloaders.py`.
2. Cache basin data as `data/tcs/tcs_<basin>.nc`; regional all-basin data uses `data/tcs/tcs_ALL.nc`.
3. Use `wmo_wind` in knots and `wmo_pres` in hPa. State when missing winds are omitted or estimated.
4. Use thresholds consistently: named storm `≥34 kt`, typhoon/hurricane/cyclone `≥64 kt`, major/severe `≥96 kt` or National category `≥3` after repository categorisation.
5. Do not call every `≥64 kt` system a hurricane. Use the configured regional label: Typhoon, Hurricane, or Cyclone.
6. Normalize longitude to 0–360° for Pacific subregion logic. Keep 180° edge handling explicit and non-overlapping for genesis classification.
7. Distinguish selection methods in every result: National storms enter a site radius; Regional counts use box entry; Regional genesis, ACE, and seasonality use exclusive first-position assignment.
8. Report the analysis window, source, units, selection method, threshold, trend rate per decade, p-value, and missing-wind treatment.

## Calculation integrity

- Count unique storms, not track observations, unless explicitly producing observation density.
- For spatial density, count a storm at most once per grid cell before dividing by years.
- Compute ACE as `1e-4 * sum(wind**2)` at 00/06/12/18 UTC for winds `≥34 kt`; assign complete-track ACE to genesis region/year. Describe WMO-wind ACE as internally consistent, not necessarily interchangeable with agency-specific ACE products.
- Use mutually exclusive classes for stacked bars: `34–63`, `64–(major_threshold-1)`, `≥major_threshold` kt.
- Use cumulative labels (`≥34`, `≥64`, `≥96 kt`) when areas overlap from zero.
- Avoid overlapping comparison periods unless explicitly requested. If boundary years are repeated, disclose it.
- Treat an incomplete final year explicitly when it could bias annual or monthly summaries.
- Fit trends on annual values with `scipy.stats.linregress`; use a solid line at `p < 0.05` and dotted otherwise. Report slope ×10 per decade.

## Plotting and persistence

- Call plotting helpers in `functions/tcs.py`; do not place complete matplotlib/cartopy figure construction in notebooks.
- Return `fig` and axes from helpers; call `fig.savefig(...)` before `plt.show()`.
- Use `dpi=300, bbox_inches="tight"`.
- Regional figures go to `outputs/figures/regional_<region_key>/` with `region_key="pacific"` and `TC_regional_*_<region_key>.png` filenames.
- Preserve the four regional colors and derive light/medium/dark intensity shades with `regional_intensity_colors`.
- Use readable publication sizing: panel titles at least 15 pt, axis labels 14 pt, ticks 12 pt, legends 11 pt; increase when panels remain legible.

## Validation

1. Parse every edited notebook code cell with `ast.parse`.
2. Run `python -m py_compile functions/tcs.py`.
3. Confirm notebooks contain no local function definitions when helpers belong in `tcs.py`.
4. Search all call sites after changing a function signature.
5. Run a small synthetic `xarray.Dataset` smoke test when the environment can import the scientific stack.
6. Do not redownload multi-gigabyte IBTrACS data merely to validate syntax.

## Hard rules

- Do not silently mix radius-based, box-entry, and genesis-based populations.
- Do not infer missing regional WMO winds unless the user explicitly requests it; National `fillwinds=True` uses the repository pressure–wind fit and must be disclosed.
- Do not use the 1961–1990 rainfall/temperature anomaly baseline for cyclones by default.
- Do not use GHCN regional station setup for the Regional cyclone notebook; it loads IBTrACS independently.
- Do not fabricate basin labels, category conversions, ACE equivalence, or statistical significance.
