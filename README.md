# CIndRA Climate Indicators

[![Jupyter Book](https://img.shields.io/badge/Jupyter%20Book-open-2f6f9f?logo=jupyter&logoColor=white)](https://lauracagigal.github.io/CIndRA/intro.html)
[![Deploy book](https://github.com/lauracagigal/CIndRA/actions/workflows/deploy-book.yml/badge.svg)](https://github.com/lauracagigal/CIndRA/actions/workflows/deploy-book.yml)
[![License: GPL v2](https://img.shields.io/badge/License-GPL%20v2-blue.svg)](LICENSE)

Reproducible climate-indicator workflows for Pacific Island countries and subregions, covering the atmosphere, tropical cyclones and the ocean.

## Explore the published book

The complete documentation, scientific narrative, notebooks and stored results are available in the interactive Jupyter Book:

### [Open the CIndRA Climate Indicators Book →](https://lauracagigal.github.io/CIndRA/intro.html)

The book provides guided navigation through the National and Regional analyses, explanations of each indicator and a dedicated section describing the CIndRA Assistant.

## Indicators

| Theme | National analyses | Regional analyses |
|---|---|---|
| **Air temperature** | Mean, minimum and maximum temperature, diurnal range, hot days and cold nights | Multi-station indicators, Pacific maps, regional anomaly series and supported ERA5 context |
| **Rainfall** | Annual and seasonal totals, anomalies, dry days, consecutive dry spells and heavy rainfall | Multi-station indicators, Pacific trend maps and supported ERA5 context |
| **Tropical cyclones** | Cyclones entering a configurable radius around a site, including severe systems and ENSO context | Tracks, genesis seasonality, spatial density, intensity, period comparisons, trends and ACE for four Pacific subregions |
| **Sea level** | Satellite and tide-gauge trends, anomalies, minor flooding and extreme-level rankings | Documented placeholder and experimental foundations for future development |

## Project organization

```text
CIndRA/
├── notebooks/historical/
│   ├── National/                 # site-based indicator workflows
│   └── Regional/                 # Pacific multi-station/subregion workflows
├── functions/                    # reusable calculations, plotting and I/O
├── assistant/                    # CIndRA role, skills and knowledge builder
├── data/                         # local source-data caches and site settings
├── outputs/                      # generated figures, tables and metrics
├── _config.yml                   # Jupyter Book configuration
└── _toc.yml                      # published book structure
```

The setup notebooks prepare shared data and configuration. Indicator notebooks then load those cached inputs and call the reusable modules in `functions/`. National outputs are organized by configured site, while Regional outputs use a Pacific region key.

## Running the analyses

The recommended order is:

1. Open the relevant National or Regional setup notebook.
2. Select or configure the site, station or region.
3. Run the indicator notebooks in the order shown in the Jupyter Book.
4. Review completeness and quality-control diagnostics.
5. Save notebook outputs before rebuilding the documentation.

Some workflows access external datasets such as NOAA GHCN-Daily, NOAA IBTrACS and ONI, UHSLC tide gauges, CMEMS satellite altimetry and ERA5. Cached data and credentials are not necessarily distributed with the repository.

## Building the Jupyter Book locally

Install the documentation dependency and build from the repository root:

```bash
python -m pip install -r requirements-book.txt
jupyter-book build .
```

Open `_build/html/index.html` in a browser to inspect the result. The build renders the outputs already stored in the notebooks and does not automatically rerun data-intensive analyses.

## Publishing

Pushes to `main` trigger [`.github/workflows/deploy-book.yml`](.github/workflows/deploy-book.yml), which builds the book and deploys `_build/html` to GitHub Pages.

The repository must have **Settings → Pages → Source → GitHub Actions** enabled. After a successful deployment, the site is published at:

<https://lauracagigal.github.io/CIndRA/intro.html>

## CIndRA Assistant

The `assistant/` directory contains the domain knowledge used to configure CIndRA as a specialized climate-indicator assistant:

- [`CIndRA_role.md`](assistant/CIndRA_role.md) defines its scope and global scientific rules.
- [`skills/`](assistant/skills) contains focused National, Regional and cross-cutting workflows.
- [`aggregated_CIndRA_markdowns.md`](assistant/aggregated_CIndRA_markdowns.md) combines the role and skills for platforms that accept a single knowledge file.
- [`build_aggregated_CIndRA.py`](assistant/build_aggregated_CIndRA.py) regenerates that combined document.

After changing any assistant source document, run:

```bash
python assistant/build_aggregated_CIndRA.py
```

## License

This project is distributed under the [GNU General Public License v2.0](LICENSE).
