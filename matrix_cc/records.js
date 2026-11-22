// CIndRA product records: the hand-written "source-of-record" content shown with every product of the
// matrix (CIndRA CMPLV description, 11.01.26). index.html combines it with products.js (captions, paths) and
// inventory.js (run dates, file inventory, code version, data copies; built by build_inventory_js.py) to
// assemble the record and its validation checks.
//
// Edit this file to document an indicator:
//   indicators['<code>']            one entry per indicator code of products.js ('1.1', 'R2.3', ...)
//     methodId                      stable method identifier, cited in the record
//     methods                       short reproducible methods note (data, calculation, QC, period/baseline,
//                                   spatial treatment, aggregation, product-generation steps)
//     limitations                   list of known constraints and caveats
//     sources                       keys of `sources` below
//     parameters                    { name: value } used by the notebook
//     units                         default units; products: { '<product title>': { units } } overrides
//     spatial                       spatial scope; tokens {site}, {station}
//     qc                            QC reference (what was filtered / checked and where)
//     review                        { status: 'pending' | 'in-review' | 'approved', by, date, notes }
//     projections                   same fields, for the indicator's projection products
//   sources['<key>']                dataset, provider, version, url, citation and `copy`: the local data
//                                   file(s) the notebook reads (tokens {ghcn}, {station}, {eez}); its date is
//                                   reported as the date of the local copy
//   issues['<id>']                  issue log entries; `codes` and `sites` select the products they affect
//
// A product is only labelled "Approved for report use" when review.status is 'approved' AND every
// validation check passes (CMPLV: human scientific review, complete provenance, successful validation).

window.CINDRA_RECORDS = {
  workflow: 'CIndRA matrix workflow v1 · CMPLV product record (11.01.26)',

  sources: {
    ghcn_temp: {
      dataset: 'GHCN-Daily (TMIN, TMAX)', provider: 'NOAA National Centers for Environmental Information (NCEI)',
      version: 'GHCN-Daily v3 (station files, accessed via NCEI)', url: 'https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/',
      citation: 'Menne, M.J., et al. (2012). Global Historical Climatology Network – Daily (GHCN-Daily), Version 3. NOAA NCEI. doi:10.7289/V5D21VHZ',
      copy: ['../data/air_temp/GHCN_{ghcn}.pkl'],
    },
    ghcn_prcp: {
      dataset: 'GHCN-Daily (PRCP)', provider: 'NOAA National Centers for Environmental Information (NCEI)',
      version: 'GHCN-Daily v3 (station files, accessed via NCEI)', url: 'https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/',
      citation: 'Menne, M.J., et al. (2012). Global Historical Climatology Network – Daily (GHCN-Daily), Version 3. NOAA NCEI. doi:10.7289/V5D21VHZ',
      copy: ['../data/rainfall/GHCN_{ghcn}.pkl'],
    },
    oni: {
      dataset: 'Oceanic Niño Index (ONI)', provider: 'NOAA Climate Prediction Center / Physical Sciences Laboratory',
      version: 'ONI v5 (ERSSTv5)', url: 'https://psl.noaa.gov/data/correlation/oni.data',
      citation: 'NOAA CPC, Cold & Warm Episodes by Season (ONI v5).',
      copy: ['../data/rainfall/oni_index.pkl'],
    },
    co2_mlo: {
      dataset: 'Mauna Loa CO₂ monthly means, annual means and annual growth rates', provider: 'NOAA Global Monitoring Laboratory (GML) / Scripps Institution of Oceanography',
      version: 'NOAA GML trends files co2_mm_mlo.txt, co2_annmean_mlo.txt, co2_gr_mlo.txt', url: 'https://gml.noaa.gov/ccgg/trends/',
      citation: 'Lan, X., Tans, P. and Thoning, K.W.: Trends in globally-averaged CO₂ determined from NOAA Global Monitoring Laboratory measurements. Keeling, R. (SIO).',
      copy: ['../data/ghg/co2_mm_mlo.txt', '../data/ghg/co2_annmean_mlo.txt', '../data/ghg/co2_gr_mlo.txt'],
    },
    ibtracs: {
      dataset: 'IBTrACS best-track tropical cyclone archive (all basins)', provider: 'NOAA NCEI',
      version: 'IBTrACS v04r01 (IBTrACS.ALL.v04r01.nc)', url: 'https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/netcdf/IBTrACS.ALL.v04r01.nc',
      citation: 'Knapp, K.R., et al. (2010). The International Best Track Archive for Climate Stewardship (IBTrACS). BAMS 91, 363–376. doi:10.1175/2009BAMS2755.1',
      copy: ['../data/tcs/tcs_WP.nc'],
    },
    oni_tc: {
      dataset: 'Oceanic Niño Index (ONI)', provider: 'NOAA Climate Prediction Center / Physical Sciences Laboratory',
      version: 'ONI v5 (ERSSTv5)', url: 'https://psl.noaa.gov/data/correlation/oni.data',
      citation: 'NOAA CPC, Cold & Warm Episodes by Season (ONI v5).',
      copy: ['../data/tcs/oni_index.pkl'],
    },
    uhslc: {
      dataset: 'UHSLC Fast Delivery tide-gauge sea level (daily and hourly)', provider: 'University of Hawaii Sea Level Center (UHSLC)',
      version: 'Fast Delivery NetCDF (level-1 QC)', url: 'https://uhslc.soest.hawaii.edu/data/netcdf/fast/',
      citation: 'Caldwell, P.C., Merrifield, M.A., Thompson, P.R. (2015). Sea level measured by tide gauges from global oceans — the Joint Archive for Sea Level holdings. NOAA NCEI. doi:10.7289/V5V40S7W',
      copy: ['../data/sea_level/d007.nc', '../data/sea_level/h007.nc'],
    },
    cmems_sl: {
      dataset: 'Global Ocean gridded L4 sea surface heights and derived variables (DUACS)', provider: 'Copernicus Marine Service (CMEMS)',
      version: 'SEALEVEL_GLO_PHY_L4_MY_008_047 (daily P1D national; monthly P1M-m regional)', url: 'https://doi.org/10.48670/moi-00148',
      citation: 'E.U. Copernicus Marine Service Information (CMEMS). Global Ocean Gridded L4 Sea Surface Heights And Derived Variables Reprocessed. doi:10.48670/moi-00148',
      copy: ['../data/sea_level/cmems_L4_SSH_0.125deg_1993_2025.nc', '../data/regional/sea_level/cmems_L4_SLA_monthly_0.25deg_pacific_1993_2025.nc'],
    },
    ar6_sl: {
      dataset: 'IPCC AR6 sea-level projections (total, medium confidence): ar6-regional-confidence (with vertical land motion) and ar6-regional_novlm-confidence (without)',
      provider: 'IPCC AR6 WGI / NASA Sea Level Change Team (Garner et al., 2021)',
      version: 'Zenodo record 6382554, version 20210809', url: 'https://doi.org/10.5281/zenodo.6382554',
      citation: 'Garner, G.G., et al. (2021). IPCC AR6 Sea Level Projections. Zenodo. doi:10.5281/zenodo.6382554; Fox-Kemper, B., et al. (2021). Ocean, Cryosphere and Sea Level Change. In: Climate Change 2021: The Physical Science Basis (IPCC AR6 WGI), Ch. 9.',
      copy: ['../data/projections/regional/sl_ar6_vlm_medium_locations.nc', '../data/projections/regional/sl_ar6_novlm_medium_pacific.nc', '../data/projections/regional/sl_ar6_novlm_medium_global_median.nc'],
    },
    warming_levels: {
      dataset: 'Global warming-level crossing years (IPCC AR6 SYR Figure SPM.4 multi-model mean)', provider: 'IPCC AR6 Synthesis Report',
      version: 'SPM.4 panel (a) data', url: 'https://www.ipcc.ch/report/ar6/syr/',
      citation: 'IPCC (2023). Climate Change 2023: Synthesis Report, Figure SPM.4.',
      copy: ['../data/projections/warming_levels_ipcc_ar6.pkl'],
    },
  },

  indicators: {},
  issues: {},
};

(() => {
  const R = window.CINDRA_RECORDS;

  // Shared pieces ------------------------------------------------------------------------------------------
  const station = 'GHCN-Daily station {station} ({site}); single-station point product, no spatial interpolation.';
  const ghcnQC = 'GHCN-Daily quality flags as distributed by NCEI; months and years with less than 75 % of daily '
    + 'observations removed by filter_by_time_completeness() in notebooks/historical/National/00_site_setup.ipynb '
    + '(the filtered series is the cached pickle read by the indicator notebook).';
  const trend = 'Linear trends are ordinary least-squares fits against year; a solid line marks p < 0.05, a dashed line p ≥ 0.05.';
  const stationLimits = [
    'Single station: values describe the station location and may not represent the whole country or EEZ.',
    'GHCN-Daily is quality-controlled but not homogenised: station relocations, instrument or observing-practice changes can introduce artificial jumps or trends.',
    'Missing data reduce comparability between years; the most recent year may be incomplete.',
    'Trend p-values assume independent annual values (no correction for autocorrelation); trends are descriptive.',
  ];
  const ghcnParams = { 'Reference period': '1961–1990 (WMO)', 'Completeness threshold': '75 % of days per month / year', 'Significance level': 'p < 0.05' };
  const pending = { status: 'pending', by: '', date: '', notes: 'Generated and packaged; awaiting human scientific review.' };

  // ── Greenhouse gases ──
  R.indicators['0.1'] = {
    methodId: 'CIndRA-M-GHG-01',
    methods: 'Monthly mean atmospheric CO₂ mole fraction measured at NOAA’s Mauna Loa Observatory (Hawaiʻi, 3400 m) since March 1958 is plotted '
      + 'as published by NOAA GML, together with NOAA’s seasonally-corrected series (the average seasonal cycle removed). Annual growth rates '
      + 'are NOAA’s published values (increase in concentration over each year) and are summarised as decadal means. The NOAA values are '
      + 'not recalculated: functions/co2.py downloads the three GML text files, parses them and the notebook produces the figures and tables.',
    limitations: [
      'Mauna Loa is a single background station: it represents the well-mixed global atmosphere, not local Pacific Island concentrations.',
      'The most recent months are preliminary and may be revised by NOAA.',
      'Gaps and the December 2022 – July 2023 measurements at Maunakea (after the Mauna Loa eruption) are handled by NOAA, not by CIndRA; early monthly means (to 1975) carry no daily-count information in the source file.',
    ],
    sources: ['co2_mlo'],
    parameters: { 'Series': 'monthly mean and deseasonalised (NOAA)', 'Growth rate': 'NOAA annual growth rate, decadal means' },
    units: 'ppm', products: { 'Annual growth rate': { units: 'ppm/year' } },
    spatial: 'Global background: Mauna Loa Observatory, Hawaiʻi (19.5° N, 155.6° W).',
    qc: 'NOAA GML quality control and data selection (only background air); values used as published.',
    review: pending,
  };
  R.indicators['R0.1'] = R.indicators['0.1'];

  // ── Air temperature ──
  R.indicators['1.1'] = {
    methodId: 'CIndRA-M-AT-01',
    methods: 'Daily mean temperature is computed as TMEAN = (TMAX + TMIN) / 2 from GHCN-Daily, averaged to annual means and expressed as anomalies '
      + 'relative to the 1961–1990 mean. The 10 warmest years of the record are highlighted, with absolute values on the right axis. Years are '
      + 'classified as El Niño, La Niña or Neutral with the Oceanic Niño Index for the ENSO composites. ' + trend,
    limitations: stationLimits,
    sources: ['ghcn_temp', 'oni'],
    parameters: ghcnParams,
    units: '°C (anomaly relative to 1961–1990)',
    spatial: station, qc: ghcnQC, review: pending,
  };
  R.indicators['1.2'] = {
    methodId: 'CIndRA-M-AT-02',
    methods: 'Annual means of daily minimum (TMIN) and maximum (TMAX) temperature from GHCN-Daily, and of the diurnal temperature range '
      + '(TMAX − TMIN), with linear trends over the record. ' + trend,
    limitations: stationLimits,
    sources: ['ghcn_temp'],
    parameters: ghcnParams,
    units: '°C',
    spatial: station, qc: ghcnQC, review: pending,
  };
  R.indicators['1.3'] = {
    methodId: 'CIndRA-M-AT-03',
    methods: 'ETCCDI percentile-based indices: hot days (TX90p, TMAX above the 90th percentile), cold nights (TN10p, TMIN below the 10th '
      + 'percentile), warm nights (TN90p, TMIN above the 90th percentile) and cold days (TX10p, TMAX below the 10th percentile). Percentiles '
      + 'are computed for each calendar day from the 1961–1990 base period with a centred 5-day window (functions/temp_func.py). The annual '
      + 'percentage of days exceeding the threshold is expressed as an anomaly from its base-period mean and converted to days per year '
      + '(× 3.6525). A fixed-percentile variant uses a single station-wide 90th / 10th percentile of the base period. ' + trend,
    limitations: [
      ...stationLimits,
      'Base-period exceedance rates are computed in-sample, without the bootstrap of Zhang et al. (2005); this can create a small artificial discontinuity at 1990/1991.',
      'Annual rates of incomplete years are computed from the available days only.',
    ],
    sources: ['ghcn_temp'],
    parameters: { ...ghcnParams, 'Percentile window': 'centred 5-day window', 'Thresholds': 'calendar-day 90th / 10th percentiles of TMAX and TMIN' },
    units: 'days/year (anomaly relative to the 1961–1990 mean)',
    spatial: station, qc: ghcnQC, review: pending,
  };

  // ── Rainfall ──
  const rainLimits = [
    ...stationLimits,
    'Rainfall varies strongly over short distances; a single gauge is a weak proxy for national rainfall.',
  ];
  R.indicators['2.1'] = {
    methodId: 'CIndRA-M-RF-01',
    methods: 'Annual rainfall from GHCN-Daily PRCP, computed as the mean daily precipitation × 365.25 so that years with missing days are '
      + 'normalised to a full year, expressed as anomalies relative to the 1961–1990 mean; the 10 wettest years are highlighted. Dry-season '
      + '(November–April) and wet-season (May–October) totals are computed in the same way. ENSO composites use the Oceanic Niño Index. ' + trend,
    limitations: [...rainLimits, 'Normalising to 365.25 days assumes missing days are representative of the rest of the year.'],
    sources: ['ghcn_prcp', 'oni'],
    parameters: { ...ghcnParams, 'Seasons': 'dry Nov–Apr, wet May–Oct' },
    units: 'mm/year (anomaly relative to 1961–1990)',
    spatial: station, qc: ghcnQC, review: pending,
  };
  R.indicators['2.2'] = {
    methodId: 'CIndRA-M-RF-02',
    methods: 'Each day is classified as dry when PRCP < 1 mm (WMO / ETCCDI convention). Products: annual number of dry days, longest run of '
      + 'consecutive dry days within each calendar year and mean length of dry spells. ' + trend,
    limitations: [...rainLimits, 'Dry spells that cross the year boundary are split between the two years.'],
    sources: ['ghcn_prcp'],
    parameters: { ...ghcnParams, 'Dry-day threshold': 'PRCP < 1 mm' },
    units: 'days/year', products: { 'Max consecutive dry days': { units: 'days' }, 'Mean consecutive dry days': { units: 'days' } },
    spatial: station, qc: ghcnQC, review: pending,
  };
  R.indicators['2.3'] = {
    methodId: 'CIndRA-M-RF-03',
    methods: 'Wet days are days with PRCP > 1 mm. Heavy-rainfall days are days with PRCP above the 95th percentile of all daily values of the '
      + 'station record (threshold rounded to 0.01 mm). Products are annual counts with linear trends. ' + trend,
    limitations: [
      ...rainLimits,
      'The heavy-rainfall threshold is the 95th percentile of all days of the full record, not of wet days in the 1961–1990 base period as in ETCCDI R95p; values are not directly comparable with ETCCDI R95p.',
    ],
    sources: ['ghcn_prcp'],
    parameters: { ...ghcnParams, 'Wet-day threshold': 'PRCP > 1 mm', 'Heavy-rainfall threshold': '95th percentile of all daily PRCP (full record)' },
    units: 'days/year',
    spatial: station, qc: ghcnQC, review: pending,
  };

  // ── Tropical cyclones ──
  const tcLimits = [
    'Best-track intensities differ between agencies; the WMO-agency wind is used, so categories may differ from JTWC-based climatologies.',
    'Counts before routine satellite monitoring (≈ 1970s) are likely incomplete, which can bias long-term trends.',
    'The 5° search radius is a convention: storms passing just outside it are not counted, and a storm passing at 5° may have had little local impact.',
    'Annual counts are small numbers; year-to-year variability (largely ENSO-driven) dominates and trends are uncertain.',
  ];
  const tcMethods = 'Tropical cyclone tracks from IBTrACS v04r01 (Western Pacific basin, storms from 1950 onwards) are selected when they pass '
    + 'within 5° of the site. Each storm is assigned a Saffir–Simpson category from the IBTrACS WMO wind (ibtracs_category, indicators_setup). '
    + 'Products show the selected tracks coloured by category and the annual number of storms by category, with a linear trend; ENSO composites '
    + 'group storms by the Oceanic Niño Index phase.';
  R.indicators['3.1'] = {
    methodId: 'CIndRA-M-TC-01',
    methods: tcMethods + ' All storms are included; storms without wind information are shown in grey.',
    limitations: tcLimits,
    sources: ['ibtracs', 'oni_tc'],
    parameters: { 'Basin': 'WP', 'Search radius': '5° around the site', 'First year': '1950', 'Wind': 'IBTrACS WMO wind (wmo_wind)' },
    units: 'storms/year', products: { 'Historical TC tracks': { units: 'track maps (category)' } },
    spatial: 'Circle of 5° radius around {site}.',
    qc: 'IBTrACS best-track QC by the reporting agencies; no additional filtering besides basin, period and search radius.',
    review: pending,
  };
  R.indicators['3.2'] = {
    ...R.indicators['3.1'],
    methodId: 'CIndRA-M-TC-02',
    methods: tcMethods + ' Severe tropical cyclones are those reaching category 3 or higher.',
    parameters: { ...R.indicators['3.1'].parameters, 'Severe': 'category ≥ 3' },
    products: { 'Severe TC tracks': { units: 'track maps (category)' } },
  };

  // ── Sea level ──
  const slLimits = [
    'UHSLC Fast Delivery data have level-1 QC only; Research Quality data can differ slightly.',
    'Tide gauges measure relative sea level, including vertical land motion; altimetry measures absolute sea level on a ~12–25 km grid.',
    'Trend p-values ignore autocorrelation and the strong ENSO variability of the western Pacific; trends over ~30 years are descriptive.',
    'Storm years (May–April) or months with less than 75 % coverage are left missing, never counted as zero.',
  ];
  const slSpatial = 'UHSLC tide gauge {sealevel} and the CMEMS altimetry grid over the {site} EEZ.';
  const slQC = 'UHSLC level-1 QC; months need ≥ 75 % of days and storm years ≥ 75 % of hours (functions/sea_level.py).';
  R.indicators['6.1'] = {
    methodId: 'CIndRA-M-SL-01',
    methods: 'Daily tide-gauge sea level (UHSLC Fast Delivery) and daily CMEMS altimetry at the nearest ocean cell are referenced to their 1993–2012 '
      + 'mean and fitted with ordinary least-squares trends over 1993–2024; the change is the fitted difference between the first and last day. '
      + 'Monthly altimetry gives per-cell trends and an EEZ-masked, cos(latitude)-weighted mean. The ENSO sensitivity regresses the detrended, '
      + 'de-seasoned gauge record on daily-interpolated ONI. ' + trend,
    limitations: slLimits, sources: ['uhslc', 'cmems_sl', 'oni'],
    parameters: { 'Period': '1993–2024', 'Reference': '1993–2012 mean', 'Significance level': 'p < 0.05' },
    units: 'mm/yr (rate), cm (change)', spatial: slSpatial, qc: slQC, review: pending,
  };
  R.indicators['6.2'] = {
    methodId: 'CIndRA-M-SL-02',
    methods: 'The gauge record is detrended over 1993–2024 and the mean seasonal cycle removed; storm-year (May–April) mean, minimum and maximum '
      + 'of daily anomalies and monthly anomalies are shown with ONI-based El Niño / La Niña periods (±0.5 °C for ≥ 5 months). Altimetry is '
      + 'detrended per cell and averaged over groups of storm years.',
    limitations: slLimits, sources: ['uhslc', 'cmems_sl', 'oni'],
    parameters: { 'Period': '1993–2024', 'Storm year': 'May–April, labelled by starting year' },
    units: 'cm (anomaly)', spatial: slSpatial, qc: slQC, review: pending,
  };
  R.indicators['6.3'] = {
    methodId: 'CIndRA-M-SL-03',
    methods: 'Hourly gauge sea level is referenced to the UHSLC MHHW datum of the station tidal epoch. A minor-flood day has at least one hour '
      + 'more than 30 cm above MHHW; flood hours count hourly exceedances. Counts are per storm year from the year before the tidal epoch to the '
      + 'last complete storm year, coloured by the dominant ENSO phase. ' + trend,
    limitations: [...slLimits, 'The 30 cm threshold is a regional proxy; local impact thresholds, waves and drainage are not considered.'],
    sources: ['uhslc', 'oni'],
    parameters: { 'Threshold': '30 cm above MHHW', 'Datum': 'UHSLC MHHW (station tidal epoch)', 'Storm year': 'May–April' },
    units: 'days/year, hours/year', spatial: slSpatial, qc: slQC, review: pending,
  };
  R.indicators['6.4'] = {
    methodId: 'CIndRA-M-SL-04',
    methods: 'The ten highest and ten lowest hourly sea levels of the full gauge record, relative to MHHW and separated by more than three days, '
      + 'are ranked and labelled with the ONI phase of the event month.',
    limitations: slLimits, sources: ['uhslc', 'oni'],
    parameters: { 'Separation': '> 3 days', 'Datum': 'MHHW' },
    units: 'm above MHHW', spatial: slSpatial, qc: slQC, review: pending,
  };
  const slRegSpatial = 'Pacific window 125° E–115° W, 35° S–35° N; tide gauges within 0.5° of a Pacific EEZ (all gauges in the window for the change map; fixed list of 24 long-record gauges for the flood matrix).';
  R.indicators['R6.1'] = {
    methodId: 'CIndRA-M-SL-R01',
    methods: 'Monthly CMEMS altimetry (block-averaged to 0.25°) is fitted per cell with OLS trends over 1993–2025 and averaged with cos(latitude) '
      + 'weights. Tide-gauge monthly means (≥ 75 % of days) give relative trends for gauges with ≥ 70 % valid months; altimetry at the nearest '
      + 'ocean cell is sampled on the same months. The change map multiplies trends by the epoch length.',
    limitations: slLimits, sources: ['cmems_sl', 'uhslc'],
    parameters: { 'Period': '1993–2025', 'Grid': '0.25°', 'Valid months per station': '≥ 70 %' },
    units: 'mm/yr (trend), cm (change)', spatial: slRegSpatial, qc: slQC, review: pending,
  };
  R.indicators['R6.2'] = {
    methodId: 'CIndRA-M-SL-R02',
    methods: 'Five-year means of monthly altimetry relative to 1993–2012 (not detrended), and the regression of detrended, de-seasoned monthly sea '
      + 'level on the ONI at every cell.',
    limitations: slLimits, sources: ['cmems_sl', 'oni'],
    parameters: { 'Reference': '1993–2012', 'Blocks': '1995–1999 … 2020–2024' },
    units: 'cm, cm per °C', spatial: slRegSpatial, qc: slQC, review: pending,
  };
  R.indicators['R6.3'] = {
    methodId: 'CIndRA-M-SL-R03',
    methods: R.indicators['6.3'].methods + ' The regional total sums the stations with data in each storm year.',
    limitations: [...R.indicators['6.3'].limitations, 'Regional totals are lowered in years when a station is missing.'],
    sources: ['uhslc'], parameters: { ...R.indicators['6.3'].parameters, 'Matrix period': '1983–2025' },
    units: 'days/year', spatial: slRegSpatial, qc: slQC, review: pending,
  };

  // ── Sea-level projections (IPCC AR6) ──
  const slPrjLimits = [
    'Medium-confidence projections exclude low-likelihood, high-impact ice-sheet processes; the upper tail could be substantially higher, especially after 2100.',
    'Vertical land motion is extrapolated linearly from observed rates; it is uncertain where motion is episodic (e.g. post-seismic subsidence).',
    'AR6 values are decadal; annual values are interpolated between decades and anchored at 0 cm in 2005 (centre of 1995–2014).',
  ];
  const slMatch = 'Each UHSLC gauge is matched to the nearest AR6 (PSMSL) tide-gauge location within 30 km, otherwise to the nearest ocean grid cell (flagged).';
  const gwlText = 'Values are read in the year each SSP first reaches +1.5, +2.0, +2.5 and +3.0 °C (IPCC AR6 multi-model mean global surface temperature), as in the other projection notebooks.';
  R.indicators['6.1'].projections = {
    methodId: 'CIndRA-M-SL-P01',
    methods: 'IPCC AR6 relative sea-level projections with vertical land motion (ar6-regional-confidence, total, medium confidence) at the national '
      + 'tide gauge, for SSP1-2.6, SSP2-4.5, SSP3-7.0 and SSP5-8.5, relative to 1995–2014. ' + slMatch + ' ' + gwlText
      + ' The observed annual mean (≥ 75 % of days) is referenced to its own 1995–2014 mean. The VLM contribution is the difference with the '
      + 'no-VLM product at the same AR6 location.',
    limitations: slPrjLimits, sources: ['ar6_sl', 'uhslc', 'warming_levels'],
    parameters: { 'Product': 'AR6 total, medium confidence, with VLM', 'Reference': '1995–2014', 'Quantiles': '17th, 50th, 83rd (likely range)', 'Match radius': '30 km' },
    units: 'cm', spatial: 'UHSLC tide gauge {sealevel} (nearest AR6 tide-gauge location).', qc: 'Source quantiles used as published; matching distance reported in the notebook.', review: pending,
  };
  R.indicators['6.3'].projections = {
    methodId: 'CIndRA-M-SL-P03',
    methods: 'Hourly gauge sea level above the UHSLC MHHW datum of the last 19 complete storm years (one nodal cycle) is detrended to the 2005 '
      + 'mean sea level; for each sea-level offset the days with an hourly value more than 30 cm above MHHW are counted in every base year, '
      + 'giving a response curve. Projected flood days apply the AR6 relative sea-level projection (with VLM) at the gauge to that curve. '
      + gwlText + ' Simplification of Thompson et al. (2021), the method of the NASA Pacific Flooding Analysis Tool.',
    limitations: [...slPrjLimits,
      'Tidal nodal modulation and monthly sea-level variability are replayed from observed years rather than projected statistically.',
      'Curve ranges reflect the likely range of sea-level rise; warming-level boxes reflect interannual variability at the median rise.',
      'The 30 cm threshold is a regional proxy; local impact thresholds, waves and drainage are not considered.'],
    sources: ['ar6_sl', 'uhslc', 'warming_levels'],
    parameters: { 'Threshold': '30 cm above MHHW', 'Base years': 'last 19 complete storm years', 'Reference sea level': '2005 (centre of 1995–2014)' },
    units: 'days/year', spatial: 'UHSLC tide gauge {sealevel}.', qc: slQC, review: pending,
  };
  const slPrjRegSpatial = 'Pacific window 125° E–115° W, 35° S–35° N (1° grid, land masked with Natural Earth); UHSLC gauges within 0.5° of a Pacific EEZ.';
  R.indicators['R6.1'].projections = {
    methodId: 'CIndRA-M-SL-PR01',
    methods: 'IPCC AR6 sea-level projections without vertical land motion (ar6-regional_novlm-confidence, total, medium confidence) on the global '
      + '1° grid, relative to 1995–2014, for the four SSPs: change by 2050 and 2100, AR6 decadal rates around 2050 and 2100, and the least-squares '
      + 'trend of the decadal medians over 2020–2100. Cells whose centre is on land or Antarctic ice shelves are masked. Regional and EEZ means '
      + 'are cos(latitude)-weighted averages of each quantile.',
    limitations: [...slPrjLimits, 'Absolute sea level: excludes vertical land motion, so it differs from what tide gauges record.',
      'Averaging quantiles cell by cell approximates the uncertainty of area means.'],
    sources: ['ar6_sl'],
    parameters: { 'Product': 'AR6 total, medium confidence, no VLM', 'Reference': '1995–2014', 'Horizons': '2050, 2100', 'Trend period': '2020–2100' },
    units: 'cm (change), mm/yr (rate, trend)', spatial: slPrjRegSpatial, qc: 'Source quantiles used as published.', review: pending,
  };
  R.indicators['R6.4'] = { projections: {
    methodId: 'CIndRA-M-SL-PR04',
    methods: 'IPCC AR6 relative sea-level projections with vertical land motion (ar6-regional-confidence) at every UHSLC tide gauge within 0.5° '
      + 'of a Pacific EEZ, for the four SSPs and the end-of-century warming levels. ' + slMatch + ' The VLM contribution is the difference with '
      + 'the no-VLM product at the same location.',
    limitations: slPrjLimits, sources: ['ar6_sl', 'uhslc'],
    parameters: { 'Product': 'AR6 total, medium confidence, with VLM', 'Reference': '1995–2014', 'Horizons': '2050, 2100', 'Match radius': '30 km' },
    units: 'cm', spatial: slPrjRegSpatial, qc: 'Source quantiles used as published; matching distance per station in the tables.', review: pending,
  } };
  R.indicators['R6.5'] = { projections: {
    methodId: 'CIndRA-M-SL-PR05',
    methods: 'The gridded AR6 projections without vertical land motion (R6.1) and the tide-gauge projections with vertical land motion (R6.4) drawn '
      + 'on the same colour scale for 2050, 2100 and the 2020–2100 trend; the table gives, per station and scenario, the relative minus the '
      + 'absolute change at the same AR6 location (the vertical land motion contribution).',
    limitations: [...slPrjLimits, 'Grid and circles are different quantities (absolute vs relative sea level).'],
    sources: ['ar6_sl', 'uhslc'],
    parameters: { 'Products': 'AR6 total, medium confidence, with and without VLM', 'Reference': '1995–2014' },
    units: 'cm (change), mm/yr (trend)', spatial: slPrjRegSpatial, qc: 'Source quantiles used as published.', review: pending,
  } };

  // Issue log --------------------------------------------------------------------------------------------
  R.issues['ISS-001'] = {
    title: 'Koror TMAX drop from 2020',
    status: 'open',
    sites: ['palau'], codes: ['1.1', '1.2', '1.3'],
    text: 'Mean annual TMAX at Koror (GHCN PSW00040309) falls by about 2.5 °C between 2018 and 2021, with no hot days from 2021 and 240 cold '
      + 'days in 2021. Likely an instrument or observing-practice change; recent values and trends that include 2020 onwards should be checked '
      + 'before use. 2026 is a partial year (117 days).',
  };
})();
