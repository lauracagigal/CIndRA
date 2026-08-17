from math import radians, degrees, sin, cos, asin, acos, sqrt, atan2, pi
import numpy as np
import pandas as pd
import xarray as xr

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.colors import to_hex
from matplotlib.colors import to_rgb
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Patch, Rectangle
import seaborn as sns
import plotly.colors
from scipy.stats import linregress

import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.mpl.ticker import LongitudeFormatter, LatitudeFormatter


def classify_genesis_region(lon, lat):
    """Assign a genesis point to one non-overlapping Pacific subregion."""
    lon = lon % 360
    if 0 <= lat <= 40 and 120 <= lon < 180:
        return "Western North Pacific"
    if 0 <= lat <= 40 and 180 <= lon <= 220:
        return "Central North Pacific"
    if -40 <= lat < 0 and 135 <= lon < 180:
        return "Western South Pacific"
    if -40 <= lat < 0 and 180 <= lon <= 240:
        return "Central South Pacific"
    return None


def observations_in_region(dataset, bounds, start_year, end_year):
    """Return valid in-box track observations as a tidy DataFrame."""
    lon = np.mod(dataset.lon.values.astype(float), 360)
    lat = dataset.lat.values.astype(float)
    wind = dataset.wmo_wind.values.astype(float)
    time = dataset.time.values
    lat_min, lat_max = bounds["lat"]
    lon_min, lon_max = bounds["lon"]
    valid = (
        (lat >= lat_min)
        & (lat <= lat_max)
        & (lon >= lon_min)
        & (lon <= lon_max)
        & np.isfinite(wind)
        & ~pd.isna(time)
    )
    storm_index, time_index = np.where(valid)
    dates = pd.to_datetime(time[storm_index, time_index])
    frame = pd.DataFrame(
        {
            "storm": storm_index,
            "year": dates.year,
            "wind": wind[storm_index, time_index],
        }
    )
    return frame.loc[frame.year.between(start_year, end_year)]


def build_storm_metrics(dataset):
    """Build one genesis-based record per IBTrACS storm."""
    lon = np.mod(dataset.lon.values.astype(float), 360)
    lat = dataset.lat.values.astype(float)
    wind = dataset.wmo_wind.values.astype(float)
    time = dataset.time.values
    valid_position = np.isfinite(lon) & np.isfinite(lat) & ~pd.isna(time)
    has_position = valid_position.any(axis=1)
    first_position = valid_position.argmax(axis=1)
    storm_index = np.arange(dataset.sizes["storm"])
    genesis_lon = lon[storm_index, first_position]
    genesis_lat = lat[storm_index, first_position]
    genesis_date = pd.to_datetime(time[storm_index, first_position])

    finite_wind = np.isfinite(wind)
    maximum_wind = np.where(finite_wind, wind, -np.inf).max(axis=1)
    maximum_wind[~finite_wind.any(axis=1)] = np.nan

    observation_hours = np.asarray(pd.to_datetime(time.ravel()).hour).reshape(time.shape)
    ace_mask = finite_wind & (wind >= 34) & np.isin(
        observation_hours, [0, 6, 12, 18]
    )
    storm_ace = np.where(ace_mask, wind**2 * 1e-4, 0.0).sum(axis=1)

    return pd.DataFrame(
        {
            "storm": storm_index,
            "genesis_year": genesis_date.year,
            "genesis_month": genesis_date.month,
            "genesis_region": [
                classify_genesis_region(x, y) if valid else None
                for x, y, valid in zip(genesis_lon, genesis_lat, has_position)
            ],
            "maximum_wind": maximum_wind,
            "ace": storm_ace,
        }
    )


def annual_region_metrics(
    dataset, storm_table, region_name, bounds, years, start_year, end_year
):
    """Calculate annual cyclone counts and ACE for a Pacific subregion."""
    observations = observations_in_region(dataset, bounds, start_year, end_year)
    storms = observations.groupby(["year", "storm"], as_index=False).wind.max()
    genesis_storms = storm_table.loc[
        (storm_table.genesis_region == region_name)
        & storm_table.genesis_year.between(start_year, end_year)
    ]
    result = pd.DataFrame(index=years)
    result.index.name = "year"
    thresholds = (
        ("named", 34),
        ("system", 64),
        ("major", bounds["major_threshold"]),
    )
    for column, threshold in thresholds:
        result[column] = (
            storms.loc[storms.wind >= threshold]
            .groupby("year")
            .size()
            .reindex(years, fill_value=0)
        )
    result["ace"] = (
        genesis_storms.groupby("genesis_year")
        .ace.sum()
        .reindex(years, fill_value=0.0)
    )
    return result


def plot_annual_counts(
    ax, metrics, region_name, system_label, major_threshold,
    start_year, end_year, colors
):
    """Plot overlapping annual cyclone-count areas for a region."""
    x = metrics.index.to_numpy()
    series = [
        ("named", "Named Storms (≥34 kt)"),
        ("system", f"{system_label} (≥64 kt)"),
        ("major", f"Major {system_label} (≥{major_threshold} kt)"),
    ]
    for column, label in series:
        y = metrics[column].to_numpy(dtype=float)
        ax.fill_between(x, 0, y, color=colors[column], alpha=0.9, label=label)
        ax.axhline(y.mean(), color=colors[column], lw=1.2, alpha=0.9)
    ax.set(title=f"{region_name}: {start_year}-{end_year}", ylabel="Annual Count")
    ax.set_xlim(start_year, end_year)
    ax.set_ylim(bottom=0)
    ax.grid(axis="y", alpha=0.3)
    ax.legend(loc="upper left")


def regional_intensity_colors(region_name, region_colors):
    """Create light-to-dark shades from a region's map colour."""
    base = np.asarray(to_rgb(region_colors[region_name]))
    white = np.ones(3)
    return {
        "named_only": 0.35 * base + 0.65 * white,
        "system_only": 0.72 * base + 0.28 * white,
        "major": 0.58 * base,
    }


def plot_stacked_annual_counts(
    ax,
    metrics,
    region_name,
    system_label,
    major_threshold,
    start_year,
    end_year,
    region_colors,
):
    """Plot annual counts as non-overlapping intensity classes."""
    x = metrics.index.to_numpy()
    named_only = (metrics["named"] - metrics["system"]).clip(lower=0)
    system_only = (metrics["system"] - metrics["major"]).clip(lower=0)
    major = metrics["major"].clip(lower=0)
    colors = regional_intensity_colors(region_name, region_colors)

    ax.bar(x, named_only, width=0.82, color=colors["named_only"],
           label="Named only (34–63 kt)", linewidth=0)
    ax.bar(x, system_only, bottom=named_only, width=0.82,
           color=colors["system_only"],
           label=f"{system_label} (64–{major_threshold - 1} kt)", linewidth=0)
    ax.bar(x, major, bottom=named_only + system_only, width=0.82,
           color=colors["major"],
           label=f"Major {system_label} (≥{major_threshold} kt)", linewidth=0)

    rolling = metrics["named"].rolling(5, center=True, min_periods=3).mean()
    ax.plot(x, rolling, color="#252525", linewidth=2.2,
            label="Named storms: 5-year mean", zorder=5)
    valid = metrics["named"].notna()
    trend = linregress(x[valid], metrics.loc[valid, "named"].to_numpy())
    significant = trend.pvalue < 0.05
    ax.plot(
        x, trend.intercept + trend.slope * x, color="#2166ac", linewidth=2.2,
        linestyle="-" if significant else ":", zorder=6,
        label=(f"Linear trend: {trend.slope * 10:+.2f}/decade "
               f"(p={trend.pvalue:.3f}; "
               f"{'significant' if significant else 'not significant'})"),
    )
    ax.axhline(metrics["named"].mean(), color="#252525", linewidth=1,
               linestyle="--", alpha=0.65, label="Period mean")
    ax.set_title(f"{region_name}: {start_year}–{end_year}",
                 fontsize=15, fontweight="bold", pad=10)
    ax.set_ylabel("Annual count", fontsize=15)
    ax.set_xlim(start_year - 0.6, end_year + 0.6)
    ax.tick_params(axis="both", labelsize=13)
    ax.set_ylim(bottom=0)
    ax.grid(axis="y", color="#d9d9d9", linewidth=0.7)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper left", fontsize=12, frameon=False)


def plot_region_inset(
    ax, metrics, region_name, start_year, end_year, region_colors
):
    """Plot a compact annual-count chart for embedding in a regional map."""
    x = metrics.index.to_numpy()
    named_only = (metrics["named"] - metrics["system"]).clip(lower=0)
    system_only = (metrics["system"] - metrics["major"]).clip(lower=0)
    major = metrics["major"].clip(lower=0)
    colors = regional_intensity_colors(region_name, region_colors)
    ax.bar(x, named_only, width=0.9, color=colors["named_only"], linewidth=0)
    ax.bar(x, system_only, bottom=named_only, width=0.9,
           color=colors["system_only"], linewidth=0)
    ax.bar(x, major, bottom=named_only + system_only, width=0.9,
           color=colors["major"], linewidth=0)

    valid = metrics["named"].notna()
    trend = linregress(x[valid], metrics.loc[valid, "named"].to_numpy())
    significant = trend.pvalue < 0.05
    ax.plot(x, trend.intercept + trend.slope * x, color="#2166ac",
            linewidth=1.8, linestyle="-" if significant else ":", zorder=5)
    ax.set_title(region_name, fontsize=9, fontweight="bold", pad=3)
    ax.text(
        0.97, 0.94, f"Trend: {trend.slope * 10:+.2f}/decade\np={trend.pvalue:.3f}",
        transform=ax.transAxes, ha="right", va="top", fontsize=7.5,
        color="#2166ac", zorder=8,
        bbox=dict(facecolor="white", edgecolor="none", alpha=0.78, pad=2),
    )
    ax.set_xlim(start_year - 0.8, end_year + 0.8)
    ax.set_ylim(bottom=0)
    ax.set_xticks([start_year, end_year])
    ax.tick_params(labelsize=7, length=2)
    ax.grid(axis="y", color="#cccccc", linewidth=0.45, alpha=0.8)
    ax.set_axisbelow(True)
    ax.patch.set_facecolor("white")
    ax.patch.set_alpha(0.9)
    for spine in ax.spines.values():
        spine.set_color(region_colors[region_name])
        spine.set_linewidth(1.6)


def plot_pacific_regions_map(regions, region_colors):
    """Create a map showing the Pacific tropical-cyclone subregions."""
    projection = ccrs.PlateCarree(central_longitude=180)
    data_crs = ccrs.PlateCarree()
    fig, ax = plt.subplots(
        figsize=(14, 7), subplot_kw={"projection": projection}
    )
    ax.set_extent([110, 250, -50, 50], crs=data_crs)
    ax.add_feature(cfeature.OCEAN, facecolor="#f3f3f3")
    ax.add_feature(cfeature.LAND, facecolor="#c8c8c8", edgecolor="#8a8a8a")
    ax.add_feature(cfeature.COASTLINE, linewidth=0.5, edgecolor="#777777")
    ax.add_feature(cfeature.BORDERS, linewidth=0.35, linestyle=":")

    for name, bounds in regions.items():
        lon_min, lon_max = bounds["lon"]
        lat_min, lat_max = bounds["lat"]
        color = region_colors[name]
        ax.add_patch(
            Rectangle(
                (lon_min, lat_min), lon_max - lon_min, lat_max - lat_min,
                facecolor=color, edgecolor=color, linewidth=2.5, alpha=0.22,
                transform=data_crs, label=name,
            )
        )
        ax.text(
            (lon_min + lon_max) / 2, (lat_min + lat_max) / 2,
            name.replace(" Pacific", "\nPacific"), color=color, fontsize=11,
            fontweight="bold", ha="center", va="center", transform=data_crs,
        )

    gridlines = ax.gridlines(
        crs=data_crs, draw_labels=True, linewidth=0.5, color="gray",
        alpha=0.6, linestyle="--",
    )
    gridlines.top_labels = False
    gridlines.right_labels = False
    ax.spines["geo"].set_visible(False)
    ax.set_title("Pacific tropical-cyclone subregions", fontsize=16,
                 fontweight="bold")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.17), ncol=2)
    return fig, ax


def plot_genesis_tracks(
    dataset, regions, region_colors, start_year, end_year
):
    """Create a map of historical cyclone tracks grouped by genesis region."""
    track_lon = np.mod(dataset.lon.values.astype(float), 360)
    track_lat = dataset.lat.values.astype(float)
    track_time = dataset.time.values
    valid_position = (
        np.isfinite(track_lon) & np.isfinite(track_lat) & ~pd.isna(track_time)
    )
    has_position = valid_position.any(axis=1)
    first_position = valid_position.argmax(axis=1)
    storm_number = np.arange(dataset.sizes["storm"])
    genesis_lon = track_lon[storm_number, first_position]
    genesis_lat = track_lat[storm_number, first_position]
    genesis_date = pd.to_datetime(track_time[storm_number, first_position])
    genesis_year = genesis_date.year.to_numpy()
    genesis_zone = np.array(
        [
            classify_genesis_region(lon, lat) if available else None
            for lon, lat, available in zip(
                genesis_lon, genesis_lat, has_position
            )
        ],
        dtype=object,
    )

    projection = ccrs.PlateCarree(central_longitude=180)
    data_crs = ccrs.PlateCarree()
    fig, ax = plt.subplots(
        figsize=(15, 9), subplot_kw={"projection": projection}
    )
    ax.set_extent([110, 250, -50, 50], crs=data_crs)
    ax.add_feature(cfeature.OCEAN, facecolor="#f3f3f3")
    ax.add_feature(cfeature.LAND, facecolor="#c8c8c8",
                   edgecolor="#8a8a8a", zorder=2)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.5,
                   edgecolor="#777777", zorder=3)
    ax.add_feature(cfeature.BORDERS, linewidth=0.35, linestyle=":", zorder=3)

    region_counts = {}
    for region_name, bounds in regions.items():
        color = region_colors[region_name]
        selected = np.where(
            (genesis_zone == region_name)
            & (genesis_year >= start_year)
            & (genesis_year <= end_year)
        )[0]
        region_counts[region_name] = len(selected)
        for storm_i in selected:
            valid_track = valid_position[storm_i]
            lon = track_lon[storm_i, valid_track]
            lat = track_lat[storm_i, valid_track]
            seam = np.where(np.abs(np.diff(lon)) > 180)[0]
            lon_plot = lon.astype(float).copy()
            lat_plot = lat.astype(float).copy()
            if seam.size:
                lon_plot = np.insert(lon_plot, seam + 1, np.nan)
                lat_plot = np.insert(lat_plot, seam + 1, np.nan)
            ax.plot(lon_plot, lat_plot, color=color, linewidth=0.75,
                    alpha=0.38, transform=data_crs, zorder=1)
            ax.plot(genesis_lon[storm_i], genesis_lat[storm_i], marker=".",
                    color=color, markersize=3.5, alpha=0.75,
                    transform=data_crs, zorder=4)

        lon_min, lon_max = bounds["lon"]
        lat_min, lat_max = bounds["lat"]
        ax.add_patch(
            Rectangle(
                (lon_min, lat_min), lon_max - lon_min, lat_max - lat_min,
                fill=False, edgecolor=color, linewidth=1.8, alpha=0.9,
                transform=data_crs, zorder=5,
            )
        )

    gridlines = ax.gridlines(
        crs=data_crs, draw_labels=True, linewidth=0.45, color="gray",
        alpha=0.4, linestyle="--",
    )
    gridlines.top_labels = False
    gridlines.right_labels = False
    ax.spines["geo"].set_visible(False)
    handles = [
        Line2D([0], [0], color=region_colors[name], linewidth=2, marker=".",
               label=f"{name} genesis (n={region_counts[name]})")
        for name in regions
    ]
    ax.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, -0.16),
              ncol=2, frameon=False, fontsize=9)
    ax.set_title(
        f"Historical tropical cyclone tracks by genesis subregion, "
        f"{start_year}–{end_year}", fontsize=15, fontweight="bold"
    )
    return fig, ax


def monthly_genesis_metrics(
    storm_table, region_name, major_threshold, start_year, end_year
):
    """Calculate mean monthly genesis counts by exclusive intensity class."""
    storms = storm_table.loc[
        (storm_table.genesis_region == region_name)
        & storm_table.genesis_year.between(start_year, end_year)
        & storm_table.maximum_wind.notna()
        & (storm_table.maximum_wind >= 34)
    ]
    months = pd.Index(range(1, 13), name="month")
    n_years = end_year - start_year + 1
    classes = {
        "named_only": (storms.maximum_wind >= 34)
        & (storms.maximum_wind < 64),
        "system_only": (storms.maximum_wind >= 64)
        & (storms.maximum_wind < major_threshold),
        "major": storms.maximum_wind >= major_threshold,
    }
    result = pd.DataFrame(index=months)
    for name, mask in classes.items():
        result[name] = (
            storms.loc[mask].groupby("genesis_month").size()
            .reindex(months, fill_value=0).astype(float) / n_years
        )
    return result


def plot_monthly_intensity_distribution(
    storm_table, regions, region_colors, start_year, end_year
):
    """Plot monthly cyclone genesis climatology by basin and intensity."""
    month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    fig, axes = plt.subplots(
        2, 2, figsize=(18, 10), constrained_layout=True, sharex=True
    )
    for ax, (region_name, bounds) in zip(axes.flat, regions.items()):
        metrics = monthly_genesis_metrics(
            storm_table, region_name, bounds["major_threshold"],
            start_year, end_year,
        )
        colors = regional_intensity_colors(region_name, region_colors)
        named_only = metrics["named_only"]
        system_only = metrics["system_only"]
        major = metrics["major"]
        x = metrics.index.to_numpy()
        ax.bar(x, named_only, color=colors["named_only"], width=0.82,
               label="Named only (34–63 kt)")
        ax.bar(x, system_only, bottom=named_only,
               color=colors["system_only"], width=0.82,
               label=f"{bounds['system']} (64–{bounds['major_threshold'] - 1} kt)")
        ax.bar(x, major, bottom=named_only + system_only,
               color=colors["major"], width=0.82,
               label=f"Major {bounds['system']} (≥{bounds['major_threshold']} kt)")
        ax.set_title(region_name, fontsize=15, fontweight="bold")
        ax.set_ylabel("Mean cyclones per year", fontsize=16)
        ax.set_xticks(x, month_labels)
        ax.tick_params(axis="both", labelsize=14)
        ax.set_ylim(bottom=0)
        ax.grid(axis="y", color="#d9d9d9", linewidth=0.7)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(loc="upper left", fontsize=13, frameon=False)
    fig.suptitle(
        f"Monthly tropical cyclone genesis by Pacific subregion, "
        f"{start_year}–{end_year}", fontsize=20, fontweight="bold",
    )
    fig.supxlabel("Genesis month", fontsize=18, fontweight="bold")
    return fig, axes


def spatial_track_density(
    dataset, bounds, start_year, end_year, grid_size=2.0
):
    """Count unique cyclone passages through regular lon-lat grid cells."""
    lon = np.mod(dataset.lon.values.astype(float), 360)
    lat = dataset.lat.values.astype(float)
    time = dataset.time.values
    years = np.asarray(pd.to_datetime(time.ravel()).year).reshape(time.shape)
    lon_min, lon_max = bounds["lon"]
    lat_min, lat_max = bounds["lat"]
    lon_edges = np.arange(lon_min, lon_max + grid_size, grid_size)
    lat_edges = np.arange(lat_min, lat_max + grid_size, grid_size)
    density = np.zeros((len(lat_edges) - 1, len(lon_edges) - 1), dtype=float)

    valid = (
        np.isfinite(lon) & np.isfinite(lat)
        & (years >= start_year) & (years <= end_year)
        & (lon >= lon_min) & (lon <= lon_max)
        & (lat >= lat_min) & (lat <= lat_max)
    )
    for storm_index in range(dataset.sizes["storm"]):
        if not valid[storm_index].any():
            continue
        storm_lon = lon[storm_index, valid[storm_index]]
        storm_lat = lat[storm_index, valid[storm_index]]
        lon_bin = np.searchsorted(lon_edges, storm_lon, side="right") - 1
        lat_bin = np.searchsorted(lat_edges, storm_lat, side="right") - 1
        lon_bin = np.clip(lon_bin, 0, density.shape[1] - 1)
        lat_bin = np.clip(lat_bin, 0, density.shape[0] - 1)
        visited_cells = np.unique(np.column_stack([lat_bin, lon_bin]), axis=0)
        density[visited_cells[:, 0], visited_cells[:, 1]] += 1

    density /= end_year - start_year + 1
    return density, lon_edges, lat_edges


def plot_spatial_track_density(
    dataset, regions, region_colors, start_year, end_year, grid_size=2.0
):
    """Plot mean annual cyclone-track density for each Pacific subregion."""
    projection = ccrs.PlateCarree(central_longitude=180)
    data_crs = ccrs.PlateCarree()
    fig, axes = plt.subplots(
        2, 2, figsize=(18, 10), constrained_layout=True,
        subplot_kw={"projection": projection},
    )
    for ax, (region_name, bounds) in zip(axes.flat, regions.items()):
        density, lon_edges, lat_edges = spatial_track_density(
            dataset, bounds, start_year, end_year, grid_size
        )
        color_map = mcolors.LinearSegmentedColormap.from_list(
            f"{region_name}-density", ["#ffffff", region_colors[region_name]]
        )
        masked_density = np.ma.masked_equal(density, 0)
        mesh = ax.pcolormesh(
            lon_edges, lat_edges, masked_density, cmap=color_map,
            shading="flat", transform=data_crs,
        )
        lon_min, lon_max = bounds["lon"]
        lat_min, lat_max = bounds["lat"]
        ax.set_extent(
            [lon_min, lon_max, lat_min, lat_max], crs=data_crs
        )
        ax.add_feature(cfeature.OCEAN, facecolor="#f5f5f5", zorder=-2)
        ax.add_feature(cfeature.LAND, facecolor="#d0d0d0",
                       edgecolor="#888888", zorder=2)
        ax.add_feature(cfeature.COASTLINE, linewidth=0.6,
                       edgecolor="#777777", zorder=3)
        ax.add_feature(cfeature.BORDERS, linewidth=0.35,
                       linestyle=":", zorder=3)
        gridlines = ax.gridlines(
            crs=data_crs, draw_labels=True, linewidth=0.4,
            color="gray", alpha=0.5, linestyle="--",
        )
        gridlines.top_labels = False
        gridlines.right_labels = False
        gridlines.xlabel_style = {"size": 11}
        gridlines.ylabel_style = {"size": 11}
        ax.spines["geo"].set_visible(False)
        ax.set_title(region_name, fontsize=15, fontweight="bold", pad=10)
        colorbar = fig.colorbar(mesh, ax=ax, shrink=0.84, pad=0.03)
        colorbar.set_label("Mean cyclone passages per year", fontsize=12)
        colorbar.ax.tick_params(labelsize=11)
    fig.suptitle(
        f"Spatial density of tropical cyclone tracks, {start_year}–{end_year}",
        fontsize=20, fontweight="bold",
    )
    return fig, axes


def plot_period_comparison(
    regional_metrics, region_colors, periods, metric="named"
):
    """Compare annual regional cyclone metrics across named periods."""
    metric_labels = {
        "named": "Annual named cyclones (≥34 kt)",
        "system": "Annual systems (≥64 kt)",
        "major": "Annual major systems (≥96 kt)",
        "ace": r"Annual ACE ($10^4$ kt$^2$)",
    }
    if metric not in metric_labels:
        raise ValueError(
            f"metric must be one of {', '.join(metric_labels)}"
        )

    fig, axes = plt.subplots(
        2, 2, figsize=(18, 10), constrained_layout=True, sharey=False
    )
    for ax, (region_name, metrics) in zip(
        axes.flat, regional_metrics.items()
    ):
        period_values = []
        period_labels = []
        for label, (period_start, period_end) in periods.items():
            values = metrics.loc[period_start:period_end, metric].dropna().astype(float)
            period_values.append(values.to_numpy())
            period_labels.append(f"{label}\n(n={len(values)})")

        color = region_colors[region_name]
        boxplot = ax.boxplot(
            period_values, tick_labels=period_labels, patch_artist=True,
            widths=0.58, showmeans=True,
            medianprops={"color": "#202020", "linewidth": 2.2},
            meanprops={"marker": "D", "markerfacecolor": "white",
                       "markeredgecolor": "#202020", "markersize": 6},
            whiskerprops={"color": color, "linewidth": 1.7},
            capprops={"color": color, "linewidth": 1.7},
            flierprops={"marker": "o", "markerfacecolor": color,
                        "markeredgecolor": color, "alpha": 0.5},
        )
        for box in boxplot["boxes"]:
            box.set_facecolor(color)
            box.set_edgecolor(color)
            box.set_alpha(0.55)

        for position, values in enumerate(period_values, start=1):
            if not len(values):
                continue
            offsets = np.linspace(-0.16, 0.16, len(values))
            ax.scatter(
                position + offsets, values, s=32, color=color,
                edgecolor="white", linewidth=0.5, alpha=0.8, zorder=4,
            )

        legend_handles = [
            Line2D(
                [0], [0], marker="o", linestyle="none", color=color,
                markeredgecolor="white", markersize=8, label="Annual values",
            ),
            Line2D([0], [0], color="#202020", linewidth=2.2,
                   label="Median"),
            Line2D(
                [0], [0], marker="D", linestyle="none", color="#202020",
                markerfacecolor="white", markersize=7, label="Mean",
            ),
        ]
        ax.set_title(region_name, fontsize=18, fontweight="bold")
        ax.set_ylabel(metric_labels[metric], fontsize=18)
        ax.tick_params(axis="both", labelsize=15)
        ax.set_ylim(bottom=0)
        ax.grid(axis="y", color="#d9d9d9", linewidth=0.7)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(
            handles=legend_handles, loc="upper right", fontsize=14,
            frameon=False,
        )

    first_year = min(start for start, _ in periods.values())
    last_year = max(end for _, end in periods.values())
    fig.suptitle(
        f"Annual tropical cyclone activity by period, "
        f"{first_year}–{last_year}", fontsize=24, fontweight="bold",
    )
    fig.supxlabel("Period", fontsize=20, fontweight="bold")
    return fig, axes


def plot_regional_annual_counts(
    regional_metrics, regions, start_year, end_year, colors
):
    """Create the four-panel annual cyclone-count figure."""
    fig, axes = plt.subplots(2, 2, figsize=(15, 9), constrained_layout=True)
    for ax, (name, bounds) in zip(axes.flat, regions.items()):
        plot_annual_counts(
            ax, regional_metrics[name], name, bounds["system"],
            bounds["major_threshold"], start_year, end_year, colors,
        )
    fig.suptitle("Tropical cyclone activity in Pacific subregions (IBTrACS)",
                 fontsize=16, fontweight="bold")
    return fig, axes


def plot_regional_intensity_counts(
    regional_metrics, regions, start_year, end_year, region_colors
):
    """Create the four-panel annual intensity-composition figure."""
    fig, axes = plt.subplots(
        2, 2, figsize=(18, 11), constrained_layout=True, sharex=True
    )
    for ax, (name, bounds) in zip(axes.flat, regions.items()):
        plot_stacked_annual_counts(
            ax, regional_metrics[name], name, bounds["system"],
            bounds["major_threshold"], start_year, end_year, region_colors,
        )
    fig.suptitle("Annual tropical cyclone intensity composition (IBTrACS)",
                 fontsize=20, fontweight="bold")
    fig.supxlabel("Year", fontsize=16, fontweight="bold")
    return fig, axes


def plot_regional_map_dashboard(
    regional_metrics, regions, start_year, end_year, region_colors,
    inset_positions
):
    """Create the regional map with embedded annual-count charts."""
    projection = ccrs.PlateCarree(central_longitude=180)
    data_crs = ccrs.PlateCarree()
    fig = plt.figure(figsize=(17, 10))
    map_ax = fig.add_axes([0.04, 0.09, 0.92, 0.82], projection=projection)
    map_ax.set_extent([110, 250, -50, 50], crs=data_crs)
    map_ax.add_feature(cfeature.OCEAN, facecolor="#f3f3f3")
    map_ax.add_feature(cfeature.LAND, facecolor="#c8c8c8",
                       edgecolor="#8a8a8a")
    map_ax.add_feature(cfeature.COASTLINE, linewidth=0.5,
                       edgecolor="#777777")
    map_ax.add_feature(cfeature.BORDERS, linewidth=0.3, linestyle=":")
    map_ax.gridlines(color="gray", linewidth=0.4, alpha=0.35, linestyle="--")
    map_ax.spines["geo"].set_visible(False)

    for name, bounds in regions.items():
        lon_min, lon_max = bounds["lon"]
        lat_min, lat_max = bounds["lat"]
        map_ax.add_patch(
            Rectangle(
                (lon_min, lat_min), lon_max - lon_min, lat_max - lat_min,
                facecolor=region_colors[name], edgecolor=region_colors[name],
                linewidth=2.2, alpha=0.12, transform=data_crs,
            )
        )

    inset_axes = {}
    for name, position in inset_positions.items():
        inset_axes[name] = fig.add_axes(position)
        plot_region_inset(
            inset_axes[name], regional_metrics[name], name, start_year, end_year,
            region_colors,
        )

    handles = [
        Patch(facecolor="#dedede",
              label="Named only (34–63 kt)"),
        Patch(facecolor="#999999",
              label="System below major threshold"),
        Patch(facecolor="#4d4d4d",
              label="Major systems (≥96 kt)"),
        Line2D([0], [0], color="#2166ac", lw=2, label="Linear trend"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=4, frameon=False,
               bbox_to_anchor=(0.5, 0.035), fontsize=10)
    fig.suptitle(
        f"Tropical cyclone activity by Pacific subregion, "
        f"{start_year}–{end_year}", fontsize=17, fontweight="bold", y=0.96,
    )
    return fig, map_ax, inset_axes


def plot_regional_ace(
    regional_metrics, region_colors, start_year, end_year
):
    """Create the four-panel Accumulated Cyclone Energy figure."""
    fig, axes = plt.subplots(
        2, 2, figsize=(15, 8), constrained_layout=True, sharex=True
    )
    for ax, (name, metrics) in zip(axes.flat, regional_metrics.items()):
        values = metrics["ace"].astype(float)
        ax.bar(values.index, values, color=region_colors[name], alpha=0.58,
               width=0.82, edgecolor="none", label="Annual ACE")
        rolling = values.rolling(5, center=True, min_periods=3).mean()
        ax.plot(values.index, rolling, color="#252525", linewidth=2.1,
                label="5-year mean", zorder=4)
        valid = values.notna()
        trend = linregress(values.index[valid], values[valid])
        trend_values = trend.intercept + trend.slope * values.index.to_numpy()
        significant = trend.pvalue < 0.05
        ax.plot(values.index, trend_values, color="#2166ac", linewidth=2,
                linestyle="-" if significant else ":", label="Linear trend",
                zorder=5)
        ax.text(
            0.98, 0.95,
            f"Trend: {trend.slope * 10:+.2f} ACE/decade\np={trend.pvalue:.3f}",
            transform=ax.transAxes, ha="right", va="top", fontsize=8,
            color="#2166ac",
            bbox=dict(facecolor="white", edgecolor="none", alpha=0.8, pad=2),
        )
        ax.set(title=name, ylabel=r"ACE ($10^4$ kt$^2$)")
        ax.set_xlim(start_year - 0.6, end_year + 0.6)
        ax.set_ylim(bottom=0)
        ax.grid(axis="y", color="#d9d9d9", linewidth=0.7)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(loc="upper left", frameon=False, fontsize=8)
    fig.suptitle(
        f"Accumulated Cyclone Energy by Pacific subregion, "
        f"{start_year}–{end_year}", fontsize=16, fontweight="bold",
    )
    return fig, axes


def style_matrix(df_metrics, title="Key Metrics Summary"):
    """Format a tropical-cyclone metrics table for notebook display."""
    if not isinstance(df_metrics, pd.DataFrame):
        raise TypeError("df_metrics must be a pandas DataFrame")

    required_cols = {"Metric", "Value"}
    if not required_cols.issubset(df_metrics.columns):
        raise ValueError('df_metrics must contain "Metric" and "Value" columns')

    styled = (
        df_metrics.style
        .hide(axis="index")
        .set_caption(title)
        .set_table_styles([
            {
                "selector": "caption",
                "props": [
                    ("font-size", "18px"),
                    ("font-weight", "bold"),
                    ("text-align", "center"),
                    ("color", "#2C013B"),
                    ("margin-bottom", "12px"),
                ],
            },
            {
                "selector": "thead th",
                "props": [
                    ("background-color", "#eed3f4"),
                    ("color", "#2C013B"),
                    ("font-weight", "bold"),
                    ("text-align", "center"),
                ],
            },
            {
                "selector": "td",
                "props": [
                    ("padding", "6px"),
                    ("border-bottom", "1px solid #ccc"),
                    ("text-align", "center"),
                ],
            },
        ])
        .set_properties(subset=["Metric"], **{"text-align": "center"})
        .applymap(lambda value: "font-weight: bold", subset=["Metric"])
    )

    formatters = {"Value": "{:.3f}"}
    if "Year" in df_metrics.columns:
        formatters["Year"] = "{:.0f}"
    return styled.format(formatters, na_rep="")


def _tc_enso_year_count(oni, category):
    """Return the number of unique years in an ONI category."""
    return len(oni.loc[oni.oni_cat == category].index.year.unique())


def table_tcs_32a(tcs_sel_params, oni):
    """Build key TC metrics for storms selected around a study site."""
    counts = {}
    for name, oni_category in (("nino", 1), ("nina", -1), ("neutral", 0)):
        storms = tcs_sel_params.where(tcs_sel_params.oni_cat == oni_category, drop=True)
        severe = tcs_sel_params.where(
            (tcs_sel_params.oni_cat == oni_category)
            & (tcs_sel_params.category >= 3),
            drop=True,
        )
        _, storm_counts = np.unique(storms.dmin_date.dt.year.values, return_counts=True)
        _, severe_counts = np.unique(severe.dmin_date.dt.year.values, return_counts=True)
        n_years = _tc_enso_year_count(oni, oni_category)
        counts[name] = (
            len(storms.storm) / n_years,
            storm_counts.std(),
            len(severe.storm) / n_years,
            severe_counts.std(),
        )

    years, annual_counts = np.unique(
        tcs_sel_params.dmin_date.dt.year.values, return_counts=True
    )
    severe = tcs_sel_params.where(tcs_sel_params.category >= 3, drop=True)
    severe_years, severe_annual_counts = np.unique(
        severe.dmin_date.dt.year.values, return_counts=True
    )

    metrics = {
        "Metric": [
            "Total number of tracks",
            "Tropical Storms per year",
            "Standard deviation of storms per year",
            f"Maximum number of storms in a year {years[np.argmax(annual_counts)]}",
            f"Minimum number of storms in a year {years[np.argmin(annual_counts)]}",
            "Major Hurricanes (Category 3+) per year",
            "Standard deviation of major hurricanes per year",
            f"Maximum number of major hurricanes in a year {severe_years[np.argmax(severe_annual_counts)]}",
            f"Minimum number of major hurricanes in a year {severe_years[np.argmin(severe_annual_counts)]}",
            " ", "EL NIÑO",
            "Total number of storm per year",
            "Standard deviation of storms per year",
            "Major Hurricanes (Category 3+) per year",
            "Standard deviation of severe storms per year",
            " ", "LA NIÑA",
            "Total number of storm per year",
            "Standard deviation of storms per year",
            "Major Hurricanes (Category 3+) per year",
            "Standard deviation of severe storms per year",
            " ", "NEUTRAL",
            "Total number of storm per year",
            "Standard deviation of storms per year",
            "Major Hurricanes (Category 3+) per year",
            "Standard deviation of severe storms per year",
        ],
        "Value": [
            len(tcs_sel_params.storm),
            len(tcs_sel_params.storm) / len(years),
            annual_counts.std(), annual_counts.max(), annual_counts.min(),
            len(severe.storm) / len(years),
            severe_annual_counts.std(),
            severe_annual_counts.max(), severe_annual_counts.min(),
            np.nan, np.nan, *counts["nino"],
            np.nan, np.nan, *counts["nina"],
            np.nan, np.nan, *counts["neutral"],
        ],
    }
    return pd.DataFrame(metrics)


def table_tcs_32b(tcs_WP, oni):
    """Build key TC metrics for the western Pacific basin."""
    first_times = pd.DataFrame(tcs_WP.isel(date_time=0).time.values)
    first_times.index = pd.DatetimeIndex(first_times[0]).to_period("M").to_timestamp()
    first_times["oni_cat"] = oni.oni_cat

    # Work on a copy so creating helper variables does not mutate notebook data.
    tcs_WP = tcs_WP.copy()
    tcs_WP["oni_cat"] = (("storm",), first_times["oni_cat"].values)
    tcs_WP["storm_c"] = (("storm",), np.ones(tcs_WP.storm.size))

    years, annual_counts = np.unique(
        tcs_WP.isel(date_time=0).time.dt.year.values, return_counts=True
    )
    severe = tcs_WP.where(tcs_WP.category >= 3, drop=True)
    severe_years, severe_annual_counts = np.unique(
        severe.isel(date_time=0).time.dt.year.values, return_counts=True
    )

    counts = {}
    for name, oni_category in (("nino", 1), ("nina", -1), ("neutral", 0)):
        storms = tcs_WP.where(tcs_WP.oni_cat == oni_category, drop=True)
        severe_storms = tcs_WP.where(
            (tcs_WP.oni_cat == oni_category) & (tcs_WP.category >= 3),
            drop=True,
        )
        n_years = _tc_enso_year_count(oni, oni_category)

        def annual_std(dataset):
            if dataset.storm.size == 0:
                return np.nan
            first = dataset.isel(date_time=0)
            return first.groupby(first.time.dt.year).sum().storm_c.std().item()

        counts[name] = (
            len(storms.storm) / n_years,
            annual_std(storms),
            len(severe_storms.storm) / n_years,
            annual_std(severe_storms),
        )

    metrics = {
        "Metric": [
            "Total number of tracks",
            "Tropical Storms per year",
            "Standard deviation of storms per year",
            f"Maximum number of storms in a year {years[np.argmax(annual_counts)]}",
            f"Minimum number of storms in a year {years[np.argmin(annual_counts)]}",
            "Major Hurricanes (Category 3+) per year",
            "Standard deviation of major hurricanes per year",
            f"Maximum number of major hurricanes in a year {severe_years[np.argmax(severe_annual_counts)]}",
            f"Minimum number of major hurricanes in a year {severe_years[np.argmin(severe_annual_counts)]}",
            " ", "EL NIÑO",
            "Total number of storm per year",
            "Standard deviation of storms per year",
            "Major Hurricanes (Category 3+) per year",
            "Standard deviation of major hurricanes per year",
            " ", "LA NIÑA",
            "Total number of storm per year",
            "Standard deviation of storms per year",
            "Major Hurricanes (Category 3+) per year",
            "Standard deviation of major hurricanes per year",
            " ", "NEUTRAL",
            "Total number of storm per year",
            "Standard deviation of storms per year",
            "Major Hurricanes (Category 3+) per year",
            "Standard deviation of major hurricanes per year",
        ],
        "Value": [
            len(tcs_WP.storm), len(tcs_WP.storm) / len(years),
            annual_counts.std(), annual_counts.max(), annual_counts.min(),
            len(severe.storm) / len(years),
            severe_annual_counts.std(),
            severe_annual_counts.max(), severe_annual_counts.min(),
            np.nan, np.nan, *counts["nino"],
            np.nan, np.nan, *counts["nina"],
            np.nan, np.nan, *counts["neutral"],
        ],
    }
    return pd.DataFrame(metrics)


def GetUniqueRows(np_array):
    d = collections.OrderedDict()
    for a in np_array:
        t = tuple(a)
        if t in d:
            d[t] += 1
        else:
            d[t] = 1

    result = []
    for (key, value) in d.items():
        result.append(list(key) + [value])

    np_result = np.asarray(result)
    return np_result

def get_ibtracs_category(xds_TCs, d_vns, fillwinds = True):

    n_storms = xds_TCs.storm.shape[0]

    if fillwinds:

        xfit = xds_TCs.wmo_pres.min(dim = 'date_time').values
        yfit = xds_TCs.wmo_wind.max(dim = 'date_time').values
        mask = np.isnan(xfit) | np.isnan(yfit)
        linreg = np.polyfit(xfit[~mask], yfit[~mask], 2)
        xds_TCs['wmo_wind'] = xds_TCs['wmo_wind'].fillna(linreg[0]*xds_TCs['wmo_pres']**2 + linreg[1]*xds_TCs['wmo_pres'] + linreg[2])
    
    nm_wnd = d_vns['wind']
    wnd = xds_TCs[nm_wnd].values[:]

    l_categ_in = []
    for i_storm in range(n_storms):
        wnd_s_in = wnd[i_storm]

        wnd_s_max = np.nanmax(wnd_s_in)
        categ = GetStormCategory_wind(wnd_s_max)
        l_categ_in.append(np.array(categ))

    xds_TCs['category'] = (('storm'), np.array(l_categ_in))

    return xds_TCs

def GeoDistance(lat1, lon1, lat2, lon2):
    'Returns great circle distance between points in degrees'

    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    a = sin((lat2-lat1)/2)**2 + cos(lat1) * cos(lat2) * sin((lon2-lon1)/2)**2;
    if a < 0: a = 0
    if a > 1: a = 1

    r = 1
    rng = r * 2 * atan2(sqrt(a), sqrt(1-a))
    rng = degrees(rng)

    return rng

def GeoAzimuth(lat1, lon1, lat2, lon2):
    'Returns geodesic azimuth between point1 and point2'

    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    az = atan2(
        cos(lat2) * sin(lon2-lon1),
        cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(lon2-lon1)
    )
    if lat1 <= -pi/2: az = 0
    if lat2 >=  pi/2: az = 0
    if lat2 <= -pi/2: az = pi
    if lat1 >=  pi/2: az = pi

    az = az % (2*pi)
    az = degrees(az)

    return az


def Extract_Circle(xds_TCs, p_lon, p_lat, r, d_vns, fillwinds = False):
    '''
    Extracts TCs inside circle - used with NWO or Nakajo databases

    xds_TCs: tropical cyclones track database
        lon, lat, pressure variables
        storm dimension

    circle defined by:
        p_lon, p_lat  -  circle center
        r             -  circle radius (degree)

    d_vns: dictionary to set longitude, latitude, time and pressure varnames

    returns:
        xds_area: selection of xds_TCs inside circle
        xds_inside: contains TCs custom data inside circle
    '''

    if fillwinds:
        
        xfit = xds_TCs.wmo_pres.min(dim = 'date_time').values
        yfit = xds_TCs.wmo_wind.max(dim = 'date_time').values
        mask = np.isnan(xfit) | np.isnan(yfit)
        linreg = np.polyfit(xfit[~mask], yfit[~mask], 2)
        xds_TCs['wmo_wind'] = xds_TCs['wmo_wind'].fillna(linreg[0]*xds_TCs['wmo_pres']**2 + linreg[1]*xds_TCs['wmo_pres'] + linreg[2])


    # point longitude and latitude
    lonlat_p = np.array([[p_lon, p_lat]])

    # get names of vars: longitude, latitude, pressure and time
    nm_lon = d_vns['longitude']
    nm_lat = d_vns['latitude']
    nm_prs = d_vns['pressure']
    nm_wnd = d_vns['wind']
    nm_tim = d_vns['time']

    # storms longitude, latitude, pressure and time (if available)
    lon = xds_TCs[nm_lon].values[:]
    lat = xds_TCs[nm_lat].values[:]
    prs = xds_TCs[nm_prs].values[:]
    wnd = xds_TCs[nm_wnd].values[:]
    time = xds_TCs[nm_tim].values[:]

    # get storms inside circle area
    n_storms = xds_TCs.storm.shape[0]
    l_storms_area = []

    # inside parameters holders
    l_prs_min_in = []   # circle minimun pressure
    l_prs_mean_in = []  # circle mean pressure
    l_vel_mean_in = []  # circle mean translation speed
    l_categ_in = []     # circle storm category
    l_date_in = []      # circle date (day)
    l_date_last = []    # last cyclone date 
    l_gamma = []        # azimuth 
    l_delta = []        # delta 

    l_wnd_max_in = []   # circle minimun pressure

    l_ix_in = []        # historical enters the circle index
    l_ix_out = []       # historical leaves the circle index 

    for i_storm in range(n_storms):

        # fix longitude <0 data and skip "one point" tracks
        lon_storm = lon[i_storm]
        if not isinstance(lon_storm, np.ndarray): continue
        lon_storm[lon_storm<0] = lon_storm[lon_storm<0] + 360

        # stack storm longitude, latitude
        lonlat_s = np.column_stack(
            (lon_storm, lat[i_storm])
        )

        # index for removing nans
        ix_nonan = ~np.isnan(lonlat_s).any(axis=1)
        lonlat_s = lonlat_s[ix_nonan]


        # calculate geodesic distance (degree)
        geo_dist = []
        for lon_ps, lat_ps in lonlat_s:
            geo_dist.append(GeoDistance(lat_ps, lon_ps, p_lat, p_lon))
        geo_dist = np.asarray(geo_dist)

        # find storm inside circle and calculate parameters
        if (geo_dist < r).any():


            # storm inside circle
            ix_in = np.where(geo_dist < r)[0][:]

            # storm translation velocity
            geo_dist_ss = []
            for i_row in range(lonlat_s.shape[0]-1):
                i0_lat, i0_lon = lonlat_s[i_row][1], lonlat_s[i_row][0]
                i1_lat, i1_lon = lonlat_s[i_row+1][1], lonlat_s[i_row+1][0]
                geo_dist_ss.append(GeoDistance(i0_lat, i0_lon, i1_lat, i1_lon))
            geo_dist_ss = np.asarray(geo_dist_ss)

            # get delta time in hours (irregular data time delta)
            if isinstance(time[i_storm][0], np.datetime64):
                # round to days
                time[i_storm] = np.array(
                    [np.datetime64(xt, 'h') for xt in time[i_storm]]
                )

                delta_h = np.diff(
                    time[i_storm][~np.isnat(time[i_storm])]
                ).astype('timedelta64[h]').astype(float)

            else:
                # nakajo: time already in hours
                delta_h = np.diff(
                    time[i_storm][~np.isnan(time[i_storm])]
                ).astype(float)

            vel = geo_dist_ss * 111.0/delta_h  # km/h

            # promediate vel 
            velpm = (vel[:-1] + vel[1:])/2
            velpm = np.append(vel[0], velpm)
            velpm = np.append(velpm, vel[-1])

            # calculate azimuth 
            lat_in_end, lon_in_end = lonlat_s[ix_in[-1]][1], lonlat_s[ix_in[-1]][0]
            lat_in_ini, lon_in_ini = lonlat_s[ix_in[0]][1], lonlat_s[ix_in[0]][0]
            gamma = GeoAzimuth(lat_in_end, lon_in_end, lat_in_ini, lon_in_ini)
            if gamma < 0.0: gamma += 360

            # calculate delta
            nd = 1000
            st = 2*np.pi/nd
            ang = np.arange(0, 2*np.pi + st, st)
            xps = r * np.cos(ang) + p_lat
            yps = r * np.sin(ang) + p_lon
            angle_radius = []
            for x, y in zip(xps, yps):
                angle_radius.append(GeoAzimuth(lat_in_end, lon_in_end, x, y))
            angle_radius = np.asarray(angle_radius)

            im = np.argmin(np.absolute(angle_radius - gamma))
            delta = GeoAzimuth(p_lat, p_lon, xps[im], yps[im]) # (-180, +180)
            if delta < 0.0: delta += 360

            # more parameters 
            prs_s_in = prs[i_storm][ix_in]  # pressure
            wnd_s_in = wnd[i_storm][ix_in]  # pressure

            # nan data filter
            if np.all(np.isnan(prs_s_in)):

                dist_in = geo_dist[ix_in]
                p_dm = np.where((dist_in==np.min(dist_in)))[0]  # closest to point
                time_s_in = time[i_storm][ix_in]  # time
                time_closest = time_s_in[p_dm][0]  # time closest to point 
                # continue
                l_storms_area.append(i_storm)
                l_prs_min_in.append(np.array(np.nan))
                l_prs_mean_in.append(np.array(np.nan))
                l_vel_mean_in.append(np.array(np.nan))
                l_categ_in.append(np.array(np.nan))
                l_date_in.append(time_closest)
                l_gamma.append(np.nan)
                l_delta.append(np.nan)
                l_wnd_max_in.append(np.array(np.nan))

                # store historical indexes inside circle 
                l_ix_in.append(ix_in[0])
                l_ix_out.append(ix_in[-1])

                # store last cyclone date too
                l_date_last.append(time[i_storm][ix_nonan][-1])
            else:

                no_nan = ~np.isnan(prs_s_in)
                    
                prs_s_in = prs_s_in[no_nan]
                prs_s_min = np.min(prs_s_in)  # pressure minimun
                prs_s_mean = np.mean(prs_s_in)


                wnd_s_max = np.nanmax(wnd_s_in)  # wind maximum inside
                # wnd_s_max = np.nanmax(wnd[i_storm]) # wind maximum all track


                vel_s_in = velpm[ix_in][no_nan]  # velocity
                vel_s_mean = np.mean(vel_s_in) # velocity mean

                # categ = GetStormCategory_pres(prs_s_min)  # category
                categ = GetStormCategory_wind(wnd_s_max)  # category

                dist_in = geo_dist[ix_in][no_nan]
                p_dm = np.where((dist_in==np.min(dist_in)))[0]  # closest to point

                time_s_in = time[i_storm][ix_in][no_nan]  # time
                time_closest = time_s_in[p_dm][0]  # time closest to point 

                
                # filter storms 
                # TODO: storms with only one track point inside radius. solve?
                if np.isnan(np.array(prs_s_in)).any() or \
                (np.array(prs_s_in) <= 860).any() or \
                gamma == 0.0:
                    
                    continue

                # store parameters

                l_storms_area.append(i_storm)
                l_prs_min_in.append(np.array(prs_s_min))
                l_prs_mean_in.append(np.array(prs_s_mean))
                l_vel_mean_in.append(np.array(vel_s_mean))
                l_categ_in.append(np.array(categ))
                l_date_in.append(time_closest)
                l_gamma.append(gamma)
                l_delta.append(delta)
                l_wnd_max_in.append(np.array(wnd_s_max))

                # store historical indexes inside circle 
                l_ix_in.append(ix_in[0])
                l_ix_out.append(ix_in[-1])

                # store last cyclone date too
                l_date_last.append(time[i_storm][ix_nonan][-1])

    # cut storm dataset to selection
    xds_TCs_sel = xds_TCs.isel(storm=l_storms_area)
    xds_TCs_sel = xds_TCs_sel.assign_coords(storm = np.array(l_storms_area))

    # store storms parameters 
    xds_TCs_sel_params = xr.Dataset(
        {
            'pressure_min':(('storm'), np.array(l_prs_min_in)),
            'pressure_mean':(('storm'), np.array(l_prs_mean_in)),
            'wind_max':(('storm'), np.array(l_wnd_max_in)),
            'velocity_mean':(('storm'), np.array(l_vel_mean_in)),
            'gamma':(('storm'), np.array(l_gamma)),
            'delta':(('storm'), np.array(l_delta)),
            'category':(('storm'), np.array(l_categ_in)),
            'dmin_date':(('storm'), np.array(l_date_in)),
            'last_date':(('storm'), np.array(l_date_last)),
            'index_in':(('storm'), np.array(l_ix_in)),
            'index_out':(('storm'), np.array(l_ix_out)),
        },
        coords = {
            'storm':(('storm'), np.array(l_storms_area))
        },
        attrs = {
            'point_lon' : p_lon,
            'point_lat' : p_lat,
            'point_r' : r,
        }
    )

    return xds_TCs_sel, xds_TCs_sel_params

def GetStormCategory_pres(pres_min):
    '''
    Returns storm category (int 5-0)
    '''

    pres_lims = [920, 944, 964, 979, 1000]

    if pres_min <= pres_lims[0]:
        return 5
    elif pres_min <= pres_lims[1]:
        return 4
    elif pres_min <= pres_lims[2]:
        return 3
    elif pres_min <= pres_lims[3]:
        return 2
    elif pres_min <= pres_lims[4]:
        return 1
    else:
        return 0

def GetStormCategory_wind(wind_max):
    '''
    Returns storm category (int 5-0)
    '''
    # https://www.nhc.noaa.gov/aboutsshws.php

    wind_max = wind_max/.88 # The saffir simpson scale corresponds to the 1min sustained wind speed. WMO is 10min

    wind_lims = [136, 114, 98, 83, 64]

    if wind_max >= wind_lims[0]:
        return 5
    elif wind_max >= wind_lims[1]:
        return 4
    elif wind_max >= wind_lims[2]:
        return 3
    elif wind_max >= wind_lims[3]:
        return 2
    elif wind_max >= wind_lims[4]:
        return 1
    else:
        return 0

def SortCategoryCount(np_categ, nocat=9):
    '''
    Sort category change - count matrix
    np_categ = [[category1, category2, count], ...]
    '''

    categs = [0,1,2,3,4,5,9]

    np_categ = np_categ.astype(int)
    np_sort = np.empty((len(categs)*(len(categs)-1),3))
    rc=0
    for c1 in categs[:-1]:
        for c2 in categs:
            p_row = np.where((np_categ[:,0]==c1) & (np_categ[:,1]==c2))
            if p_row[0].size:
                np_sort[rc,:]=[c1,c2,np_categ[p_row,2]]
            else:
                np_sort[rc,:]=[c1,c2,0]

            rc+=1

    return np_sort.astype(int)


## Plotting

fontsize = 14


def plotting_style():
    """
    Sets the default plotting style using Seaborn.
    """
    sns.set_style("whitegrid")


def get_df_col():
    """
    Returns the default line colors for plotting.

    Returns:
        list: A list of default line colors.
    """
    colors = plotly.colors.qualitative.Plotly

    palette = sns.color_palette("gist_ncar", n_colors=100)
    palette = [to_hex(color) for color in palette]

    colors.extend(palette)

    return colors


plotting_style()


def plot_trendline_year(data, var, ax, color='k'):

    """
    Plots a trendline on a given axis based on the provided data and variable.

    Parameters:
    - data (pandas.DataFrame): The data containing the variable to plot.
    - var (str): The name of the variable to plot.
    - ax (matplotlib.axes.Axes): The axis on which to plot the trendline.
    """

    data = data[var].dropna()

    time = data.index.values
    try:
        time_num = data.index.year
    except:
        time_num = time

    coefficients = np.polyfit(time_num, data.values, 1)  # Linear fit
    trendline = np.poly1d(coefficients)  # Create trendline function
    change_rate = coefficients[0]

    _, _, _, p_value, _ = linregress(time_num, data.values)
    if p_value < 0.05:
        label = f'Trend (rate = {np.round(change_rate, 3)}/year) - Significant (p < 0.05)'
        ax.plot(time_num, trendline(time_num), color=color, linestyle='-', label=label)
    else:
        label = f'Trend (rate = {np.round(change_rate, 3)}/year) - Not Significant (p > 0.05)'
        ax.plot(time_num, trendline(time_num), color=color, linestyle=':', label=label)


def add_oni_cat(df1, lims=[-.5, .5]):
    """
    Adds a categorical column 'oni_cat' to the input DataFrame based on ONI values.

    Parameters:
    df1 (DataFrame): Input DataFrame containing the 'ONI' column.

    Returns:
    DataFrame: DataFrame with the additional 'oni_cat' column.
    """
    number_months = 5
    df1['oni_cat'] = 0
    df1['oni_cat'] = np.where(df1.groupby(df1.index.year)['ONI'].transform(lambda x: x[x > lims[1]].count()) >= number_months, 1, df1['oni_cat'])
    df1['oni_cat'] = np.where(df1.groupby(df1.index.year)['ONI'].transform(lambda x: x[x < lims[0]].count()) >= number_months, -1, df1['oni_cat'])

    return df1


def plot_bar_probs(x, y, bar_label=None, labels=None, trendline=False,
                    y_label=' ', figsize=[7, 5], return_trend=False):
    """
    Plots a bar chart showing the distribution of wet days.

    Parameters:
    x (list): The x-axis values for the bar chart.
    y (list): The y-axis values for the bar chart.
    labels (list, optional): The labels for the x-axis ticks. Defaults to None.

    Returns:
    None
    """

    fig, ax = plt.subplots(figsize=figsize)
    if bar_label is not None:
        ax.bar(x=x, height=y, color=get_df_col()[0], edgecolor='white', alpha=.5, label=bar_label)
    else:
        ax.bar(x=x, height=y, color=get_df_col()[0], edgecolor='white', alpha=.5)

    ax.set_ylabel(y_label, fontsize=fontsize)
    if labels:
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=fontsize)

    if trendline:
        time = x
        time_num = time
        mask = np.isfinite(y)

        coefficients = np.polyfit(time_num[mask], y[mask], 1)  # Linear fit
        trendline = np.poly1d(coefficients)  # Create trendline function
        _, _, _, p_value, _ = linregress(time_num[mask], y[mask])

        change_rate = coefficients[0]
        trend = np.round(change_rate, 3)

        if p_value < 0.05:
            label = f'Trend (rate = {np.round(change_rate, 3)}/year) - Significant (p < 0.05)'
            ax.plot(time_num, trendline(time_num), color='k', linestyle='-', label=label)
        else:
            label = f'Trend (rate = {np.round(change_rate, 3)}/year) - Not Significant (p > 0.05)'
            ax.plot(time_num, trendline(time_num), color='k', linestyle=':', label=label)
        ax.legend(fontsize=fontsize)

    ax.grid(color='lightgrey', linestyle=':', alpha=0.6)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_visible(False)

    return (fig, ax, trend) if return_trend else (fig, ax)


def plot_bar_probs_ONI(df2, var, y_label=''):
    """
    Plots a bar chart of the mean annual precipitation with respect to the ONI categories.

    Parameters:
    df2 (pandas.DataFrame): The DataFrame containing the data.
    var (str): The variable to be plotted.

    Returns:
    None
    """

    try:
        x = df2.index.year
    except:
        x = df2.index
    y = df2[var]

    # Map ONI categories to colors
    categories = [-1, 0, 1]
    colors = ['lightblue', 'lightgray', 'lightcoral']
    cmap = mcolors.ListedColormap(colors)
    norm = mcolors.BoundaryNorm([category - 0.5 for category in categories] + [1.5], cmap.N)  # Shift for centered labels

    # Get colors for bars
    colors_bars = [cmap(norm(value)) for value in df2['oni_cat']]

    fig, ax = plt.subplots(figsize=(15, 6))

    # Plot bars
    ax.bar(x=x, height=y, color=colors_bars, edgecolor='white', alpha=0.7)

    ax.set_ylabel(y_label, fontsize=fontsize)
    ax.set_xlabel('Year', fontsize=fontsize)

    # Add colorbar
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])  # No data needed, just a mapping
    cbar = fig.colorbar(sm, ax=ax, orientation='vertical')

    # Set custom tick positions and labels
    tick_positions = categories  # Use category values as tick positions
    cbar.set_ticks(tick_positions)
    cbar.set_ticklabels(['La Niña', 'Neutral', 'El Niño'], fontsize=fontsize)

    # Format plot
    ax.grid(color='lightgrey', linestyle=':', alpha=0.6)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_visible(False)

    # Add trendline
    plot_trendline_year(df2, var, ax, color='k')
    ax.legend(fontsize=fontsize)
    plt.tight_layout()

    return fig


def plot_tc_categories_trend(tcs_sel_params, trendline_plot=True):

    fig, ax = plt.subplots(1, figsize=(15, 4))
    df_tcs = tcs_sel_params.to_dataframe()
    df_tcs['year'] = df_tcs.dmin_date.dt.year

    # --- Define all categories and their colors ---
    categories = [-1, 0, 1, 2, 3, 4, 5]
    colors = ['lightgrey', 'green', 'yellow', 'orange', 'red', 'purple', 'black']

    # --- Count and reindex to preserve order ---
    counts = (df_tcs.groupby('year').category.value_counts().unstack(fill_value=0)
        .reindex(columns=categories, fill_value=0))

    # --- Ensure every year in full range appears ---
    years = range(df_tcs['year'].min(), 2025 + 1)
    counts = counts.reindex(years, fill_value=0)

    # --- Plot with colors aligned to category order ---
    counts.plot(ax=ax, kind='bar', stacked=True, color=colors)

    ax.set_ylabel('Counts', fontsize=14)
    ax.set_xlabel('Year', fontsize=14)
    ax.legend(title='Category', ncols=7, prop={'size': 12})

    ax.grid(':', color='lightgrey', alpha=0.5)
    # trendline
    x = df_tcs.groupby('year').count().index - df_tcs.groupby('year').count().index[0]
    y = df_tcs.groupby('year').month.count().values

    coefficients = np.polyfit(x, y, 1)  # Linear fit
    trendline = np.poly1d(coefficients)  # Create trendline function

    _, _, _, p_value, _ = linregress(x, y)

    change_rate = coefficients[0]

    if trendline_plot:
        if p_value < 0.05:
            label = f'Trend (rate = {np.round(change_rate, 2)}/year) - Significant (p < 0.05)'
            ax.plot(x, trendline(x), color='k', linestyle='-', label=label)
        else:
            label = f'Trend (rate = {np.round(change_rate, 2)}/year) - Not Significant (p > 0.05)'
            ax.plot(x, trendline(x), color='k', linestyle=':', label=label)

    ax.legend(fontsize=12, ncol=7)

    return fig


def get_storm_color(categ):

    dcs = {
        -1: 'lightgrey',
        0: 'green',
        1: 'yellow',
        2: 'orange',
        3: 'red',
        4: 'purple',
        5: 'black',
    }
    return dcs[categ]


def Plot_TCs_HistoricalTracks_Category(
    xds_TCs_r1, cat,
    lon1, lon2, lat1, lat2,
    pnt_lon, pnt_lat, r1,
    nm_lon='lon', nm_lat='lat',
    title='Historical Cs',
    ax=None
):

    ax_orig = ax
    # Define projection
    if ax is None:
        projection = ccrs.PlateCarree(central_longitude=180)

        # Create figure and axes with projection
        fig, ax = plt.subplots(
            1,
            figsize=(10, 8),
            subplot_kw={'projection': projection}
        )

    # Add geographic features
    ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
    ax.add_feature(cfeature.BORDERS, linewidth=0.5, linestyle=':')
    ax.add_feature(cfeature.LAND, color='silver')
    ax.add_feature(cfeature.OCEAN, color='lightcyan')

    # Set extent (bounding box)
    ax.set_extent([lon1, lon2, lat1, lat2], crs=ccrs.PlateCarree())

    # Add gridlines
    gl = ax.gridlines(draw_labels=True, linewidth=0.5, color='gray', alpha=0.5, linestyle='--')
    gl.top_labels = False
    gl.right_labels = False
    gl.xformatter = LongitudeFormatter()
    gl.yformatter = LatitudeFormatter()

    # Plot storm tracks
    for s in range(len(xds_TCs_r1.storm)):
        lon = xds_TCs_r1.isel(storm=s)[nm_lon].values[:]
        lon[lon < 0] += 360  # Convert to 0-360 if needed

        # Plot storm track
        ax.plot(
            lon, xds_TCs_r1.isel(storm=s)[nm_lat].values[:],
            '-', color=get_storm_color(int(cat[s].values)),
            alpha=0.5, transform=ccrs.PlateCarree()
        )

        # Mark storm start points
        ax.plot(
            lon[0], xds_TCs_r1.isel(storm=s)[nm_lat].values[0],
            '.', color=get_storm_color(int(cat[s].values)),
            markersize=10, transform=ccrs.PlateCarree()
        )

    # Plot study site
    ax.plot(
        pnt_lon, pnt_lat, '.', color='brown',
        markersize=15, label='STUDY SITE', transform=ccrs.PlateCarree()
    )

    # Plot circle around the study site
    circle = Circle(
        (pnt_lon, pnt_lat), r1,
        facecolor='grey', edgecolor='grey',
        linewidth=3, alpha=0.5, transform=ccrs.PlateCarree()
    )
    ax.add_patch(circle)

    # Customize plot
    ax.set_title(title, fontsize=15)
    ax.legend(loc='lower left', fontsize=12)
    ax.set_aspect('equal')  # Allow automatic scaling for map aspect ratio

    if ax_orig is None:
        return fig, ax
