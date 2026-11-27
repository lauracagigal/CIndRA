"""Regional tropical-cyclone projections from the CMIP6-HighResMIP storm tracks.

Tropical-cyclone tracks detected in the HighResMIP atmosphere-only runs by two trackers, TRACK
(Hodges et al., 2017) and TempestExtremes (Zarzycki & Ullrich, 2017), are distributed by CEDA
(Roberts, 2019; CC BY 4.0):

    https://dap.ceda.ac.uk/badc/highresmip-derived/data/storm_tracks/<tracker>/<institution>/<model>/
        <experiment>/<member>/tropical/<version>/TC-<NH|SH>_<tracker>_<model>_<experiment>_<member>_<grid>_<dates>.nc

The set-up follows Li & Zhou (2024, npj Clim. Atmos. Sci. 7, 161): the four high-resolution models
CMCC-CM2-VHR4, CNRM-CM6-1-HR, EC-Earth3P-HR and HadGEM3-GC31-HM, ``highresSST-present`` for 1980–2010
and ``highresSST-future`` (SSP5-8.5) for 2020–2050. Genesis is the first track point with a 10-m wind of
at least 34 kt; storms whose genesis lies over land, or poleward of a monthly latitude limit (south of
the westerlies and north of the 26 °C isotherm), are removed. Li & Zhou give the limits for the
northern hemisphere; the southern-hemisphere limits used here are the same limits shifted by six
months (a CIndRA adaptation).

Each storm is assigned to a Pacific subregion by its genesis point (``tcs.classify_genesis_region``,
the boxes of the historical regional notebook). Only a small table of genesis points is cached in
``data/projections/regional/tcs_highresmip/``; the raw track files are downloaded to a temporary
folder and deleted unless ``keep_raw=True``.
"""

from __future__ import annotations

import re
import shutil
import urllib.request
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr

import projections as prj
from tcs import classify_genesis_region

CEDA_URL = "https://dap.ceda.ac.uk/badc/highresmip-derived/data/storm_tracks"
CACHE_DIR = prj.PROJECTIONS_DATA_DIR / "regional" / "tcs_highresmip"

TRACKERS = ("TRACK", "TempExt")
TRACKER_LABEL = {"TRACK": "TRACK", "TempExt": "TempestExtremes"}
MODELS = {  # model: institution folder on CEDA
    "CMCC-CM2-VHR4": "CMCC",
    "CNRM-CM6-1-HR": "CNRM-CERFACS",
    "EC-Earth3P-HR": "EC-Earth-Consortium",
    "HadGEM3-GC31-HM": "MOHC",
}
PERIODS = {  # period: (experiment, first year, last year)
    "present": ("highresSST-present", 1980, 2010),
    "future": ("highresSST-future", 2020, 2050),
}
REGIONS = ("Western North Pacific", "Central North Pacific", "Western South Pacific", "Central South Pacific")
REGION_COLORS = {
    "Western North Pacific": "#5E9A8D",
    "Central North Pacific": "#6B8CD3",
    "Western South Pacific": "#A284C9",
    "Central South Pacific": "#CC79A7",
}
MODEL_MARKERS = {"CMCC-CM2-VHR4": "o", "CNRM-CM6-1-HR": "s", "EC-Earth3P-HR": "^", "HadGEM3-GC31-HM": "D"}

KT34 = 34 * 0.514444  # 34 kt in m/s

# Genesis latitude limit by month (Li & Zhou, 2024), northern hemisphere ...
NH_MAX_LAT = {12: 20, 1: 20, 2: 20, 3: 20, 11: 25, 4: 25, 5: 25, 6: 30, 10: 30, 7: 35, 8: 35, 9: 35}
# ... and the same limits shifted by six months for the southern hemisphere (CIndRA adaptation).
SH_MAX_LAT = {m: NH_MAX_LAT[(m + 5) % 12 + 1] for m in range(1, 13)}


# ---------------------------------------------------------------------------
# Download and genesis extraction
# ---------------------------------------------------------------------------

def _list_dir(url):
    with urllib.request.urlopen(url, timeout=60) as response:
        html = response.read().decode("utf-8", "replace")
    return [h for h in re.findall(r'href="([^"?]+)"', html) if not h.startswith("..") and not h.startswith("/")]


def list_members(tracker, model, experiment):
    """Ensemble members available on CEDA for a tracker, model and experiment (empty if none)."""
    try:
        return [m.rstrip("/") for m in _list_dir(f"{CEDA_URL}/{tracker}/{MODELS[model]}/{model}/{experiment}/")]
    except Exception:
        return []


def _track_files(tracker, model, experiment, member):
    """URLs of the NH and SH track files of the latest version."""
    base = f"{CEDA_URL}/{tracker}/{MODELS[model]}/{model}/{experiment}/{member}/tropical/"
    version = sorted(_list_dir(base))[-1]
    return {name.split("_")[0][3:]: base + version + name for name in _list_dir(base + version) if name.endswith(".nc")}


def _land_checker():
    """Function telling whether (lon, lat) points lie on land (Natural Earth 10 m land)."""
    import shapely
    import cartopy.io.shapereader as shpreader
    from shapely.ops import unary_union

    land = unary_union(list(shpreader.Reader(shpreader.natural_earth("10m", "physical", "land")).geometries()))
    shapely.prepare(land)
    return lambda lon, lat: shapely.contains_xy(land, ((np.asarray(lon) + 180) % 360) - 180, np.asarray(lat))


def genesis_points(path, hemisphere):
    """One row per storm reaching 34 kt: genesis time and position, lifetime maximum intensity (LMI)."""
    ds = xr.open_dataset(path, use_cftime=True)
    first, npts = ds["FIRST_PT"].values, ds["NUM_PTS"].values
    lon, lat = ds["lon"].values % 360, ds["lat"].values
    wind, psl, time = ds["sfcWind"].values, ds["psl"].values, ds["time"].values
    rows = []
    for k in range(len(first)):
        sl = slice(first[k], first[k] + npts[k])
        w = wind[sl]
        strong = np.where(np.isfinite(w) & (w >= KT34))[0]
        if strong.size == 0:
            continue
        g, i_lmi = strong[0], int(np.nanargmax(w))
        t = time[sl][g]
        rows.append({"hemisphere": hemisphere, "year": t.year, "month": t.month,
                     "lon": float(lon[sl][g]), "lat": float(lat[sl][g]),
                     "lmi_lat": float(lat[sl][i_lmi]), "max_wind": float(np.nanmax(w)),
                     "min_psl": float(np.nanmin(psl[sl]))})
    ds.close()
    return pd.DataFrame(rows)


def constrain(table, on_land):
    """Flag storms kept by the constrained detection (not over land, within the monthly latitude limit)."""
    limit = np.where(table["hemisphere"] == "NH", table["month"].map(NH_MAX_LAT), table["month"].map(SH_MAX_LAT))
    table = table.assign(over_land=on_land(table["lon"].values, table["lat"].values), lat_limit=limit)
    table["kept"] = ~table["over_land"] & (table["lat"].abs() <= table["lat_limit"])
    table["region"] = [classify_genesis_region(x, y) for x, y in zip(table["lon"], table["lat"])]
    return table


def extract_member(tracker, model, period, member, raw_dir, on_land, keep_raw=False):
    """Genesis table of one member and period (both hemispheres), cached as CSV."""
    cache = CACHE_DIR / f"{tracker}_{model}_{period}_{member}.csv"
    if cache.exists():
        return pd.read_csv(cache)
    experiment, y0, y1 = PERIODS[period]
    tables = []
    for hemisphere, url in sorted(_track_files(tracker, model, experiment, member).items()):
        path = Path(raw_dir) / url.rsplit("/", 1)[1]
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(url, path)
        table = genesis_points(path, hemisphere)
        tables.append(table.loc[table["year"].between(y0, y1)])
        if not keep_raw:
            path.unlink()
    out = constrain(pd.concat(tables, ignore_index=True), on_land)
    out = out.assign(tracker=tracker, model=model, period=period, member=member)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(cache, index=False)
    return out


GENESIS_KEY = ["tracker", "model", "period", "member", "hemisphere", "year", "month", "lon", "lat", "max_wind", "min_psl"]
MIN_YEAR_COVERAGE = 0.8


def load_genesis(raw_dir=None, keep_raw=False, verbose=True, return_qc=False):
    """Genesis tables of every tracker, model, period and member (downloads what is not cached).

    Quality control of the archive: storms stored twice in a file are kept once, and members whose
    tracks cover less than ``MIN_YEAR_COVERAGE`` of the period's years (e.g. a file with a broken time
    axis) are excluded. With ``return_qc=True`` also returns one row per member with the number of
    duplicates removed, the years covered and whether the member is used.
    """
    import tempfile

    raw_dir = Path(raw_dir or Path(tempfile.gettempdir()) / "cindra_tcs_highresmip")
    on_land, tables = None, []
    for tracker in TRACKERS:
        for model in MODELS:
            for period, (experiment, _, _) in PERIODS.items():
                for member in list_members(tracker, model, experiment):
                    cache = CACHE_DIR / f"{tracker}_{model}_{period}_{member}.csv"
                    if not cache.exists() and on_land is None:
                        on_land = _land_checker()
                    if verbose:
                        print(f"{tracker:7s} {model:16s} {period:7s} {member}{'' if cache.exists() else '  (downloading)'}")
                    ident = {"tracker": tracker, "model": model, "period": period, "member": member}
                    tables.append((ident, extract_member(tracker, model, period, member, raw_dir, on_land, keep_raw)))
    if not keep_raw and raw_dir.exists() and not any(raw_dir.iterdir()):
        shutil.rmtree(raw_dir)
    genesis, qc = _quality_control(tables)
    if verbose:
        for _, row in qc.loc[~qc["used"]].iterrows():
            print(f"Excluded: {row['tracker']} {row['model']} {row['period']} {row['member']} "
                  f"({row['years_covered']}/{row['years_in_period']} years)")
    return (genesis, qc) if return_qc else genesis


def _quality_control(tables):
    """Remove duplicated storms and members with too few years: (genesis table, one QC row per member)."""
    rows, kept = [], []
    for ident, table in tables:
        clean = table.drop_duplicates(GENESIS_KEY) if len(table) else table
        years = clean["year"].nunique()
        expected = _n_years(ident["period"])
        used = years >= MIN_YEAR_COVERAGE * expected
        rows.append({**ident, "storms": len(clean), "duplicates_removed": len(table) - len(clean),
                     "years_covered": years, "years_in_period": expected, "used": used})
        if used:
            kept.append(clean)
    return pd.concat(kept, ignore_index=True), pd.DataFrame(rows)


def observed_genesis(ibtracs, start=1980, end=2010):
    """IBTrACS storms reaching 34 kt (WMO wind), with the same genesis definition and subregions."""
    lon = np.mod(ibtracs["lon"].values.astype(float), 360)
    lat = ibtracs["lat"].values.astype(float)
    wind = ibtracs["wmo_wind"].values.astype(float)
    time = pd.to_datetime(ibtracs["time"].values.ravel()).values.reshape(lat.shape)
    rows = []
    for k in range(lat.shape[0]):
        strong = np.where(np.isfinite(wind[k]) & (wind[k] >= 34))[0]
        if strong.size == 0:
            continue
        g = strong[0]
        t = pd.Timestamp(time[k, g])
        if not start <= t.year <= end:
            continue
        rows.append({"year": t.year, "month": t.month, "lon": lon[k, g], "lat": lat[k, g],
                     "lmi_lat": lat[k, int(np.nanargmax(wind[k]))]})
    table = pd.DataFrame(rows)
    table["region"] = [classify_genesis_region(x, y) for x, y in zip(table["lon"], table["lat"])]
    return table


# ---------------------------------------------------------------------------
# Indicators
# ---------------------------------------------------------------------------

def _n_years(period):
    _, y0, y1 = PERIODS[period]
    return y1 - y0 + 1


def annual_counts(genesis, months=None):
    """Mean number of TCs per year in each subregion: one row per tracker, model, period and member."""
    kept = genesis.loc[genesis["kept"] & genesis["region"].isin(REGIONS)]
    if months is not None:
        kept = kept.loc[kept["month"].isin(months)]
    members = genesis[["tracker", "model", "period", "member"]].drop_duplicates()
    counts = kept.groupby(["tracker", "model", "period", "member", "region"]).size().unstack("region")
    counts = counts.reindex(pd.MultiIndex.from_frame(members)).reindex(columns=list(REGIONS)).fillna(0)
    return counts.div(member_years(genesis).reindex(counts.index), axis=0)


def member_years(genesis):
    """Number of years covered by each member's tracks (some files end a year early)."""
    return genesis.groupby(["tracker", "model", "period", "member"])["year"].nunique()


def model_counts(genesis, months=None):
    """Member-mean TCs per year by tracker, model, period (rows) and subregion (columns)."""
    return annual_counts(genesis, months).groupby(level=["tracker", "model", "period"]).mean()


def count_change(genesis, months=None):
    """Present and future TCs per year and % change, per tracker and model, plus each tracker's ensemble mean."""
    counts = model_counts(genesis, months)
    rows = []
    for (tracker, model), sub in counts.groupby(level=["tracker", "model"]):
        present, future = sub.xs("present", level="period").iloc[0], sub.xs("future", level="period").iloc[0]
        for region in REGIONS:
            rows.append({"Tracker": TRACKER_LABEL[tracker], "Model": model, "Region": region,
                         "Present (TCs/yr)": present[region], "Future (TCs/yr)": future[region],
                         "Change (%)": (future[region] - present[region]) / present[region] * 100 if present[region] > 0 else np.nan})
    table = pd.DataFrame(rows)
    mme = (table.groupby(["Tracker", "Region"], sort=False)[["Present (TCs/yr)", "Future (TCs/yr)"]].mean().reset_index()
           .assign(Model="Multi-model mean"))
    mme["Change (%)"] = (mme["Future (TCs/yr)"] - mme["Present (TCs/yr)"]) / mme["Present (TCs/yr)"] * 100
    return pd.concat([table, mme[table.columns]], ignore_index=True)


def summary_table(change, observed=None, decimals=1):
    """Region × tracker summary: multi-model mean present and future TCs/yr, % change, model range, models decreasing."""
    rows = []
    for (tracker, region), sub in change.groupby(["Tracker", "Region"], sort=False):
        models, mme = sub.loc[sub["Model"] != "Multi-model mean"], sub.loc[sub["Model"] == "Multi-model mean"].iloc[0]
        row = {"Region": region, "Tracker": tracker}
        if observed is not None:
            row["Observed 1980–2010 (TCs/yr)"] = observed.get(region, np.nan)
        row.update({"Present 1980–2010 (TCs/yr)": mme["Present (TCs/yr)"], "Future 2020–2050 (TCs/yr)": mme["Future (TCs/yr)"],
                    "Change (%)": mme["Change (%)"],
                    "Model range (%)": f"{models['Change (%)'].min():+.0f} to {models['Change (%)'].max():+.0f}",
                    "Models with decrease": f"{int((models['Change (%)'] < 0).sum())}/{len(models)}"})
        rows.append(row)
    return pd.DataFrame(rows).round(decimals)


def observed_counts(obs, start=1980, end=2010):
    """Observed TCs per year by subregion (genesis classification)."""
    return obs.loc[obs["region"].isin(REGIONS)].groupby("region").size().reindex(list(REGIONS)).fillna(0) / (end - start + 1)


def latitude_change(genesis, months=None, column="lat"):
    """Future minus present mean poleward genesis latitude (|lat|, degrees; positive = poleward), per tracker and model."""
    kept = genesis.loc[genesis["kept"] & genesis["region"].isin(REGIONS)]
    if months is not None:
        kept = kept.loc[kept["month"].isin(months)]
    mean = kept.assign(abs_lat=kept[column].abs()).groupby(["tracker", "model", "period", "region"])["abs_lat"].mean().unstack("period")
    change = (mean["future"] - mean["present"]).unstack("region").reindex(columns=list(REGIONS))
    change.index = change.index.set_levels([TRACKER_LABEL[t] for t in change.index.levels[0]], level=0)
    out = change.reset_index().rename(columns={"tracker": "Tracker", "model": "Model"})
    mme = out.groupby("Tracker", sort=False)[list(REGIONS)].mean().reset_index().assign(Model="Multi-model mean")
    return pd.concat([out, mme[out.columns]], ignore_index=True)


def monthly_cycle(genesis):
    """Multi-model mean TCs per month by tracker, period and region (models weighted equally)."""
    kept = genesis.loc[genesis["kept"] & genesis["region"].isin(REGIONS)]
    counts = kept.groupby(["tracker", "model", "period", "member", "region", "month"]).size()
    per_year = counts / member_years(genesis).reindex(counts.index.droplevel(["region", "month"])).values
    per_member = per_year.unstack("month").reindex(columns=range(1, 13)).fillna(0)
    per_model = per_member.groupby(level=["tracker", "model", "period", "region"]).mean()
    return per_model.groupby(level=["tracker", "period", "region"]).mean()


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------

def plot_counts(change, observed=None, figsize=(14, 9)):
    """TCs per year in each subregion: observed, and present and future multi-model mean for each tracker,
    with each model as a marker."""
    fig, axes = plt.subplots(2, 2, figsize=figsize)
    trackers = list(dict.fromkeys(change["Tracker"]))
    width = 0.35
    for ax, region in zip(axes.flat, REGIONS):
        sub = change.loc[change["Region"] == region]
        color = REGION_COLORS[region]
        for i, tracker in enumerate(trackers):
            t = sub.loc[sub["Tracker"] == tracker]
            mme = t.loc[t["Model"] == "Multi-model mean"].iloc[0]
            for j, (col, alpha) in enumerate((("Present (TCs/yr)", 0.45), ("Future (TCs/yr)", 0.95))):
                x = i + (j - 0.5) * width
                ax.bar(x, mme[col], width=width * 0.92, color=color, alpha=alpha, edgecolor="0.3",
                       label=("Present 1980–2010" if j == 0 else "Future 2020–2050 (SSP5-8.5)") if i == 0 else None)
                for _, m in t.loc[t["Model"] != "Multi-model mean"].iterrows():
                    ax.scatter(x, m[col], marker=MODEL_MARKERS[m["Model"]], color="0.15", s=22, zorder=3)
            ax.text(i, max(t[["Present (TCs/yr)", "Future (TCs/yr)"]].max()) * 1.04, f"{mme['Change (%)']:+.0f}%",
                    ha="center", va="bottom", fontsize=12, fontweight="bold")
        if observed is not None:
            ax.axhline(observed[region], color="black", linestyle="--", linewidth=1.2, label="Observed 1980–2010 (IBTrACS)")
        ax.set_xticks(range(len(trackers)))
        ax.set_xticklabels(trackers)
        ax.set_title(region, fontsize=13, fontweight="bold")
        ax.set_ylabel("TCs per year")
        ax.set_ylim(0, ax.get_ylim()[1] * 1.12)
        ax.grid(axis="y", alpha=0.3)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    handles += [plt.Line2D([], [], marker=MODEL_MARKERS[m], color="0.15", linestyle="") for m in MODELS]
    labels += list(MODELS)
    fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False, fontsize=11)
    fig.suptitle("Tropical cyclones forming in each Pacific subregion: CMIP6-HighResMIP (bars: multi-model mean, markers: models)",
                 fontsize=14, fontweight="bold")
    fig.tight_layout(rect=(0, 0.08, 1, 0.97))
    return fig


def plot_change(change, value="Change (%)", ylabel="Change in TCs per year (%)", title=None, figsize=(12, 5)):
    """Per-model change (markers) and multi-model mean (bars) in each subregion, one bar per tracker."""
    fig, ax = plt.subplots(figsize=figsize)
    trackers = list(dict.fromkeys(change["Tracker"]))
    width = 0.8 / len(trackers)
    for r, region in enumerate(REGIONS):
        for i, tracker in enumerate(trackers):
            t = change.loc[(change["Region"] == region) & (change["Tracker"] == tracker)]
            x = r + (i - (len(trackers) - 1) / 2) * width
            ax.bar(x, t.loc[t["Model"] == "Multi-model mean", value].iloc[0], width=width * 0.9,
                   color=REGION_COLORS[region], alpha=0.55 if i == 0 else 0.95, edgecolor="0.3", hatch=None if i == 0 else "//")
            for _, m in t.loc[t["Model"] != "Multi-model mean"].iterrows():
                ax.scatter(x, m[value], marker=MODEL_MARKERS[m["Model"]], color="0.15", s=26, zorder=3)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(range(len(REGIONS)))
    ax.set_xticklabels(REGIONS)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.3)
    from matplotlib.patches import Patch

    handles = [Patch(facecolor="0.7", alpha=0.55 if i == 0 else 0.95, edgecolor="0.3", hatch=None if i == 0 else "//",
                     label=f"{tracker} (multi-model mean)") for i, tracker in enumerate(trackers)]
    handles += [plt.Line2D([], [], marker=MODEL_MARKERS[m], color="0.15", linestyle="", label=m) for m in MODELS]
    ax.legend(handles=handles, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, frameon=False)
    ax.set_title(title or "Projected change 2020–2050 (SSP5-8.5) vs 1980–2010, CMIP6-HighResMIP", fontsize=13, fontweight="bold")
    fig.tight_layout()
    return fig


def latitude_change_long(lat_change):
    """Reshape ``latitude_change`` to the long layout of ``count_change`` (Tracker, Model, Region, value)."""
    return lat_change.melt(id_vars=["Tracker", "Model"], var_name="Region", value_name="Poleward shift (°)")


def plot_monthly_cycle(cycle, tracker="TRACK", figsize=(14, 8)):
    """Multi-model mean monthly TC genesis, present vs future, in each subregion (one tracker)."""
    fig, axes = plt.subplots(2, 2, figsize=figsize, sharex=True)
    months = np.arange(1, 13)
    for ax, region in zip(axes.flat, REGIONS):
        for period, alpha, label in (("present", 0.45, "1980–2010"), ("future", 0.95, "2020–2050 (SSP5-8.5)")):
            values = cycle.loc[(tracker, period, region)].values
            ax.bar(months + (-0.2 if period == "present" else 0.2), values, width=0.4, color=REGION_COLORS[region],
                   alpha=alpha, edgecolor="0.3", label=label)
        ax.set_title(region, fontsize=13, fontweight="bold")
        ax.set_ylabel("TCs per month")
        ax.grid(axis="y", alpha=0.3)
        ax.legend(fontsize=10)
    for ax in axes[1]:
        ax.set_xticks(months)
        ax.set_xticklabels(["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"])
    fig.suptitle(f"Monthly TC genesis, multi-model mean ({TRACKER_LABEL.get(tracker, tracker)} tracker)", fontsize=14, fontweight="bold")
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Track translation: is the projected change a poleward shift of the tracks?
# ---------------------------------------------------------------------------

# Grid of the track density (cell edges, 2.5°) and poleward shifts applied to the present-day tracks.
DENSITY_LON = np.arange(90, 272.5, 2.5)
DENSITY_LAT = np.arange(-50, 52.5, 2.5)
SHIFTS = np.array(sorted(set(np.round(np.arange(0, 2.51, 0.25), 2)) | {1.13}))
REGION_BOUNDS = {  # (lon_min, lon_max, lat_min, lat_max) of tcs.classify_genesis_region
    "Western North Pacific": (120, 180, 0, 40),
    "Central North Pacific": (180, 220, 0, 40),
    "Western South Pacific": (135, 180, -40, 0),
    "Central South Pacific": (180, 240, -40, 0),
}


def _storm_tracks(path, hemisphere):
    """Genesis rows (as ``genesis_points``) plus the TC-strength track points (≥ 34 kt from genesis on) of every storm."""
    ds = xr.open_dataset(path, use_cftime=True)
    first, npts = ds["FIRST_PT"].values, ds["NUM_PTS"].values
    lon, lat = ds["lon"].values % 360, ds["lat"].values
    wind, psl, time = ds["sfcWind"].values, ds["psl"].values, ds["time"].values
    rows, points = [], []
    for k in range(len(first)):
        sl = slice(first[k], first[k] + npts[k])
        w = wind[sl]
        strong = np.where(np.isfinite(w) & (w >= KT34))[0]
        if strong.size == 0:
            continue
        g, t = strong[0], time[sl][strong[0]]
        rows.append({"hemisphere": hemisphere, "year": t.year, "month": t.month, "lon": float(lon[sl][g]),
                     "lat": float(lat[sl][g]), "max_wind": float(np.nanmax(w)), "min_psl": float(np.nanmin(psl[sl]))})
        tc = strong[strong >= g]
        points.append((lon[sl][tc].astype(float), lat[sl][tc].astype(float)))
    ds.close()
    return pd.DataFrame(rows), points


def track_summary(lons, lats, signs, regions, n_years):
    """Track density per year (TC days per 2.5° cell, for every shift in ``SHIFTS``) and, per genesis region,
    the sum and number of absolute track-point latitudes."""
    density = np.zeros((len(SHIFTS), len(DENSITY_LAT) - 1, len(DENSITY_LON) - 1))
    for i, shift in enumerate(SHIFTS):
        density[i] = np.histogram2d(lats + signs * shift, lons, bins=[DENSITY_LAT, DENSITY_LON])[0]
    density /= 4 * n_years  # 6-hourly points -> days, per year
    lat_sum = np.array([np.abs(lats[regions == r]).sum() for r in REGIONS])
    lat_n = np.array([(regions == r).sum() for r in REGIONS])
    return density, lat_sum, lat_n


def extract_member_tracks(tracker, model, period, member, raw_dir, on_land, keep_raw=False):
    """Track density and per-region track latitudes of one member (constrained TCs, duplicates removed), cached as npz."""
    cache = CACHE_DIR / f"{tracker}_{model}_{period}_{member}_tracks.npz"
    if cache.exists():
        return dict(np.load(cache))
    experiment, y0, y1 = PERIODS[period]
    lons, lats, signs, regions, years = [], [], [], [], set()
    for hemisphere, url in sorted(_track_files(tracker, model, experiment, member).items()):
        path = Path(raw_dir) / url.rsplit("/", 1)[1]
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(url, path)
        table, points = _storm_tracks(path, hemisphere)
        if not keep_raw:
            path.unlink()
        if table.empty:
            continue
        table = constrain(table, on_land)
        keep = table["year"].between(y0, y1) & table["kept"] & ~table.duplicated(GENESIS_KEY[4:])
        years |= set(table.loc[table["year"].between(y0, y1), "year"])
        for k in np.where(keep)[0]:
            lo, la = points[k]
            lons.append(lo)
            lats.append(la)
            signs.append(np.full(lo.size, 1.0 if hemisphere == "NH" else -1.0))
            regions.append(np.full(lo.size, table["region"].iloc[k] or "", dtype=object))
    cat = lambda x, dtype=float: np.concatenate(x) if x else np.array([], dtype=dtype)
    density, lat_sum, lat_n = track_summary(cat(lons), cat(lats), cat(signs), cat(regions, object), max(len(years), 1))
    out = {"density": density, "lat_sum": lat_sum, "lat_n": lat_n, "years": np.array(len(years))}
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, **out)
    return out


def load_tracks(qc, raw_dir=None, keep_raw=False, verbose=True):
    """Track summaries of every member used in ``qc`` (``load_genesis(return_qc=True)``); downloads what is not cached.

    Returns ``density`` (tracker, model, period, shift, lat, lon; member mean, TC days per year per 2.5° cell) and
    ``track_lat`` (tracker, model, period, region; mean absolute latitude of the track points of storms forming there).
    """
    import tempfile

    raw_dir = Path(raw_dir or Path(tempfile.gettempdir()) / "cindra_tcs_highresmip")
    on_land, dens, tlat = None, {}, {}
    for _, row in qc.loc[qc["used"]].iterrows():
        key = (row["tracker"], row["model"], row["period"], row["member"])
        cache = CACHE_DIR / f"{key[0]}_{key[1]}_{key[2]}_{key[3]}_tracks.npz"
        if not cache.exists() and on_land is None:
            on_land = _land_checker()
        if verbose:
            print(" ".join(key) + ("" if cache.exists() else "  (downloading)"))
        out = extract_member_tracks(*key, raw_dir, on_land, keep_raw)
        dens.setdefault(key[:3], []).append(out["density"])
        tlat.setdefault(key[:3], []).append((out["lat_sum"], out["lat_n"]))
    if not keep_raw and raw_dir.exists() and not any(raw_dir.iterdir()):
        shutil.rmtree(raw_dir)

    keys = sorted(dens)
    index = pd.MultiIndex.from_tuples(keys, names=["tracker", "model", "period"])
    lat_c = (DENSITY_LAT[:-1] + DENSITY_LAT[1:]) / 2
    lon_c = (DENSITY_LON[:-1] + DENSITY_LON[1:]) / 2
    density = xr.DataArray(np.stack([np.mean(dens[k], axis=0) for k in keys]), dims=("key", "shift", "lat", "lon"),
                           coords={"key": index, "shift": SHIFTS, "lat": lat_c, "lon": lon_c}).unstack("key")
    track_lat = pd.DataFrame([np.mean([s / np.maximum(n, 1) for s, n in tlat[k]], axis=0) for k in keys],
                             index=index, columns=list(REGIONS))
    return density.transpose("tracker", "model", "period", "shift", "lat", "lon"), track_lat


def observed_density(ibtracs, start=1980, end=2010):
    """IBTrACS track density (TC days per year per 2.5° cell, points ≥ 34 kt from genesis on) for every shift in ``SHIFTS``."""
    lon = np.mod(ibtracs["lon"].values.astype(float), 360)
    lat = ibtracs["lat"].values.astype(float)
    wind = ibtracs["wmo_wind"].values.astype(float)
    time = pd.to_datetime(ibtracs["time"].values.ravel())
    hours = np.asarray(time.hour).reshape(lat.shape)
    years = np.asarray(time.year).reshape(lat.shape)
    lons, lats, signs, regions = [], [], [], []
    for k in range(lat.shape[0]):
        strong = np.where(np.isfinite(wind[k]) & (wind[k] >= 34))[0]
        if strong.size == 0 or not start <= years[k, strong[0]] <= end:
            continue
        g = strong[0]
        pts = strong[(strong >= g) & np.isin(hours[k, strong], [0, 6, 12, 18])]  # 6-hourly, as the models
        sign = 1.0 if lat[k, g] >= 0 else -1.0
        lons.append(lon[k, pts]); lats.append(lat[k, pts]); signs.append(np.full(pts.size, sign))
        regions.append(np.full(pts.size, classify_genesis_region(lon[k, g], lat[k, g]) or "", dtype=object))
    density, lat_sum, lat_n = track_summary(np.concatenate(lons), np.concatenate(lats), np.concatenate(signs),
                                            np.concatenate(regions), end - start + 1)
    lat_c = (DENSITY_LAT[:-1] + DENSITY_LAT[1:]) / 2
    lon_c = (DENSITY_LON[:-1] + DENSITY_LON[1:]) / 2
    return xr.DataArray(density, dims=("shift", "lat", "lon"), coords={"shift": SHIFTS, "lat": lat_c, "lon": lon_c})


def track_latitude_change(track_lat):
    """Future minus present mean absolute latitude of the track points (°, + poleward), per tracker and model, plus mean."""
    change = (track_lat.xs("future", level="period") - track_lat.xs("present", level="period")).reset_index()
    change["tracker"] = change["tracker"].map(TRACKER_LABEL)
    change = change.rename(columns={"tracker": "Tracker", "model": "Model"})
    mme = change.groupby("Tracker", sort=False)[list(REGIONS)].mean().reset_index().assign(Model="Multi-model mean")
    return pd.concat([change, mme[change.columns]], ignore_index=True)


def _box(da, region):
    x0, x1, y0, y1 = REGION_BOUNDS[region]
    return da.sel(lon=slice(x0, x1), lat=slice(y0, y1))


def translation_skill(density):
    """How well a poleward translation of the present tracks reproduces the future track pattern in each region.

    In each region box, the present density shifted by every ``SHIFTS`` value and the future density are normalised
    to the same total (so only the spatial pattern counts, not the change in the number of TCs) and compared by RMSE.
    Returns, per tracker and model (and their mean), the best-fitting shift, and the share of the present-vs-future
    pattern difference removed by the best shift and by the 1.13° shift (100 % = the translation explains it fully).
    """
    rows = []
    for tracker in density.tracker.values:
        for model in density.model.values:
            d = density.sel(tracker=tracker, model=model)
            if not np.isfinite(d.sel(period="future").values).any():
                continue
            for region in REGIONS:
                present = _box(d.sel(period="present"), region)
                future = _box(d.sel(period="future", shift=0), region)
                fut_n = future / future.sum()
                pre_n = present / present.sum(("lat", "lon"))
                rmse = np.sqrt(((pre_n - fut_n) ** 2).mean(("lat", "lon"))).to_series()
                best = rmse.idxmin()
                rows.append({"Tracker": TRACKER_LABEL[tracker], "Model": model, "Region": region, "Best shift (°)": best,
                             "Explained by best shift (%)": (1 - rmse[best] ** 2 / rmse[0] ** 2) * 100,
                             "Explained by 1.13° (%)": (1 - rmse[1.13] ** 2 / rmse[0] ** 2) * 100})
    table = pd.DataFrame(rows)
    mme = table.groupby(["Tracker", "Region"], sort=False)[["Best shift (°)", "Explained by best shift (%)",
                                                              "Explained by 1.13° (%)"]].mean().reset_index()
    return pd.concat([table, mme.assign(Model="Multi-model mean")[table.columns]], ignore_index=True)


def rmse_curves(density, tracker):
    """Normalised pattern RMSE between shifted present and future density, per model, region and shift (one tracker)."""
    out = {}
    for model in density.model.values:
        d = density.sel(tracker=tracker, model=model)
        if not np.isfinite(d.sel(period="future").values).any():
            continue
        for region in REGIONS:
            present, future = _box(d.sel(period="present"), region), _box(d.sel(period="future", shift=0), region)
            diff = present / present.sum(("lat", "lon")) - future / future.sum()
            rmse = np.sqrt((diff ** 2).mean(("lat", "lon")))
            out[(model, region)] = (rmse / rmse.sel(shift=0)).to_series()
    return pd.DataFrame(out).T


def plot_rmse_curves(density, figsize=(14, 8)):
    """Pattern mismatch (relative to no shift) vs poleward shift of the present tracks, per region; one line per model and tracker."""
    fig, axes = plt.subplots(2, 2, figsize=figsize, sharex=True)
    for ls, tracker in zip(("-", "--"), density.tracker.values):
        curves = rmse_curves(density, tracker)
        for ax, region in zip(axes.flat, REGIONS):
            sub = curves.xs(region, level=1)
            for model, row in sub.iterrows():
                ax.plot(row.index, row.values, ls, color="0.6", linewidth=0.9)
            ax.plot(sub.columns, sub.mean().values, ls, color=REGION_COLORS[region], linewidth=2.5,
                    label=f"{TRACKER_LABEL[tracker]} (mean)")
    for ax, region in zip(axes.flat, REGIONS):
        ax.axvline(1.13, color="black", linestyle=":", linewidth=1.2, label="1.13°")
        ax.set_title(region, fontsize=13, fontweight="bold")
        ax.set_ylabel("Pattern RMSE / RMSE without shift")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=9)
    for ax in axes[1]:
        ax.set_xlabel("Poleward shift of the 1980–2010 tracks (°)")
    fig.suptitle("Does translating the present tracks poleward reproduce the 2020–2050 track pattern? (grey: individual models)",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    return fig


def plot_density_maps(density, observed, tracker="TRACK", shift=1.13, figsize=(16, 11)):
    """Track density change: projected by the models (future - present) vs implied by translating the present tracks
    by ``shift``; and the observed density with the change implied by the same translation."""
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    from matplotlib.patches import Rectangle

    d = density.sel(tracker=tracker)
    valid = [m for m in d.model.values if np.isfinite(d.sel(model=m, period="future").values).any()]
    d = d.sel(model=valid).mean("model")
    panels = {
        f"Models: projected change 2020–2050 minus 1980–2010 ({TRACKER_LABEL[tracker]}, multi-model mean)":
            d.sel(period="future", shift=0) - d.sel(period="present", shift=0),
        f"Models: change implied by translating the 1980–2010 tracks {shift}° poleward":
            d.sel(period="present", shift=shift) - d.sel(period="present", shift=0),
        "Observed (IBTrACS) TC track density, 1980–2010": observed.sel(shift=0),
        f"Observed: change implied by translating the tracks {shift}° poleward":
            observed.sel(shift=shift) - observed.sel(shift=0),
    }
    fig, axes = plt.subplots(2, 2, figsize=figsize, subplot_kw={"projection": ccrs.PlateCarree(central_longitude=180)})
    diff_lim = max(float(np.nanpercentile(np.abs(v.values), 99)) for k, v in panels.items() if "change" in k)
    for ax, (title, field) in zip(axes.flat, panels.items()):
        is_change = "change" in title
        mesh = ax.pcolormesh(field.lon, field.lat, field.values, transform=ccrs.PlateCarree(),
                             cmap="RdBu_r" if is_change else "YlOrRd",
                             vmin=-diff_lim if is_change else 0, vmax=diff_lim if is_change else float(np.nanpercentile(field.values, 99)))
        ax.set_extent((95, 265, -45, 45), crs=ccrs.PlateCarree())
        ax.add_feature(cfeature.LAND, facecolor="lightgrey", zorder=2)
        ax.coastlines(linewidth=0.4, zorder=3)
        for region, (x0, x1, y0, y1) in REGION_BOUNDS.items():
            ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, edgecolor=REGION_COLORS[region],
                                   linewidth=1.5, transform=ccrs.PlateCarree(), zorder=4))
        ax.set_title(title, fontsize=11)
        fig.colorbar(mesh, ax=ax, orientation="horizontal", fraction=0.05, pad=0.04,
                     label="Δ TC days per year per 2.5° cell" if is_change else "TC days per year per 2.5° cell")
    fig.suptitle("Tropical-cyclone track density: projected change vs a uniform poleward translation", fontsize=14, fontweight="bold")
    fig.subplots_adjust(top=0.93, hspace=0.12, wspace=0.08)
    return fig


def pattern_noise(qc):
    """Internal-variability check of the track-pattern test, for models with several members.

    In each region box, the normalised-pattern RMSE between two present-day members of the same model (same
    climate, only internal variability) is compared with the RMSE between present and future members. The ratio of
    their squares (%) is the share of the present-vs-future pattern difference that internal variability alone
    would produce: near 100 % means the projected change in the track map cannot be told apart from noise.
    """
    import itertools

    lat_c = (DENSITY_LAT[:-1] + DENSITY_LAT[1:]) / 2
    lon_c = (DENSITY_LON[:-1] + DENSITY_LON[1:]) / 2
    load = lambda key: xr.DataArray(np.load(CACHE_DIR / f"{'_'.join(key)}_tracks.npz")["density"][0], dims=("lat", "lon"),
                                    coords={"lat": lat_c, "lon": lon_c})
    used = qc.loc[qc["used"]]
    rows = []
    for (tracker, model), sub in used.groupby(["tracker", "model"]):
        present = [load((tracker, model, "present", m)) for m in sub.loc[sub["period"] == "present", "member"]]
        future = [load((tracker, model, "future", m)) for m in sub.loc[sub["period"] == "future", "member"]]
        if len(present) < 2 or not future:
            continue
        for region in REGIONS:
            norm = lambda d: (lambda b: b / b.sum())(_box(d, region))
            rmse = lambda a, b: float(np.sqrt(((norm(a) - norm(b)) ** 2).mean()))
            noise = np.mean([rmse(a, b) for a, b in itertools.combinations(present, 2)])
            change = np.mean([rmse(a, b) for a in present for b in future])
            rows.append({"Tracker": TRACKER_LABEL[tracker], "Model": model, "Region": region,
                         "Members (present)": len(present), "Internal variability / present-vs-future (%)": noise ** 2 / change ** 2 * 100})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Site analysis: tropical cyclones passing near a point
# ---------------------------------------------------------------------------

POINTS_WINDOW = (90, 270, -50, 50)  # lon_min, lon_max (0–360), lat_min, lat_max of the cached track points


def extract_member_points(tracker, model, period, member, raw_dir, on_land, keep_raw=False):
    """TC-strength track points (≥ 34 kt, from genesis on) of the constrained, de-duplicated storms of one member
    inside ``POINTS_WINDOW``, cached as npz: storm id, year and month of genesis, lon, lat, wind (m/s), sea-level
    pressure (hPa), hemisphere sign. Points are in track order within each storm."""
    cache = CACHE_DIR / f"{tracker}_{model}_{period}_{member}_points.npz"
    if cache.exists():
        cached = dict(np.load(cache))
        if "psl" in cached:
            return cached
        cache.unlink()  # cache from an earlier version without pressure
    experiment, y0, y1 = PERIODS[period]
    x0, x1, la0, la1 = POINTS_WINDOW
    cols = {k: [] for k in ("storm", "year", "month", "lon", "lat", "wind", "psl", "sign")}
    years, next_id = set(), 0
    for hemisphere, url in sorted(_track_files(tracker, model, experiment, member).items()):
        path = Path(raw_dir) / url.rsplit("/", 1)[1]
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(url, path)
        ds = xr.open_dataset(path, use_cftime=True)
        first, npts = ds["FIRST_PT"].values, ds["NUM_PTS"].values
        lon, lat = ds["lon"].values % 360, ds["lat"].values
        wind, psl, time = ds["sfcWind"].values, ds["psl"].values, ds["time"].values
        rows, pts = [], []
        for k in range(len(first)):
            sl = slice(first[k], first[k] + npts[k])
            w = wind[sl]
            strong = np.where(np.isfinite(w) & (w >= KT34))[0]
            if strong.size == 0:
                continue
            g, t = strong[0], time[sl][strong[0]]
            rows.append({"hemisphere": hemisphere, "year": t.year, "month": t.month, "lon": float(lon[sl][g]),
                         "lat": float(lat[sl][g]), "max_wind": float(np.nanmax(w)), "min_psl": float(np.nanmin(psl[sl]))})
            pts.append((lon[sl][strong], lat[sl][strong], w[strong], psl[sl][strong]))
        ds.close()
        if not keep_raw:
            path.unlink()
        if not rows:
            continue
        table = constrain(pd.DataFrame(rows), on_land)
        years |= set(table.loc[table["year"].between(y0, y1), "year"])
        keep = table["year"].between(y0, y1) & table["kept"] & ~table.duplicated(GENESIS_KEY[4:])
        for k in np.where(keep)[0]:
            lo, la, wi, ps = pts[k]
            inside = (lo >= x0) & (lo <= x1) & (la >= la0) & (la <= la1)
            n = int(inside.sum())
            if n == 0:
                continue
            cols["storm"].append(np.full(n, next_id, np.int32)); next_id += 1
            cols["year"].append(np.full(n, table["year"].iloc[k], np.int16))
            cols["month"].append(np.full(n, table["month"].iloc[k], np.int8))
            cols["lon"].append(lo[inside].astype(np.float32)); cols["lat"].append(la[inside].astype(np.float32))
            cols["wind"].append(wi[inside].astype(np.float32))
            cols["psl"].append(ps[inside].astype(np.float32))
            cols["sign"].append(np.full(n, 1 if hemisphere == "NH" else -1, np.int8))
    out = {k: (np.concatenate(v) if v else np.array([])) for k, v in cols.items()}
    out["years"] = np.array(len(years))
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, **out)
    return out


def load_points(qc, raw_dir=None, keep_raw=False, verbose=True):
    """Track points of every member used in ``qc`` (``load_genesis(return_qc=True)``): {(tracker, model, period, member): dict}.
    Downloads the track files of the members not yet cached."""
    import tempfile

    raw_dir = Path(raw_dir or Path(tempfile.gettempdir()) / "cindra_tcs_highresmip")
    on_land, points = None, {}
    for _, row in qc.loc[qc["used"]].iterrows():
        key = (row["tracker"], row["model"], row["period"], row["member"])
        cache = CACHE_DIR / f"{'_'.join(key)}_points.npz"
        if cache.exists() and "psl" not in np.load(cache).files:
            cache.unlink()  # cache from an earlier version without pressure
        if not cache.exists() and on_land is None:
            on_land = _land_checker()
        if verbose and not cache.exists():
            print(" ".join(key) + "  (downloading)")
        points[key] = extract_member_points(*key, raw_dir, on_land, keep_raw)
    if not keep_raw and raw_dir.exists() and not any(raw_dir.iterdir()):
        shutil.rmtree(raw_dir)
    return points


def great_circle_deg(lon1, lat1, lon2, lat2):
    """Great-circle distance in degrees (as ``tcs.GeoDistance``), vectorised."""
    lon1, lat1, lon2, lat2 = map(np.radians, (lon1, lat1, lon2, lat2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return np.degrees(2 * np.arctan2(np.sqrt(np.clip(a, 0, 1)), np.sqrt(np.clip(1 - a, 0, 1))))


def site_passages(pts, site_lon, site_lat, radius=5, shift=0.0):
    """Storms with at least one TC-strength point within ``radius`` degrees of the site, after moving every track
    ``shift`` degrees poleward: one row per storm (genesis year and month, closest distance, maximum wind inside)."""
    columns = ["storm", "year", "month", "min_distance", "max_wind", "min_psl", "lifetime_min_psl"]
    if pts["lon"].size == 0:
        return pd.DataFrame(columns=columns)
    lat = pts["lat"] + pts["sign"] * shift
    dist = great_circle_deg(pts["lon"], lat, site_lon % 360, site_lat)
    inside = dist <= radius
    psl = pts["psl"] if "psl" in pts else np.full(pts["lon"].size, np.nan)
    frame = pd.DataFrame({"storm": pts["storm"][inside], "year": pts["year"][inside], "month": pts["month"][inside],
                          "distance": dist[inside], "wind": pts["wind"][inside], "psl": psl[inside]})
    out = frame.groupby("storm").agg(year=("year", "first"), month=("month", "first"), min_distance=("distance", "min"),
                                     max_wind=("wind", "max"), min_psl=("psl", "min")).reset_index()
    lifetime = pd.Series(psl).groupby(pts["storm"]).min()
    out["lifetime_min_psl"] = out["storm"].map(lifetime)
    return out[columns]


def site_counts(points, site_lon, site_lat, radius=5, shifts=(0.0,)):
    """TCs per year passing within ``radius`` of the site, per tracker, model, period and shift (member mean)."""
    rows = []
    for (tracker, model, period, member), pts in points.items():
        n_years = max(int(pts["years"]), 1)
        for shift in shifts:
            n = len(site_passages(pts, site_lon, site_lat, radius, shift))
            rows.append({"tracker": tracker, "model": model, "period": period, "member": member, "shift": shift,
                         "tcs_per_year": n / n_years})
    frame = pd.DataFrame(rows)
    return frame.groupby(["tracker", "model", "period", "shift"])["tcs_per_year"].mean().unstack("period")


def site_change_table(counts):
    """Present and future TCs per year near the site and % change (no shift), per tracker and model, plus mean."""
    base = counts.xs(0.0, level="shift").reset_index()
    base["Change (%)"] = (base["future"] - base["present"]) / base["present"] * 100
    base["tracker"] = base["tracker"].map(TRACKER_LABEL)
    base = base.rename(columns={"tracker": "Tracker", "model": "Model", "present": "Present 1980–2010 (TCs/yr)",
                                "future": "Future 2020–2050 (TCs/yr)"})
    mme = base.groupby("Tracker", sort=False)[["Present 1980–2010 (TCs/yr)", "Future 2020–2050 (TCs/yr)"]].mean().reset_index()
    mme["Change (%)"] = (mme["Future 2020–2050 (TCs/yr)"] - mme["Present 1980–2010 (TCs/yr)"]) / mme["Present 1980–2010 (TCs/yr)"] * 100
    return pd.concat([base, mme.assign(Model="Multi-model mean")[base.columns]], ignore_index=True)


def translation_vs_projection(counts, observed_counts_by_shift=None):
    """% change in TCs near the site: projected by each model (future vs present) and implied by moving its present
    tracks poleward by each shift; optionally the change implied by the same shifts for the observed tracks."""
    pres = counts["present"].unstack("shift")
    fut0 = counts["future"].xs(0.0, level="shift")
    rows = []
    for (tracker, model), row in pres.iterrows():
        rec = {"Tracker": TRACKER_LABEL[tracker], "Model": model,
               "Projected (models)": (fut0.loc[(tracker, model)] - row[0.0]) / row[0.0] * 100}
        for shift in row.index:
            if shift > 0:
                rec[f"Translation {shift:g}°"] = (row[shift] - row[0.0]) / row[0.0] * 100
        rows.append(rec)
    table = pd.DataFrame(rows)
    mme = table.groupby("Tracker", sort=False).mean(numeric_only=True).reset_index().assign(Model="Multi-model mean")
    table = pd.concat([table, mme[table.columns]], ignore_index=True)
    if observed_counts_by_shift is not None:
        obs = observed_counts_by_shift
        rec = {"Tracker": "IBTrACS", "Model": "Observed 1980–2010", "Projected (models)": np.nan}
        rec.update({f"Translation {s:g}°": (obs[s] - obs[0.0]) / obs[0.0] * 100 for s in obs.index if s > 0})
        table = pd.concat([table, pd.DataFrame([rec])], ignore_index=True)
    return table


def observed_points(ibtracs, start=1980, end=2010):
    """IBTrACS 6-hourly points ≥ 34 kt (WMO wind, from genesis on) of storms forming in ``start``–``end``,
    in the format of ``extract_member_points``."""
    lon = np.mod(ibtracs["lon"].values.astype(float), 360)
    lat = ibtracs["lat"].values.astype(float)
    wind = ibtracs["wmo_wind"].values.astype(float)
    time = pd.to_datetime(ibtracs["time"].values.ravel())
    hours = np.asarray(time.hour).reshape(lat.shape)
    years = np.asarray(time.year).reshape(lat.shape)
    months = np.asarray(time.month).reshape(lat.shape)
    pres = ibtracs["wmo_pres"].values.astype(float)
    cols = {k: [] for k in ("storm", "year", "month", "lon", "lat", "wind", "psl", "sign")}
    for k in range(lat.shape[0]):
        strong = np.where(np.isfinite(wind[k]) & (wind[k] >= 34))[0]
        if strong.size == 0 or not start <= years[k, strong[0]] <= end:
            continue
        g = strong[0]
        p = strong[np.isin(hours[k, strong], [0, 6, 12, 18])]
        cols["storm"].append(np.full(p.size, k)); cols["year"].append(np.full(p.size, years[k, g]))
        cols["month"].append(np.full(p.size, months[k, g])); cols["lon"].append(lon[k, p]); cols["lat"].append(lat[k, p])
        cols["wind"].append(wind[k, p] * 0.514444)  # kt -> m/s, as the models
        cols["psl"].append(pres[k, p])
        cols["sign"].append(np.full(p.size, 1 if lat[k, g] >= 0 else -1))
    out = {k: np.concatenate(v) for k, v in cols.items()}
    out["years"] = np.array(end - start + 1)
    return out


def plot_site_counts(change, observed=None, site_label="site", radius=5, figsize=(10, 5.5)):
    """TCs per year passing within ``radius`` of the site: present and future multi-model mean per tracker, models as markers."""
    fig, ax = plt.subplots(figsize=figsize)
    trackers = list(dict.fromkeys(change["Tracker"]))
    width = 0.35
    for i, tracker in enumerate(trackers):
        t = change.loc[change["Tracker"] == tracker]
        mme = t.loc[t["Model"] == "Multi-model mean"].iloc[0]
        for j, (col, alpha, label) in enumerate((("Present 1980–2010 (TCs/yr)", 0.45, "Present 1980–2010"),
                                                 ("Future 2020–2050 (TCs/yr)", 0.95, "Future 2020–2050 (SSP5-8.5)"))):
            x = i + (j - 0.5) * width
            ax.bar(x, mme[col], width=width * 0.92, color="#5E9A8D", alpha=alpha, edgecolor="0.3", label=label if i == 0 else None)
            for _, m in t.loc[t["Model"] != "Multi-model mean"].iterrows():
                ax.scatter(x, m[col], marker=MODEL_MARKERS[m["Model"]], color="0.15", s=30, zorder=3)
        top = t[["Present 1980–2010 (TCs/yr)", "Future 2020–2050 (TCs/yr)"]].max().max()
        ax.text(i, top * 1.04, f"{mme['Change (%)']:+.0f}%", ha="center", va="bottom", fontsize=13, fontweight="bold")
    if observed is not None:
        ax.axhline(observed, color="black", linestyle="--", linewidth=1.2, label="Observed 1980–2010 (IBTrACS)")
    ax.set_xticks(range(len(trackers)))
    ax.set_xticklabels(trackers)
    ax.set_ylabel("TCs per year")
    ax.set_ylim(0, ax.get_ylim()[1] * 1.12)
    ax.grid(axis="y", alpha=0.3)
    handles, labels = ax.get_legend_handles_labels()
    handles += [plt.Line2D([], [], marker=MODEL_MARKERS[m], color="0.15", linestyle="") for m in MODELS]
    labels += list(MODELS)
    ax.legend(handles, labels, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=3, frameon=False)
    ax.set_title(f"TCs passing within {radius}° of {site_label} (≥ 34 kt): CMIP6-HighResMIP", fontsize=13, fontweight="bold")
    fig.tight_layout()
    return fig


def site_monthly(points, site_lon, site_lat, radius=5):
    """Multi-model mean TCs per year passing near the site by genesis month, per tracker and period."""
    rows = []
    for (tracker, model, period, member), pts in points.items():
        p = site_passages(pts, site_lon, site_lat, radius)
        n = p.groupby("month").size().reindex(range(1, 13), fill_value=0) / max(int(pts["years"]), 1)
        rows.append(pd.Series(n.values, index=range(1, 13), name=(tracker, model, period, member)))
    frame = pd.DataFrame(rows)
    frame.index = pd.MultiIndex.from_tuples(frame.index, names=["tracker", "model", "period", "member"])
    return frame.groupby(level=["tracker", "model", "period"]).mean().groupby(level=["tracker", "period"]).mean()


def site_intensity(points, site_lon, site_lat, radius=5, bins=(17.5, 25, 33, 43, 100)):
    """Multi-model mean TCs per year near the site by maximum 10-m wind inside the circle (m/s classes), per tracker and period."""
    labels = [f"{a:g}–{b:g} m/s" if b < 100 else f"≥ {a:g} m/s" for a, b in zip(bins[:-1], bins[1:])]
    rows = []
    for (tracker, model, period, member), pts in points.items():
        p = site_passages(pts, site_lon, site_lat, radius)
        n = pd.cut(p["max_wind"], bins=list(bins), labels=labels, right=False).value_counts().reindex(labels, fill_value=0)
        rows.append(pd.Series(n.values / max(int(pts["years"]), 1), index=labels, name=(tracker, model, period, member)))
    frame = pd.DataFrame(rows)
    frame.index = pd.MultiIndex.from_tuples(frame.index, names=["tracker", "model", "period", "member"])
    return frame.groupby(level=["tracker", "model", "period"]).mean().groupby(level=["tracker", "period"]).mean()



# Pressure classes of the Saffir–Simpson scale (minimum central pressure, hPa). The scale gives no pressure limit
# between tropical storms and category 1, so both are one class. Model winds at 25–75 km resolution are too weak
# for wind-based categories (Roberts et al., 2020), so model storms are classified by pressure.
PRESSURE_CLASSES = [("TS–Cat 1 (≥ 980 hPa)", 980, np.inf), ("Cat 2 (965–979)", 965, 980), ("Cat 3 (945–964)", 945, 965),
                    ("Cat 4 (920–944)", 920, 945), ("Cat 5 (< 920)", -np.inf, 920)]
PRESSURE_COLORS = {"TS–Cat 1 (≥ 980 hPa)": "yellowgreen", "Cat 2 (965–979)": "orange", "Cat 3 (945–964)": "red",
                   "Cat 4 (920–944)": "purple", "Cat 5 (< 920)": "black", "No pressure": "lightgrey"}


def pressure_class(p):
    """Saffir–Simpson pressure class of a minimum central pressure (hPa); 'No pressure' if missing."""
    if not np.isfinite(p):
        return "No pressure"
    for name, low, high in PRESSURE_CLASSES:
        if low <= p < high:
            return name


def site_category_counts(points, site_lon, site_lat, radius=5, observed=None, column="lifetime_min_psl"):
    """TCs per year passing near the site by pressure class (lifetime minimum pressure by default), multi-model mean
    per tracker and period; with ``observed`` (IBTrACS points) also the observed 1980–2010 counts."""
    classes = [c[0] for c in PRESSURE_CLASSES]
    rows = []
    for (tracker, model, period, member), pts in points.items():
        p = site_passages(pts, site_lon, site_lat, radius)
        n = p[column].map(pressure_class).value_counts().reindex(classes, fill_value=0) / max(int(pts["years"]), 1)
        rows.append(pd.Series(n.values, index=classes, name=(tracker, model, period, member)))
    frame = pd.DataFrame(rows)
    frame.index = pd.MultiIndex.from_tuples(frame.index, names=["tracker", "model", "period", "member"])
    out = frame.groupby(level=["tracker", "model", "period"]).mean().groupby(level=["tracker", "period"]).mean()
    out.index = pd.MultiIndex.from_tuples([(TRACKER_LABEL[t], "1980–2010" if p == "present" else "2020–2050 (SSP5-8.5)")
                                           for t, p in out.index], names=["Source", "Period"])
    if observed is not None:
        p = site_passages(observed, site_lon, site_lat, radius)
        n = p[column].map(pressure_class).value_counts()
        obs = n.reindex(classes, fill_value=0) / int(observed["years"])
        out.loc[("IBTrACS", "1980–2010"), :] = obs.values
        if "No pressure" in n:
            print(f"IBTrACS storms without pressure (not classified): {n['No pressure'] / int(observed['years']):.2f} per year")
    order = [("IBTrACS", "1980–2010")] + [(TRACKER_LABEL[t], p) for t in TRACKERS for p in ("1980–2010", "2020–2050 (SSP5-8.5)")]
    return out.reindex([o for o in order if o in out.index])


def _storms_near(pts, site_lon, site_lat, radius):
    """Track points (lon, lat, storm id, lifetime minimum pressure) of the storms passing within ``radius`` of the site."""
    ids = site_passages(pts, site_lon, site_lat, radius)["storm"].values
    sel = np.isin(pts["storm"], ids)
    psl = pd.Series(pts["psl"]).groupby(pts["storm"]).min()
    return pts["lon"][sel], pts["lat"][sel], pts["storm"][sel], psl


def plot_site_tracks(points, site_lon, site_lat, radius=5, tracker="TRACK", member_index=0, zoom=10, site_label="site",
                     figsize=None):
    """Tracks of the storms passing within ``radius`` of the site, 1980–2010 (left) vs 2020–2050 (right), one row per
    model (one member each), coloured by Saffir–Simpson pressure class of the storm's lifetime minimum pressure."""
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    from matplotlib.lines import Line2D

    models = [m for m in MODELS if any(k[0] == tracker and k[1] == m and k[2] == "future" for k in points)]
    figsize = figsize or (14, 5.2 * len(models))
    fig, axes = plt.subplots(len(models), 2, figsize=figsize, squeeze=False,
                             subplot_kw={"projection": ccrs.PlateCarree(central_longitude=180)})
    lon0 = site_lon % 360
    theta = np.linspace(0, 2 * np.pi, 200)
    for r, model in enumerate(models):
        for c, period in enumerate(("present", "future")):
            ax = axes[r, c]
            members = sorted(k for k in points if k[:3] == (tracker, model, period))
            key = members[min(member_index, len(members) - 1)]
            pts = points[key]
            lon, lat, storm, psl = _storms_near(pts, site_lon, site_lat, radius)
            for sid in np.unique(storm):
                m = storm == sid
                ax.plot(lon[m], lat[m], "-", color=PRESSURE_COLORS[pressure_class(psl[sid])], linewidth=1.1, alpha=0.75,
                        transform=ccrs.PlateCarree())
                ax.plot(lon[m][0], lat[m][0], "o", color=PRESSURE_COLORS[pressure_class(psl[sid])], markersize=3,
                        transform=ccrs.PlateCarree())
            ax.fill(lon0 + radius * np.cos(theta) / np.cos(np.radians(site_lat)), site_lat + radius * np.sin(theta),
                    color="grey", alpha=0.3, transform=ccrs.PlateCarree(), zorder=4)
            ax.plot(lon0, site_lat, "o", color="brown", markersize=8, transform=ccrs.PlateCarree(), zorder=5)
            ax.set_extent((lon0 - zoom, lon0 + zoom, site_lat - zoom, site_lat + zoom), crs=ccrs.PlateCarree())
            ax.add_feature(cfeature.LAND, color="silver", zorder=3)
            ax.coastlines(linewidth=0.4, zorder=3)
            gl = ax.gridlines(draw_labels=True, linewidth=0.4, color="gray", alpha=0.5, linestyle="--")
            gl.top_labels = gl.right_labels = False
            n_storms = len(np.unique(storm))
            ax.set_title(f"{model} ({key[3]}) – {'1980–2010' if period == 'present' else '2020–2050'}: "
                         f"{n_storms} TCs ({n_storms / max(int(pts['years']), 1):.1f}/yr)", fontsize=11)
    handles = [Line2D([], [], color=col, linewidth=2, label=name) for name, col in PRESSURE_COLORS.items() if name != "No pressure"]
    fig.legend(handles=handles, loc="lower center", ncol=5, frameon=False, fontsize=11,
               title="Saffir–Simpson class of the lifetime minimum pressure")
    fig.suptitle(f"TCs passing within {radius}° of {site_label}: {TRACKER_LABEL[tracker]} tracks (one member per model)",
                 fontsize=14, fontweight="bold")
    fig.tight_layout(rect=(0, 0.05, 1, 0.97))
    return fig


def site_density(points, tracker, period, extent, resolution=1.0, sigma=2):
    """Smoothed multi-model mean TC track density (TC days per year per cell) over ``extent`` (lon0, lon1, lat0, lat1)."""
    from scipy.ndimage import gaussian_filter

    lon_edges = np.arange(extent[0], extent[1] + resolution, resolution)
    lat_edges = np.arange(extent[2], extent[3] + resolution, resolution)
    per_model = {}
    for key, pts in points.items():
        if key[0] != tracker or key[2] != period:
            continue
        h = np.histogram2d(pts["lat"], pts["lon"], bins=[lat_edges, lon_edges])[0] / (4 * max(int(pts["years"]), 1))
        per_model.setdefault(key[1], []).append(h)
    mean = np.mean([np.mean(v, axis=0) for v in per_model.values()], axis=0)
    return xr.DataArray(gaussian_filter(mean, sigma), dims=("lat", "lon"),
                        coords={"lat": (lat_edges[:-1] + lat_edges[1:]) / 2, "lon": (lon_edges[:-1] + lon_edges[1:]) / 2})


def plot_site_density(points, site_lon, site_lat, tracker="TRACK", extent=None, site_label="site", figsize=(16, 4.8)):
    """Multi-model mean track density 1980–2010 with 2020–2050 contours (left) and the reverse (right), as the
    historical-vs-shifted figure of the IBTrACS notebook."""
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature

    extent = extent or ((100, 200, -5, 50) if site_lat >= 0 else (130, 240, -45, 5))
    present = site_density(points, tracker, "present", extent)
    future = site_density(points, tracker, "future", extent)
    vmax = float(max(present.max(), future.max()))
    levels = np.array([0.1, 0.4, 0.7]) * vmax
    fig, axes = plt.subplots(1, 2, figsize=figsize, subplot_kw={"projection": ccrs.PlateCarree(central_longitude=180)})
    for ax, (field, cmap, other, ocol, title, label) in zip(axes, (
            (present, "Blues", future, "darkred", "1980–2010 density + 2020–2050 contours", "1980–2010 TC days per year"),
            (future, "Reds", present, "navy", "2020–2050 density + 1980–2010 contours", "2020–2050 TC days per year"))):
        mesh = ax.pcolormesh(field.lon, field.lat, field.values, cmap=cmap, vmin=0, vmax=vmax, transform=ccrs.PlateCarree())
        ax.contour(other.lon, other.lat, other.values, levels=levels, colors=ocol, linewidths=1.6, transform=ccrs.PlateCarree())
        ax.contour(field.lon, field.lat, field.values, levels=levels, colors="black", linewidths=0.6, linestyles="--",
                   transform=ccrs.PlateCarree())
        ax.plot(site_lon % 360, site_lat, "*", color="gold", markeredgecolor="black", markersize=16, transform=ccrs.PlateCarree(), zorder=5)
        ax.set_extent(extent, crs=ccrs.PlateCarree())
        ax.add_feature(cfeature.LAND, color="silver", zorder=2)
        ax.coastlines(linewidth=0.4, zorder=3)
        gl = ax.gridlines(draw_labels=True, linewidth=0.4, color="gray", alpha=0.5, linestyle="--")
        gl.top_labels = gl.right_labels = False
        ax.set_title(title, fontsize=12)
        fig.colorbar(mesh, ax=ax, orientation="horizontal", fraction=0.05, pad=0.08, label=label)
    fig.suptitle(f"TC track density, CMIP6-HighResMIP multi-model mean ({TRACKER_LABEL[tracker]}); star: {site_label}; "
                 "contours at 10, 40 and 70 % of the maximum", fontsize=13, fontweight="bold")
    fig.subplots_adjust(top=0.9, wspace=0.08)
    return fig


def plot_density_change(density, tracker="TRACK", figsize=(10, 6)):
    """Projected change in TC track density (2020–2050 minus 1980–2010, multi-model mean, TC days per year per
    2.5° cell) with the four Pacific subregions outlined."""
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    from matplotlib import patheffects
    from matplotlib.patches import Rectangle

    d = density.sel(tracker=tracker)
    valid = [m for m in d.model.values if np.isfinite(d.sel(model=m, period="future").values).any()]
    d = d.sel(model=valid).mean("model")
    change = d.sel(period="future", shift=0) - d.sel(period="present", shift=0)
    lim = float(np.nanpercentile(np.abs(change.values), 99))
    fig, ax = plt.subplots(figsize=figsize, subplot_kw={"projection": ccrs.PlateCarree(central_longitude=180)})
    mesh = ax.pcolormesh(change.lon, change.lat, change.values, cmap="RdBu_r", vmin=-lim, vmax=lim, transform=ccrs.PlateCarree())
    ax.set_extent((95, 265, -45, 45), crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.LAND, facecolor="lightgrey", zorder=2)
    ax.coastlines(linewidth=0.4, zorder=3)
    for region, (x0, x1, y0, y1) in REGION_BOUNDS.items():
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, edgecolor=REGION_COLORS[region], linewidth=1.8,
                               transform=ccrs.PlateCarree(), zorder=4))
        ax.text(x0 + 1, y1 - 1 if y1 > 0 else y0 + 1, region, transform=ccrs.PlateCarree(), color=REGION_COLORS[region],
                fontsize=10, fontweight="bold", ha="left", va="top" if y1 > 0 else "bottom", zorder=5,
                path_effects=[patheffects.withStroke(linewidth=2.5, foreground="white")])
    gl = ax.gridlines(draw_labels=True, linewidth=0.4, color="gray", alpha=0.5, linestyle="--")
    gl.top_labels = gl.right_labels = False
    fig.colorbar(mesh, ax=ax, orientation="horizontal", fraction=0.05, pad=0.08, label="Δ TC days per year per 2.5° cell")
    ax.set_title(f"Projected change in TC track density, 2020–2050 (SSP5-8.5) minus 1980–2010\n"
                 f"CMIP6-HighResMIP multi-model mean ({TRACKER_LABEL[tracker]})", fontsize=13, fontweight="bold")
    return fig
