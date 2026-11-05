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
