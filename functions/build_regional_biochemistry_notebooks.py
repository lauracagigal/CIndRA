"""Build the five Regional/biochemistry notebooks with one consistent layout."""

from pathlib import Path
import textwrap

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notebooks" / "historical" / "Regional" / "biochemistry"

VARIABLES = {
    "a_oceanic_pH.ipynb": {
        "title": "Regional Pacific ocean acidification: pH",
        "variable": "ph",
        "label": "Surface pH",
        "units": "pH units",
        "cmap": "magma_r",
        "source_file": "data_phyc_o2_ph.nc",
        "source": "Copernicus Marine biogeochemical reanalysis",
        "url": "https://data.marine.copernicus.eu/product/GLOBAL_MULTIYEAR_BGC_001_029/description",
    },
    "b_chlorophyll.ipynb": {
        "title": "Regional Pacific chlorophyll-a",
        "variable": "chl",
        "label": "Chlorophyll-a",
        "units": "mg m⁻³",
        "cmap": "YlGn",
        "source_file": "griddap_chlor_a.nc",
        "source": "Copernicus Marine biogeochemical reanalysis",
        "url": "https://data.marine.copernicus.eu/product/GLOBAL_MULTIYEAR_BGC_001_029/description",
    },
    "c_phytoplankton.ipynb": {
        "title": "Regional Pacific phytoplankton size",
        "variable": "MD50",
        "label": "Median phytoplankton size",
        "units": "µm",
        "cmap": "viridis",
        "source_file": "griddap_MD50.nc",
        "source": "NOAA PIFSC experimental MD50 product",
        "url": "https://oceanwatch.pifsc.noaa.gov/erddap/info/md50_exp_2025/index.html",
    },
    "c2_phytoplankton.ipynb": {
        "title": "Regional Pacific phytoplankton biomass",
        "variable": "phyc",
        "label": "Surface phytoplankton biomass",
        "units": "mmol C m⁻³",
        "cmap": "YlGnBu",
        "source_file": "data_phyc_o2_ph.nc",
        "source": "Copernicus Marine biogeochemical reanalysis",
        "url": "https://data.marine.copernicus.eu/product/GLOBAL_MULTIYEAR_BGC_001_029/description",
    },
    "d_dissolved_o2.ipynb": {
        "title": "Regional Pacific dissolved oxygen",
        "variable": "o2",
        "label": "Dissolved oxygen",
        "units": "µmol L⁻¹",
        "cmap": "cividis",
        "source_file": "data_phyc_o2_ph.nc",
        "source": "Copernicus Marine biogeochemical reanalysis",
        "url": "https://data.marine.copernicus.eu/product/GLOBAL_MULTIYEAR_BGC_001_029/description",
    },
}


def md(text):
    return nbf.v4.new_markdown_cell(textwrap.dedent(text).strip())


def code(text):
    return nbf.v4.new_code_cell(textwrap.dedent(text).strip())


def build(filename, cfg):
    title = cfg["title"]
    var = cfg["variable"]
    download_cells = []
    if var in {"ph", "chl", "phyc", "o2"}:
        download_cells = [
            md("""
            ### Automatic Copernicus Marine download

            The four Copernicus workflows for pH, chlorophyll-a, phytoplankton biomass and dissolved oxygen share
            one surface-biogeochemistry cache. If it is absent, this cell downloads all
            four variables (`chl`, `ph`, `phyc`, `o2`) for the Pacific domain. Copernicus
            Marine credentials must already be configured on the computer. Run
            `copernicusmarine login` once in a terminal before executing the notebook;
            credentials are intentionally never written in the notebook.
            """),
            code("""
            import copernicusmarine
            from packaging.version import Version

            if Version(copernicusmarine.__version__) < Version('2.2.0'):
                raise RuntimeError(
                    f'copernicusmarine {copernicusmarine.__version__} is incompatible '
                    'with the installed Zarr stack. Install copernicusmarine>=2.2.0 '
                    'and restart the kernel.'
                )

            copernicus_dataset_id = 'cmems_mod_glo_bgc_my_0.25deg_P1M-m'
            copernicus_variables = ['chl', 'ph', 'phyc', 'o2']
            copernicus_start = '1993-01-01T00:00:00'
            copernicus_end = '2026-05-01T00:00:00'
            surface_depth = 0.5057600140571594

            if not regional_path.is_file():
                credentials_valid = copernicusmarine.login(check_credentials_valid=True)
                if not credentials_valid:
                    raise RuntimeError(
                        'Copernicus Marine credentials were not found or are invalid. '
                        'Run this command in Terminal and then execute this cell again: '
                        '/Users/laurac/opt/anaconda3/envs/cc_indicators_v2/bin/'
                        'copernicusmarine login'
                    )
                # Copernicus longitudes are -180..180, whereas the regional maps use
                # 0..360. Download either side of the dateline and merge afterwards.
                download_parts = [
                    ('west', pacific_extent[0], 179.75),
                    ('east', -180.0, pacific_extent[1] - 360.0),
                ]
                part_paths = []
                for suffix, minimum_lon, maximum_lon in download_parts:
                    part_name = f'copernicus_bgc_pacific_{suffix}.nc'
                    part_path = regional_dir / part_name
                    part_paths.append(part_path)
                    if part_path.is_file():
                        print(f'Using completed download part: {part_path}')
                        continue
                    print(f'Downloading Copernicus Marine longitudes {minimum_lon} to {maximum_lon} ...')
                    copernicusmarine.subset(
                        dataset_id=copernicus_dataset_id,
                        variables=copernicus_variables,
                        minimum_longitude=minimum_lon,
                        maximum_longitude=maximum_lon,
                        minimum_latitude=pacific_extent[2],
                        maximum_latitude=pacific_extent[3],
                        start_datetime=copernicus_start,
                        end_datetime=copernicus_end,
                        minimum_depth=surface_depth,
                        maximum_depth=surface_depth,
                        coordinates_selection_method='outside',
                        output_directory=regional_dir,
                        output_filename=part_name,
                        file_format='netcdf',
                        netcdf_compression_level=4,
                        skip_existing=True,
                    )

                pieces = []
                for part_path in part_paths:
                    if not part_path.is_file():
                        raise FileNotFoundError(f'Copernicus download did not create {part_path}')
                    with xr.open_dataset(part_path) as part:
                        part = part.load()
                    part = part.assign_coords(
                        longitude=xr.where(part.longitude < 0, part.longitude + 360, part.longitude)
                    )
                    pieces.append(part)
                combined = xr.concat(pieces, dim='longitude').sortby('longitude')
                combined = combined.isel(
                    longitude=~combined.get_index('longitude').duplicated()
                )
                final_temporary = regional_path.with_suffix('.nc.part')
                combined.to_netcdf(final_temporary)
                final_temporary.replace(regional_path)
                for part_path in part_paths:
                    part_path.unlink(missing_ok=True)
                if not regional_path.is_file():
                    raise FileNotFoundError(
                        f'Copernicus Marine finished without creating {regional_path}'
                    )
            else:
                print(f'Using cached Copernicus Marine file: {regional_path}')
            """),
        ]
    if var == "MD50":
        download_cells = [
            md("""
            ### Automatic regional MD50 download

            When the cache is absent, the next cell downloads the NOAA PIFSC
            `md50_exp_2025` product in short time blocks and combines them. The native
            0.05° grid is sampled every 20 cells (1°) to avoid proxy timeouts and keep
            the regional file compact. Existing valid blocks and the final cache are
            reused, so an interrupted download can be resumed.
            """),
            code("""
            import time
            from urllib.parse import quote

            import requests

            md50_base_url = 'https://oceanwatch.pifsc.noaa.gov/erddap/griddap/md50_exp_2025.nc'
            download_start_year = 1998
            download_end_year = 2025
            spatial_stride = 20  # native 0.05° × 20 = 1°
            download_extent = (125, 245, -20, 35)  # constrained by product coverage
            block_years = 5

            def md50_block_url(first_year, last_year):
                west, east, south, north = download_extent
                constraint = (
                    f'[(%s-01-01T00:00:00Z):1:(%s-12-01T00:00:00Z)]'
                    f'[(%s):%s:(%s)][(%s):%s:(%s)]'
                    % (first_year, last_year, south, spatial_stride, north,
                       west, spatial_stride, east)
                )
                return md50_base_url + '?MD50' + quote(constraint, safe='():')

            def download_with_retries(url, destination, attempts=4):
                temporary = destination.with_suffix(destination.suffix + '.part')
                for attempt in range(1, attempts + 1):
                    try:
                        with requests.get(url, stream=True, timeout=(30, 300)) as response:
                            response.raise_for_status()
                            with temporary.open('wb') as stream:
                                for chunk in response.iter_content(chunk_size=1024 * 1024):
                                    if chunk:
                                        stream.write(chunk)
                        temporary.replace(destination)
                        return
                    except (requests.RequestException, OSError):
                        if attempt == attempts:
                            raise
                        time.sleep(5 * attempt)

            if not regional_path.is_file():
                block_paths = []
                for first in range(download_start_year, download_end_year + 1, block_years):
                    last = min(first + block_years - 1, download_end_year)
                    block = regional_dir / f'MD50_pacific_{first}_{last}.nc'
                    block_paths.append(block)
                    if not block.is_file():
                        print(f'Downloading MD50 {first}–{last} ...')
                        download_with_retries(md50_block_url(first, last), block)

                pieces = []
                for block in block_paths:
                    with xr.open_dataset(block) as source:
                        pieces.append(source.load())
                combined = xr.concat(pieces, dim='time').sortby('time')
                combined = combined.isel(time=~combined.get_index('time').duplicated())
                final_temporary = regional_path.with_suffix('.nc.part')
                combined.to_netcdf(final_temporary)
                final_temporary.replace(regional_path)
                for block in block_paths:
                    block.unlink(missing_ok=True)
                print(f'Created regional cache: {regional_path}')
            else:
                print(f'Using cached regional MD50: {regional_path}')
            """),
        ]
    cells = [
        md(f"""
        # {title}

        Regional counterpart of `National/biochemistry/{filename}`. The workflow maps the
        mean, seasonal cycle, anomalies and linear trend of **{cfg['label']}**, overlays
        Pacific EEZ boundaries, calculates area-weighted regional and EEZ summaries, and
        compares ENSO phases using the project's five-consecutive-month ONI rule.
        """),
        code(f"""
        from pathlib import Path
        import sys
        import warnings

        warnings.filterwarnings('ignore')

        import cartopy.crs as ccrs
        import cartopy.feature as cfeature
        import geopandas as gpd
        import matplotlib.pyplot as plt
        import numpy as np
        import pandas as pd
        import plotly.graph_objects as go
        import xarray as xr
        from matplotlib.path import Path as MplPath
        from scipy import stats

        root_candidates = [Path.cwd().resolve(), *Path.cwd().resolve().parents]
        repo_root = next((p for p in root_candidates if (p / 'functions').is_dir() and (p / 'data').is_dir()), None)
        if repo_root is None:
            raise FileNotFoundError('Run this notebook from inside the CIndRA repository.')
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))

        from functions.data_downloaders import download_oni_index
        from functions.ocean import process_trend_with_nan

        # CIndRA notebook display standard
        plt.rcParams.update({{'font.size': 12, 'axes.titlesize': 15, 'axes.labelsize': 14,
                             'xtick.labelsize': 12, 'ytick.labelsize': 12,
                             'legend.fontsize': 13}})
        """),
        md("""
        ## 1. Configuration and data

        Regional NetCDF files are cached at `data/regional/biochemistry/`. The source is
        downloaded automatically when absent. National subsets are never used in this
        regional workflow. Coordinates may be named `lon`/`lat` or
        `longitude`/`latitude`.
        """),
        code(f"""
        variable = '{var}'
        label = '{cfg['label']}'
        units = '{cfg['units']}'
        cmap = '{cfg['cmap']}'
        pacific_extent = (125, 245, -35, 35)
        trend_period = {(1998, 2025) if var == 'MD50' else (1993, 2025)}
        reference_period = {(1998, 2020) if var == 'MD50' else (1993, 2020)}
        regional_file = '{'MD50_pacific_monthly.nc' if var == 'MD50' else 'copernicus_bgc_pacific_surface_monthly.nc'}'
        data_dir = repo_root / 'data'
        regional_dir = data_dir / 'regional' / 'biochemistry'
        fig_dir = repo_root / 'matrix_cc' / 'figures'
        regional_dir.mkdir(parents=True, exist_ok=True)
        fig_dir.mkdir(parents=True, exist_ok=True)

        eez_file = data_dir / 'regional' / 'Pacific_EEZs' / 'Pacific_EEZs.shp'
        if not eez_file.is_file():
            raise FileNotFoundError(f'Pacific EEZ shapefile not found: {{eez_file}}')

        regional_path = regional_dir / regional_file
        """),
        *download_cells,
        code(f"""
        if not regional_path.is_file():
            raise FileNotFoundError(
                f'Regional download is missing: {{regional_path}}. '
                'Review the download-cell output before continuing.'
            )
        source_path = regional_path
        is_regional_dataset = True
        print('Data:', source_path)
        print('Source: {cfg['source']}')
        print('Reference: {cfg['url']}')
        """),
        code("""
        ds = xr.open_dataset(source_path)
        rename = {}
        if 'lon' in ds.coords: rename['lon'] = 'longitude'
        if 'lat' in ds.coords: rename['lat'] = 'latitude'
        ds = ds.rename(rename)
        if variable not in ds:
            raise KeyError(f'{variable!r} is not present in {source_path.name}: {list(ds.data_vars)}')
        if 'depth' in ds[variable].dims:
            ds = ds.isel(depth=0, drop=True)
        field = ds[variable].sortby('time').sortby('latitude').sortby('longitude')
        field = field.sel(time=slice(str(trend_period[0]), str(trend_period[1])))
        field = field.where(np.isfinite(field))

        eez = gpd.read_file(eez_file).to_crs(4326)
        country_col = next((c for c in ('Country', 'GEONAME', 'SOVEREIGN1', 'TERRITORY1') if c in eez.columns), None)
        if country_col is None:
            eez['Country'] = eez.index.astype(str)
            country_col = 'Country'

        data_extent = (float(field.longitude.min()), float(field.longitude.max()),
                       float(field.latitude.min()), float(field.latitude.max()))
        map_extent = pacific_extent if is_regional_dataset else data_extent
        print(f'Coverage: {data_extent}; {field.sizes["time"]} months')
        """),
        md("## 2. Map helpers and long-term mean"),
        code("""
        def setup_map(ax, title):
            ax.set_extent(map_extent, crs=ccrs.PlateCarree())
            ax.add_feature(cfeature.LAND, facecolor='0.88', edgecolor='0.35', linewidth=0.4, zorder=3)
            ax.coastlines(linewidth=0.45, zorder=4)
            eez.boundary.plot(ax=ax, transform=ccrs.PlateCarree(), color='0.2', linewidth=0.45, zorder=5)
            gl = ax.gridlines(draw_labels=True, linewidth=0.25, color='0.45', alpha=0.5)
            gl.top_labels = gl.right_labels = False
            ax.set_title(title, pad=10)
            return ax

        def map_field(values, title, colour_map, cbar_label, symmetric=False):
            finite = np.asarray(values.values)[np.isfinite(values.values)]
            if not len(finite):
                raise ValueError('No finite values are available for this map.')
            if symmetric:
                lim = float(np.nanpercentile(np.abs(finite), 98))
                vmin, vmax = -lim, lim
            else:
                vmin, vmax = np.nanpercentile(finite, [2, 98])
            fig, ax = plt.subplots(figsize=(15, 6), subplot_kw={'projection': ccrs.PlateCarree(central_longitude=180)})
            setup_map(ax, title)
            im = ax.pcolormesh(values.longitude, values.latitude, values, transform=ccrs.PlateCarree(),
                               cmap=colour_map, vmin=vmin, vmax=vmax, shading='auto')
            cb = fig.colorbar(
                im, ax=ax, orientation='horizontal', pad=0.07,
                shrink=0.48, aspect=32,
            )
            cb.set_label(cbar_label, fontsize=14)
            fig.tight_layout()
            return fig

        climatology = field.sel(time=slice(str(reference_period[0]), str(reference_period[1]))).mean('time')
        fig_mean = map_field(climatology, f'{label} mean ({reference_period[0]}–{reference_period[1]})', cmap, units)
        fig_mean.savefig(fig_dir / f'regional_{variable}_mean.png', dpi=180, bbox_inches='tight')
        """),
        md("## 3. Linear trend"),
        code("""
        annual = field.resample(time='YS').mean()
        trend, _, _, _, _ = process_trend_with_nan(annual)
        trend = xr.DataArray(trend * 10, coords={'latitude': annual.latitude, 'longitude': annual.longitude},
                             dims=('latitude', 'longitude'))
        fig_trend = map_field(trend, f'{label} linear trend ({trend_period[0]}–{trend_period[1]})',
                              'RdBu_r', f'{units} per decade', symmetric=True)
        fig_trend.savefig(fig_dir / f'regional_{variable}_trend.png', dpi=180, bbox_inches='tight')
        """),
        md("## 4. Seasonal climatology and anomalies"),
        code("""
        seasonal = field.groupby('time.season').mean().sel(season=['DJF', 'MAM', 'JJA', 'SON'])
        seasonal_anomaly = seasonal - climatology

        def seasonal_panels(values, title, colour_map, symmetric=False):
            finite = values.values[np.isfinite(values.values)]
            if symmetric:
                lim = float(np.nanpercentile(np.abs(finite), 98)); vmin, vmax = -lim, lim
            else:
                vmin, vmax = np.nanpercentile(finite, [2, 98])
            fig, axes = plt.subplots(2, 2, figsize=(15, 8),
                subplot_kw={'projection': ccrs.PlateCarree(central_longitude=180)}, constrained_layout=True)
            for ax, season in zip(axes.flat, values.season.values):
                setup_map(ax, str(season))
                im = ax.pcolormesh(values.longitude, values.latitude, values.sel(season=season),
                                   transform=ccrs.PlateCarree(), cmap=colour_map,
                                   vmin=vmin, vmax=vmax, shading='auto')
            fig.suptitle(title, fontsize=18)
            cb = fig.colorbar(
                im, ax=axes, orientation='horizontal', pad=0.05,
                shrink=0.55, aspect=35,
            )
            cb.set_label(units, fontsize=14)
            return fig

        fig_season = seasonal_panels(seasonal, f'Seasonal climatology of {label}', cmap)
        fig_season.savefig(fig_dir / f'regional_{variable}_seasonal.png', dpi=180, bbox_inches='tight')
        fig_season_anom = seasonal_panels(seasonal_anomaly, f'Seasonal anomalies of {label}', 'RdBu_r', True)
        fig_season_anom.savefig(fig_dir / f'regional_{variable}_seasonal_anomaly.png', dpi=180, bbox_inches='tight')
        """),
        md("## 5. Area-weighted regional time series"),
        code("""
        weights = np.cos(np.deg2rad(field.latitude))
        regional_monthly = field.weighted(weights).mean(('latitude', 'longitude'))
        regional_annual = regional_monthly.resample(time='YS').mean()
        x_dates = pd.DatetimeIndex(regional_annual.time.values)
        x = x_dates.year.to_numpy()
        y = regional_annual.values
        valid = np.isfinite(y)
        trend_result = stats.linregress(x[valid], y[valid])
        slope = trend_result.slope
        significant = trend_result.pvalue < 0.05
        trend_style = 'solid' if significant else 'dash'
        significance_text = 'Significant (p < 0.05)' if significant else 'Not significant (p ≥ 0.05)'

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x_dates, y=y, mode='lines+markers', name='Area-weighted annual mean',
            line=dict(color='#1f77b4', width=2), marker=dict(size=7),
            hovertemplate='%{x|%Y}<br>%{y:.4g} ' + units + '<extra></extra>',
        ))
        fig.add_trace(go.Scatter(
            x=x_dates[valid], y=trend_result.intercept + slope*x[valid], mode='lines',
            line=dict(color='black', width=2.5, dash=trend_style),
            name=f'Trend (rate = {slope*10:+.3g} {units}/decade) – {significance_text}',
            hovertemplate='Trend %{x|%Y}<br>%{y:.4g} ' + units + '<extra></extra>',
        ))
        fig.update_layout(
            title=dict(text=f'Regional annual {label}', x=0.5, xanchor='center'),
            xaxis=dict(title='Year', range=[x_dates[valid].min(), x_dates[valid].max()], showgrid=True),
            yaxis=dict(title=units, showgrid=True), template='plotly_white',
            width=1000, height=500, hovermode='x unified',
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5, font=dict(size=13)),
            margin=dict(l=75, r=35, t=110, b=65),
        )
        fig.write_html(fig_dir / f'regional_{variable}_timeseries.html', include_plotlyjs='cdn')
        fig.show()
        """),
        md("""
        ## 6. ENSO modulation

        El Niño and La Niña episodes require at least five consecutive months with ONI
        above +0.5 °C or below −0.5 °C, respectively. Other months remain Neutral.
        Each phase composite is shown as an anomaly from the grid-cell mean over the
        complete analysis period, rather than as a difference from the Neutral phase.
        """),
        code("""
        oni_cache = regional_dir / 'oni_index.pkl'
        if oni_cache.is_file():
            oni = pd.read_pickle(oni_cache)
        else:
            oni = download_oni_index('https://psl.noaa.gov/data/correlation/oni.data')
            oni.to_pickle(oni_cache)
        oni = oni.rename(columns={oni.columns[0]: 'ONI'})[['ONI']].copy()

        def sustained(mask, minimum=5):
            groups = mask.ne(mask.shift()).cumsum()
            lengths = mask.groupby(groups).transform('sum')
            return mask & (lengths >= minimum)

        oni['phase'] = 'Neutral'
        oni.loc[sustained(oni.ONI >= .5), 'phase'] = 'El Nino'
        oni.loc[sustained(oni.ONI <= -.5), 'phase'] = 'La Nina'
        monthly_phase = oni.phase.reindex(pd.DatetimeIndex(field.time.values).to_period('M').to_timestamp())
        phase_code = monthly_phase.map({'La Nina': -1, 'Neutral': 0, 'El Nino': 1}).fillna(0).to_numpy()
        field_with_phase = field.assign_coords(ENSO=('time', phase_code))
        phase_names = {-1: 'La Niña', 0: 'Neutral', 1: 'El Niño'}
        full_period_mean = field.mean('time')
        phase_means = {phase_names[k]: field_with_phase.where(field_with_phase.ENSO == k, drop=True).mean('time') for k in phase_names}
        phase_anomalies = {phase: values - full_period_mean for phase, values in phase_means.items()}

        fig, axes = plt.subplots(1, 3, figsize=(17, 5),
            subplot_kw={'projection': ccrs.PlateCarree(central_longitude=180)}, constrained_layout=True)
        all_values = np.concatenate([v.values.ravel() for v in phase_anomalies.values()])
        finite_values = all_values[np.isfinite(all_values)]
        limit = float(np.nanpercentile(np.abs(finite_values), 98))
        for ax, (phase, values) in zip(axes, phase_anomalies.items()):
            setup_map(ax, phase)
            im = ax.pcolormesh(values.longitude, values.latitude, values, transform=ccrs.PlateCarree(),
                               cmap='RdBu_r', vmin=-limit, vmax=limit, shading='auto')
        fig.suptitle(f'{label} anomalies by ENSO phase', fontsize=18)
        cb = fig.colorbar(
            im, ax=axes, orientation='horizontal', pad=0.06,
            shrink=0.55, aspect=35,
        )
        cb.set_label(f'Anomaly from full-period mean ({units})', fontsize=14)
        fig.savefig(fig_dir / f'regional_{variable}_enso_anomalies.png', dpi=180, bbox_inches='tight')
        """),
        md("## 7. EEZ summaries"),
        code("""
        lon2d, lat2d = np.meshgrid(field.longitude.values, field.latitude.values)
        geometry_lon = np.where(lon2d.ravel() > 180, lon2d.ravel() - 360, lon2d.ravel())
        points = gpd.GeoDataFrame(
            {'row': np.repeat(np.arange(field.sizes['latitude']), field.sizes['longitude']),
             'col': np.tile(np.arange(field.sizes['longitude']), field.sizes['latitude'])},
            geometry=gpd.points_from_xy(geometry_lon, lat2d.ravel()), crs=4326)
        joined = gpd.sjoin(points, eez[[country_col, 'geometry']], predicate='within', how='inner')

        rows = []
        for country, group in joined.groupby(country_col):
            jj, ii = group.row.to_numpy(), group.col.to_numpy()
            w = np.cos(np.deg2rad(field.latitude.values[jj]))
            mean_values = climatology.values[jj, ii]
            trend_values = trend.values[jj, ii]
            good_mean = np.isfinite(mean_values)
            good_trend = np.isfinite(trend_values)
            rows.append({
                'EEZ': country,
                f'Mean ({units})': np.average(mean_values[good_mean], weights=w[good_mean]) if good_mean.any() else np.nan,
                f'Trend ({units}/decade)': np.average(trend_values[good_trend], weights=w[good_trend]) if good_trend.any() else np.nan,
                'Grid cells': int(good_mean.sum()),
            })
        eez_summary = pd.DataFrame(rows).sort_values('EEZ').reset_index(drop=True)
        if eez_summary.empty:
            print('No EEZ contains a grid-cell centre at the current data resolution.')
        else:
            display(eez_summary.style.format(precision=3))
        """),
        md(f"""
        ## Interpretation and reproducibility notes

        - The regional mean uses cosine-of-latitude weights.
        - EEZ statistics assign grid-cell centres to polygons; very small EEZs can have no
          cells when the input is coarse.
        - Trends are descriptive ordinary least-squares trends and do not account for
          temporal autocorrelation.
        - Data source: [{cfg['source']}]({cfg['url']}).
        """),
    ]
    nb = nbf.v4.new_notebook(cells=cells)
    nb.metadata.kernelspec = {"display_name": "cc_indicators_v2", "language": "python", "name": "python3"}
    nb.metadata.language_info = {"name": "python", "version": "3.12"}
    nbf.write(nb, OUT / filename)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for filename, cfg in VARIABLES.items():
        build(filename, cfg)


if __name__ == "__main__":
    main()
