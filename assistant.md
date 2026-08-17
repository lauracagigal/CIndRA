# CIndRA Assistant

CIndRA — the **Climate Indicator Research Assistant** — is a specialized assistant for working with the climate-indicator methods, notebooks and conventions in this repository. It is designed to help researchers configure analyses, understand the methodology, modify code, diagnose problems and produce consistent outputs for Pacific Island sites and regions.

The assistant covers national and regional **rainfall**, **air temperature**, **sea level** and **tropical cyclone** workflows. It also understands the repository's data sources, units, reference periods, quality-control rules, function API and output naming conventions.

## Explore its components

<div class="dashboard-grid">

<a href="https://github.com/lauracagigal/CIndRA/blob/main/assistant/CIndRA_role.md" class="dashboard-card atmosphere">
  <h3>Role and instructions</h3>
  <p>The assistant's identity, scientific scope, repository layout, calculation rules, data sources and expected behaviour.</p>
</a>

<a href="https://github.com/lauracagigal/CIndRA/tree/main/assistant/skills" class="dashboard-card regional">
  <h3>Specialized skills</h3>
  <p>Focused instructions for each indicator and workflow, loaded when a question concerns that particular topic.</p>
</a>

<a href="https://github.com/lauracagigal/CIndRA/blob/main/assistant/aggregated_CIndRA_markdowns.md" class="dashboard-card rainfall">
  <h3>Aggregated knowledge file</h3>
  <p>A generated single-file version of the role, skills and supporting documentation for platforms that accept one knowledge upload.</p>
</a>

<a href="https://github.com/lauracagigal/CIndRA/blob/main/assistant/build_aggregated_CIndRA.py" class="dashboard-card setup">
  <h3>Build script</h3>
  <p>The reproducible script that combines all assistant documentation after its source instructions have changed.</p>
</a>

</div>

## How it is built

The assistant separates stable, repository-wide knowledge from task-specific guidance:

```text
assistant/
├── CIndRA_role.md                 # identity, scope and global rules
├── skills/
│   ├── site-setup/                # shared National atmosphere setup
│   ├── national-rainfall/         # all National rainfall indicators
│   ├── national-temperature/      # all National temperature indicators
│   ├── regional-atmosphere/       # Regional rainfall and temperature
│   ├── trend-analysis/, flood-frequency/, ...
│   ├── tropical-cyclones/
│   ├── functions-api/
│   ├── data-sources/
│   └── output-conventions/
├── build_aggregated_CIndRA.py     # deterministic knowledge-file builder
└── aggregated_CIndRA_markdowns.md # generated upload-ready document
```

`CIndRA_role.md` supplies the persistent scientific and operational context. Each `SKILL.md` contains the detailed procedure, definitions, inputs, outputs and safeguards for a bounded domain or specialized task. Closely related notebooks share one skill with internal routing, which avoids repeating setup, plotting and persistence instructions.

The aggregated document is generated from those source files; it should not be edited manually. The source role and skills remain the authoritative material.

## What CIndRA can help with

<div class="dashboard-grid">

<a href="notebooks/historical/National/national.html" class="dashboard-card atmosphere">
  <h3>National workflows</h3>
  <p>Select and configure a site, run indicators in the correct order, interpret outputs and keep figures and tables consistent.</p>
</a>

<a href="notebooks/historical/Regional/regional.html" class="dashboard-card regional">
  <h3>Regional workflows</h3>
  <p>Work with multi-station climate indicators and the four Pacific tropical-cyclone subregions.</p>
</a>

<a href="notebooks/historical/Regional/tropical_cyclones/tropical_cyclones.html" class="dashboard-card cyclone">
  <h3>Tropical cyclones</h3>
  <p>Use IBTrACS and ONI consistently for tracks, seasonality, spatial density, intensity, trends, period comparisons and ACE.</p>
</a>

<a href="https://github.com/lauracagigal/CIndRA/tree/main/functions" class="dashboard-card ocean">
  <h3>Functions and code</h3>
  <p>Find and reuse the canonical calculation, plotting, persistence and data-access functions before adding new implementations.</p>
</a>

</div>

Typical requests include:

- explaining an indicator, threshold, unit or reference period;
- identifying which setup and analysis notebooks must be run;
- adapting a national workflow to another configured site;
- adding a figure while preserving the established visual conventions;
- diagnosing missing data, incomplete station coverage or path problems;
- locating the canonical function for a calculation or plot;
- comparing national results with their regional context; and
- documenting a new notebook, output or data source.

## How to use it

### In an Agent-Skills-compatible coding assistant

Make the `assistant/skills/` directory available in the client's skill-discovery location and use `CIndRA_role.md` as the project or agent instructions. The client can then load only the relevant skill when a request concerns rainfall, temperature, sea level, cyclones, setup, functions or outputs.

Ask for the outcome in plain language and include the relevant scale, indicator and site when known. For example:

> Update the national heavy-rainfall indicator for the configured Palau station, reuse the existing plotting functions and save the figure using the repository convention.

### In a custom assistant with uploaded knowledge

Use `CIndRA_role.md` as the main instruction text and upload the individual skill files as knowledge. If the platform is easier to configure with a single knowledge document, upload `aggregated_CIndRA_markdowns.md` instead.

```{important}
The aggregated file duplicates the source role and skills. Upload either the individual knowledge files or the aggregated file to avoid redundant context.
```

### Asking effective questions

Provide the country or `site_key`, the National or Regional scale, the desired indicator, the analysis period and whether you want explanation, diagnosis or implementation. If these are already defined in a site configuration or notebook, ask CIndRA to inspect and reuse them rather than repeating values manually.

## Updating the assistant

The assistant documentation must evolve with the analytical code:

1. Update the relevant `SKILL.md` whenever a workflow, threshold, input or output changes.
2. Update `CIndRA_role.md` when the change affects the assistant's general scope, repository map or global conventions.
3. Add a new skill for a genuinely new notebook or bounded workflow.
4. Add that skill to `SOURCE_FILES` in `build_aggregated_CIndRA.py`.
5. Regenerate the combined knowledge document:

   ```bash
   python assistant/build_aggregated_CIndRA.py
   ```

6. Review the generated diff and validate that paths, function names, units and notebook status still match the repository.

```{warning}
The assistant is only as current as its source instructions. When analytical code changes without a corresponding documentation update, it may recommend an outdated function, path or convention.
```

## Scientific safeguards

CIndRA is instructed to reuse validated repository functions, distinguish observations from reanalysis, preserve units, report data completeness and avoid silently inventing station identifiers or unsupported workflows. Its answers and generated code should still be reviewed by a domain expert before publication or operational use, particularly when interpreting trends, rare extremes and incomplete observational records.

For the complete setup and maintenance instructions, see the [assistant README on GitHub](https://github.com/lauracagigal/CIndRA/blob/main/assistant/README.md).
