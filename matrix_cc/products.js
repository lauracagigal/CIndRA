// CIndRA product catalogue used by matrix_cc/index.html.
//
// Paths are relative to matrix_cc/index.html. Tokens:
//   {FIG}      matrix_cc/figures            (ocean / biochemistry / TC products)
//   {OUT}      outputs/figures              (station + regional atmosphere products)
//   {TAB}      outputs/tables               (station summary tables)
//   {MHW}      notebooks/matrix_cc/figures  (national MHW notebook output)
//   {station}  station slug of the selected national site
//   {eez}      EEZ slug of the selected national site
//   {natfig}   per-site subfolder of {FIG} for TC / SST / biochemistry products ('' = {FIG} itself)
// An indicator may carry `projections: { notebook, products, tables }` (national and regional scales);
// these are attached by indicator code at the end of this file.
// A product with `mx: false` is listed in the National/Regional views but hidden in the Matrix tab;
// ENSO products and tables (`enso: true`) are hidden in the Matrix tab too.
// A product whose path uses a token the selected site does not define is shown as "not available".
// Missing files are detected at runtime and flagged as "not generated yet".
// Every product and table opens a "Product record" (CMPLV source of record): its written content is in records.js
// and its automatic part (run dates, file inventory, code version) in inventory.js (build_inventory_js.py).

window.CINDRA = {
  book: 'https://lauracagigal.github.io/CIndRA/',
  roots: {
    FIG: 'figures',
    OUT: '../outputs/figures',
    TAB: '../outputs/tables',
    MHW: '../notebooks/matrix_cc/figures',
  },

  // Regional domain used by the regional notebooks (functions/rainfall_regional.py PACIFIC_EXTENT, lon 0-360).
  regionalExtent: { lonMin: 125, lonMax: 245, latMin: -35, latMax: 45 },

  // National sites. `eezName` matches the Country field of data/regional/Pacific_EEZs (see eez.js).
  sites: [
    {
      id: 'palau', label: 'Palau', station: 'Koror (GSN 91408)', eezName: 'Palau', lat: 7.337, lon: 134.477,
      tokens: { station: 'palau_psw00040309_lat7p337_lon134p477', ghcn: 'PSW00040309', eez: 'palau', ocean: 'palau', natfig: '' },
    },
    {
      id: 'marshall', label: 'Marshall Islands', station: 'Majuro (GSN 91376)', eezName: 'Marshall Islands', lat: 7.065, lon: 171.272,
      tokens: { station: 'marshall_islands_rmw00040710_lat7p065_lon171p272', ghcn: 'RMW00040710', eez: 'marshall_islands', natfig: 'marshall_islands_rmw00040710_lat7p065_lon171p272/' },
    },
  ],

  national: [
    co2Group('0.1', false),  // national matrix: Mauna Loa series only, as in the report
    // ─────────────────────────── ATMOSPHERE ───────────────────────────
    {
      domain: 'Atmosphere', variable: 'Air Temperature', icon: 'thermo',
      page: 'notebooks/historical/National/air_temperature/surface_temperature',
      indicators: [
        {
          code: '1.1', name: 'Mean surface temperature',
          notebook: 'notebooks/historical/National/air_temperature/a_mean_temperature',
          products: [
            { kind: 'plot', title: 'Anomalies & 10 warmest years', path: '{OUT}/{station}/F2_ST_Annomalies_top10_{station}.png',
              caption: 'Annual mean temperature anomalies relative to the reference period. Coloured dots mark the 10 warmest years on record; the black line is the linear trend (solid when significant, p < 0.05).' },
            { kind: 'plot', mx: false, title: 'Annual mean temperature', path: '{OUT}/{station}/F2_ST_Mean_{station}.png',
              caption: 'Annual mean air temperature at the station with its linear trend.' },
          ],
          tables: [
            { title: 'Summary table', path: '{TAB}/{station}/T_mean_summary_table_{station}.csv' },
            { title: 'Annual series', path: '{TAB}/{station}/T_mean_annual_{station}.csv' },
            { title: 'Top-10 warmest years', path: '{TAB}/{station}/T_mean_top10_warmest_years_{station}.csv' },
            { title: 'ENSO summary', enso: true, path: '{TAB}/{station}/ENSO_temperature_summary_{station}.csv' },
          ],
        },
        {
          code: '1.2', name: 'Minimum and maximum temperature',
          notebook: 'notebooks/historical/National/air_temperature/b_min_max_temperature',
          products: [
            { kind: 'interactive', title: 'Annual Tmin & Tmax', path: '{OUT}/{station}/F3_ST_min_max_{station}.html',
              caption: 'Annual maximum (red) and minimum (blue) temperature. Solid black lines: significant trends (p < 0.05); dashed: not significant.' },
            { kind: 'interactive', mx: false, title: 'Minimum temperature', path: '{OUT}/{station}/F3_ST_min_{station}.html',
              caption: 'Annual minimum temperature (TMIN) and trend.' },
            { kind: 'interactive', mx: false, title: 'Maximum temperature', path: '{OUT}/{station}/F3_ST_max_{station}.html',
              caption: 'Annual maximum temperature (TMAX) and trend.' },
          ],
          tables: [
            { title: 'Summary table', path: '{TAB}/{station}/T_minmax_summary_table_{station}.csv' },
            { title: 'Annual series', path: '{TAB}/{station}/T_minmax_annual_{station}.csv' },
          ],
        },
        {
          code: '1.3', name: 'Hot and cold days and nights',
          notebook: 'notebooks/historical/National/air_temperature/c_hot_cold_days',
          products: [
            { kind: 'interactive', title: 'Hot days & cold nights (TX90p / TN10p)', path: '{OUT}/{station}/F4_ST_hot_cold_{station}.html',
              caption: 'Annual number of hot days (above the calendar-day 90th percentile) and cold nights (below the calendar-day 10th percentile) of the reference period.' },
            { kind: 'interactive', mx: false, title: 'Fixed-percentile variant', path: '{OUT}/{station}/F4_ST_hot_cold_percentiles_{station}.html',
              caption: 'Hot days and cold nights computed with fixed percentile thresholds.' },
            { kind: 'interactive', mx: false, title: 'Warm nights & cold days (TN90p / TX10p)', path: '{OUT}/{station}/F4_ST_warm_cold_{station}.html',
              caption: 'Annual number of warm nights (minimum temperature above the calendar-day 90th percentile) and cold days (maximum temperature below the calendar-day 10th percentile) of the reference period.' },
          ],
          tables: [
            { title: 'ETCCDI summary', path: '{TAB}/{station}/T_hot_cold_summary_table_etccdi_{station}.csv' },
            { title: 'Percentile summary', path: '{TAB}/{station}/T_hot_cold_summary_table_percentiles_{station}.csv' },
            { title: 'Hot days per year', path: '{TAB}/{station}/T_hot_days_per_year_{station}.csv' },
            { title: 'Cold nights per year', path: '{TAB}/{station}/T_cold_nights_per_year_{station}.csv' },
            { title: 'Warm nights & cold days summary', path: '{TAB}/{station}/T_warm_cold_summary_table_etccdi_{station}.csv' },
            { title: 'Warm nights per year', path: '{TAB}/{station}/T_warm_nights_per_year_{station}.csv' },
            { title: 'Cold days per year', path: '{TAB}/{station}/T_cold_days_per_year_{station}.csv' },
          ],
        },
      ],
    },
    {
      domain: 'Atmosphere', variable: 'Rainfall', icon: 'rain',
      page: 'notebooks/historical/National/rainfall/rainfall',
      indicators: [
        {
          code: '2.1', name: 'Total rainfall',
          notebook: 'notebooks/historical/National/rainfall/a_Total_rainfall',
          products: [
            { kind: 'plot', title: 'Anomalies & 10 wettest years', path: '{OUT}/{station}/F5_Rain_anom_top10_{station}.png',
              caption: 'Annual total rainfall anomalies relative to the reference period (mm/year). Coloured dots mark the 10 wettest years.' },
            { kind: 'interactive', mx: false, title: 'Daily precipitation', path: '{OUT}/{station}/F5_Rain_daily_{station}.html',
              caption: 'Daily precipitation time series at the station.' },
            { kind: 'interactive', mx: false, title: 'Annual daily maxima', path: '{OUT}/{station}/F5_Rain_annual_max_{station}.html',
              caption: 'Annual maximum daily rainfall.' },
            { kind: 'plot', mx: false, title: 'Accumulated precipitation', path: '{OUT}/{station}/F5_Rain_accum_{station}.png',
              caption: 'Annual accumulated precipitation.' },
            { kind: 'plot', title: 'Dry season (Nov–Apr)', path: '{OUT}/{station}/F6a_Rain_dry_season_{station}.png',
              caption: 'Accumulated rainfall during the dry season (November–April).' },
            { kind: 'plot', title: 'Wet season (May–Oct)', path: '{OUT}/{station}/F6a_Rain_wet_season_{station}.png',
              caption: 'Accumulated rainfall during the wet season (May–October).' },
            { kind: 'plot', title: 'ENSO – daily rainfall', path: '{OUT}/{station}/F5_Rain_mean_ONI_daily_{station}.png', enso: true,
              caption: 'Daily rainfall modulated by ENSO phase (ONI index).' },
            { kind: 'plot', title: 'ENSO – accumulated rainfall', path: '{OUT}/{station}/F5_Rain_mean_ONI_accum_{station}.png', enso: true,
              caption: 'Accumulated rainfall by ENSO phase (ONI index).' },
          ],
          tables: [
            { title: 'Summary table', path: '{TAB}/{station}/R_mean_summary_table_{station}.csv' },
            { title: 'Annual series', path: '{TAB}/{station}/R_mean_annual_{station}.csv' },
            { title: 'Top-10 wettest years', path: '{TAB}/{station}/R_top10_wettest_years_{station}.csv' },
            { title: 'Dry-season totals', path: '{TAB}/{station}/R_dry_season_annual_{station}.csv' },
            { title: 'Wet-season totals', path: '{TAB}/{station}/R_wet_season_annual_{station}.csv' },
            { title: 'ONI annual', enso: true, path: '{TAB}/{station}/R_ONI_annual_{station}.csv' },
          ],
        },
        {
          code: '2.2', name: 'Dry conditions',
          notebook: 'notebooks/historical/National/rainfall/b_Consecutive_dry_days',
          products: [
            { kind: 'plot', title: 'Dry days per year', path: '{OUT}/{station}/F6a_Number_dry_{station}.png',
              caption: 'Annual number of dry days (below 1 mm).' },
            { kind: 'plot', title: 'Max consecutive dry days', path: '{OUT}/{station}/F6b_Consecutive_dry_{station}.png',
              caption: 'Longest sequence of consecutive days with rainfall below 1 mm in each year.' },
            { kind: 'plot', mx: false, title: 'Mean consecutive dry days', path: '{OUT}/{station}/F6b_Mean_consecutive_dry_{station}.png',
              caption: 'Mean length of dry spells in each year.' },
            { kind: 'plot', mx: false, title: 'Wet / dry distribution', path: '{OUT}/{station}/F6a_Wet_dry_distribution_{station}.png',
              caption: 'Distribution of wet and dry days.' },
          ],
          tables: [
            { title: 'Summary table', path: '{TAB}/{station}/R_dry_summary_table_{station}.csv' },
            { title: 'Dry days per year', path: '{TAB}/{station}/R_dry_days_per_year_{station}.csv' },
            { title: 'Max consecutive dry days', path: '{TAB}/{station}/R_consecutive_dry_max_per_year_{station}.csv' },
            { title: 'Mean consecutive dry days', path: '{TAB}/{station}/R_consecutive_dry_mean_per_year_{station}.csv' },
          ],
        },
        {
          code: '2.3', name: 'Heavy rainfall',
          notebook: 'notebooks/historical/National/rainfall/c_Heavy_rainfall',
          products: [
            { kind: 'plot', title: 'Wet days (> 1 mm)', path: '{OUT}/{station}/F7a_Wet_days_1mm_{station}.png',
              caption: 'Annual number of wet days (above 1 mm).' },
            { kind: 'plot', title: 'Heavy rainfall days (> p95)', path: '{OUT}/{station}/F7b_Wet_days_95p_{station}.png',
              caption: 'Annual number of days above the 95th percentile of wet-day rainfall.' },
            { kind: 'plot', mx: false, title: 'Wet / dry distribution', path: '{OUT}/{station}/F7a_Wet_dry_distribution_{station}.png',
              caption: 'Distribution of wet and dry days.' },
          ],
          tables: [
            { title: 'Summary table', path: '{TAB}/{station}/R_heavy_summary_table_{station}.csv' },
            { title: 'Wet days per year', path: '{TAB}/{station}/R_wet_days_per_year_{station}.csv' },
            { title: 'Heavy days per year', path: '{TAB}/{station}/R_heavy_days_per_year_{station}.csv' },
          ],
        },
      ],
    },
    {
      domain: 'Atmosphere', variable: 'Tropical Cyclones', icon: 'cyclone',
      page: 'notebooks/historical/National/tropical_cyclones/tropical_cyclones',
      indicators: [
        {
          code: '3.1', name: 'All tropical cyclones',
          notebook: 'notebooks/historical/National/tropical_cyclones/a_tropical_cyclones',
          products: [
            { kind: 'map', title: 'Historical TC tracks', path: '{FIG}/{natfig}F8_TCs_Historical.png', sites: ['palau', 'marshall'],
              caption: 'Tropical cyclone tracks in the vicinity of the site since 1950, coloured by Saffir–Simpson category. Grey: no wind information.' },
            { kind: 'plot', title: 'Annual counts by category', path: '{FIG}/{natfig}F8_TCs_Historical_bars_category.png', sites: ['palau', 'marshall'],
              caption: 'Annual storm count by category with linear trend.' },
            { kind: 'map', title: 'El Niño years', path: '{FIG}/{natfig}F9_TCs_El Niño.png', sites: ['palau', 'marshall'], enso: true,
              caption: 'Historical TC tracks during El Niño years.' },
            { kind: 'map', title: 'La Niña years', path: '{FIG}/{natfig}F9_TCs_La Niña.png', sites: ['palau', 'marshall'], enso: true,
              caption: 'Historical TC tracks during La Niña years.' },
            { kind: 'map', title: 'Neutral years', path: '{FIG}/{natfig}F9_TCs_Neutral.png', sites: ['palau', 'marshall'], enso: true,
              caption: 'Historical TC tracks during ENSO-neutral years.' },
          ],
        },
        {
          code: '3.2', name: 'Severe tropical cyclones',
          notebook: 'notebooks/historical/National/tropical_cyclones/b_severe_tropical_cyclones',
          products: [
            { kind: 'map', title: 'Severe TC tracks', path: '{FIG}/{natfig}F8_TCs_Historical_Severe.png', sites: ['palau', 'marshall'],
              caption: 'Severe tropical cyclones (Category 3 or greater, winds above 96 kt) in the vicinity of the site since 1950.' },
            { kind: 'plot', title: 'Severe TCs by category', path: '{FIG}/{natfig}F8_TCs_Historical_bars_category_severe.png', sites: ['palau', 'marshall'],
              caption: 'Annual count of severe TCs by category.' },
            { kind: 'plot', mx: false, title: 'Severe TCs through time', path: '{FIG}/{natfig}F8_TCs_Historical_Severe_cat_time.png', sites: ['palau', 'marshall'],
              caption: 'Annual severe storm count and trend.' },
            { kind: 'plot', title: 'Severe TCs & ENSO trend', path: '{FIG}/{natfig}F9_TCs_severe_bars_trend.png', sites: ['palau', 'marshall'], enso: true,
              caption: 'Severe TC counts coloured by ENSO phase (ONI index).' },
            { kind: 'map', title: 'Severe – El Niño', path: '{FIG}/{natfig}F9_TCs_El Niño_SEVERE.png', sites: ['palau', 'marshall'], enso: true,
              caption: 'Severe TC tracks during El Niño years.' },
            { kind: 'map', title: 'Severe – La Niña', path: '{FIG}/{natfig}F9_TCs_La Niña_SEVERE.png', sites: ['palau', 'marshall'], enso: true,
              caption: 'Severe TC tracks during La Niña years.' },
            { kind: 'map', title: 'Severe – Neutral', path: '{FIG}/{natfig}F9_TCs_Neutral_SEVERE.png', sites: ['palau', 'marshall'], enso: true,
              caption: 'Severe TC tracks during ENSO-neutral years.' },
          ],
        },
      ],
    },

    // ───────────────────────────── OCEAN ─────────────────────────────
    {
      domain: 'Ocean', variable: 'Sea Surface Temperature', icon: 'wave',
      page: 'notebooks/historical/National/sea_surface_temperature/sea_surface_temperature',
      indicators: [
        {
          code: '4.1', name: 'Mean sea surface temperature',
          notebook: 'notebooks/historical/National/sea_surface_temperature/a_Mean_Temperature_maps',
          products: [
            { kind: 'map', title: 'Mean SST', path: '{FIG}/{natfig}SST_mean_{eez}.png',
              caption: 'Mean sea surface temperature inside the EEZ from NOAA OISST v2.1.' },
            { kind: 'map', title: 'SST trend', path: '{FIG}/{natfig}SST_trend_{eez}.png',
              caption: 'Linear SST trend (°C per decade) inside the EEZ.' },
            { kind: 'plot', title: 'Trends & anomalies', path: '{FIG}/{natfig}SST_trends_anomalies_{eez}.png',
              caption: 'EEZ-averaged SST anomalies and linear trend.' },
            { kind: 'plot', title: 'Point time series', path: '{FIG}/{natfig}SST_timeseries_{eez}.png',
              caption: 'SST time series at the selected point.' },
            { kind: 'map', title: 'SST by ENSO phase', path: '{FIG}/{natfig}SST_ENSO_{eez}.png', enso: true,
              caption: 'SST anomalies under La Niña, Neutral and El Niño conditions.' },
          ],
        },
        {
          code: '4.2', name: 'Degree heating weeks',
          notebook: 'notebooks/historical/National/sea_surface_temperature/b_DHW',
          products: [
            { kind: 'plot', title: 'DHW full period', path: '{FIG}/F13_DHW.png', sites: ['palau'],
              caption: 'Degree Heating Weeks (NOAA Coral Reef Watch) over the full period.' },
            { kind: 'plot', title: 'Days per bleaching alert level', path: '{FIG}/F13_DHW_days_year_level.png', sites: ['palau'],
              caption: 'Annual number of days at each bleaching alert level.' },
            { kind: 'plot', title: 'DHW by ENSO phase', path: '{FIG}/F13_DHW_oni_cat.png', sites: ['palau'], enso: true,
              caption: 'Degree Heating Weeks by ENSO phase (ONI index).' },
          ],
        },
        {
          code: '4.3', name: 'Marine heatwaves',
          notebook: 'notebooks/historical/National/sea_surface_temperature/c_MHW',
          products: [
            { kind: 'map', title: 'EEZ mask', path: '{MHW}/F_MHW_EEZ_mask.png', sites: ['palau'],
              caption: 'Grid cells used for the EEZ-wide marine heatwave analysis.' },
            { kind: 'plot', title: 'EEZ MHWs – full period', path: '{MHW}/F_MHW_EEZ_full_period.png', sites: ['palau'],
              caption: 'EEZ-average marine heatwaves detected with the Hobday et al. (2016) method.' },
            { kind: 'plot', title: 'EEZ MHWs – last 10 years', path: '{MHW}/F_MHW_EEZ_last_10_years.png', sites: ['palau'],
              caption: 'EEZ-average marine heatwaves over the last 10 years.' },
            { kind: 'plot', title: 'EEZ annual indicators', path: '{MHW}/F_MHW_EEZ_annual_indicators.png', sites: ['palau'],
              caption: 'Annual MHW frequency, duration, intensity and trends for the EEZ average.' },
            { kind: 'plot', title: 'Selected point', path: '{MHW}/F_MHW_selected_point_full_period.png', sites: ['palau'],
              caption: 'Marine heatwaves at the user-selected point.' },
            { kind: 'plot', title: 'EEZ vs point', path: '{MHW}/F_MHW_EEZ_vs_point.png', sites: ['palau'],
              caption: 'Comparison between EEZ-average and single-point MHW statistics.' },
          ],
        },
      ],
    },
    {
      domain: 'Ocean', variable: 'Ocean Biogeochemistry', icon: 'leaf',
      page: 'notebooks/historical/National/biochemistry/biochemistry',
      indicators: [
        bioNational('5.1', 'Ocean acidification: pH', 'a_oceanic_pH', 'F14_pH', 'pH'),
        bioNational('5.2', 'Chlorophyll concentration', 'b_chlorophyll', 'F15_chlorophyll', 'chlorophyll-a'),
        bioNational('5.3', 'Estimated phytoplankton size', 'c_phytoplankton', 'F16_phytoplankton', 'phytoplankton size'),
        bioNational('5.4', 'Subsurface oxygen (O₂)', 'd_dissolved_o2', 'F17_O2', 'dissolved oxygen'),
        { code: '5.5', name: 'Aragonite saturation state', notebook: 'notebooks/projections/National/biochemistry/b_aragonite', products: [] },
        { code: '5.6', name: 'Sea surface salinity', notebook: 'notebooks/projections/National/biochemistry/c_salinity', products: [] },
      ],
    },
  ],

  regional: [
    co2Group('R0.1'),
    {
      domain: 'Atmosphere', variable: 'Air Temperature', icon: 'thermo',
      page: 'notebooks/historical/Regional/air_temperature/air_temperature',
      indicators: [
        {
          code: 'R1.1', name: 'Mean temperature',
          notebook: 'notebooks/historical/Regional/air_temperature/regional_indicators',
          products: [
            { kind: 'plot', mx: false, title: 'Regional mean anomaly (stations)', path: '{OUT}/regional_pacific/T_regional_mean_anomaly_timeseries_pacific.png',
              caption: 'Regional-mean annual temperature anomaly from GHCN stations inside the Pacific EEZs.' },
            { kind: 'map', mx: false, title: 'Station trends – Tmean', path: '{OUT}/regional_pacific/T_regional_tmean_annual_trend_pacific.png',
              caption: 'Linear trend of annual mean temperature at each station (filled markers: significant).' },
            { kind: 'map', mx: false, title: 'ERA5 mean temperature', path: '{OUT}/regional_pacific/T_regional_tmean_annual_mean_era5_pacific.png',
              caption: 'ERA5 annual mean 2 m temperature over the Pacific.' },
            { kind: 'map', title: 'ERA5 temperature trend', path: '{OUT}/regional_pacific/T_regional_tmean_annual_trend_era5_pacific.png',
              caption: 'ERA5 linear trend of annual mean 2 m temperature.' },
            { kind: 'plot', title: 'ERA5 EEZ-mean anomaly', path: '{OUT}/regional_pacific/T_regional_mean_anomaly_timeseries_era5_pacific.png',
              caption: 'ERA5 annual temperature anomaly averaged over the Pacific EEZs.' },
          ],
          tables: [
            { title: 'Summary table', path: '{TAB}/regional_pacific/T_regional_summary_table_tmean_pacific.csv' },
            { title: 'EEZ summary – stations', path: '{TAB}/regional_pacific/T_regional_EEZ_tmean_stations_pacific.csv' },
            { title: 'EEZ summary – ERA5', path: '{TAB}/regional_pacific/T_regional_EEZ_tmean_era5_pacific.csv' },
          ],
        },
        {
          code: 'R1.2', name: 'Minimum, maximum & diurnal range',
          notebook: 'notebooks/historical/Regional/air_temperature/regional_indicators',
          products: [
            { kind: 'map', title: 'Station trends – Tmax', path: '{OUT}/regional_pacific/T_regional_tmax_annual_trend_pacific.png',
              caption: 'Linear trend of annual maximum temperature at each station.' },
            { kind: 'map', title: 'Station trends – Tmin', path: '{OUT}/regional_pacific/T_regional_tmin_annual_trend_pacific.png',
              caption: 'Linear trend of annual minimum temperature at each station.' },
            { kind: 'map', title: 'Station trends – diurnal range', path: '{OUT}/regional_pacific/T_regional_diff_annual_trend_pacific.png',
              caption: 'Linear trend of the diurnal temperature range (Tmax − Tmin).' },
          ],
          tables: [
            { title: 'Summary table', path: '{TAB}/regional_pacific/T_regional_summary_table_minmax_pacific.csv' },
            { title: 'EEZ summary – stations', path: '{TAB}/regional_pacific/T_regional_EEZ_minmax_stations_pacific.csv' },
          ],
        },
        {
          code: 'R1.3', name: 'Hot & cold days and nights',
          notebook: 'notebooks/historical/Regional/air_temperature/regional_indicators',
          products: [
            { kind: 'map', title: 'Hot days trend', path: '{OUT}/regional_pacific/T_regional_hot_days_pct_trend_pacific.png',
              caption: 'Trend in the percentage of hot days (TX90p) at each station.' },
            { kind: 'map', title: 'Cold nights trend', path: '{OUT}/regional_pacific/T_regional_cold_nights_pct_trend_pacific.png',
              caption: 'Trend in the percentage of cold nights (TN10p) at each station.' },
            { kind: 'plot', title: 'Hot days – station average', path: '{OUT}/regional_pacific/T_regional_hot_days_timeseries_pacific.png',
              caption: 'Annual percentage of hot days (TMAX above each station’s 90th percentile), averaged over the GHCN stations, with linear trend (solid: significant at 95%; dashed: not significant).' },
            { kind: 'plot', title: 'Cold nights – station average', path: '{OUT}/regional_pacific/T_regional_cold_nights_timeseries_pacific.png',
              caption: 'Annual percentage of cold nights (TMIN below each station’s 10th percentile), averaged over the GHCN stations, with linear trend (solid: significant at 95%; dashed: not significant).' },
            { kind: 'map', title: 'Warm nights trend', path: '{OUT}/regional_pacific/T_regional_warm_nights_pct_trend_pacific.png',
              caption: 'Trend in the percentage of warm nights (TMIN above the station’s 90th percentile, ~TN90p) at each station.' },
            { kind: 'map', title: 'Cold days trend', path: '{OUT}/regional_pacific/T_regional_cold_days_pct_trend_pacific.png',
              caption: 'Trend in the percentage of cold days (TMAX below the station’s 10th percentile, ~TX10p) at each station.' },
            { kind: 'plot', title: 'Warm nights – station average', path: '{OUT}/regional_pacific/T_regional_warm_nights_timeseries_pacific.png',
              caption: 'Annual percentage of warm nights (TMIN above each station’s 90th percentile), averaged over the GHCN stations, with linear trend (solid: significant at 95%; dashed: not significant).' },
            { kind: 'plot', title: 'Cold days – station average', path: '{OUT}/regional_pacific/T_regional_cold_days_timeseries_pacific.png',
              caption: 'Annual percentage of cold days (TMAX below each station’s 10th percentile), averaged over the GHCN stations, with linear trend (solid: significant at 95%; dashed: not significant).' },
          ],
          tables: [
            { title: 'Summary table', path: '{TAB}/regional_pacific/T_regional_summary_table_hot_cold_pacific.csv' },
            { title: 'EEZ summary – stations', path: '{TAB}/regional_pacific/T_regional_EEZ_hot_cold_stations_pacific.csv' },
            { title: 'Summary table – warm nights & cold days', path: '{TAB}/regional_pacific/T_regional_summary_table_warm_cold_pacific.csv' },
            { title: 'EEZ summary – warm nights & cold days', path: '{TAB}/regional_pacific/T_regional_EEZ_warm_cold_stations_pacific.csv' },
          ],
        },
      ],
    },
    {
      domain: 'Atmosphere', variable: 'Rainfall', icon: 'rain',
      page: 'notebooks/historical/Regional/rainfall/rainfall',
      indicators: [
        {
          code: 'R2.1', name: 'Total rainfall',
          notebook: 'notebooks/historical/Regional/rainfall/regional_indicators',
          products: [
            { kind: 'map', mx: false, title: 'Station trends – total rainfall', path: '{OUT}/regional_pacific/R_regional_total_annual_mm_trend_pacific.png',
              caption: 'Linear trend of annual total rainfall at each station.' },
            { kind: 'map', mx: false, title: 'ERA5 mean rainfall', path: '{OUT}/regional_pacific/R_regional_total_annual_mm_mean_era5_pacific.png',
              caption: 'ERA5 mean annual total precipitation.' },
            { kind: 'map', title: 'ERA5 rainfall trend', path: '{OUT}/regional_pacific/R_regional_total_annual_mm_trend_era5_pacific.png',
              caption: 'ERA5 linear trend of annual total precipitation.' },
          ],
          tables: [
            { title: 'Summary table', path: '{TAB}/regional_pacific/R_regional_summary_table_total_pacific.csv' },
            { title: 'EEZ summary – stations', path: '{TAB}/regional_pacific/R_regional_EEZ_total_stations_pacific.csv' },
            { title: 'EEZ summary – ERA5', path: '{TAB}/regional_pacific/R_regional_EEZ_total_era5_pacific.csv' },
          ],
        },
        {
          code: 'R2.2', name: 'Dry conditions',
          notebook: 'notebooks/historical/Regional/rainfall/regional_indicators',
          products: [
            { kind: 'map', title: 'Dry days trend', path: '{OUT}/regional_pacific/R_regional_dry_days_trend_pacific.png',
              caption: 'Trend in annual dry days (below 1 mm) at each station.' },
            { kind: 'map', title: 'Max consecutive dry days', path: '{OUT}/regional_pacific/R_regional_max_consecutive_dry_days_trend_pacific.png',
              caption: 'Trend in the annual maximum dry-spell length.' },
            { kind: 'map', title: 'Mean consecutive dry days', path: '{OUT}/regional_pacific/R_regional_mean_consecutive_dry_days_trend_pacific.png',
              caption: 'Trend in the mean dry-spell length.' },
          ],
          tables: [
            { title: 'Summary table', path: '{TAB}/regional_pacific/R_regional_summary_table_dry_pacific.csv' },
            { title: 'EEZ summary – stations', path: '{TAB}/regional_pacific/R_regional_EEZ_dry_stations_pacific.csv' },
          ],
        },
        {
          code: 'R2.3', name: 'Heavy rainfall',
          notebook: 'notebooks/historical/Regional/rainfall/regional_indicators',
          products: [
            { kind: 'map', title: 'Wet days trend', path: '{OUT}/regional_pacific/R_regional_wet_days_trend_pacific.png',
              caption: 'Trend in annual wet days (above 1 mm).' },
            { kind: 'map', title: 'Heavy rainfall days trend', path: '{OUT}/regional_pacific/R_regional_heavy_days_trend_pacific.png',
              caption: 'Trend in annual heavy rainfall days (above the 95th percentile).' },
          ],
          tables: [
            { title: 'Summary table', path: '{TAB}/regional_pacific/R_regional_summary_table_heavy_pacific.csv' },
            { title: 'EEZ summary – stations', path: '{TAB}/regional_pacific/R_regional_EEZ_heavy_stations_pacific.csv' },
          ],
        },
      ],
    },
    {
      domain: 'Atmosphere', variable: 'Tropical Cyclones', icon: 'cyclone',
      page: 'notebooks/historical/Regional/tropical_cyclones/tropical_cyclones',
      indicators: [
        {
          code: 'R3.1', name: 'Tracks and spatial patterns',
          notebook: 'notebooks/historical/Regional/tropical_cyclones/regional_indicators',
          products: [
            { kind: 'map', title: 'Pacific TC subregions', path: '{OUT}/regional_pacific/TC_regional_subregions_pacific.png',
              caption: 'Subregions used to aggregate tropical-cyclone statistics.' },
            { kind: 'map', title: 'Tracks by genesis subregion', path: '{OUT}/regional_pacific/TC_regional_genesis_tracks_pacific.png',
              caption: 'Historical cyclone tracks coloured by genesis subregion (IBTrACS).' },
            { kind: 'map', title: 'Track density', path: '{OUT}/regional_pacific/TC_regional_track_density_pacific.png',
              caption: 'Spatial density of cyclone tracks.' },
            { kind: 'map', title: 'Period comparison', path: '{OUT}/regional_pacific/TC_regional_period_comparison_pacific.png',
              caption: 'Difference in track density between two periods.' },
            { kind: 'map', title: 'Regional activity dashboard', path: '{OUT}/regional_pacific/TC_regional_map_dashboard_pacific.png',
              caption: 'Per-subregion activity charts plotted over the Pacific map.' },
          ],
          tables: [
            { title: 'Summary table – storm counts', path: '{TAB}/regional_pacific/TC_regional_summary_table_counts_pacific.csv' },
          ],
        },
        {
          code: 'R3.2', name: 'Frequency, intensity & energy',
          notebook: 'notebooks/historical/Regional/tropical_cyclones/regional_indicators',
          products: [
            { kind: 'plot', title: 'Annual storm counts', path: '{OUT}/regional_pacific/TC_regional_annual_counts_pacific.png',
              caption: 'Annual number of tropical cyclones per subregion with trends.' },
            { kind: 'plot', title: 'Intensity composition', path: '{OUT}/regional_pacific/TC_regional_intensity_composition_pacific.png',
              caption: 'Annual storm counts stacked by intensity category.' },
            { kind: 'plot', title: 'Monthly genesis', path: '{OUT}/regional_pacific/TC_regional_monthly_genesis_pacific.png',
              caption: 'Monthly distribution of cyclone genesis by intensity.' },
            { kind: 'plot', title: 'Accumulated Cyclone Energy', path: '{OUT}/regional_pacific/TC_regional_ace_pacific.png',
              caption: 'Annual Accumulated Cyclone Energy (ACE) per subregion.' },
          ],
          tables: [
            { title: 'Summary table – storm counts', path: '{TAB}/regional_pacific/TC_regional_summary_table_counts_pacific.csv' },
            { title: 'Summary table – ACE', path: '{TAB}/regional_pacific/TC_regional_summary_table_ace_pacific.csv' },
          ],
        },
      ],
    },
    {
      domain: 'Ocean', variable: 'Sea Surface Temperature', icon: 'wave',
      page: 'notebooks/historical/Regional/sea_surface_temperature/sea_surface_temperature',
      indicators: [
        {
          code: 'R4.1', name: 'Mean SST & trends',
          notebook: 'notebooks/historical/Regional/sea_surface_temperature/regional_indicators',
          products: [
            { kind: 'map', mx: false, title: 'Regional mean SST', path: '{FIG}/SST_regional_mean.png',
              caption: 'Mean sea surface temperature over the Pacific (NOAA OISST).' },
            { kind: 'map', title: 'SST trend', path: '{FIG}/F19_SST_regional_trend.png',
              caption: 'Linear SST trend over the Pacific with EEZ boundaries.' },
            { kind: 'map', mx: false, title: 'DJF 5-year anomalies', path: '{FIG}/F20_SST_DJF_5year_anomalies.png',
              caption: 'Boreal-winter (DJF) SST anomalies by five-year period.' },
          ],
          tables: [
            { title: 'Summary table', path: '{TAB}/regional_pacific/SST_regional_summary_table_pacific.csv' },
            { title: 'EEZ summary', path: '{TAB}/regional_pacific/SST_regional_EEZ_summary_pacific.csv' },
          ],
        },
        {
          code: 'R4.2', name: 'Marine heatwaves',
          notebook: 'notebooks/historical/Regional/sea_surface_temperature/mhw_regional',
          products: [
            { kind: 'map', mx: false, title: 'Mean annual MHW days', path: '{FIG}/MHW_regional_mean_days.png',
              caption: 'Mean number of marine-heatwave days per year in each grid cell.' },
            { kind: 'map', title: 'Trend in MHW days', path: '{FIG}/MHW_regional_days_trend.png',
              caption: 'Linear trend in annual marine-heatwave days.' },
            { kind: 'map', mx: false, title: 'Frequency, duration & intensity', path: '{FIG}/MHW_regional_frequency_duration_intensity.png',
              caption: 'Mean MHW event frequency, duration and intensity.' },
            { kind: 'map', mx: false, title: '5-year MHW-day anomalies', path: '{FIG}/MHW_regional_5year_days_anomalies.png',
              caption: 'Recent five-year anomalies of MHW days.' },
            { kind: 'map', mx: false, title: 'Decadal summaries', path: '{FIG}/MHW_regional_decadal_summaries.png',
              caption: 'Decadal marine-heatwave summaries.' },
            { kind: 'plot', title: 'Annual MHW days & ENSO', path: '{FIG}/MHW_regional_annual_days_ENSO.png', enso: true,
              caption: 'Regional mean annual MHW days coloured by ENSO phase.' },
            { kind: 'map', mx: false, title: 'MHW anomalies by ENSO phase', path: '{FIG}/MHW_regional_ENSO_anomalies.png', enso: true,
              caption: 'MHW-day anomaly maps for La Niña, Neutral and El Niño.' },
          ],
          tables: [
            { title: 'Summary table', path: '{TAB}/regional_pacific/MHW_regional_summary_table_pacific.csv' },
            { title: 'EEZ summary', path: '{TAB}/regional_pacific/MHW_regional_EEZ_summary_pacific.csv' },
            { title: 'EEZ summary by ENSO phase', enso: true, path: '{TAB}/regional_pacific/MHW_regional_EEZ_ENSO_summary_pacific.csv' },
          ],
        },
      ],
    },
    {
      domain: 'Ocean', variable: 'Ocean Biogeochemistry', icon: 'leaf',
      page: 'notebooks/historical/Regional/biochemistry/biochemistry',
      indicators: [
        bioRegional('R5.1', 'Ocean acidification: pH', 'a_oceanic_pH', 'ph', 'pH'),
        bioRegional('R5.2', 'Chlorophyll-a', 'b_chlorophyll', 'chl', 'chlorophyll-a'),
        bioRegional('R5.3', 'Phytoplankton size (MD50)', 'c_phytoplankton', 'MD50', 'median phytoplankton size (MD50)'),
        bioRegional('R5.4', 'Phytoplankton biomass', 'c2_phytoplankton', 'phyc', 'phytoplankton biomass'),
        bioRegional('R5.5', 'Dissolved oxygen (O₂)', 'd_dissolved_o2', 'o2', 'dissolved oxygen'),
        { code: 'R5.6', name: 'Aragonite saturation state', notebook: 'notebooks/projections/Regional/biochemistry/b_aragonite', products: [] },
        { code: 'R5.7', name: 'Sea surface salinity', notebook: 'notebooks/projections/Regional/biochemistry/c_salinity', products: [] },
      ],
    },
  ],
};

// Atmospheric CO2 (NOAA Mauna Loa + CMIP6 SSP pathways): one global record, shown at both scales.
function co2Group(code, mxGrowth = true) {
  const nb = 'notebooks/historical/Regional/greenhouse_gases/co2_mauna_loa';
  return {
    domain: 'Atmosphere', variable: 'Greenhouse Gases', icon: 'globe',
    page: 'notebooks/historical/Regional/greenhouse_gases/greenhouse_gases',
    indicators: [{
      code, name: 'Atmospheric CO₂ (Mauna Loa)', notebook: nb,
      products: [
        { kind: 'plot', title: 'Monthly CO₂ at Mauna Loa', path: '{OUT}/global/GHG_co2_mauna_loa_monthly.png',
          caption: 'Monthly mean CO₂ at NOAA’s Mauna Loa Observatory (red) and the series with the seasonal cycle removed (black).' },
        { kind: 'plot', mx: mxGrowth, title: 'Annual growth rate', path: '{OUT}/global/GHG_co2_mauna_loa_growth_rate.png',
          caption: 'Annual increase of CO₂ at Mauna Loa (bars) and decadal means (red lines).' },
      ],
      tables: [
        { title: 'Summary table', path: '{TAB}/global/GHG_co2_summary_table.csv' },
        { title: 'Growth rate by decade', path: '{TAB}/global/GHG_co2_growth_rate_by_decade.csv' },
        { title: 'Annual means', path: '{TAB}/global/GHG_co2_mauna_loa_annual.csv' },
      ],
      projections: {
        notebook: 'notebooks/projections/Regional/greenhouse_gases/co2_ssps',
        products: [
          { kind: 'plot', title: 'Observed CO₂ and SSP pathways', path: '{OUT}/global/GHG_co2_observed_and_ssps.png',
            caption: 'Mauna Loa annual means with the CMIP6 global-mean CO₂ concentration of SSP1-1.9 to SSP5-8.5 (Meinshausen et al., 2020).' },
        ],
        tables: [
          { title: 'SSP concentrations', path: '{TAB}/global/GHG_co2_ssp_concentrations.csv' },
        ],
      },
    }],
  };
}

function bioNational(code, name, nb, prefix, label) {
  return {
    code, name,
    notebook: 'notebooks/historical/National/biochemistry/' + nb,
    products: [
      { kind: 'map', title: 'Mean', path: `{FIG}/{natfig}${prefix}_mean_map.png`, sites: ['palau', 'marshall'],
        caption: `Long-term mean ${label} in the vicinity of the site.` },
      { kind: 'map', title: 'Change', path: `{FIG}/{natfig}${prefix}_mean_map_trend.png`, sites: ['palau', 'marshall'],
        caption: `Linear trend in ${label}.` },
      { kind: 'interactive', title: 'Area-average time series', path: `{FIG}/{natfig}${prefix}_mean_trend.html`, sites: ['palau', 'marshall'],
        caption: `Area-averaged ${label} time series with linear trend.` },
      { kind: 'map', title: 'ENSO composites', path: `{FIG}/{natfig}${prefix}_ENSO.png`, sites: ['palau', 'marshall'], enso: true,
        caption: `Mean ${label} under La Niña, Neutral and El Niño conditions.` },
    ],
    tables: [
      { title: 'Summary table', path: `{FIG}/{natfig}${prefix}_summary_table.csv`, sites: ['palau', 'marshall'] },
    ],
  };
}

function bioRegional(code, name, nb, v, label) {
  return {
    code, name,
    notebook: 'notebooks/historical/Regional/biochemistry/' + nb,
    products: [
      { kind: 'map', mx: false, title: 'Long-term mean', path: `{FIG}/regional_${v}_mean.png`,
        caption: `Long-term mean ${label} over the Pacific.` },
      { kind: 'map', title: 'Linear trend', path: `{FIG}/regional_${v}_trend.png`,
        caption: `Linear trend in ${label}.` },
      { kind: 'map', mx: false, title: 'Seasonal climatology', path: `{FIG}/regional_${v}_seasonal.png`,
        caption: `Seasonal climatology of ${label}.` },
      { kind: 'map', mx: false, title: 'Seasonal anomaly', path: `{FIG}/regional_${v}_seasonal_anomaly.png`,
        caption: `Seasonal anomalies of ${label} relative to the annual mean.` },
      { kind: 'interactive', title: 'Regional time series', path: `{FIG}/regional_${v}_timeseries.html`,
        caption: `Area-weighted regional ${label} time series.` },
      { kind: 'map', mx: false, title: 'ENSO anomalies', path: `{FIG}/regional_${v}_enso_anomalies.png`, enso: true,
        caption: `${label[0].toUpperCase() + label.slice(1)} anomalies under La Niña, Neutral and El Niño conditions.` },
    ],
    tables: [
      { title: 'Summary table', path: `{TAB}/regional_pacific/regional_${v}_summary_table_pacific.csv` },
      { title: 'EEZ summary', path: `{TAB}/regional_pacific/regional_${v}_EEZ_summary_pacific.csv` },
    ],
  };
}

// ─────────────────────── NATIONAL PROJECTIONS & EXTRA TABLES ───────────────────────
// Projection figures and tables are written by notebooks/projections/National to
// outputs/figures/<station>/PRJ_<name>_<station>.png and outputs/tables/<station>/PRJ_<name>_<station>.csv.

function prj(nb, products, tables = []) {
  return {
    notebook: 'notebooks/projections/National/' + nb,
    products: products.map(([kind, title, name, caption]) => ({ kind, title, path: `{OUT}/{station}/PRJ_${name}_{station}.png`, caption })),
    tables: [
      ...tables.map(([title, name]) => ({ title, path: `{TAB}/{station}/PRJ_${name}_{station}.csv` })),
      { title: 'Warming-level years (IPCC AR6)', path: '{TAB}/global/PRJ_warming_level_crossing_years_ipcc.csv' },
    ],
  };
}

const PRJ_SCENARIOS = ['ssp126', 'ssp245', 'ssp370', 'ssp585'];
const GWL = 'at the year each scenario first reaches +1.5, +2.0, +2.5 and +3.0 °C of global warming; boxes show the spread across models.';

(() => {
  const byCode = Object.fromEntries(window.CINDRA.national.flatMap(g => g.indicators).map(i => [i.code, i]));
  const addTables = (code, tables) => { byCode[code].tables = [...(byCode[code].tables || []), ...tables]; };

  // Historical tables exported next to their figures
  addTables('3.1', [
    { title: 'Key metrics – site', path: '{FIG}/{natfig}T_TCs_key_metrics_site.csv', sites: ['palau', 'marshall'] },
    { title: 'Key metrics – basin', path: '{FIG}/{natfig}T_TCs_key_metrics_basin.csv', sites: ['palau', 'marshall'] },
  ]);
  addTables('3.2', [
    { title: 'Summary table – severe TCs', path: '{FIG}/{natfig}T_TCs_severe_summary.csv', sites: ['palau', 'marshall'] },
  ]);
  addTables('4.1', [{ title: 'Summary table', path: '{FIG}/{natfig}T_SST_summary_{eez}.csv' }]);
  addTables('4.2', [{ title: 'Days per bleaching alert level', path: '{FIG}/F13_DHW_days_per_alert_level.csv', sites: ['palau'] }]);
  addTables('4.3', [
    ['EEZ events', 'T_MHW_EEZ_events'], ['EEZ trends', 'T_MHW_EEZ_trends'],
    ['Top 10 – intensity', 'T_MHW_EEZ_top10_intensity'], ['Top 10 – duration', 'T_MHW_EEZ_top10_duration'],
    ['Point events', 'T_MHW_point_events'], ['EEZ vs point trends', 'T_MHW_EEZ_vs_point_trends'],
  ].map(([title, name]) => ({ title, path: `{MHW}/${name}.csv`, sites: ['palau'] })));

  const P = {
    '1.1': prj('air_temperature/a_mean_temperature', [
      ['plot', 'Projected mean temperature', 'air_temp_mean_timeseries', 'Annual mean temperature: ensemble mean ±1σ per scenario; vertical lines mark the warming-level years.'],
      ['plot', 'Temperature at warming levels', 'air_temp_mean_gwl', 'Local annual mean temperature ' + GWL],
      ['plot', 'Change at warming levels', 'air_temp_change_gwl', 'Local warming relative to 1850–1900 ' + GWL],
    ], [['Temperature at warming levels', 'air_temp_mean_gwl'], ['Change at warming levels', 'air_temp_change_gwl']]),
    '1.2': prj('air_temperature/b_min_max_temperature', [
      ...PRJ_SCENARIOS.map(sc => ['plot', `Anomalies – ${sc.toUpperCase()}`, `air_temp_minmax_${sc}`, `Mean, minimum and maximum temperature anomalies vs 2015–2035 under ${sc.toUpperCase()} (median, 25–75 % and 10–90 % ranges).`]),
      ['plot', 'Tmin at warming levels', 'air_temp_tasmin_gwl', 'Annual minimum temperature ' + GWL],
      ['plot', 'Tmax at warming levels', 'air_temp_tasmax_gwl', 'Annual maximum temperature ' + GWL],
    ], [['Tmin / Tmax at warming levels', 'air_temp_minmax_gwl']]),
    '1.3': prj('air_temperature/c_hot_cold_days', [
      ['plot', 'Warm days over time', 'air_temp_warmdays_timeseries', 'Warm-day anomalies vs 2015–2035 (multi-model fan chart).'],
      ['plot', 'Cold nights over time', 'air_temp_coldnights_timeseries', 'Cold-night anomalies vs 2015–2035 (multi-model fan chart).'],
      ['plot', 'Warm days at warming levels', 'air_temp_warmdays_gwl', 'Warm days per year ' + GWL],
      ['plot', 'Cold nights at warming levels', 'air_temp_coldnights_gwl', 'Cold nights per year ' + GWL],
    ], [['Warm days & cold nights at warming levels', 'air_temp_warm_cold_gwl']]),
    '2.1': prj('rainfall/a_Total_rainfall', [
      ['plot', 'Projected annual rainfall', 'rain_total_timeseries', 'Annual rainfall anomalies vs 2015–2035 (multi-model fan chart).'],
      ['plot', 'Rainfall at warming levels', 'rain_total_gwl', 'Annual rainfall ' + GWL + ' Dashed lines: 2015–2035 mean.'],
      ['plot', 'Rainfall change at warming levels', 'rain_total_change_gwl', 'Change in annual rainfall (%) vs 2015–2035 ' + GWL],
    ], [['Rainfall at warming levels', 'rain_total_gwl'], ['Rainfall change at warming levels', 'rain_total_change_gwl']]),
    '2.2': prj('rainfall/b_Dry_days', [
      ['plot', 'Dry days over time', 'rain_dry_days_timeseries', 'Dry-day anomalies vs 2015–2035 (multi-model fan chart).'],
      ['plot', 'Dry days at warming levels', 'rain_dry_days_gwl', 'Dry days per year ' + GWL],
    ], [['Dry days at warming levels', 'rain_dry_days_gwl']]),
    '2.3': prj('rainfall/c_Heavy_rainfall', [
      ['plot', 'Heavy-rainfall days over time', 'rain_heavy_days_timeseries', 'Heavy-rainfall day anomalies vs 2015–2035 (multi-model fan chart).'],
      ['plot', 'Heavy-rainfall days at warming levels', 'rain_heavy_days_gwl', 'Heavy-rainfall days per year ' + GWL],
      ['plot', 'Max daily rainfall over time', 'rain_yearmax_timeseries', 'Annual maximum daily rainfall anomalies vs 2015–2035 (multi-model fan chart).'],
      ['plot', 'Max daily rainfall at warming levels', 'rain_yearmax_gwl', 'Annual maximum daily rainfall ' + GWL],
    ], [['Heavy-rainfall days at warming levels', 'rain_heavy_days_gwl'], ['Max daily rainfall at warming levels', 'rain_yearmax_gwl']]),
    '3.1': prj('tropical_cyclones/a_tropical_cyclones', [
      ['map', 'Historical vs shifted tracks', 'tc_tracks', 'Historical IBTrACS tracks (left) and the same tracks shifted poleward (right), coloured by category.'],
      ['map', 'Tracks – zoom', 'tc_tracks_zoom', 'Historical and shifted tracks within ±10° of the site.'],
      ['plot', 'Storms by category', 'tc_categories', 'Number of storms within the search radius by category, historical and shifted.'],
      ['map', 'Track density', 'tc_density', 'Smoothed track density, historical and shifted.'],
    ], [['Storms by category', 'tc_categories']]),
    '4.1': prj('sea_surface_temperature/a_Mean_Temperature', [
      ['plot', 'Projected SST – EEZ', 'sst_eez_timeseries', 'EEZ-average annual SST: ensemble mean ±1σ per scenario.'],
      ['plot', 'SST at warming levels – EEZ', 'sst_eez_gwl', 'EEZ-average SST ' + GWL],
      ['plot', 'Projected SST – site', 'sst_point_timeseries', 'Annual SST at the grid cell nearest to the site.'],
      ['plot', 'SST at warming levels – site', 'sst_point_gwl', 'SST at the site ' + GWL],
    ], [['SST at warming levels – EEZ', 'sst_eez_gwl'], ['SST at warming levels – site', 'sst_point_gwl']]),
    '4.3': prj('sea_surface_temperature/c_MHW', [
      ['plot', 'MHW days by category', 'mhw_timeseries', 'EEZ-average MHW days per year by category (ensemble mean ± std), SSP1-2.6 and SSP5-8.5.'],
      ['plot', 'MHW days – panels by category', 'mhw_timeseries_by_category', 'MHW days per year for each category, individual models and ensemble mean.'],
      ['plot', 'Days with any MHW', 'mhw_total_days', 'MHW days per year, all categories combined.'],
      ['plot', 'Stacked categories', 'mhw_stacked', 'Ensemble-mean MHW days per year stacked by category.'],
      ['plot', 'Categories at warming levels', 'mhw_categories_gwl_ssp585', 'MHW days per category under SSP5-8.5 ' + GWL],
      ['plot', 'Categories at warming levels (violins)', 'mhw_categories_violin_ssp585', 'MHW days per category under SSP5-8.5 at each warming level.'],
    ], [['MHW categories at warming levels', 'mhw_categories_gwl']]),
    '5.1': prj('biochemistry/a_oceanic_pH', [
      ['plot', 'Projected pH', 'ph_timeseries', 'Surface pH (CMIP6, IPCC Atlas): ensemble mean ±1σ per scenario.'],
      ['plot', 'pH at warming levels', 'ph_gwl', 'Surface pH ' + GWL],
      ...PRJ_SCENARIOS.map(sc => ['plot', `pH maps – ${sc.toUpperCase()}`, `ph_maps_timeseries_${sc}`, `Decadal surface pH at the site and maps of the region under ${sc.toUpperCase()} (Jiang et al., 2023).`]),
    ], [['pH at warming levels', 'ph_gwl'], ['pH by decade', 'ph_ocads_decadal']]),
    '5.5': prj('biochemistry/b_aragonite',
      PRJ_SCENARIOS.map(sc => ['plot', `Aragonite – ${sc.toUpperCase()}`, `aragonite_maps_timeseries_${sc}`, `Decadal aragonite saturation state at the site and maps of the region under ${sc.toUpperCase()} (Jiang et al., 2023).`]),
      [['Aragonite saturation by decade', 'aragonite_ocads_decadal']]),
    '5.6': prj('biochemistry/c_salinity',
      PRJ_SCENARIOS.map(sc => ['plot', `Salinity – ${sc.toUpperCase()}`, `salinity_maps_timeseries_${sc}`, `Decadal sea surface salinity at the site and maps of the region under ${sc.toUpperCase()} (Jiang et al., 2023).`]),
      [['Salinity by decade', 'salinity_ocads_decadal']]),
  };
  Object.entries(P).forEach(([code, p]) => { byCode[code].projections = p; });
})();

// ─────────────────────────── REGIONAL PROJECTIONS ───────────────────────────
// Written by notebooks/projections/Regional to outputs/figures/regional_pacific/PRJ_<name>_pacific.png
// and outputs/tables/regional_pacific/PRJ_<name>_pacific.csv.

const PRJ_REGIONS = [
  ['North Pacific Subtropical Gyre', 'north_pacific_subtropical_gyre'],
  ['Equatorial Upwelling', 'equatorial_upwelling'],
  ['Western Equatorial Pacific', 'western_equatorial_pacific'],
  ['South Pacific Subtropical Gyre', 'south_pacific_subtropical_gyre'],
];
const RFIG = name => `{OUT}/regional_pacific/PRJ_${name}_pacific.png`;
const RTAB = name => `{TAB}/regional_pacific/PRJ_${name}_pacific.csv`;

// Trend map, warming-level map and ocean-region box plots of one indicator (`v`, `label`).
function prjRegionalIndicator(v, label, mapScenario = 'ssp370', absolute = false) {
  const what = absolute ? label : `Change in ${label.toLowerCase()} vs 2015–2035`;
  return {
    products: [
      { kind: 'map', title: `${label} – trend by EEZ`, path: RFIG(`${v}_trend_eez`),
        caption: `Linear trend over 2015–2100 of the multi-model median ${absolute ? '' : 'change in '}${label.toLowerCase()} in each EEZ, one panel per scenario.` },
      { kind: 'map', title: `${label} – warming levels by EEZ`, path: RFIG(`${v}_gwl_eez_${mapScenario}`),
        caption: `${what} in each EEZ in the year ${mapScenario.toUpperCase()} reaches +1.5, +2.0, +2.5 and +3.0 °C (multi-model median).` },
      ...PRJ_REGIONS.map(([region, slug]) => ({ kind: 'plot', title: `${label} – ${region}`, path: RFIG(`${v}_gwl_${slug}`),
        caption: `${what} averaged over the ${region} at each global warming level; boxes show the spread across models.` })),
    ],
    tables: [
      { title: `${label} – trend by EEZ / region`, path: RTAB(`${v}_trend_regions`) },
      { title: `${label} – warming levels by EEZ / region`, path: RTAB(`${v}_gwl_regions_${mapScenario}`) },
      { title: `${label} – ocean regions at warming levels`, path: RTAB(`${v}_gwl_ocean_regions`) },
    ],
  };
}

// Decadal OCADS products (no model spread): change map and ocean-region series.
function prjRegionalOcads(v, label) {
  return {
    products: [
      { kind: 'map', title: `${label} – change 2020–2100 by EEZ`, path: RFIG(`${v}_change_eez`),
        caption: `Change in ${label.toLowerCase()} between 2020 and 2100 in each EEZ, one panel per scenario (Jiang et al., 2023).` },
      { kind: 'plot', title: `${label} – ocean regions`, path: RFIG(`${v}_ocean_regions`),
        caption: `Decadal ${label.toLowerCase()} in the four ocean regions, one line per scenario (Jiang et al., 2023).` },
    ],
    tables: [
      { title: `${label} – change by EEZ / region`, path: RTAB(`${v}_change_regions`) },
      { title: `${label} – ocean regions by decade`, path: RTAB(`${v}_ocean_regions`) },
    ],
  };
}

function prjRegional(nb, parts) {
  return {
    notebook: 'notebooks/projections/Regional/' + nb,
    products: [
      { kind: 'map', title: 'EEZs and ocean regions', path: RFIG('regions_map'),
        caption: 'Pacific EEZs and the four ocean regions used in the regional projection analysis.' },
      ...parts.flatMap(p => p.products),
    ],
    tables: [
      ...parts.flatMap(p => p.tables),
      { title: 'Warming-level years (IPCC AR6)', path: '{TAB}/global/PRJ_warming_level_crossing_years_ipcc.csv' },
    ],
  };
}

(() => {
  const byCode = Object.fromEntries(window.CINDRA.regional.flatMap(g => g.indicators).map(i => [i.code, i]));
  const R = {
    'R1.1': prjRegional('air_temperature/regional_indicators', [prjRegionalIndicator('tas', 'Mean temperature')]),
    'R1.2': prjRegional('air_temperature/regional_indicators', [prjRegionalIndicator('tasmin', 'Minimum temperature'), prjRegionalIndicator('tasmax', 'Maximum temperature')]),
    'R1.3': prjRegional('air_temperature/regional_indicators', [prjRegionalIndicator('warmdays', 'Warm days'), prjRegionalIndicator('coldnights', 'Cold nights')]),
    'R2.1': prjRegional('rainfall/regional_indicators', [prjRegionalIndicator('pr', 'Annual rainfall')]),
    'R2.2': prjRegional('rainfall/regional_indicators', [prjRegionalIndicator('dry_days', 'Dry days')]),
    'R2.3': prjRegional('rainfall/regional_indicators', [prjRegionalIndicator('heavyraindays', 'Heavy-rainfall days'), prjRegionalIndicator('yearmax', 'Annual maximum daily rainfall')]),
    'R4.1': prjRegional('sea_surface_temperature/regional_indicators', [prjRegionalIndicator('tos', 'Sea surface temperature')]),
    'R4.2': prjRegional('sea_surface_temperature/mhw_regional', [prjRegionalIndicator('mhw_days', 'Marine heatwave days', 'ssp585', true)]),
    'R5.1': prjRegional('biochemistry/a_oceanic_pH', [prjRegionalIndicator('ph', 'Surface pH'), prjRegionalOcads('pHT', 'pH')]),
    'R5.6': prjRegional('biochemistry/b_aragonite', [prjRegionalOcads('aragonite', 'Aragonite saturation state')]),
    'R5.7': prjRegional('biochemistry/c_salinity', [prjRegionalOcads('salinity', 'Sea surface salinity')]),
  };
  Object.entries(R).forEach(([code, p]) => { byCode[code].projections = p; });
})();
