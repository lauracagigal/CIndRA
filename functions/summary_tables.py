"""Metric | Value summary tables built from annual series.

Same layout as the national station summaries (e.g. ``R_dry_summary_table_<station>.csv``): one
``Metric`` / ``Value`` row per statistic, blank rows between sections. Used by the regional notebooks
(and the national ones that had no summary table) so every indicator in the product matrix
(``matrix_cc/products.js``) has one.

    table = combine_sections([
        annual_series_summary(series, 'MHW days per year', 'days'),
        annual_series_summary(other, 'MHW events per year', 'events'),
    ])
    save_summary_table(table, table_dir, 'MHW_regional_summary_table_pacific.csv')
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


def _fmt_unit(units: str) -> str:
    return f" ({units})" if units else ""


def annual_series_summary(
    series: pd.Series,
    label: str,
    units: str = "",
    window: int = 11,
    significance_level: float = 0.05,
    title: str | None = None,
    extra_rows: list[tuple[str, object]] | None = None,
) -> pd.DataFrame:
    """Summary statistics of one annual series (index = year).

    Rows: period average, change since the first year implied by the linear trend, rate of change
    per decade with its p-value, the mean of the first and last ``window`` years, and the highest and
    lowest annual values with their years. ``title`` adds a heading row; ``extra_rows`` are appended
    as ``(metric, value)`` pairs (e.g. number of stations).
    """
    s = pd.Series(series).dropna().sort_index()
    s.index = s.index.astype(int)
    y0, y1 = int(s.index.min()), int(s.index.max())
    u = _fmt_unit(units)
    rows: list[tuple[str, object]] = []
    if title:
        rows.append((title, ""))
    rows.append((f"Average {label}, {y0}–{y1}{u}", s.mean()))
    if len(s) >= 3:
        fit = stats.linregress(s.index.to_numpy(float), s.to_numpy(float))
        rows += [
            (f"Change in {label} since {y0}{u}", fit.slope * (y1 - y0)),
            (f"Rate of change in {label}{_fmt_unit(f'{units}/decade' if units else 'per decade')}", fit.slope * 10),
            ("Trend p-value", "< 0.001" if fit.pvalue < 0.001 else round(float(fit.pvalue), 3)),
            (f"Trend significant at {100 * (1 - significance_level):.0f}%", "Yes" if fit.pvalue < significance_level else "No"),
        ]
    first = s.loc[s.index <= y0 + window - 1]
    last = s.loc[s.index >= y1 - window + 1]
    rows += [
        (f"Average {label}: {first.index.min()}–{first.index.max()}{u}", first.mean()),
        (f"Average {label}: {last.index.min()}–{last.index.max()}{u}", last.mean()),
        (f"Highest annual {label} ({s.idxmax()}){u}", s.max()),
        (f"Lowest annual {label} ({s.idxmin()}){u}", s.min()),
    ]
    rows += extra_rows or []
    return pd.DataFrame(rows, columns=["Metric", "Value"])


def combine_sections(sections: list[pd.DataFrame], decimals: int = 3) -> pd.DataFrame:
    """Stack summary sections with a blank row between them and round the numeric values."""
    blank = pd.DataFrame([(" ", "")], columns=["Metric", "Value"])
    parts = []
    for i, section in enumerate(sections):
        if i:
            parts.append(blank)
        parts.append(section)
    table = pd.concat(parts, ignore_index=True)
    table["Value"] = [
        int(v) if isinstance(v, (int, np.integer)) and not isinstance(v, bool)
        else round(float(v), decimals) if isinstance(v, (float, np.floating)) else v
        for v in table["Value"]
    ]
    return table


def save_summary_table(table: pd.DataFrame, table_dir: str | Path, filename: str) -> Path:
    """Write ``table`` as CSV under ``table_dir`` (created if needed) and return the path."""
    path = Path(table_dir) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(path, index=False)
    print(f"Saved summary table ({len(table)} rows) to {path}")
    return path


def station_average_summary(
    annual_data: dict[str, pd.DataFrame],
    station_summary: pd.DataFrame,
    variable: str,
    label: str,
    units: str,
    period: tuple[int, int],
    reference_period: tuple[int, int] | None = (1961, 1990),
    min_stations: int = 5,
    title: str | None = None,
) -> pd.DataFrame:
    """Summary section for a station-based regional indicator.

    With ``reference_period`` the series is the unweighted station average of each station's anomaly
    from its own reference-period mean (stations at very different climates stay comparable and
    changes in the station network do not create spurious jumps); with ``None`` the station values
    are averaged directly (e.g. percentages of hot days). Years with fewer than ``min_stations``
    stations are dropped. ``station_summary`` (per-station ``<variable>_trend`` /
    ``<variable>_significant`` columns) adds the counts of significant positive / negative trends.
    """
    columns = []
    for df in annual_data.values():
        if variable not in df.columns:
            continue
        s = df.set_index("Year")[variable].dropna()
        if reference_period is not None:
            ref = s.loc[reference_period[0]:reference_period[1]].mean()
            if pd.isna(ref):
                continue
            s = s - ref
        columns.append(s)
    combined = pd.concat(columns, axis=1).sort_index().loc[period[0]:period[1]]
    n = combined.notna().sum(axis=1)
    series = combined.mean(axis=1)[n >= min_stations]
    n = n.loc[series.index]

    trend = station_summary[f"{variable}_trend"]
    sig = station_summary[f"{variable}_significant"].astype(bool) & trend.notna()
    what = f"{label} anomaly" if reference_period else label
    section = annual_series_summary(
        series, what, units, title=title,
        extra_rows=[
            ("Stations in the regional average", int(len(columns))),
            ("Stations per year (min–max)", f"{n.min()}–{n.max()}"),
            ("Stations with a trend", int(trend.notna().sum())),
            ("Stations with a significant increase", int((sig & (trend > 0)).sum())),
            ("Stations with a significant decrease", int((sig & (trend < 0)).sum())),
        ],
    )
    if reference_period:
        row = pd.DataFrame([(f"Anomalies relative to each station's {reference_period[0]}–{reference_period[1]} mean", "")],
                           columns=["Metric", "Value"])
        at = 1 if title else 0
        section = pd.concat([section.iloc[:at], row, section.iloc[at:]], ignore_index=True)
    return section


def area_weighted_annual_mean(field, lat_name: str = "latitude", time_name: str = "time") -> pd.Series:
    """Cosine-latitude weighted spatial mean of a (time, lat, lon) field, averaged to calendar years."""
    weights = np.cos(np.deg2rad(field[lat_name]))
    spatial = field.weighted(weights.fillna(0)).mean([d for d in field.dims if d != time_name])
    annual = spatial.groupby(f"{time_name}.year").mean() if time_name != "year" else spatial
    return annual.to_series()
