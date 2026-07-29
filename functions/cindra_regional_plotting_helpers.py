"""CIndRA regional plotting helpers.

Canonical public helpers:
- plot_regional_altimetry_trend_map_filled_tide_gauges
- plot_regional_flood_frequency_overview

Status: Draft / Experimental -- not yet wired into any notebook. Intended for
``notebooks/historical/Regional/regional_plots.ipynb`` once that notebook is
written; until then these are exposed for ad-hoc use only.
"""


def plot_regional_altimetry_trend_map_filled_tide_gauges(
    trend_mag_cm,
    station_df=None,
    xlims=(125, 245),
    ylims=(-35, 35),
    vmin=-25,
    vmax=25,
    station_vmin=-25,
    station_vmax=25,
    title="Regional sea level trend (1993-2025)",
    domain_avg_rate_mm_yr=None,
    station_value_col="sea_level_change_cm",
):
    """Plot regional absolute altimetry change with optional relative tide-gauge markers.

    The gridded background is absolute satellite-altimetry sea-level change in
    cm/epoch. Filled station circles, when available, show QC-passed relative
    tide-gauge sea-level change in cm/epoch over the same epoch. These two
    quantities are displayed together but are not merged into a single metric.

    Parameters
    ----------
    trend_mag_cm : xarray.DataArray
        Gridded absolute altimetry sea-level change in cm/epoch. Coordinates
        should include lon/lat or longitude/latitude.
    station_df : pandas.DataFrame, optional
        Station table. If supplied, it should include longitude and latitude
        columns named lon/lat or longitude/latitude. If station_value_col is
        present, finite values are plotted as filled relative tide-gauge
        markers; non-finite values are plotted as open station markers.
    xlims, ylims : tuple
        Map limits in degrees east and degrees north.
    vmin, vmax : float
        Color limits for the absolute altimetry background in cm/epoch.
    station_vmin, station_vmax : float
        Color limits for filled relative tide-gauge markers in cm/epoch.
    title : str
        Figure title.
    domain_avg_rate_mm_yr : float, optional
        Domain-average absolute altimetry trend rate in mm/yr.
    station_value_col : str
        Column in station_df containing relative tide-gauge sea-level change
        in cm/epoch. Defaults to sea_level_change_cm.

    Returns
    -------
    fig, ax
        Matplotlib figure and axes.
    """
    import numpy as np
    import matplotlib.pyplot as plt

    da = trend_mag_cm

    lon_name = "lon" if "lon" in da.coords else "longitude" if "longitude" in da.coords else None
    lat_name = "lat" if "lat" in da.coords else "latitude" if "latitude" in da.coords else None
    if lon_name is None or lat_name is None:
        raise ValueError("trend_mag_cm must have lon/lat or longitude/latitude coordinates")

    fig, ax = plt.subplots(figsize=(12, 6))

    mesh = ax.pcolormesh(
        da[lon_name],
        da[lat_name],
        da,
        cmap="RdBu_r",
        vmin=vmin,
        vmax=vmax,
        shading="auto",
    )

    ax.set_xlim(*xlims)
    ax.set_ylim(*ylims)
    ax.set_title(title)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.grid(True, color="0.75", linewidth=0.5, alpha=0.6)

    def fmt_lon(x):
        if abs(x - 180) < 1e-6:
            return "180°"
        if x > 180:
            return f"{int(round(360 - x))}°W"
        return f"{int(round(x))}°E"

    def fmt_lat(y):
        if abs(y) < 1e-6:
            return "0°"
        return f"{abs(int(round(y)))}°" + ("N" if y > 0 else "S")

    xticks = [125, 150, 180, 210, 245]
    yticks = [-35, -20, 0, 20, 35]
    ax.set_xticks(xticks)
    ax.set_xticklabels([fmt_lon(x) for x in xticks])
    ax.set_yticks(yticks)
    ax.set_yticklabels([fmt_lat(y) for y in yticks])

    cbar = fig.colorbar(mesh, ax=ax, orientation="horizontal", pad=0.12, fraction=0.055)
    cbar.set_label("Altimetry absolute sea-level change (cm/epoch)")

    station_scatter = None
    if station_df is not None and len(station_df) > 0:
        sdf = station_df.copy()
        lon_col = "lon" if "lon" in sdf.columns else "longitude" if "longitude" in sdf.columns else None
        lat_col = "lat" if "lat" in sdf.columns else "latitude" if "latitude" in sdf.columns else None
        if lon_col is None or lat_col is None:
            raise ValueError("station_df must include lon/lat or longitude/latitude columns")

        if station_value_col in sdf.columns:
            valid = sdf[station_value_col].notna()
            if valid.any():
                station_scatter = ax.scatter(
                    sdf.loc[valid, lon_col],
                    sdf.loc[valid, lat_col],
                    c=sdf.loc[valid, station_value_col],
                    s=48,
                    cmap="RdBu_r",
                    vmin=station_vmin,
                    vmax=station_vmax,
                    edgecolors="black",
                    linewidth=0.75,
                    zorder=6,
                    label="Relative tide-gauge change",
                )
            if (~valid).any():
                ax.scatter(
                    sdf.loc[~valid, lon_col],
                    sdf.loc[~valid, lat_col],
                    s=28,
                    facecolors="white",
                    edgecolors="0.35",
                    linewidth=0.6,
                    zorder=5,
                    label="UHSLC station, no trend marker",
                )
        else:
            ax.scatter(
                sdf[lon_col],
                sdf[lat_col],
                s=28,
                facecolors="white",
                edgecolors="black",
                linewidth=0.7,
                zorder=5,
                label="UHSLC stations",
            )

        ax.legend(loc="upper right", frameon=True)

    if station_scatter is not None:
        scbar = fig.colorbar(station_scatter, ax=ax, orientation="vertical", pad=0.015, fraction=0.035)
        scbar.set_label("Tide-gauge relative sea-level change (cm/epoch)")

    if domain_avg_rate_mm_yr is not None:
        ax.text(
            0.02,
            0.04,
            f"{domain_avg_rate_mm_yr:.2f} mm/yr domain-average altimetry trend",
            transform=ax.transAxes,
            ha="left",
            va="bottom",
            bbox=dict(facecolor="white", edgecolor="0.4", alpha=0.85),
        )

    ax.text(
        0.02,
        0.96,
        "Background: absolute altimetry\nCircles: relative tide gauges",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9,
        bbox=dict(facecolor="white", edgecolor="0.4", alpha=0.85),
    )

    fig.tight_layout()
    return fig, ax


def plot_regional_flood_frequency_overview(
    matrix_df,
    annual_totals,
    station_latitudes=None,
    title="Regional flood-frequency station-year matrix",
    annot=True,
    cmap="Reds",
    heatmap_tick_step=None,
):
    """Plot regional flood-day matrix with annual regional totals.

    This is the canonical CIndRA regional flood-frequency overview helper. The
    upper panel shows station-year flood-day counts, with station rows ordered
    north-to-south when station_latitudes is supplied. The heatmap includes
    visible storm-year x-axis labels. The lower panel shows regional annual
    total flood-day counts.

    Parameters
    ----------
    matrix_df : pandas.DataFrame
        Index is station name, columns are storm years, values are annual
        flood-day counts. Missing or not-computable station-years should be
        represented as NaN, not zero.
    annual_totals : pandas.Series or pandas.DataFrame
        Annual regional total flood days by storm year. If a DataFrame is
        supplied, it should include year_storm and regional_total_flood_days
        columns; otherwise the first column is used.
    station_latitudes : pandas.Series or dict, optional
        Station latitude keyed by station name. When supplied, y-axis rows are
        sorted north-to-south with northernmost stations at the top.
    title : str
        Figure title.
    annot : bool
        If True, place integer flood-day counts in finite heatmap cells.
    cmap : str or matplotlib colormap
        Sequential colormap for flood-day counts.
    heatmap_tick_step : int, optional
        Spacing for heatmap storm-year tick labels. If None, chosen
        automatically from the number of years.

    Returns
    -------
    fig, (ax1, ax2)
        Matplotlib figure and axes. Upper panel is the station-year heatmap;
        lower panel is regional annual total flood-day counts.
    """
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    import seaborn as sns

    mat = matrix_df.copy()
    mat.columns = [int(c) for c in mat.columns]

    if station_latitudes is not None:
        lat_series = pd.Series(station_latitudes, dtype="float64").reindex(mat.index)
        sort_df = pd.DataFrame({"station": mat.index, "lat": lat_series.values})
        sort_df["lat_sort"] = sort_df["lat"].fillna(-999.0)
        ordered = sort_df.sort_values(["lat_sort", "station"], ascending=[False, True])["station"].tolist()
        mat = mat.reindex(ordered)

    years = [int(c) for c in mat.columns]

    if isinstance(annual_totals, pd.DataFrame):
        if {"year_storm", "regional_total_flood_days"}.issubset(annual_totals.columns):
            totals = annual_totals.set_index("year_storm")["regional_total_flood_days"]
        else:
            totals = annual_totals.iloc[:, 0]
    else:
        totals = annual_totals

    totals = pd.Series(totals).reindex(years)

    if heatmap_tick_step is None:
        heatmap_tick_step = max(1, len(years) // 14)

    height = max(8.5, len(mat) * 0.36 + 3.4)
    width = max(14, len(years) * 0.36)

    fig, (ax1, ax2) = plt.subplots(
        2,
        1,
        figsize=(width, height),
        gridspec_kw={"height_ratios": [max(4.8, len(mat) * 0.30), 1.6], "hspace": 0.24},
    )

    annot_data = None
    if annot:
        annot_data = mat.copy().map(lambda v: "" if pd.isna(v) else f"{int(round(v))}")

    sns.heatmap(
        mat,
        ax=ax1,
        cmap=cmap,
        linewidths=0.15,
        linecolor="white",
        cbar_kws={"label": "Flood days"},
        annot=annot_data if annot else False,
        fmt="",
        annot_kws={"fontsize": 5.5, "color": "#1f1f1f"},
        mask=mat.isna(),
    )

    ax1.set_ylabel("UHSLC station (north to south)")
    ax1.set_xlabel("Storm year (May–Apr)")
    ax1.set_title(title)
    ax1.tick_params(axis="y", labelsize=8)

    heatmap_tick_positions = np.arange(len(years))[::heatmap_tick_step] + 0.5
    heatmap_tick_labels = [str(y) for y in years[::heatmap_tick_step]]
    ax1.set_xticks(heatmap_tick_positions)
    ax1.set_xticklabels(heatmap_tick_labels, rotation=45, ha="right", fontsize=8)
    ax1.tick_params(axis="x", labelbottom=True, bottom=True)

    x = np.arange(len(years))
    ax2.bar(x + 0.5, totals.values, width=0.8, color="#b44747", edgecolor="#5c1f1f")
    ax2.set_xlim(0, len(years))
    ax2.set_ylabel("Regional total\nflood days")
    ax2.set_xlabel("Storm year (May–Apr)")

    bar_tick_step = max(1, len(years) // 12)
    ax2.set_xticks(x[::bar_tick_step] + 0.5)
    ax2.set_xticklabels([str(y) for y in years[::bar_tick_step]], rotation=45, ha="right")
    ax2.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    return fig, (ax1, ax2)

