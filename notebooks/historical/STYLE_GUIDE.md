# Notebook style guide

National and Regional notebooks share a common presentation standard while retaining
the methods and visual forms appropriate to each indicator.

## Structure

1. Use one level-one title (`#`) naming the indicator and spatial scope.
2. Organize the workflow with level-two sections (`##`) and reserve deeper headings
   for subsections.
3. Introduce the data source, period, spatial domain and reference period before the
   analysis.
4. End analytical notebooks with **Interpretation and reproducibility notes**.
5. Keep setup notebooks explicit about the files or configuration they create.

## Figures and tables

- Titles state the variable, spatial scope and period when relevant.
- Axes and colorbars always include units; legends and axis labels must remain legible
  at the size used in the Jupyter Book.
- Maps show coastlines and the relevant EEZ or regional boundaries.
- Diverging anomaly scales are centered on zero and shared across comparable panels.
- Line-based time series with trends are interactive where practical. Trend lines are
  solid when significant (`p < 0.05`) and dashed otherwise, with the rate and
  significance stated in the legend.
- Tables use stable, descriptive column names and retain missing values as missing
  rather than silently converting them to zero.

## Interpretation

- State the source and important limits of the observations or model product.
- Distinguish spatial averages from point or station measurements.
- Treat linear trends as descriptive unless autocorrelation and other statistical
  assumptions have explicitly been addressed.
- Explain the reference used for anomalies. ENSO phase maps use the complete-period
  mean unless a notebook explicitly documents another scientific baseline.
- Do not compare indicators without considering differences in coverage, resolution,
  depth, completeness and uncertainty.

## Technical conventions

- Resolve data and output paths from the CIndRA repository root.
- Use the `cc_indicators_v2` kernel metadata throughout the published collection.
- Cache large downloads and never store passwords or access tokens in notebooks.
- Keep expensive execution disabled during the Jupyter Book build; refresh and save
  notebook outputs before publication.
