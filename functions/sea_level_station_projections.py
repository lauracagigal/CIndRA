"""IPCC AR6 relative sea-level projections at tide gauges, and projected minor flooding.

Projections come from the AR6 product **with** vertical land motion
(``ar6-regional-confidence``, Garner et al., 2021; Zenodo 6382554), the
relative sea level a tide gauge records, as used by the NASA/UHSLC Pacific
Flooding Analysis Tool. Two families of projections are handled:

* SSP scenarios (``ssp126`` … ``ssp585``);
* end-of-century global warming levels (``tlim1.5win0.25`` … ``tlim5.0win0.25``),
  the scenarios offered by the NASA tool.

AR6 provides projections at ~1,030 PSMSL tide gauges and on a 1° grid. UHSLC
stations are matched to the nearest AR6 tide-gauge location (default within
30 km); if none is close enough, the nearest grid cell is used instead and the
match is flagged.

Projected flood days follow a simple, transparent approach: the observed
hourly variability of the last complete storm years (tides, seasonal cycle,
ENSO, surges), referenced to the AR6 baseline (1995–2014, centred on 2005), is
raised by the projected sea-level rise and the days with an hourly value above
the flood threshold are counted. It is a simplification of the Thompson et al.
(2021) method used by the NASA tool (no projection of tidal modulation or of
monthly sea-level variability).
"""

from pathlib import Path

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr

from data_downloaders import ar6_sea_level_file, download_ar6_sea_level_projections
from sea_level import storm_year
from sea_level_projections import GRID_ID_MIN, SCENARIO_COLOR, SCENARIO_LABEL, ocean_mask

PLATE = ccrs.PlateCarree()
SSP_SCENARIOS = ("ssp126", "ssp245", "ssp370", "ssp585")
GWL_SCENARIOS = ("tlim1.5win0.25", "tlim2.0win0.25", "tlim3.0win0.25", "tlim4.0win0.25", "tlim5.0win0.25")
GWL_COLOR = {
    "tlim1.5win0.25": "#2c7bb6", "tlim2.0win0.25": "#80b0c8", "tlim3.0win0.25": "#fdae61",
    "tlim4.0win0.25": "#e5552f", "tlim5.0win0.25": "#a50026",
}
BASELINE_YEAR = 2005  # centre of the AR6 1995–2014 reference period


def scenario_label(scenario):
    if scenario.startswith("tlim"):
        return f"+{scenario[4:7]} °C"
    return SCENARIO_LABEL.get(scenario, scenario.upper())


def scenario_color(scenario):
    return GWL_COLOR.get(scenario) or SCENARIO_COLOR.get(scenario, "0.3")


# ---------------------------------------------------------------------------
# AR6 projections at tide gauges
# ---------------------------------------------------------------------------

def load_ar6_locations(
    raw_dir,
    cache_file,
    scenarios=SSP_SCENARIOS + GWL_SCENARIOS,
    grid_extent=(125, 245, -35, 35),
    quantiles=(0.05, 0.17, 0.5, 0.83, 0.95),
    confidence="medium",
    vlm=True,
    keep_raw=False,
    overwrite=False,
    force_download=False,
):
    """AR6 sea-level change (cm, 1995–2014 ref.) at every tide gauge and at the grid cells of ``grid_extent``.

    Returns a Dataset with ``change`` on (scenario, quantile, year, location) and
    per-location ``lat``, ``lon`` (0–360°), ``is_gauge`` and ``ocean``. Missing
    raw files are downloaded; with ``keep_raw=False`` each ~75 MB raw file is
    deleted once its values are cached (the cache is a few MB).
    """
    cache_file = Path(cache_file)
    cached = None
    if cache_file.is_file() and not overwrite and not force_download:
        cached = xr.load_dataset(cache_file)
        if set(scenarios) <= set(cached.scenario.values) and np.all(np.isin(quantiles, cached["quantile"].values)):
            return cached.sel(scenario=list(scenarios), quantile=list(quantiles))

    done = {} if cached is None else {s: cached.sel(scenario=s) for s in cached.scenario.values}
    todo = [s for s in scenarios if s not in done or force_download or overwrite]
    meta = None
    for scenario in todo:
        paths = download_ar6_sea_level_projections(raw_dir, (scenario,), kinds=("values",), confidence=confidence,
                                                   vlm=vlm, force_download=force_download)
        path = paths[(scenario, "values")]
        with xr.open_dataset(path) as ds:
            if meta is None:
                loc = ds.locations.values
                lat = ds.lat.values.astype(float)
                lon = ds.lon.values.astype(float) % 360
                x0, x1, y0, y1 = grid_extent
                is_gauge = loc < GRID_ID_MIN
                keep = is_gauge | ((lon >= x0) & (lon <= x1) & (lat >= y0) & (lat <= y1))
                idx = np.where(keep)[0]
                grid_lon, grid_lat = lon[idx], lat[idx]
                ocean = np.ones(idx.size, dtype=bool)
                grid = ~is_gauge[idx]
                mask = ocean_mask(np.unique(grid_lon[grid]), np.unique(grid_lat[grid]))
                ocean[grid] = mask.sel(lon=xr.DataArray(grid_lon[grid]), lat=xr.DataArray(grid_lat[grid])).values
                meta = dict(location=loc[idx], lat=grid_lat, lon=grid_lon, is_gauge=is_gauge[idx], ocean=ocean)
            da = ds["sea_level_change"].sel(quantiles=list(quantiles)).isel(locations=idx).load()
        done[scenario] = xr.Dataset(
            {"change": (("quantile", "year", "location"), (0.1 * da.values).astype("float32"))},
            coords={"quantile": list(quantiles), "year": da.years.values, "location": meta["location"],
                    "lat": ("location", meta["lat"]), "lon": ("location", meta["lon"]),
                    "is_gauge": ("location", meta["is_gauge"]), "ocean": ("location", meta["ocean"])},
        )
        if not keep_raw:
            path.unlink()

    out = xr.concat([done[s].drop_vars("scenario", errors="ignore") for s in done], dim=pd.Index(list(done), name="scenario"))
    out["change"].attrs.update(units="cm", long_name="Relative sea-level change relative to 1995–2014")
    out.attrs.update(
        source="IPCC AR6 sea-level projections, Garner et al. (2021), Zenodo 10.5281/zenodo.6382554",
        product=f"{'regional' if vlm else 'regional_novlm'} total, {confidence} confidence",
        vertical_land_motion="included" if vlm else "excluded",
        reference_period="1995-2014",
    )
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    out.to_netcdf(cache_file)
    return out.sel(scenario=list(scenarios), quantile=list(quantiles))


def _distance_km(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(np.deg2rad, (lon1, lat1, lon2, lat2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def match_stations(locations, stations, max_km=30):
    """Nearest AR6 tide gauge (≤ ``max_km``) for each station, else the nearest ocean grid cell.

    ``stations`` has ``uhslc_id``, ``lon``, ``lat``. Returns a copy with
    ``ar6_location``, ``ar6_kind`` ('tide gauge' or 'grid cell'), ``ar6_distance_km``,
    ``ar6_lon`` and ``ar6_lat``.
    """
    lon, lat = locations.lon.values, locations.lat.values
    gauge = locations.is_gauge.values
    grid = (~gauge) & locations.ocean.values
    rows = []
    for _, st in stations.iterrows():
        d = _distance_km(st["lon"] % 360, st["lat"], lon, lat)
        dg = np.where(gauge, d, np.inf)
        if np.isfinite(dg).any() and dg.min() <= max_km:
            i, kind = int(np.argmin(dg)), "tide gauge"
        else:
            dc = np.where(grid, d, np.inf)
            if not np.isfinite(dc).any():
                rows.append(dict(ar6_location=np.nan, ar6_kind=None, ar6_distance_km=np.nan, ar6_lon=np.nan, ar6_lat=np.nan))
                continue
            i, kind = int(np.argmin(dc)), "grid cell"
        rows.append(dict(ar6_location=int(locations.location.values[i]), ar6_kind=kind, ar6_distance_km=round(float(d[i]), 1),
                         ar6_lon=float(lon[i]), ar6_lat=float(lat[i])))
    return pd.concat([stations.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


def annual_projection(change, years=None):
    """Interpolate decadal AR6 change to annual values, anchored at 0 cm in 2005 (centre of 1995–2014)."""
    anchor = xr.zeros_like(change.isel(year=0)).assign_coords(year=BASELINE_YEAR)
    da = xr.concat([anchor, change], dim="year")
    years = np.arange(BASELINE_YEAR, int(change.year.max()) + 1) if years is None else np.asarray(years)
    return da.interp(year=years)


def projection_table(change, years=(2050, 2100), decimals=0):
    """'median (likely range)' strings for each scenario (rows) and year (columns)."""
    out = {}
    for year in years:
        c = change.sel(year=year)
        out[str(year)] = [f"{float(c.sel(scenario=s, quantile=0.5)):.{decimals}f} "
                          f"({float(c.sel(scenario=s, quantile=0.17)):.{decimals}f}–{float(c.sel(scenario=s, quantile=0.83)):.{decimals}f})"
                          for s in change.scenario.values]
    return pd.DataFrame(out, index=[scenario_label(str(s)) for s in change.scenario.values]).rename_axis("Scenario")


# ---------------------------------------------------------------------------
# Observations at the gauge
# ---------------------------------------------------------------------------

def observed_annual_relative(daily_mm, reference=(1995, 2014), min_fraction=0.75):
    """Annual-mean tide-gauge sea level (cm) relative to the 1995–2014 mean (AR6 baseline).

    Years with less than ``min_fraction`` of daily values are dropped. If fewer
    than 10 reference years are available, the baseline is the value of a
    linear fit at 2005. Returns (Series, description of the baseline).
    """
    s = daily_mm.to_series().dropna()
    counts = s.groupby(s.index.year).size()
    annual = s.groupby(s.index.year).mean()[counts >= min_fraction * 365]
    ref = annual.loc[reference[0]:reference[1]]
    if len(ref) >= 10:
        base, how = ref.mean(), f"{reference[0]}–{reference[1]} mean ({len(ref)} complete years)"
    else:
        coef = np.polyfit(annual.index.values, annual.values, 1)
        base, how = np.polyval(coef, BASELINE_YEAR), f"linear fit evaluated at {BASELINE_YEAR}"
    return (annual - base) / 10, how


# ---------------------------------------------------------------------------
# Projected minor flooding
# ---------------------------------------------------------------------------

def baseline_daily_max(hourly_mhhw_mm, n_years=19, min_fraction=0.75):
    """Daily maxima (cm above MHHW) of the last ``n_years`` complete storm years, referenced to 2005 sea level.

    The long-term linear trend of the full hourly record (fitted to monthly
    means) is removed so that every year sits at the 2005 mean sea level, the
    centre of the AR6 reference period. Nineteen years span a full nodal tidal
    cycle. Returns (daily-max Series indexed by date, list of storm years, trend in mm/yr).
    """
    s = hourly_mhhw_mm.to_series()
    monthly = s.resample("MS").mean()[s.resample("MS").count() >= 0.75 * 24 * 28]
    t = monthly.index.year + (monthly.index.dayofyear - 0.5) / 365.25
    slope = np.polyfit(t, monthly.values, 1)[0]  # mm/yr
    th = s.index.year + (s.index.dayofyear - 1 + s.index.hour / 24) / 365.25
    detrended = s - slope * (th - BASELINE_YEAR)

    labels = storm_year(detrended.index)
    valid = detrended.notna().groupby(labels).sum()
    complete = []
    for year in valid.index:
        start, end = pd.Timestamp(f"{year}-05-01"), pd.Timestamp(f"{year + 1}-04-30 23:00")
        if detrended.index.min() <= start and detrended.index.max() >= end:
            n_hours = (end - start) / pd.Timedelta(hours=1) + 1
            if valid[year] / n_hours >= min_fraction:
                complete.append(int(year))
    years = complete[-n_years:]
    daily = detrended.resample("D").max() / 10
    daily = daily[np.isin(storm_year(daily.index), years)]
    return daily, years, float(slope)


def flood_days_response(daily_max_cm, threshold_cm, offsets_cm=np.arange(0, 201, 1)):
    """Flood days per year for each sea-level offset (cm above 2005 sea level).

    Columns: mean and percentiles (10/90 and 5/17/50/83/95) of the flood days across the base storm years,
    i.e. the spread due to interannual variability (ENSO, nodal cycle, storms) at a given sea level.
    """
    years = storm_year(daily_max_cm.index)
    rows = []
    values = daily_max_cm.values
    for offset in offsets_cm:
        above = pd.Series(values + offset > threshold_cm, index=daily_max_cm.index)
        valid = pd.Series(np.isfinite(values), index=daily_max_cm.index)
        per_year = above.groupby(years).sum() / valid.groupby(years).sum() * 365.25
        row = dict(offset_cm=float(offset), mean_days=per_year.mean(),
                   p10_days=per_year.quantile(0.1), p90_days=per_year.quantile(0.9))
        row.update({f"q{q:g}_days": per_year.quantile(q) for q in (0.05, 0.17, 0.5, 0.83, 0.95)})
        rows.append(row)
    return pd.DataFrame(rows).set_index("offset_cm")


def project_flood_days(response, slr_annual_cm):
    """Map annual sea-level rise (cm, any dims incl. ``year``) to expected flood days per year."""
    x = response.index.values
    y = response["mean_days"].values
    days = np.clip(np.interp(slr_annual_cm.values, x, y, left=y[0], right=y[-1]), 0, 365)
    return xr.DataArray(days, dims=slr_annual_cm.dims, coords=slr_annual_cm.coords, name="flood_days")


def first_year_exceeding(days, levels=(50, 100, 182, 300)):
    """First year in which the median projected flood days reach each level, per scenario.

    Levels already reached in the first projected year are reported as 'already in <year>'.
    """
    out = {}
    for scenario in days.scenario.values:
        med = days.sel(scenario=scenario, quantile=0.5)
        row = {}
        for level in levels:
            hit = med.year.values[med.values >= level]
            if not hit.size:
                row[f"≥{level} days/yr"] = f"after {int(med.year.values[-1])}"
            elif hit[0] == med.year.values[0]:
                row[f"≥{level} days/yr"] = f"already in {int(hit[0])}"
            else:
                row[f"≥{level} days/yr"] = str(int(hit[0]))
        out[scenario_label(str(scenario))] = row
    return pd.DataFrame(out).T.rename_axis("Scenario")


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------

def plot_station_projection(change, observed=None, title="", end_year=2150, ylabel="Relative sea-level change (cm)"):
    """Observed annual means and projected median with likely (17–83 %) range for each scenario."""
    fig, ax = plt.subplots(figsize=(12, 6.5))
    if observed is not None and len(observed):
        ax.plot(observed.index, observed.values, color="0.25", lw=1.4, marker=".", label="Tide gauge, annual mean")
    sub = annual_projection(change).sel(year=slice(None, end_year))
    for scenario in sub.scenario.values:
        s = sub.sel(scenario=scenario)
        color = scenario_color(str(scenario))
        ax.fill_between(s.year, s.sel(quantile=0.17), s.sel(quantile=0.83), color=color, alpha=0.13, lw=0)
        ax.plot(s.year, s.sel(quantile=0.5), color=color, lw=2.2, label=scenario_label(str(scenario)))
    ax.axhline(0, color="0.5", lw=0.6)
    ax.axvspan(1995, 2014, color="0.85", alpha=0.5, lw=0, label="Reference 1995–2014")
    ax.set_xlabel("Year")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left", fontsize=11, ncol=2, title="Median (shading: 17–83 % likely range)", title_fontsize=10)
    return fig, ax


def plot_flood_response(response, threshold_cm, station):
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.fill_between(response.index, response["p10_days"], response["p90_days"], color="#1f5f99", alpha=0.2, lw=0,
                    label="10th–90th percentile of base years")
    ax.plot(response.index, response["mean_days"], color="#1f5f99", lw=2.2, label="Mean of base years")
    for level in (50, 100, 182):
        ax.axhline(level, color="0.6", lw=0.6, ls=":")
    ax.set_xlabel("Sea-level rise relative to 2005 (cm)")
    ax.set_ylabel("Flood days per year")
    ax.set_title(f"Flood days above {threshold_cm:g} cm over MHHW vs sea-level rise — {station}")
    ax.set_ylim(0, 366)
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left", fontsize=11)
    return fig, ax


def plot_projected_flood_days(days, observed_table=None, title="", end_year=2100):
    """Observed flood days per storm year (bars) and projected median with likely range per scenario."""
    fig, ax = plt.subplots(figsize=(13, 6.5))
    if observed_table is not None:
        obs = observed_table.dropna(subset=["flood_days_count"])
        ax.bar(obs["year_storm"], obs["flood_days_count"], color="0.6", width=0.85, label="Observed (storm years)")
    sub = days.sel(year=slice(2020, end_year))
    for scenario in sub.scenario.values:
        s = sub.sel(scenario=scenario)
        color = scenario_color(str(scenario))
        ax.fill_between(s.year, s.sel(quantile=0.17), s.sel(quantile=0.83), color=color, alpha=0.13, lw=0)
        ax.plot(s.year, s.sel(quantile=0.5), color=color, lw=2.2, label=scenario_label(str(scenario)))
    ax.set_ylim(0, 366)
    ax.set_xlabel("Year")
    ax.set_ylabel("Flood days per year")
    ax.set_title(title)
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left", fontsize=11, ncol=2, title="Projected median (shading: likely range of sea-level rise)",
              title_fontsize=10)
    return fig, ax


def plot_flood_days_bars(days, scenario, observed_table=None, title="", end_year=2100, ax=None):
    """NASA-tool-style bars: projected median flood days per year for one scenario, with likely-range whiskers."""
    first = 2020
    if ax is None:
        fig, ax = plt.subplots(figsize=(13, 5.5))
    else:
        fig = ax.figure
    if observed_table is not None:
        obs = observed_table.dropna(subset=["flood_days_count"])
        ax.bar(obs["year_storm"], obs["flood_days_count"], color="0.6", width=0.85, label="Observed")
        first = max(first, int(obs["year_storm"].max()) + 1)
    s = days.sel(scenario=scenario, year=slice(first, end_year))
    med = s.sel(quantile=0.5).values
    err = np.vstack([med - s.sel(quantile=0.17).values, s.sel(quantile=0.83).values - med])
    ax.bar(s.year, med, color=scenario_color(scenario), width=0.85, yerr=err, error_kw=dict(ecolor="0.3", lw=0.6, capsize=0),
           label=f"Projected, {scenario_label(scenario)} (median, whiskers: likely range)")
    ax.set_ylim(0, 366)
    ax.set_xlabel("Year")
    ax.set_ylabel("Flood days per year")
    ax.set_title(title)
    ax.grid(axis="y", alpha=0.3)
    ax.legend(loc="upper left", fontsize=11)
    return fig, ax


def plot_station_map_panels(stations, columns, pacific, title, label, cmap="afmhot_r", vmin=None, vmax=None,
                            diverging=False, ncols=2, filename=None):
    """Pacific maps with one panel per column of ``stations`` (circles coloured by value, shared scale)."""
    import math

    nrows = math.ceil(len(columns) / ncols)
    projection = ccrs.PlateCarree(central_longitude=180)
    fig, axes = plt.subplots(nrows, ncols, figsize=(7.1 * ncols, 4.3 * nrows + 0.6), squeeze=False,
                             subplot_kw={"projection": projection})
    values = stations[list(columns.values())].to_numpy(dtype=float)
    if vmin is None or vmax is None:
        lo, hi = np.nanmin(values), np.nanmax(values)
        if diverging:
            hi = max(abs(lo), abs(hi))
            lo = -hi
        vmin = lo if vmin is None else vmin
        vmax = hi if vmax is None else vmax
    for ax, (panel, col) in zip(axes.flat, columns.items()):
        ax.set_extent(pacific.extent, crs=PLATE)
        ax.set_facecolor("#eef3f7")
        ax.add_feature(cfeature.LAND, facecolor="0.72", edgecolor="0.3", linewidth=0.4, zorder=3)
        pacific.eez.boundary.plot(ax=ax, transform=PLATE, color="0.35", linewidth=0.4, alpha=0.6, zorder=4)
        gl = ax.gridlines(draw_labels=True, linewidth=0.35, color="0.6", alpha=0.6)
        gl.top_labels = gl.right_labels = False
        sc = ax.scatter(stations["lon"], stations["lat"], c=stations[col], cmap=cmap, vmin=vmin, vmax=vmax, s=85,
                        edgecolor="k", linewidth=0.8, transform=PLATE, zorder=7)
        ax.set_title(panel, fontsize=12)
    for ax in axes.flat[len(columns):]:
        ax.remove()
    fig.subplots_adjust(left=0.05, right=0.91, bottom=0.09, top=0.91, wspace=0.12, hspace=0.2)
    fig.suptitle(title, y=0.975, fontsize=14)
    cbar = fig.colorbar(sc, ax=list(axes.flat[: len(columns)]), fraction=0.025, pad=0.035, aspect=35, extend="both")
    cbar.set_label(label)
    if filename:
        fig.savefig(filename, dpi=150, bbox_inches="tight")
    return fig


def plot_station_ranges(table, scenarios, year, title, xlabel="Relative sea-level change (cm)"):
    """Median and likely range per station (rows ordered as in ``table``) for each scenario."""
    n = len(table)
    fig, ax = plt.subplots(figsize=(10, 0.3 * n + 2))
    y = np.arange(n)
    offsets = np.linspace(-0.27, 0.27, len(scenarios))
    for off, scenario in zip(offsets, scenarios):
        med = table[f"{scenario}_{year}_q0.5"].values
        lo, hi = table[f"{scenario}_{year}_q0.17"].values, table[f"{scenario}_{year}_q0.83"].values
        ax.errorbar(med, y + off, xerr=[med - lo, hi - med], fmt="o", ms=4, lw=1, capsize=0,
                    color=scenario_color(scenario), label=scenario_label(scenario))
    ax.set_yticks(y)
    ax.set_yticklabels(table["label"], fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel(xlabel)
    ax.set_title(title)
    ax.grid(axis="x", alpha=0.3)
    ax.legend(loc="lower right", fontsize=10, title="Median, likely range", title_fontsize=10)
    return fig, ax


def mhhw_from_record(hourly_datum_mm, period=("1995-01-01", "2014-12-31"), min_days=0.75 * 365 * 10):
    """MHHW (mm, station datum) as the mean daily maximum hourly sea level over ``period`` (default the AR6 baseline)."""
    daily_max = hourly_datum_mm.sel(time=slice(*period)).to_series().resample("D").max().dropna()
    if len(daily_max) < min_days:
        raise ValueError(f"Only {len(daily_max)} days with data in {period}; too few to compute MHHW.")
    return float(daily_max.mean())


def slr_timing(slr_annual_cm, scenario, level_cm, end_year=2100):
    """Likely timing of a sea-level rise level: first year the 83rd and the 17th percentiles reach it."""
    s = slr_annual_cm.sel(scenario=scenario)
    years = s.year.values

    def first(q):
        hit = years[s.sel(quantile=q).values >= level_cm]
        return int(hit[0]) if hit.size else None

    early, late = first(0.83), first(0.17)
    fmt = lambda y: f"{y}" if (y is not None and y <= end_year) else f"{end_year}+"
    if early is None or early > end_year:
        return f"after {end_year}", early, late
    return f"{fmt(early)}–{fmt(late)}", early, late


def plot_flood_days_by_slr(response, slr_annual_cm, scenario, threshold_cm, station, levels_cm=range(10, 80, 10),
                           end_year=2100, units="m"):
    """NASA-tool-style chart: flood-day distribution at fixed amounts of local sea-level rise, with their likely timing.

    Boxes: very likely (5–95 %) and likely (17–83 %) ranges and median of the flood days across the base years
    (interannual variability). Below each box, the period in which the scenario likely reaches that rise.
    Returns (fig, ax, table, text lines).
    """
    rows, lines = [], []
    for level in levels_cm:
        r = response.loc[float(level)]
        timing, early, late = slr_timing(slr_annual_cm, scenario, level, end_year)
        rows.append(dict(slr_cm=level, timing=timing, **{k: r[k] for k in response.columns if k.startswith("q")}))
        if early is not None and early <= end_year:
            when = f"between {timing}" if late is not None and late <= end_year else f"from {early} to after {end_year}"
            lines.append(f"At {level / 100:.1f} m of sea-level rise, expected {when}, water levels will likely exceed "
                         f"{threshold_cm / 100:.1f} m above MHHW on {r['q0.17_days']:.0f}–{r['q0.83_days']:.0f} days per year.")
    table = pd.DataFrame(rows)

    fig, ax = plt.subplots(figsize=(12, 6.5))
    x = np.arange(len(table))
    w = 0.55
    ax.bar(x, table["q0.95_days"] - table["q0.05_days"], bottom=table["q0.05_days"], width=w, color="#cde8f6",
           label="Very likely range (5–95 %)")
    ax.bar(x, table["q0.83_days"] - table["q0.17_days"], bottom=table["q0.17_days"], width=w, color="#6ec3ea",
           label="Likely range (17–83 %)")
    ax.hlines(table["q0.5_days"], x - w / 2, x + w / 2, color="#08589e", lw=3, label="50th percentile")
    labels = [f"{lv / 100:.1f} m\n{t}" if units == "m" else f"{lv} cm\n{t}" for lv, t in zip(table["slr_cm"], table["timing"])]
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_xlabel(f"Local sea-level rise (relative to 1995–2014) and likely timing, {scenario_label(scenario)}")
    ax.set_ylabel("Flooding days per year")
    ax.set_ylim(0, 366)
    ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)
    ax.set_title(f"Projected flooding days at {station} — {scenario_label(scenario)}, threshold {threshold_cm / 100:.2f} m above MHHW")
    ax.legend(loc="upper left", fontsize=11)
    return fig, ax, table, lines


def warming_level_years(scenario_info):
    """{scenario: {level: year}} from ``projections.load_warming_levels``, keeping only levels reached."""
    out = {}
    for scenario, levels in scenario_info.items():
        reached = {}
        for level, info in levels.items():
            year = info.get("year")
            if isinstance(year, np.datetime64) and not np.isnat(year):
                reached[float(level)] = int(str(year)[:4])
        out[scenario] = reached
    return out


def flood_days_at_warming_levels(response, slr_annual_cm, gwl_years):
    """Sea-level rise and flood days in the year each scenario reaches each global warming level.

    ``days_q*`` columns: spread of flood days across the base years (interannual variability) at the
    median sea-level rise; ``days_slr_q*``: flood days for the 17th/50th/83rd percentiles of sea-level rise.
    """
    rows = []
    for scenario, levels in gwl_years.items():
        for level, year in levels.items():
            slr = slr_annual_cm.sel(scenario=scenario, year=year)
            med = float(slr.sel(quantile=0.5))
            r = response.iloc[np.argmin(np.abs(response.index.values - med))]
            row = dict(scenario=scenario, level=level, year=year,
                       **{f"slr_q{q:g}_cm": float(slr.sel(quantile=q)) for q in (0.17, 0.5, 0.83)},
                       **{f"days_{k}": r[f"{k}_days"] for k in ("q0.05", "q0.17", "q0.5", "q0.83", "q0.95")})
            for q in (0.17, 0.5, 0.83):
                row[f"days_slr_q{q:g}"] = float(np.interp(float(slr.sel(quantile=q)), response.index.values,
                                                          response["mean_days"].values))
            rows.append(row)
    return pd.DataFrame(rows)


def plot_flood_days_at_warming_levels(table, threshold_cm, station, levels=(1.5, 2.0, 2.5, 3.0)):
    """Grouped boxes: flood days per year at each global warming level, one box per scenario reaching it.

    Box = very likely (5–95 %) and likely (17–83 %) range across the base years at the median projected
    sea-level rise of the year the scenario reaches the level; line = median. The year and the median
    sea-level rise are written above each box.
    """
    from matplotlib.colors import to_rgba

    scenarios = list(dict.fromkeys(table["scenario"]))
    fig, ax = plt.subplots(figsize=(13, 6.8))
    width = 0.8 / max(len(scenarios), 1)
    for i, level in enumerate(levels):
        present = [s for s in scenarios if ((table["scenario"] == s) & (table["level"] == level)).any()]
        for j, scenario in enumerate(present):
            r = table[(table["scenario"] == scenario) & (table["level"] == level)].iloc[0]
            x = i + width * (j - (len(present) - 1) / 2)
            color = scenario_color(scenario)
            ax.bar(x, r["days_q0.95"] - r["days_q0.05"], bottom=r["days_q0.05"], width=width * 0.85,
                   color=to_rgba(color, 0.25), edgecolor="none")
            ax.bar(x, r["days_q0.83"] - r["days_q0.17"], bottom=r["days_q0.17"], width=width * 0.85,
                   color=to_rgba(color, 0.6), edgecolor="none")
            ax.hlines(r["days_q0.5"], x - width * 0.42, x + width * 0.42, color=color, lw=3)
            ax.text(x, r["days_q0.95"] + 6, f"{int(r['year'])}\n{r['slr_q0.5_cm']:.0f} cm",
                    ha="center", va="bottom", fontsize=9)
    handles = [plt.Rectangle((0, 0), 1, 1, color=scenario_color(s)) for s in scenarios]
    labels = [scenario_label(s) for s in scenarios]
    handles += [plt.Rectangle((0, 0), 1, 1, color=to_rgba("0.3", 0.6)), plt.Rectangle((0, 0), 1, 1, color=to_rgba("0.3", 0.25))]
    labels += ["Likely range (17–83 %)", "Very likely range (5–95 %)"]
    ax.legend(handles, labels, loc="upper left", fontsize=10, ncol=2)
    ax.set_xticks(range(len(levels)))
    ax.set_xticklabels([f"+{lv:g} °C" for lv in levels])
    ax.set_xlabel("Global warming level (year reached and median relative sea-level rise above each box)")
    ax.set_ylabel("Flooding days per year")
    ax.set_ylim(0, 400)
    ax.set_yticks(range(0, 366, 50))
    ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)
    ax.set_title(f"Projected flooding days (> {threshold_cm:g} cm above MHHW) at {station} at global warming levels")
    return fig, ax


def pacific_eez_stations(eez, extent=(125, 245, -35, 35), start="1993-01-01", end="2025-12-31", max_distance_deg=0.5):
    """UHSLC Fast Delivery stations in ``extent`` inside, or within ``max_distance_deg`` of, a Pacific EEZ.

    Same selection as the historical regional sea-level notebook; returns uhslc_id, name, country, eez, lon, lat.
    """
    import warnings

    import geopandas as gpd

    from sea_level import pacific_uhslc_stations

    stations = pacific_uhslc_stations(extent, start, end)
    points = gpd.GeoDataFrame(stations, geometry=gpd.points_from_xy(((stations["lon"] + 180) % 360) - 180, stations["lat"]),
                              crs=4326)
    with warnings.catch_warnings():  # distances in degrees are adequate for a sub-degree tolerance
        warnings.simplefilter("ignore")
        joined = gpd.sjoin_nearest(points, eez[["Country", "geometry"]].rename(columns={"Country": "eez"}),
                                   how="inner", max_distance=max_distance_deg)
    out = joined.drop(columns=["geometry", "index_right"]).drop_duplicates("uhslc_id").reset_index(drop=True)
    return out[["uhslc_id", "name", "country", "eez", "lon", "lat"]]


def plot_flood_days_bars_grid(days, scenarios, observed_table=None, title="", end_year=2100, ncols=2):
    """:func:`plot_flood_days_bars` for every scenario in a grid with shared axes."""
    import math

    nrows = math.ceil(len(scenarios) / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(8 * ncols, 4.2 * nrows + 0.6), sharex=True, sharey=True, squeeze=False)
    for ax, scenario in zip(axes.flat, scenarios):
        plot_flood_days_bars(days, scenario, observed_table, title=scenario_label(scenario), end_year=end_year, ax=ax)
        ax.set_title(scenario_label(scenario), fontsize=14, fontweight="bold")
        ax.legend(loc="upper left", fontsize=9)
    for ax in axes.flat[len(scenarios):]:
        ax.remove()
    for ax in axes[:, 1:].flat:
        ax.set_ylabel("")
    for ax in axes[:-1, :].flat:
        ax.set_xlabel("")
    fig.suptitle(title, fontsize=15, fontweight="bold")
    fig.tight_layout()
    return fig, axes
