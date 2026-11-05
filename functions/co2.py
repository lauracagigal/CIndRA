"""Atmospheric CO2: NOAA Mauna Loa observations and CMIP6 SSP concentration pathways.

Data
----
* NOAA Global Monitoring Laboratory, Mauna Loa Observatory (Hawaiʻi): monthly means (with the
  seasonal cycle removed in the ``deseasonalized`` column), annual means and annual growth rates
  since 1958. Dr. Xin Lan, NOAA/GML (gml.noaa.gov/ccgg/trends/) and Dr. Ralph Keeling, Scripps
  Institution of Oceanography (scrippsco2.ucsd.edu/).
* CMIP6 greenhouse-gas concentrations (Meinshausen et al., 2020, GMD 13, 3571–3605): global-mean
  annual CO2 for the historical period (to 2014) and SSP1-1.9 … SSP5-8.5 (2015–2100), read from the
  RCMIP v5.1.0 concentration file. These are *global* means; Mauna Loa (19.5°N) reads ~1–2 ppm higher.
"""

from __future__ import annotations

import io
from pathlib import Path
from urllib.request import urlopen

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

NOAA_URLS = {
    "monthly": "https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_mlo.txt",
    "annual": "https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_annmean_mlo.txt",
    "growth": "https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_gr_mlo.txt",
}
RCMIP_URL = ("https://rcmip-protocols-au.s3-ap-southeast-2.amazonaws.com/v5.1.0/"
             "rcmip-concentrations-annual-means-v5-1-0.csv")
SSPS = ["ssp119", "ssp126", "ssp245", "ssp370", "ssp585"]
SSP_LABELS = {"ssp119": "SSP1-1.9", "ssp126": "SSP1-2.6", "ssp245": "SSP2-4.5",
              "ssp370": "SSP3-7.0", "ssp585": "SSP5-8.5"}
SSP_COLORS = {"ssp119": "#00a9cf", "ssp126": "#003466", "ssp245": "#f69320",
              "ssp370": "#df0000", "ssp585": "#980002"}  # IPCC AR6 scenario colours
PREINDUSTRIAL_PPM = 278.0  # 1750 (IPCC AR6)


# ───────────────────────────── download / load ─────────────────────────────

def _fetch(url: str, timeout: int = 120) -> bytes:
    with urlopen(url, timeout=timeout) as r:
        return r.read()


def download_noaa_co2(data_dir: str | Path, force: bool = False) -> dict[str, Path]:
    """Download the NOAA Mauna Loa text files into ``data_dir`` (skipped when cached)."""
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for kind, url in NOAA_URLS.items():
        path = data_dir / Path(url).name
        if force or not path.is_file():
            path.write_bytes(_fetch(url))
            print(f"Downloaded {url}")
        paths[kind] = path
    return paths


def _read_noaa(path: Path, names: list[str]) -> pd.DataFrame:
    df = pd.read_csv(path, comment="#", sep=r"\s+", header=None, engine="python")
    df = df.iloc[:, :len(names)]
    df.columns = names
    return df


def load_noaa_co2(paths: dict[str, Path]) -> dict[str, pd.DataFrame]:
    """Parse the NOAA files; missing monthly values (-99.99) become NaN."""
    monthly = _read_noaa(paths["monthly"], ["year", "month", "decimal_date", "average", "deseasonalized",
                                            "ndays", "sdev", "unc"])
    monthly = monthly.replace([-99.99, -9.99], np.nan)
    monthly["time"] = pd.to_datetime(dict(year=monthly.year, month=monthly.month, day=15))
    annual = _read_noaa(paths["annual"], ["year", "mean", "unc"])
    growth = _read_noaa(paths["growth"], ["year", "growth", "unc"])
    return {"monthly": monthly, "annual": annual, "growth": growth}


def download_ssp_co2(data_dir: str | Path, force: bool = False) -> Path:
    """Global-mean CMIP6 CO2 (historical + SSPs) as a small CSV: year × scenario, ppm.

    The 21 MB RCMIP concentration file is read in memory and only the CO2 rows are kept.
    """
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / "co2_cmip6_concentrations_meinshausen2020.csv"
    if path.is_file() and not force:
        return path
    raw = pd.read_csv(io.BytesIO(_fetch(RCMIP_URL, timeout=300)))
    co2 = raw[(raw["Variable"] == "Atmospheric Concentrations|CO2") & (raw["Region"] == "World")
              & (raw["Mip_Era"] == "CMIP6") & raw["Scenario"].isin(["historical", *SSPS])]
    years = [c for c in co2.columns if c.isdigit()]
    table = co2.set_index("Scenario")[years].T
    table.index = table.index.astype(int)
    table.index.name = "year"
    table = table.loc[1850:2100, ["historical", *SSPS]]
    table.to_csv(path, float_format="%.3f")
    print(f"Saved CMIP6 CO2 concentrations to {path}")
    return path


def load_ssp_co2(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path, index_col="year")


# ───────────────────────────── statistics ─────────────────────────────

def decadal_growth(growth: pd.DataFrame) -> pd.DataFrame:
    """Mean annual growth rate (ppm/yr) per complete calendar decade (and the running one)."""
    g = growth.copy()
    g["decade"] = (g["year"] // 10) * 10
    out = g.groupby("decade").agg(years=("year", "count"), growth=("growth", "mean")).reset_index()
    out["Decade"] = out["decade"].astype(str) + "s"
    out.loc[out["years"] < 10, "Decade"] += " (" + out["years"].astype(str) + " yr)"
    return out[["Decade", "growth", "years"]].rename(columns={"growth": "Mean growth rate (ppm/yr)", "years": "Years"})


def co2_summary_table(noaa: dict[str, pd.DataFrame], window: int = 10) -> pd.DataFrame:
    """Metric | Value table of the Mauna Loa record (layout of functions/summary_tables.py)."""
    from summary_tables import annual_series_summary, combine_sections

    annual = noaa["annual"].set_index("year")["mean"]
    monthly, growth = noaa["monthly"], noaa["growth"]
    y0, y1 = int(annual.index.min()), int(annual.index.max())
    rec = monthly.loc[monthly["average"].idxmax()]
    g_all = growth["growth"].mean()
    g_last = growth[growth["year"] > y1 - window]["growth"].mean()
    g_first = growth[growth["year"] < growth["year"].min() + window]["growth"].mean()
    gmax = growth.loc[growth["growth"].idxmax()]
    section = annual_series_summary(
        annual, "CO2 concentration", "ppm", window=window,
        title="ATMOSPHERIC CO2 – NOAA Mauna Loa Observatory",
        extra_rows=[
            (f"Annual mean in {y0} (ppm)", float(annual.loc[y0])),
            (f"Annual mean in {y1} (ppm)", float(annual.loc[y1])),
            (f"Increase {y0}–{y1} (ppm)", float(annual.loc[y1] - annual.loc[y0])),
            (f"Increase above pre-industrial ({PREINDUSTRIAL_PPM:.0f} ppm) in {y1} (%)",
             100 * (float(annual.loc[y1]) / PREINDUSTRIAL_PPM - 1)),
            (f"Highest monthly mean ({int(rec.year)}-{int(rec.month):02d}) (ppm)", float(rec.average)),
            (f"Mean growth rate {int(growth.year.min())}–{int(growth.year.max())} (ppm/yr)", float(g_all)),
            (f"Mean growth rate, first {window} years (ppm/yr)", float(g_first)),
            (f"Mean growth rate, last {window} years (ppm/yr)", float(g_last)),
            (f"Largest annual growth ({int(gmax.year)}) (ppm/yr)", float(gmax.growth)),
        ],
    )
    return combine_sections([section])


def ssp_table(ssp: pd.DataFrame, years=(2030, 2050, 2070, 2100)) -> pd.DataFrame:
    """CO2 concentration (ppm) of each SSP at selected years."""
    t = ssp.loc[list(years), SSPS].T
    t.index = [SSP_LABELS[s] for s in t.index]
    t.index.name = "Scenario"
    t.columns = [str(c) for c in t.columns]
    return t.round(0).astype(int).reset_index()


# ───────────────────────────── figures ─────────────────────────────

def _style(ax):
    ax.grid(color="0.88", linewidth=0.6)
    ax.spines[["top", "right"]].set_visible(False)


def plot_keeling_curve(noaa: dict[str, pd.DataFrame]):
    """Monthly mean CO2 (red) and the de-seasonalised series (black)."""
    m = noaa["monthly"]
    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.plot(m["time"], m["average"], color="#d62728", lw=1.0, label="Monthly mean")
    ax.plot(m["time"], m["deseasonalized"], color="black", lw=1.6, label="Seasonal cycle removed")
    last = m.dropna(subset=["average"]).iloc[-1]
    ax.set_title(f"Atmospheric CO$_2$ at Mauna Loa Observatory ({int(m.year.min())}–{int(last.year)})")
    ax.set_ylabel("CO$_2$ mole fraction (ppm)")
    ax.text(0.99, 0.09, f"Latest monthly mean: {last.average:.1f} ppm ({pd.Timestamp(last.time):%b %Y})",
            transform=ax.transAxes, ha="right", fontsize=11)
    ax.legend(frameon=False, loc="upper left")
    ax.text(0.99, 0.02, "Data: NOAA GML / Scripps", transform=ax.transAxes, ha="right", fontsize=9, color="0.4")
    _style(ax)
    fig.tight_layout()
    return fig, ax


def plot_growth_rate(noaa: dict[str, pd.DataFrame]):
    """Annual growth rate (bars) and decadal means (red lines)."""
    g = noaa["growth"]
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.bar(g["year"], g["growth"], color="#2b9fc9", width=0.8, label="Annual growth rate")
    g10 = g.assign(decade=(g.year // 10) * 10).groupby("decade")["growth"].agg(["mean", "count"])
    g10 = g10.loc[g10["count"] >= 3, "mean"]  # skip decades with fewer than 3 years (e.g. 1959)
    for i, (dec, val) in enumerate(g10.items()):
        x1 = min(dec + 9, g.year.max())
        ax.hlines(val, dec - 0.4, x1 + 0.4, color="#d62728", lw=3, label="Decadal mean" if i == 0 else None)
        ax.text((dec + x1) / 2, val + 0.08, f"{val:.2f}", ha="center", fontsize=9, color="#d62728")
    ax.set_title("Annual growth rate of CO$_2$ at Mauna Loa")
    ax.set_ylabel("ppm per year")
    ax.set_xlim(g.year.min() - 1, g.year.max() + 1)
    ax.legend(frameon=False, loc="upper left")
    _style(ax)
    fig.tight_layout()
    return fig, ax


def plot_observed_and_ssps(noaa: dict[str, pd.DataFrame], ssp: pd.DataFrame, start: int = 1950):
    """Mauna Loa annual means, CMIP6 historical global mean and the SSP pathways to 2100."""
    a = noaa["annual"]
    fig, ax = plt.subplots(figsize=(11, 6))
    hist = ssp["historical"].loc[start:2014]
    ax.plot(hist.index, hist.values, color="0.45", lw=1.4, ls="--", label="CMIP6 historical (global mean)")
    for s in SSPS:
        ser = ssp[s].loc[2014:2100].copy()
        ser.loc[2014] = ssp["historical"].loc[2014]
        ax.plot(ser.index, ser.values, color=SSP_COLORS[s], lw=2, label=SSP_LABELS[s])
        ax.text(2101.5, ser.loc[2100], f"{SSP_LABELS[s]}  {ser.loc[2100]:.0f}", va="center",
                fontsize=9.5, color=SSP_COLORS[s])
    ax.plot(a["year"], a["mean"], color="black", lw=2.2, label="Observed – Mauna Loa (annual mean)")
    ax.axhline(PREINDUSTRIAL_PPM, color="0.6", lw=0.8, ls=":")
    ax.text(start + 1, PREINDUSTRIAL_PPM + 12, f"Pre-industrial ({PREINDUSTRIAL_PPM:.0f} ppm)", fontsize=9, color="0.4")
    ax.set_xlim(start, 2100)
    ax.set_ylim(250, None)
    ax.set_ylabel("CO$_2$ concentration (ppm)")
    ax.set_title("Observed and projected atmospheric CO$_2$")
    ax.legend(frameon=False, loc="upper left", fontsize=10)
    ax.text(0.99, 0.02, "Observed: NOAA GML Mauna Loa.  Scenarios: CMIP6 (Meinshausen et al., 2020)",
            transform=ax.transAxes, ha="right", fontsize=8.5, color="0.4")
    _style(ax)
    fig.subplots_adjust(right=0.86)
    return fig, ax
