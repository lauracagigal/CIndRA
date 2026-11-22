"""Figures for the CIndRA sea-level notebooks (National and Regional).

Ported from SLIndRA/PICCM_SeaLevel and adapted to the CIndRA style guide:
map extents follow the selected EEZ or the Pacific window, units are stated
on every axis, missing years stay visible as gaps, and trend lines are solid
when ``p < 0.05`` and dashed otherwise.

Storm years (May–April) are labelled by their starting calendar year and
bars are centred on that label; ONI panels are shifted to the same axis.
"""

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import seaborn as sns
from matplotlib.colors import Normalize
from scipy import stats

from sea_level import get_trend_info
from sst import _setup_pacific_sst_map

ENSO_COLORS = {"El Nino": "#c0392b", "La Nina": "#2471a3", "Neutral": "0.55"}
ALT_COLOR = "#c0392b"
TG_COLOR = "#1f5f99"
PLATE = ccrs.PlateCarree()


def _trend_style(p_value):
    return "-" if np.isfinite(p_value) and p_value < 0.05 else "--"


def _significance(p_value):
    return "significant" if np.isfinite(p_value) and p_value < 0.05 else "not significant"


# =========================
# National maps
# =========================
def _base_map(xlims, ylims, figsize=(7, 6.5)):
    projection = ccrs.PlateCarree(central_longitude=180)
    fig, ax = plt.subplots(figsize=figsize, subplot_kw={"projection": projection})
    ax.set_extent([xlims[0], xlims[1], ylims[0], ylims[1]], crs=PLATE)
    ax.add_feature(cfeature.LAND, facecolor="0.85", edgecolor="0.3", linewidth=0.4, zorder=3)
    ax.coastlines(resolution="10m", linewidth=0.5, zorder=4)
    gl = ax.gridlines(draw_labels=True, linewidth=0.35, color="gray", alpha=0.6, linestyle=":")
    gl.top_labels = gl.right_labels = False
    return fig, ax


def plot_station_vs_grid_map(lon, lat, sla_nearest_lon, sla_nearest_lat, sla, half_width=0.4):
    """Tide gauge, nearest altimetry cell and surrounding grid-cell centres."""
    xlims = (lon - half_width, lon + half_width)
    ylims = (lat - half_width, lat + half_width)
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw={"projection": PLATE})
    ax.set_extent([*xlims, *ylims], crs=PLATE)
    ax.add_feature(cfeature.LAND, facecolor="0.85", zorder=0)
    ax.coastlines(resolution="10m", linewidth=0.6)
    sub = sla.sel(longitude=slice(*xlims), latitude=slice(*ylims))
    lon2d, lat2d = np.meshgrid(sub.longitude, sub.latitude)
    ax.scatter(lon2d, lat2d, s=8, color="0.45", transform=PLATE, label="Altimetry grid-cell centres")
    ax.scatter(lon, lat, s=120, marker="^", color=TG_COLOR, edgecolor="k", transform=PLATE, label="Tide gauge", zorder=5)
    ax.scatter(sla_nearest_lon, sla_nearest_lat, s=110, color=ALT_COLOR, edgecolor="k", transform=PLATE, label="Nearest altimetry cell", zorder=5)
    gl = ax.gridlines(draw_labels=True, linewidth=0.3, color="gray", alpha=0.6, linestyle=":")
    gl.top_labels = gl.right_labels = False
    ax.legend(loc="lower left", fontsize=10, framealpha=0.9)
    ax.set_title("Tide gauge and nearest altimetry grid cell")
    return fig, ax


def plot_sl_change_map(
    field_cm,
    eez,
    xlims,
    ylims,
    vmin,
    vmax,
    label,
    title,
    station=None,
    cmap="YlGnBu",
):
    """Map a gridded sea-level change field with the EEZ outline.

    ``station`` is an optional ``(lon, lat, value_cm, name)`` tuple drawn as a
    circle filled on the same colour scale (relative change at the gauge).
    """
    fig, ax = _base_map(xlims, ylims)
    im = ax.pcolormesh(field_cm.longitude, field_cm.latitude, field_cm, cmap=cmap, vmin=vmin, vmax=vmax, transform=PLATE, shading="auto", zorder=1)
    eez.boundary.plot(ax=ax, transform=PLATE, color="k", linewidth=1.4, zorder=5)
    if station is not None:
        s_lon, s_lat, s_value, s_name = station
        ax.scatter(s_lon, s_lat, s=260, c=[s_value], cmap=cmap, vmin=vmin, vmax=vmax, edgecolor="k", linewidth=1.2, transform=PLATE, zorder=6)
        ax.annotate(
            f"{s_name}\n{s_value:.1f} cm (tide gauge)",
            xy=(s_lon, s_lat),
            xycoords=PLATE._as_mpl_transform(ax),
            xytext=(12, -14),
            textcoords="offset points",
            fontsize=10,
            zorder=7,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.8, lw=0),
        )
    cbar = fig.colorbar(im, ax=ax, orientation="horizontal", pad=0.07, shrink=0.85, extend="both")
    cbar.set_label(label)
    ax.set_title(title)
    return fig, ax


def plot_sl_anomaly_period_maps(
    sla_anomaly_m,
    periods,
    eez,
    xlims,
    ylims,
    station=None,
    station_anomaly_m=None,
    vlim=None,
    title=None,
):
    """Mean detrended sea-level anomaly (cm) for several storm-year periods.

    ``periods`` is a list of ``(label, start, end)`` tuples (inclusive
    dates). ``station_anomaly_m`` is the monthly station anomaly series (m)
    whose period mean is shown as a filled circle at ``station`` (lon, lat).
    """
    fields = [100 * sla_anomaly_m.sel(time=slice(start, end)).mean("time") for _, start, end in periods]
    if vlim is None:
        vlim = float(np.nanpercentile(np.abs(np.concatenate([f.values.ravel() for f in fields])), 98))
        vlim = max(np.ceil(vlim), 1.0)
    ncols = 2
    nrows = int(np.ceil(len(periods) / ncols))
    projection = ccrs.PlateCarree(central_longitude=180)
    fig, axes = plt.subplots(nrows, ncols, figsize=(12, 5.3 * nrows), subplot_kw={"projection": projection}, squeeze=False)
    for ax, field, (label, start, end) in zip(axes.flat, fields, periods):
        ax.set_extent([xlims[0], xlims[1], ylims[0], ylims[1]], crs=PLATE)
        im = ax.pcolormesh(field.longitude, field.latitude, field, cmap="RdBu_r", vmin=-vlim, vmax=vlim, transform=PLATE, shading="auto")
        ax.add_feature(cfeature.LAND, facecolor="0.85", zorder=3)
        ax.coastlines(resolution="10m", linewidth=0.5, zorder=4)
        eez.boundary.plot(ax=ax, transform=PLATE, color="k", linewidth=1.0, zorder=5)
        if station is not None and station_anomaly_m is not None:
            value = 100 * float(station_anomaly_m.loc[start:end].mean())
            ax.scatter(*station, s=170, c=[value], cmap="RdBu_r", vmin=-vlim, vmax=vlim, edgecolor="k", linewidth=1, transform=PLATE, zorder=6)
        gl = ax.gridlines(draw_labels=True, linewidth=0.3, color="gray", alpha=0.6, linestyle=":")
        gl.top_labels = gl.right_labels = False
        ax.set_title(label)
    for ax in axes.flat[len(periods):]:
        ax.remove()
    cbar = fig.colorbar(im, ax=list(axes.flat[: len(periods)]), orientation="vertical", fraction=0.03, pad=0.04, extend="both")
    cbar.set_label("Mean detrended sea-level anomaly (cm)")
    if title:
        fig.suptitle(title, fontsize=14)
    return fig, axes


# =========================
# Time series
# =========================
def plot_combined_trends(
    sla_nearest,
    trend_line_asl,
    trend_rate_asl,
    p_asl,
    rsl_daily,
    trend_line_rsl,
    trend_rate_rsl,
    p_rsl,
    alt_label,
    station_name,
    start_date,
    end_date,
):
    """Absolute (altimetry) vs relative (tide gauge) sea level with linear trends.

    Inputs are in metres; daily values are shown faintly and monthly means
    as lines. Rates in the legend are mm/yr.
    """
    fig, ax = plt.subplots(figsize=(12, 5))
    for series, line, rate, p, color, name in [
        (sla_nearest, trend_line_asl, trend_rate_asl, p_asl, ALT_COLOR, f"Altimetry ({alt_label})"),
        (rsl_daily, trend_line_rsl, trend_rate_rsl, p_rsl, TG_COLOR, f"Tide gauge ({station_name})"),
    ]:
        ax.scatter(series.time, 100 * series, s=2, color=color, alpha=0.15, rasterized=True)
        monthly = series.resample(time="MS").mean()
        ax.plot(monthly.time, 100 * monthly, color=color, lw=1.0, alpha=0.85, label=f"{name}, monthly mean")
        ax.plot(
            line.time,
            100 * line,
            color=color,
            lw=2.4,
            ls=_trend_style(float(p)),
            label=f"{name} trend: {1000 * float(rate):.2f} mm/yr ({_significance(float(p))})",
        )
    ax.axhline(0, color="0.4", lw=0.6)
    ax.set_xlim(start_date, end_date)
    ax.set_ylabel("Sea level relative to MSL (cm)")
    ax.set_xlabel("Year")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=2, fontsize=10, frameon=False)
    ax.set_title(f"Absolute vs relative sea level, {pd.Timestamp(start_date):%Y}–{pd.Timestamp(end_date):%Y}")
    return fig, ax


def plot_series_with_trend(series_cm, title, ylabel="Sea-level anomaly (cm)", color=ALT_COLOR, label="Area-weighted mean"):
    """Monthly series with an OLS trend (rate in mm/yr, solid if p < 0.05)."""
    s = series_cm.dropna()
    t = (s.index - s.index[0]).days.values / 365.25
    res = stats.linregress(t, s.values)
    fig, ax = plt.subplots(figsize=(12, 4.5))
    ax.plot(s.index, s.values, color=color, lw=1.2, label=label)
    ax.plot(
        s.index,
        res.intercept + res.slope * t,
        color="k",
        lw=2,
        ls=_trend_style(res.pvalue),
        label=f"Trend {10 * res.slope:.2f} mm/yr (p = {res.pvalue:.3g}, {_significance(res.pvalue)})",
    )
    ax.axhline(0, color="0.5", lw=0.6)
    ax.set_ylabel(ylabel)
    ax.set_xlabel("Year")
    ax.set_title(title)
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left", fontsize=10)
    return fig, ax, res


def plot_enso_scatter(oni_daily, deseasoned_rsl):
    """De-seasoned, detrended tide-gauge sea level (m) versus ONI (°C)."""
    fig, ax = plt.subplots(figsize=(8, 6))
    x = oni_daily.squeeze().to_numpy()
    y = deseasoned_rsl.to_numpy()
    ok = np.isfinite(x) & np.isfinite(y)
    ax.scatter(x[ok], y[ok], color="gray", alpha=0.2, s=7, rasterized=True)

    nina_1998 = deseasoned_rsl.sel(time=slice("1998-08-01", "2001-01-30"))
    nino_1997 = deseasoned_rsl.sel(time=slice("1997-06-01", "1998-04-30"))
    if nina_1998.size:
        ax.scatter(oni_daily.loc["1998-08-01":"2001-01-30"].squeeze(), nina_1998, color=ENSO_COLORS["La Nina"], s=10, label="1998–2001 La Niña", alpha=0.5)
    if nino_1997.size:
        ax.scatter(oni_daily.loc["1997-06-01":"1998-04-30"].squeeze(), nino_1997, color=ENSO_COLORS["El Nino"], s=10, label="1997–98 El Niño", alpha=0.5)

    slope, intercept, r_value, p_value, std_err = stats.linregress(x[ok], y[ok])
    xx = np.linspace(-2.5, 3, 100)
    ax.plot(xx, slope * xx + intercept, color="k", label=f"{100 * slope:.1f} cm per °C (r² = {r_value ** 2:.2f})")
    for lo, hi, color, alpha in [(-2.5, -1.5, "blue", 0.12), (-1.5, -0.5, "blue", 0.06), (-0.5, 0.5, "gray", 0.04), (0.5, 1.5, "red", 0.06), (1.5, 3, "red", 0.12)]:
        ax.axvspan(lo, hi, color=color, alpha=alpha, lw=0, zorder=0)
    ax.set_xlim(-2.5, 3)
    ax.set_xlabel("Oceanic Niño Index (°C)")
    ax.set_ylabel("De-seasoned, detrended sea level (m)")
    ax.set_title("Tide-gauge sea level and ENSO")
    ax.legend(frameon=False, fontsize=10)
    return fig, ax, slope, intercept, r_value, p_value, std_err, nina_1998, nino_1997


def plot_station_anomaly_series(yearly, monthly_anomaly_m, enso_events, station_name):
    """Storm-year mean anomaly with annual range, monthly anomalies and ENSO shading.

    ``yearly`` has columns ``mean``, ``min`` and ``max`` (m) indexed by storm
    year (NaN for incomplete years). ``monthly_anomaly_m`` is a monthly
    pandas Series (m).
    """
    fig, ax = plt.subplots(figsize=(12, 5))
    x_year = yearly.index.values + 0.5  # centre of the May–April storm year
    lo = 100 * yearly["min"]
    hi = 100 * yearly["max"]
    ax.fill_between(x_year, lo, hi, color=TG_COLOR, alpha=0.15, label="Range of daily anomalies (storm year)")
    ax.plot(x_year, 100 * yearly["mean"], color=TG_COLOR, lw=2.2, marker="o", ms=4, label="Storm-year mean anomaly")
    m = monthly_anomaly_m.dropna()
    x_month = m.index.year + (m.index.month - 5) / 12 + 1 / 24
    ax.plot(x_month, 100 * m.values, color="0.4", lw=0.8, label="Monthly anomaly")
    ymin, ymax = ax.get_ylim()
    ev = enso_events.copy()
    ev_x = ev.index.year + (ev.index.month - 5) / 12
    ax.fill_between(ev_x, ymin, ymax, where=ev["El Nino"].values, color=ENSO_COLORS["El Nino"], alpha=0.1, step="post", label="El Niño")
    ax.fill_between(ev_x, ymin, ymax, where=ev["La Nina"].values, color=ENSO_COLORS["La Nina"], alpha=0.1, step="post", label="La Niña")
    ax.set_ylim(ymin, ymax)
    ax.set_xlim(yearly.index.min(), yearly.index.max() + 1)
    ax.axhline(0, color="0.4", lw=0.6)
    ax.set_xlabel("Storm year (May–April, labelled by starting year)")
    ax.set_ylabel("Detrended sea-level anomaly (cm)")
    ax.set_title(f"Sea-level anomalies at {station_name}")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=10, frameon=False)
    return fig, ax


def plot_simple_timeseries(time_values, sea_level_cm, ylabel, title=None):
    """Single-panel time series."""
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(time_values, sea_level_cm, lw=0.5, color=TG_COLOR)
    ax.set_ylabel(ylabel)
    ax.set_xlabel("Year")
    ax.grid(alpha=0.3)
    if title:
        ax.set_title(title)
    return fig, ax


# =========================
# Flood frequency
# =========================
def plot_histogram_with_threshold(hourly_mhhw_mm, threshold_cm):
    """Histogram of hourly levels (cm above MHHW) with the flood threshold and P98."""
    values = hourly_mhhw_mm.values / 10
    values = values[np.isfinite(values)]
    p98 = np.percentile(values, 98)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(values, bins=100, density=True, color="0.6")
    ax.axvline(threshold_cm, color="r", ls="--", label=f"Flood threshold: {threshold_cm:.0f} cm")
    ax.axvline(p98, color="c", ls="--", label=f"98th percentile: {p98:.1f} cm")
    ax.set_xlabel("Hourly sea level (cm above MHHW)")
    ax.set_ylabel("Probability density")
    ax.set_title("Distribution of hourly sea level")
    ax.legend(fontsize=10)
    return fig, ax, p98


def _bar_counts(table, column, ax, colors="Blues", width=0.85, alpha=1.0):
    x = table["year_storm"].to_numpy(dtype=float)
    y = table[column].to_numpy(dtype=float)
    if isinstance(colors, str):
        cmap = sns.color_palette(colors, as_cmap=True)
        finite = y[np.isfinite(y)]
        norm = Normalize(vmin=finite.min() if finite.size else 0, vmax=finite.max() if finite.size else 1)
        colors = [cmap(0.25 + 0.75 * norm(v)) if np.isfinite(v) else "none" for v in y]
    ax.bar(x, np.nan_to_num(y), width=width, color=colors, alpha=alpha)
    missing = ~np.isfinite(y)
    if missing.any():
        ax.scatter(x[missing], np.zeros(missing.sum()), marker="x", color="0.4", s=25, zorder=4, label="Incomplete year (no value)")
    ax.grid(axis="y", color="lightgray", lw=0.5, alpha=0.6)
    return x, y


def plot_flood_counts_with_trend(table, timescale="days", colors="Blues", station_name=None, threshold_cm=30):
    """Annual minor-flood days or hours with a linear trend."""
    column = "flood_days_count" if timescale == "days" else "flood_hours_count"
    fig, ax = plt.subplots(figsize=(12, 4.5))
    x, y = _bar_counts(table, column, ax, colors)
    trend, label, ls, slope, p_value = get_trend_info(x, y, timescale)
    ax.plot(x, trend, color="k", ls=ls, lw=1.5, label=label)
    ax.set_xlim(x.min() - 1, x.max() + 1)
    ax.set_ylabel(f"Flood {timescale} per storm year")
    ax.set_xlabel("Storm year (May–April, labelled by starting year)")
    where = f" at {station_name}" if station_name else ""
    ax.set_title(f"Minor-flood {timescale} (> {threshold_cm:g} cm above MHHW){where}")
    ax.legend(loc="upper left", fontsize=10)
    return fig, ax, slope, p_value, trend


def plot_oni_segments(enso_events, ax):
    """ONI coloured by ENSO phase on the storm-year axis used by the bar charts."""
    ev = enso_events.dropna(subset=["ONI"])
    x = ev.index.year + (ev.index.month - 5) / 12 - 0.5 + 1 / 24
    colors = ev["ONI Mode"].map(ENSO_COLORS).fillna("0.55").to_numpy()
    for i in range(len(ev) - 1):
        ax.plot(x[i : i + 2], ev["ONI"].iloc[i : i + 2], color=colors[i], lw=2)
    ax.axhline(0, color="0.5", lw=0.5)
    ax.set_ylim(-3, 3)
    ax.set_ylabel("ONI (°C)")
    ax.grid(color="lightgray", lw=0.5, alpha=0.6)


def plot_flood_counts_with_oni(table, enso_events, station_name=None, threshold_cm=30):
    """Flood days per storm year (bars coloured by ENSO phase) above an ONI panel."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6), sharex=True, gridspec_kw={"height_ratios": [4, 1.3], "hspace": 0.06})
    colors = [mcolors.to_rgba(ENSO_COLORS.get(m, "0.55"), 0.75) for m in table["ONI Mode"].fillna("Neutral")]
    x, y = _bar_counts(table, "flood_days_count", ax1, colors)
    trend, label, ls, slope, p_value = get_trend_info(x, y, "days")
    ax1.plot(x, trend, color="k", ls=ls, lw=1.5, label=label)
    handles = [plt.Rectangle((0, 0), 1, 1, color=ENSO_COLORS[k], alpha=0.75) for k in ["El Nino", "La Nina", "Neutral"]]
    leg = ax1.legend(loc="upper left", fontsize=10)
    ax1.add_artist(leg)
    ax1.legend(handles, ["El Niño year", "La Niña year", "Neutral year"], loc="upper center", ncol=3, fontsize=9, frameon=False)
    ax1.set_ylabel("Flood days per storm year")
    where = f" at {station_name}" if station_name else ""
    ax1.set_title(f"Minor-flood days (> {threshold_cm:g} cm above MHHW){where} and ENSO")
    plot_oni_segments(enso_events[(enso_events.index.year >= x.min() - 1) & (enso_events.index.year <= x.max() + 1)], ax2)
    ax2.set_xlim(x.min() - 1, x.max() + 1)
    ax2.set_xlabel("Storm year (May–April, labelled by starting year)")
    return fig, (ax1, ax2), slope, p_value


def plot_flood_matrix_summary(matrix, table, station_name, threshold_cm=30):
    """Composite: annual flood days, monthly heatmap and monthly contribution."""
    body = matrix.iloc[:-1, :-1]
    share = matrix.iloc[-1, :-1]
    years = body.index.astype(int)
    fig, axs = plt.subplots(2, 2, figsize=(14, 7), gridspec_kw={"height_ratios": [1, 2], "width_ratios": [5, 1], "hspace": 0.05, "wspace": 0.04})

    ax_bar = axs[0, 0]
    sub = table.set_index("year_storm").reindex(years)
    colors = [mcolors.to_rgba(ENSO_COLORS.get(m, "0.55"), 0.7) for m in sub["ONI Mode"].fillna("Neutral")]
    pos = np.arange(len(years)) + 0.5
    vals = sub["flood_days_count"].to_numpy(dtype=float)
    ax_bar.bar(pos, np.nan_to_num(vals), width=0.8, color=colors)
    for xi, yi in zip(pos, vals):
        if np.isfinite(yi):
            ax_bar.text(xi, yi + 0.5, f"{yi:.0f}", ha="center", va="bottom", fontsize=7)
    trend, label, ls, slope, p_value = get_trend_info(pos, vals, "days")
    ax_bar.plot(pos, trend, color="k", ls=ls, lw=1, label=label.replace("days/year", "days per year"))
    ax_bar.set_xlim(0, len(years))
    ax_bar.set_xticks([])
    ax_bar.set_ylabel("Flood days\n(per storm year)")
    ax_bar.spines[["top", "right"]].set_visible(False)
    ax_bar.legend(loc="upper left", fontsize=9, frameon=False)
    ax_bar.set_title(f"{station_name}: days exceeding {threshold_cm:g} cm above MHHW")

    ax_heat = axs[1, 0]
    sns.heatmap(body.T, cmap="Greys", annot=True, fmt=".0f", linewidths=0.2, ax=ax_heat, cbar=False, annot_kws={"size": 7}, vmin=0)
    ax_heat.set_ylabel("Flood days per month")
    ax_heat.set_xlabel("Storm year (May–April, labelled by starting year)")
    ax_heat.tick_params(labelsize=9)
    mode = sub["ONI Mode"]
    for tick in ax_heat.get_xticklabels():
        tick.set_color(ENSO_COLORS.get(mode.get(int(tick.get_text()), "Neutral"), "k"))

    ax_share = axs[1, 1]
    ax_share.barh(np.arange(12) + 0.5, share.values, color="0.6")
    ax_share.set_ylim(12, 0)
    ax_share.set_yticks([])
    ax_share.set_xticks([])
    for i, v in enumerate(share.values):
        if np.isfinite(v):
            ax_share.text(v + 0.5, i + 0.5, f"{v:.0f}%", va="center", fontsize=8)
    ax_share.set_xlabel("Share of all\nflood days (%)")
    ax_share.spines[["top", "right", "bottom"]].set_visible(False)

    axs[0, 1].axis("off")
    handles = [plt.Line2D([0], [0], marker="s", ls="", color=ENSO_COLORS[k], ms=10, alpha=0.7) for k in ["El Nino", "La Nina", "Neutral"]]
    axs[0, 1].legend(handles, ["El Niño", "La Niña", "Neutral"], title="Dominant ENSO\nphase", loc="center left", frameon=False)
    return fig, axs, slope, p_value


# =========================
# Rankings
# =========================
def style_oni_based(row, norm, cmap):
    """Pandas Styler helper: colour extreme values by ONI when in an ENSO phase."""
    styles = {}
    for side, oni_col in [("Highest", "ONI max"), ("Lowest", "ONI min")]:
        if row[f"{side} ONI Mode"] in ("El Nino", "La Nina"):
            styles[side] = f"background-color: {mcolors.rgb2hex(cmap(norm(row[oni_col])))}"
        else:
            styles[side] = "color: black"
    return pd.Series(styles)


def make_plotly_figure_rankings(monthly_mean, monthly_max, monthly_min, top_10_table, station_name, ylabel="Sea level (m, MHHW)"):
    """Interactive monthly envelope with the top-10 high and low events."""
    fig = go.Figure()
    x = monthly_mean.index
    # Draw the monthly range as one closed polygon per contiguous run of valid
    # months so that gaps in the record are not bridged by the fill.
    valid = (monthly_max.notna() & monthly_min.notna()).to_numpy()
    run_id = np.cumsum(~valid)
    first = True
    for rid in np.unique(run_id[valid]):
        idx = np.where(valid & (run_id == rid))[0]
        xs = list(x[idx]) + list(x[idx][::-1])
        ys = list(monthly_max.values[idx]) + list(monthly_min.values[idx][::-1])
        fig.add_trace(
            go.Scatter(
                x=xs, y=ys, mode="lines", fill="toself", fillcolor="rgba(0,120,200,0.18)",
                line=dict(color="rgba(0,120,200,0.35)", width=0.8), name="Monthly range",
                legendgroup="range", showlegend=first, hoverinfo="skip",
            )
        )
        first = False
    fig.add_trace(go.Scatter(x=x, y=monthly_mean.values, mode="lines", line_color="rgba(0,90,170,1)", name="Monthly mean", connectgaps=False))
    for mode, color, symbol, label in [("El Nino", "red", "star", "El Niño"), ("La Nina", "blue", "circle", "La Niña")]:
        sel = top_10_table[top_10_table["ONI Mode"] == mode]
        fig.add_trace(go.Scatter(x=sel["date"], y=sel["sea level (m)"], mode="markers", marker=dict(color=color, size=13, symbol=symbol), name=f"Event during {label}", hoverinfo="skip"))
    fig.add_trace(
        go.Scatter(
            x=top_10_table["date"],
            y=top_10_table["sea level (m)"],
            mode="markers",
            marker=dict(color="orange", size=7),
            name="Top-10 highest / lowest",
            hovertemplate="%{x|%Y-%m-%d %H:%M} UTC, %{y:.2f} m<extra></extra>",
        )
    )
    fig.update_layout(title=f"Extreme hourly sea levels — {station_name}", xaxis_title="Year", yaxis_title=ylabel, plot_bgcolor="white", width=950, height=500)
    fig.update_xaxes(showgrid=True, gridcolor="lightgray")
    fig.update_yaxes(showgrid=True, gridcolor="lightgray")
    return fig


def make_rankings_static_figure(monthly_mean, monthly_max, monthly_min, top_10_table, station_name, ylabel="Sea level (m, MHHW)"):
    """Static version of :func:`make_plotly_figure_rankings`."""
    fig, ax = plt.subplots(figsize=(12, 4.5))
    x = monthly_mean.index
    ax.fill_between(x, monthly_min.values, monthly_max.values, color=TG_COLOR, alpha=0.18, label="Monthly range")
    ax.plot(x, monthly_mean.values, color=TG_COLOR, lw=1.2, label="Monthly mean")
    for mode, color, marker, label in [("La Nina", ENSO_COLORS["La Nina"], "o", "Event during La Niña"), ("El Nino", ENSO_COLORS["El Nino"], "*", "Event during El Niño")]:
        sel = top_10_table[top_10_table["ONI Mode"] == mode]
        ax.scatter(sel["date"], sel["sea level (m)"], color=color, s=130, marker=marker, label=label, zorder=4)
    ax.scatter(top_10_table["date"], top_10_table["sea level (m)"], color="orange", s=22, label="Top-10 highest / lowest", zorder=5)
    ax.set_xlim(x.min(), x.max())
    ax.set_ylabel(ylabel)
    ax.set_xlabel("Year")
    ax.set_title(f"Extreme hourly sea levels — {station_name}")
    ax.grid(alpha=0.4, lw=0.5)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=3, frameon=False, fontsize=10)
    return fig, ax


# =========================
# Regional
# =========================
def plot_pacific_sl_field(
    field,
    pacific,
    title,
    cmap="RdYlBu_r",
    vmin=None,
    vmax=None,
    label="Sea-level trend (mm/yr)",
    stations=None,
    station_col=None,
    filename=None,
):
    """Pacific map of a gridded sea-level field with EEZs and optional gauges.

    ``field`` must have ``lon``/``lat`` coordinates in 0–360°. ``stations``
    is a DataFrame with ``lon``/``lat``; finite ``station_col`` values are
    drawn as filled circles on the same scale, others as open circles.
    """
    projection = ccrs.PlateCarree(central_longitude=180)
    fig, ax = plt.subplots(figsize=(14, 7.5), subplot_kw={"projection": projection})
    im = ax.pcolormesh(field.lon, field.lat, field, transform=PLATE, shading="auto", cmap=cmap, vmin=vmin, vmax=vmax, zorder=1)
    _setup_pacific_sst_map(ax, pacific, title)
    if stations is not None and len(stations):
        values = stations[station_col] if station_col else pd.Series(np.nan, index=stations.index)
        filled = np.isfinite(values.to_numpy(dtype=float))
        ax.scatter(stations.loc[filled, "lon"], stations.loc[filled, "lat"], c=values[filled], cmap=cmap, vmin=vmin, vmax=vmax, s=95, edgecolor="k", linewidth=0.9, transform=PLATE, zorder=7, label="Tide gauge (relative trend)")
        if (~filled).any():
            ax.scatter(stations.loc[~filled, "lon"], stations.loc[~filled, "lat"], facecolor="none", edgecolor="k", s=60, linewidth=0.9, transform=PLATE, zorder=7, label="Tide gauge (insufficient data)")
        ax.legend(loc="lower left", fontsize=10, framealpha=0.9)
    cbar = fig.colorbar(im, ax=ax, orientation="horizontal", pad=0.08, shrink=0.78, aspect=40, extend="both")
    cbar.set_label(label)
    if filename:
        fig.savefig(filename, dpi=150, bbox_inches="tight")
    return fig, ax


def plot_station_trend_comparison(table, period_label):
    """Relative (tide gauge) vs absolute (altimetry) trends per QC-passed station."""
    t = table.assign(_lon360=table["lon"] % 360).sort_values("_lon360", ascending=False).reset_index(drop=True)
    y = np.arange(len(t))
    fig, ax = plt.subplots(figsize=(10, 0.32 * len(t) + 2))
    ax.errorbar(t["tg_trend_mm_yr"], y + 0.15, xerr=1.96 * t["tg_trend_se_mm_yr"], fmt="o", color=TG_COLOR, ms=6, capsize=2, label="Tide gauge (relative, ±1.96 SE)")
    ax.scatter(t["alt_trend_mm_yr"], y - 0.15, color=ALT_COLOR, marker="s", s=36, label="Altimetry, nearest cell (absolute)", zorder=3)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{n} ({c})" if isinstance(c, str) else n for n, c in zip(t["name"], t["country"])], fontsize=9)
    ax.axvline(0, color="0.4", lw=0.6)
    ax.set_xlabel("Sea-level trend (mm/yr)")
    ax.set_title(f"Station sea-level trends, {period_label} (same valid months for both sources)")
    ax.grid(axis="x", alpha=0.3)
    ax.legend(loc="lower right", fontsize=10)
    return fig, ax


def plot_regional_flood_overview(matrix, threshold_cm=30, period_label=""):
    """Heatmap of minor-flood days per storm year (stations × years)."""
    fig, ax = plt.subplots(figsize=(16, 0.36 * len(matrix) + 2.5))
    finite = matrix.to_numpy(dtype=float)
    vmax = np.nanpercentile(finite, 98) if np.isfinite(finite).any() else 1
    sns.heatmap(matrix, cmap="YlGnBu", vmin=0, vmax=max(vmax, 1), linewidths=0.3, linecolor="white", ax=ax, cbar_kws={"label": "Flood days per storm year", "shrink": 0.7}, mask=matrix.isna())
    ax.set_facecolor("0.9")
    ax.set_xlabel("Storm year (May–April, labelled by starting year); grey = incomplete year")
    ax.set_ylabel("")
    ax.tick_params(labelsize=9)
    ax.set_title(f"Minor-flood days (> {threshold_cm:g} cm above MHHW) at Pacific tide gauges {period_label}")
    return fig, ax


def plot_regional_change_map_filled_tide_gauges(
    change_cm,
    pacific,
    stations=None,
    station_col="tg_change_cm",
    vmin=-25,
    vmax=25,
    station_vmin=-35,
    station_vmax=35,
    title="Regional sea-level change",
    domain_avg_rate_mm_yr=None,
    filename=None,
):
    """PICCM-style map: absolute altimetry change (cm over the epoch) with tide gauges.

    Background: gridded absolute sea-level change from altimetry (cm/epoch,
    ``change_cm`` with ``lon``/``lat`` in 0–360°). Filled circles: relative
    tide-gauge change over the same epoch (``station_col``, cm); stations
    without a value (insufficient data) are drawn as small open circles.
    The two quantities share a colormap but have separate colour bars and
    are not merged into one metric. Ported from the PICCM_SeaLevel draft
    helper ``plot_regional_altimetry_trend_map_filled_tide_gauges``.
    """
    projection = ccrs.PlateCarree(central_longitude=180)
    fig, ax = plt.subplots(figsize=(14, 8.5), subplot_kw={"projection": projection})
    mesh = ax.pcolormesh(change_cm.lon, change_cm.lat, change_cm, transform=PLATE, shading="auto", cmap="RdBu_r", vmin=vmin, vmax=vmax, zorder=1)
    ax.set_extent(pacific.extent, crs=PLATE)
    ax.add_feature(cfeature.LAND, facecolor="0.72", edgecolor="0.3", linewidth=0.4, zorder=3)
    pacific.eez.boundary.plot(ax=ax, transform=PLATE, color="0.35", linewidth=0.4, alpha=0.6, zorder=4)
    gl = ax.gridlines(draw_labels=True, linewidth=0.4, color="0.6", alpha=0.6)
    gl.top_labels = gl.right_labels = False
    ax.set_title(title, fontsize=16, fontweight="bold")

    station_scatter = None
    if stations is not None and len(stations):
        values = stations[station_col].to_numpy(dtype=float)
        valid = np.isfinite(values)
        if valid.any():
            station_scatter = ax.scatter(
                stations.loc[valid, "lon"], stations.loc[valid, "lat"], c=values[valid], cmap="RdBu_r",
                vmin=station_vmin, vmax=station_vmax, s=110, edgecolor="k", linewidth=1.0, transform=PLATE,
                zorder=7, label="Relative tide-gauge change",
            )
        if (~valid).any():
            ax.scatter(
                stations.loc[~valid, "lon"], stations.loc[~valid, "lat"], s=40, facecolor="white",
                edgecolor="0.3", linewidth=0.8, transform=PLATE, zorder=6, label="Tide gauge, insufficient data",
            )
        ax.legend(loc="upper right", fontsize=11, framealpha=0.9)

    if domain_avg_rate_mm_yr is not None:
        ax.text(
            0.02, 0.04, f"{domain_avg_rate_mm_yr:.2f} mm/yr domain-average altimetry trend",
            transform=ax.transAxes, ha="left", va="bottom", fontsize=12, zorder=8,
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="0.4", alpha=0.9),
        )

    cbar = fig.colorbar(mesh, ax=ax, orientation="horizontal", pad=0.07, fraction=0.05, shrink=0.75, extend="both")
    cbar.set_label("Altimetry absolute sea-level change (cm/epoch)")
    if station_scatter is not None:
        scbar = fig.colorbar(station_scatter, ax=ax, orientation="vertical", pad=0.02, fraction=0.03, shrink=0.8, extend="both")
        scbar.set_label("Tide-gauge relative sea-level change (cm/epoch)")
    if filename:
        fig.savefig(filename, dpi=200, bbox_inches="tight")
    return fig, ax


def plot_regional_flood_matrix(matrix, threshold_cm=30, title=None, cmap="Reds", annotate=True):
    """Station × storm-year flood-day matrix with the regional total below.

    ``matrix`` has one row per station (already in the desired order, e.g.
    north to south) and one column per storm year; NaN = incomplete year
    (left blank). The bar chart shares the heatmap's x axis so every bar sits
    exactly under its column. Bars sum the stations with data in that year.
    """
    from matplotlib.gridspec import GridSpec

    years = np.asarray(matrix.columns, dtype=int)
    values = matrix.to_numpy(dtype=float)
    nrows = len(matrix)
    fig = plt.figure(figsize=(max(14, 0.42 * len(years) + 3), 0.42 * nrows + 6.5))
    gs = GridSpec(2, 2, figure=fig, width_ratios=[1, 0.025], height_ratios=[0.42 * nrows + 1, 3.2], hspace=0.28, wspace=0.03)
    ax = fig.add_subplot(gs[0, 0])
    ax_bar = fig.add_subplot(gs[1, 0], sharex=ax)
    cax = fig.add_subplot(gs[0, 1])

    vmax = np.nanmax(values) if np.isfinite(values).any() else 1
    mesh = ax.pcolormesh(
        np.r_[years - 0.5, years[-1] + 0.5], np.arange(nrows + 1), np.ma.masked_invalid(values),
        cmap=cmap, vmin=0, vmax=vmax, edgecolors="white", linewidth=0.6,
    )
    ax.set_ylim(nrows, 0)
    ax.set_yticks(np.arange(nrows) + 0.5)
    ax.set_yticklabels(matrix.index, fontsize=11)
    ax.set_ylabel("UHSLC station (north to south)")
    if annotate:
        for i in range(nrows):
            for j, year in enumerate(years):
                v = values[i, j]
                if np.isfinite(v):
                    ax.text(year, i + 0.5, f"{v:.0f}", ha="center", va="center", fontsize=6.5,
                            color="white" if v > 0.6 * vmax else "0.15")
    ax.tick_params(axis="x", labelbottom=True)
    ax.set_xlabel("Storm year (May–Apr)")
    fig.colorbar(mesh, cax=cax).set_label("Flood days")
    ax.set_title(
        title or f"Regional flood-frequency station-year matrix\n{threshold_cm:g} cm above MHHW; counts in cells; north-to-south station order",
        fontsize=15, fontweight="bold",
    )

    totals = np.nansum(values, axis=0)
    ax_bar.bar(years, totals, width=0.8, color="#b2182b", alpha=0.85, edgecolor="0.3", linewidth=0.5)
    ax_bar.set_ylabel("Regional total\nflood days")
    ax_bar.set_xlabel("Storm year (May–Apr)")
    ax_bar.grid(axis="y", alpha=0.4)
    ax_bar.set_xlim(years[0] - 0.5, years[-1] + 0.5)
    step = 3 if len(years) > 20 else 1
    ticks = years[(years - years[0]) % step == 0]
    for a in (ax, ax_bar):
        a.set_xticks(ticks)
        a.set_xticklabels(ticks, rotation=45, ha="right", fontsize=10)
    return fig, (ax, ax_bar)
