"""Data download and quality-control helpers shared across PICCM notebooks.

This module provides access to:

- **GHCN-Daily** station catalogs and per-station precipitation/temperature
  time series, used by the rainfall and air-temperature notebooks.
- **NOAA ONI** (Oceanic Niño Index) for ENSO analysis, used by rainfall,
  air-temperature, and sea-level notebooks alike.
- **Time-completeness filtering** applied during ``00_site_setup.ipynb``.
- **UHSLC Fast Delivery tide-gauge downloads**, used by the sea-level notebooks.
- **IPCC AR6 sea-level projections** (Zenodo 6382554), extracted member by member
  from the remote archive, used by the regional sea-level projection notebook.

Rainfall notebooks use the ``PRCP`` variable (daily precipitation in mm after
the GHCN tenths scaling factor is applied).
"""

import io
from io import BytesIO, StringIO
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import xarray as xr

GHCND_ACCESS_URL = (
    "https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/"
)
ONI_URL = "https://psl.noaa.gov/data/correlation/oni.data"


class GHCN:
    """Helpers for the GHCN-Daily station archive (NOAA NCEI).

    GHCN-Daily is the primary data source for historical rainfall indicators in
    this repository. Station metadata, country codes and per-station CSV files
    are fetched directly from NOAA servers.

    Typical workflow (``00_site_setup.ipynb``)::

        df_countries = GHCN.download_country_codes()
        df_stations = GHCN.download_stations_info()
        df_inventory = GHCN.download_station_inventory()
        records, ids = GHCN.extract_dict_data_var(GHCND_ACCESS_URL, "PRCP", df_target)
    """

    @staticmethod
    def download_country_codes():
        """Download the GHCN country-code table.

        Returns
        -------
        pandas.DataFrame
            Two columns: ``Code`` (2-letter GHCN country code) and ``Country``
            (official country name as used in the GHCN catalog).
        """
        url = "https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-countries.txt"
        country_codes = requests.get(url).text.split("\n")
        codes = [line.split(" ")[0] for line in country_codes]
        countries = [" ".join(line.split(" ")[1:]).strip() for line in country_codes]
        return pd.DataFrame({"Code": codes, "Country": countries})

    @staticmethod
    def get_country_code(country):
        """Look up the GHCN country code for an exact country name.

        Parameters
        ----------
        country : str
            Country name exactly as it appears in the GHCN catalog
            (e.g. ``"Palau"``).

        Returns
        -------
        pandas.DataFrame
            Zero or one rows matching ``Country == country``.
        """
        df = GHCN.download_country_codes()
        return df.loc[df["Country"] == country]

    @staticmethod
    def download_stations_info():
        """Download GHCN-Daily station metadata.

        Returns
        -------
        pandas.DataFrame
            Columns: ``ID``, ``Latitude``, ``Longitude``, ``Elevation``, ``Name``.
            The first two characters of ``ID`` are the GHCN country code.
        """
        url = "https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-stations.txt"
        processed_data = []
        for line in requests.get(url).text.split("\n"):
            if not line:
                continue
            parts = line.split()
            processed_data.append([
                parts[0],
                float(parts[1]),
                float(parts[2]),
                float(parts[3]),
                " ".join(parts[4:]),
            ])
        return pd.DataFrame(
            processed_data,
            columns=["ID", "Latitude", "Longitude", "Elevation", "Name"],
        )

    @staticmethod
    def download_station_inventory():
        """Download the GHCN-Daily station-element inventory.

        The inventory lists, for each station and meteorological element, the
        first and last year with observations.

        Returns
        -------
        pandas.DataFrame
            Columns: ``ID``, ``Latitude``, ``Longitude``, ``ELEMENT``,
            ``FIRSTYEAR``, ``LASTYEAR``.
        """
        url = "https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-inventory.txt"
        rows = []
        for line in requests.get(url).text.splitlines():
            if not line.strip():
                continue
            rows.append(
                {
                    "ID": line[0:11].strip(),
                    "Latitude": float(line[12:20].strip()),
                    "Longitude": float(line[21:29].strip()),
                    "ELEMENT": line[31:35].strip(),
                    "FIRSTYEAR": int(line[36:40].strip()),
                    "LASTYEAR": int(line[41:45].strip()),
                }
            )
        return pd.DataFrame(rows)

    @staticmethod
    def summarize_record_years(inventory_df, station_ids, elements=("PRCP",)):
        """Summarise the combined record span per station for given elements.

        Parameters
        ----------
        inventory_df : pandas.DataFrame
            Output of :meth:`download_station_inventory`.
        station_ids : array-like
            GHCN station IDs to summarise.
        elements : tuple of str, optional
            GHCN element codes to include. Defaults to ``("PRCP",)``.

        Returns
        -------
        pandas.DataFrame
            One row per station with ``record_start``, ``record_end``,
            ``record_years`` (e.g. ``"1951-2024"``) and ``elements``.
        """
        station_ids = list(station_ids)
        subset = inventory_df[
            inventory_df["ID"].isin(station_ids) & inventory_df["ELEMENT"].isin(elements)
        ].copy()
        base = pd.DataFrame({"ID": station_ids})
        if subset.empty:
            return base.assign(
                record_start=pd.NA,
                record_end=pd.NA,
                record_years=pd.NA,
                elements=pd.NA,
            )

        summary = (
            subset.groupby("ID", as_index=False)
            .agg(record_start=("FIRSTYEAR", "min"), record_end=("LASTYEAR", "max"))
        )
        element_lists = (
            subset.groupby("ID")["ELEMENT"]
            .apply(lambda values: ", ".join(sorted(set(values))))
            .reset_index(name="elements")
        )
        summary = base.merge(summary, on="ID", how="left").merge(element_lists, on="ID", how="left")
        summary["record_years"] = summary.apply(
            lambda row: (
                f"{int(row['record_start'])}-{int(row['record_end'])}"
                if pd.notna(row["record_start"]) and pd.notna(row["record_end"])
                else pd.NA
            ),
            axis=1,
        )
        return summary

    @staticmethod
    def extract_dict_data_var(GHCND_dir, var, df_country_stations):
        """Download per-station daily time series for a single GHCN variable.

        For each station in ``df_country_stations``, downloads the GHCN-Daily
        CSV from ``GHCND_dir`` and packages the result for plotting helpers in
        ``indicators_setup``.

        Parameters
        ----------
        GHCND_dir : str
            Base URL of the GHCN-Daily access directory (typically
            :data:`GHCND_ACCESS_URL`).
        var : str
            GHCN element code (e.g. ``"PRCP"``).
        df_country_stations : pandas.DataFrame
            Station metadata table with an ``ID`` column.

        Returns
        -------
        records : list of dict
            Each dict has keys ``data``, ``var``, ``ax``, ``label``.
            ``TMIN``, ``TMAX`` and ``PRCP`` are divided by 10 (GHCN stores
            them in tenths of °C or mm).
        station_ids : list of str
            Station IDs for which data were successfully retrieved.
        """
        results = []
        station_ids = []
        for i in range(len(df_country_stations)):
            station = df_country_stations.iloc[i]
            url_download = GHCND_dir + station["ID"] + ".csv"
            df = pd.read_csv(url_download, na_values=["-9999"])
            df.index = pd.to_datetime(df["DATE"])

            if var not in df.columns:
                continue

            station_ids.append(station["ID"])
            if var in ("TMIN", "TMAX", "TAVG", "PRCP"):
                df[var] = df[var] / 10

            results.append({
                "data": df[[var]],
                "var": var,
                "ax": 1,
                "label": f"Station {station['ID']}",
            })

        return results, station_ids


def download_ibtracs(url, basin=None):
    """Download the IBTrACS tropical-cyclone track archive.

    Used by the tropical-cyclone notebooks (``a_tropical_cyclones.ipynb``,
    ``b_severe_tropical_cyclones.ipynb``) to fetch the full IBTrACS NetCDF
    file, optionally filtered to a single basin.

    Parameters
    ----------
    url : str
        URL of the IBTrACS NetCDF file (``IBTrACS.ALL.v04r01.nc`` or a
        basin-specific subset).
    basin : str, optional
        Two-letter basin code (e.g. ``"WP"`` for West Pacific) used to
        filter storms by their genesis basin. If ``None``, all basins are
        returned.

    Returns
    -------
    xarray.Dataset
        Dataset with the ``wmo_wind``, ``wmo_pres`` and ``name`` variables.

    Raises
    ------
    None
        Download failures are printed as an error message rather than
        raised.
    """
    response = requests.get(url)
    if response.status_code == 200:
        tcs = xr.open_dataset(BytesIO(response.content))
    else:
        print(f"Error while downloading file: {response.status_code}")

    if basin:
        tcs = tcs.isel(storm=np.where(tcs.isel(date_time=0).basin.values.astype(str) == basin)[0])

    return tcs[["wmo_wind", "wmo_pres", "name"]]


def download_oni_index(url=ONI_URL):
    """Download the Oceanic Niño Index (ONI) from NOAA PSL.

    Parameters
    ----------
    url : str, optional
        URL of the ONI text file. Defaults to :data:`ONI_URL`.

    Returns
    -------
    pandas.DataFrame
        Single column ``ONI`` with a monthly :class:`~pandas.DatetimeIndex`.
        Missing values encoded as ``-99.9`` in the source file are replaced
        with NaN.
    """
    content = requests.get(url).content.decode()
    oni = pd.read_csv(StringIO(content), skiprows=1, sep=r"\s+", header=None, index_col=0)[1:-8]
    oni = oni.apply(pd.to_numeric, errors="coerce")

    df = pd.DataFrame(oni.values.reshape(-1), columns=["ONI"])
    df.index = pd.date_range(start=f"{oni.index[0]}-01-01", periods=len(df), freq="MS")
    df.replace(-99.9, np.nan, inplace=True)
    return df


def download_ERDDAP_data(base_url, dataset_id, date_ini, date_end, lon_range, lat_range):
    """Download one gridded ERDDAP variable as a tidy DataFrame."""
    url = (
        f"{base_url}?{dataset_id}"
        f"%5B({date_ini}):1:({date_end})%5D"
        f"%5B({lat_range[0]}):1:({lat_range[1]})%5D"
        f"%5B({lon_range[0]}):1:({lon_range[1]})%5D"
    )
    data = pd.read_csv(url).iloc[1:].reset_index(drop=True)
    data["time"] = pd.to_datetime(data["time"])
    for variable in ["latitude", "longitude", dataset_id]:
        data[variable] = pd.to_numeric(data[variable], errors="coerce")
    return data


UHSLC_FAST_URL = "https://uhslc.soest.hawaii.edu/data/netcdf/fast/{resolution}/{prefix}{uhslc_id:03d}.nc"


def download_uhslc_data(data_dir, uhslc_id, resolution="daily", force_download=False, timeout=120):
    """Download (or reuse) one UHSLC Fast Delivery tide-gauge NetCDF file.

    Files are cached as ``d<id>.nc`` (daily) or ``h<id>.nc`` (hourly),
    zero-padded to three digits, inside ``data_dir`` (for example
    ``data/sea_level/d007.nc`` for Malakal, Palau). Fast Delivery data are
    released within 1-2 months of collection and receive level-1 quality
    control only.

    Parameters
    ----------
    data_dir : str or pathlib.Path
        Cache directory, normally ``data/sea_level``.
    uhslc_id : int
        UHSLC station identifier (not the NetCDF ``record_id``).
    resolution : {"daily", "hourly"}, optional
        Product to retrieve. Defaults to ``"daily"``.
    force_download : bool, optional
        Re-download even when a cached copy exists.
    timeout : int, optional
        HTTP timeout in seconds.

    Returns
    -------
    xarray.Dataset
        Station dataset with ``sea_level`` in mm relative to the station
        datum and dimensions ``(record_id, time)``. The single ``record_id``
        encodes station and version and differs from ``uhslc_id``.
    """
    if resolution not in ("daily", "hourly"):
        raise ValueError('resolution must be "daily" or "hourly"')

    prefix = "d" if resolution == "daily" else "h"
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    output_path = data_dir / f"{prefix}{int(uhslc_id):03d}.nc"

    if force_download or not output_path.exists():
        url = UHSLC_FAST_URL.format(resolution=resolution, prefix=prefix, uhslc_id=int(uhslc_id))
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        temporary_path = output_path.with_suffix(".nc.part")
        temporary_path.write_bytes(response.content)
        temporary_path.replace(output_path)

    with xr.open_dataset(output_path) as dataset:
        return dataset.load()


def filter_by_time_completeness(
    df,
    time_col="time",
    month_threshold=0.75,
    year_threshold=0.75,
):
    """Filter daily data by month and year completeness thresholds.

    Applied once in ``00_site_setup.ipynb`` before caching the station pickle.
    A month is retained when at least ``month_threshold`` of its calendar days
    have observations. A year is retained when at least ``year_threshold`` of
    its months pass the month-level test.

    Parameters
    ----------
    df : pandas.DataFrame
        Daily data with a DatetimeIndex (column ``PRCP``).
    time_col : str, optional
        Reserved for API compatibility; the index is used directly.
    month_threshold : float, optional
        Minimum fraction of days required to keep a month (default 0.75).
    year_threshold : float, optional
        Minimum fraction of valid months required to keep a year (default 0.75).

    Returns
    -------
    df_filtered : pandas.DataFrame
        Filtered daily DataFrame (helper columns removed).
    removed_months : pandas.DataFrame
        Months dropped by the filter, with a ``month_completeness`` column.
        Index: (year, month).
    removed_years : pandas.Series
        Years dropped by the filter, indexed by year.
    """
    df = df.copy()
    df.index = pd.to_datetime(df.index)
    df["year"] = df.index.year
    df["month"] = df.index.month
    df["day"] = df.index.day

    days_present = df.groupby(["year", "month"])["day"].nunique().rename("days_present")
    days_in_month = (
        days_present.reset_index()
        .assign(
            days_in_month=lambda x: pd.to_datetime(
                dict(year=x.year, month=x.month, day=1)
            ).dt.days_in_month
        )
        .set_index(["year", "month"])["days_in_month"]
    )
    month_completeness = days_present / days_in_month
    valid_months = month_completeness >= month_threshold
    removed_months = month_completeness[~valid_months].to_frame(name="month_completeness")

    valid_months_per_year = valid_months.groupby("year").sum()
    total_months_per_year = df.groupby("year")["month"].nunique()
    year_completeness = valid_months_per_year / total_months_per_year
    valid_years = year_completeness >= year_threshold
    removed_years = year_completeness[~valid_years]

    df_filtered = df[df.set_index(["year", "month"]).index.isin(valid_months[valid_months].index)]
    df_filtered = df_filtered[df_filtered["year"].isin(valid_years[valid_years].index)]
    df_filtered = df_filtered.drop(columns=["year", "month", "day"])

    return df_filtered, removed_months, removed_years


# ---------------------------------------------------------------------------
# IPCC AR6 sea-level projections (Garner et al., 2021; Zenodo 6382554)
# ---------------------------------------------------------------------------

AR6_SL_ZENODO_URL = "https://zenodo.org/records/6382554/files/{archive}.zip"
AR6_SL_ARCHIVES = {False: "ar6-regional_novlm-confidence", True: "ar6-regional-confidence"}


class _HttpRangeFile(io.RawIOBase):
    """Read-only, seekable view of a remote file through HTTP range requests.

    Lets :class:`zipfile.ZipFile` read the central directory and single members
    of a multi-GB archive without downloading the whole file.
    """

    def __init__(self, url, timeout=120):
        self.url, self.timeout = url, timeout
        self.session = requests.Session()
        probe = self.session.get(url, headers={"Range": "bytes=0-0"}, timeout=timeout)
        probe.raise_for_status()
        if probe.status_code != 206 or "Content-Range" not in probe.headers:
            raise OSError(f"Server does not support range requests: {url}")
        self.size = int(probe.headers["Content-Range"].rsplit("/", 1)[1])
        self.pos = 0

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=io.SEEK_SET):
        base = {io.SEEK_SET: 0, io.SEEK_CUR: self.pos, io.SEEK_END: self.size}[whence]
        self.pos = base + offset
        return self.pos

    def readinto(self, buffer):
        n = min(len(buffer), self.size - self.pos)
        if n <= 0:
            return 0
        headers = {"Range": f"bytes={self.pos}-{self.pos + n - 1}"}
        r = self.session.get(self.url, headers=headers, timeout=self.timeout)
        r.raise_for_status()
        if r.status_code != 206:
            raise OSError("Expected a partial (206) response to a range request.")
        data = r.content
        buffer[: len(data)] = data
        self.pos += len(data)
        return len(data)


def ar6_sea_level_file(out_dir, scenario, kind="values", confidence="medium", vlm=False):
    """Local path of one AR6 ``total`` sea-level projection file."""
    sub = "with_vlm" if vlm else "novlm"
    return Path(out_dir) / sub / f"total_{scenario}_{confidence}_confidence_{kind}.nc"


def download_ar6_sea_level_projections(
    out_dir,
    scenarios=("ssp126", "ssp245", "ssp370", "ssp585"),
    kinds=("values", "rates"),
    confidence="medium",
    vlm=False,
    force_download=False,
    timeout=120,
):
    """Download IPCC AR6 regional sea-level projections from Zenodo record 6382554.

    Only the ``total_<scenario>_<confidence>_confidence_<kind>.nc`` members are
    extracted from the ``ar6-regional_novlm-confidence.zip`` archive (or
    ``ar6-regional-confidence.zip`` when ``vlm=True``) through HTTP range
    requests, so each scenario costs ~75 MB (values) + ~35 MB (rates) instead
    of the 8.7 GB archive. Files that already exist are reused unless
    ``force_download`` is True.

    Each file holds ``sea_level_change`` (mm, relative to 1995–2014) or
    ``sea_level_change_rate`` (mm/yr) on (quantiles, years, locations), where
    the locations are a global 1° grid plus the PSMSL tide gauges.

    Returns a dict ``{(scenario, kind): Path}``.
    """
    import shutil
    import zipfile

    paths = {(s, k): ar6_sea_level_file(out_dir, s, k, confidence, vlm) for s in scenarios for k in kinds}
    missing = {key: path for key, path in paths.items() if force_download or not path.is_file()}
    if not missing:
        return paths

    archive = AR6_SL_ARCHIVES[bool(vlm)]
    url = AR6_SL_ZENODO_URL.format(archive=archive)
    print(f"Opening {archive}.zip on Zenodo (range requests, only the needed members are transferred)")
    remote = io.BufferedReader(_HttpRangeFile(url, timeout=timeout), buffer_size=1 << 22)
    with zipfile.ZipFile(remote) as zf:
        members = {Path(name).name: name for name in zf.namelist()}
        for (scenario, kind), path in missing.items():
            member = members.get(path.name)
            if member is None:
                available = sorted(n for n in members if n.startswith("total_") and f"_{confidence}_" in n)
                raise FileNotFoundError(f"{path.name} is not in {archive}.zip. Available: {available}")
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".part")
            size_mb = zf.getinfo(member).file_size / 1e6
            print(f"  downloading {path.name} ({size_mb:.0f} MB)")
            with zf.open(member) as src, open(tmp, "wb") as dst:  # zipfile verifies the CRC
                shutil.copyfileobj(src, dst, 1 << 24)
            tmp.replace(path)
    return paths
