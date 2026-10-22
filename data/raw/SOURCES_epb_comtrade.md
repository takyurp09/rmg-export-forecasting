# Sources: EPB, UN Comtrade, Eurostat Comext

Download date for everything below: 2026-10-21.

## EPB (Export Promotion Bureau, Bangladesh)

- Listing page: https://epb.gov.bd/site/view/epb_export_data/-
- Files: Excel links on that page, hosted at
  https://objectstorage.ap-dcc-gazipur-1.oraclecloud15.com/n/axvjbnqprylg/b/V2Ministry/o/office-epb/...
- Script: `src/download_epb.py`. Raw files in `data/raw/epb/` (only files under 150 KB; the large HS-detail files are skipped).
- What we use: the "Summary Sheet" file for each reporting period. Rows "(18) RMG (61 & 62)", "(a) Knitwear (61)" and "(b) Woven Garments (62)", in million USD. Each sheet gives the current month, the previous month and the same month a year earlier.
- Output: `data/processed/bd_rmg_exports_monthly.csv`, Dec 2024 to Sep 2026, 63 rows (21 months x 3 groups). Oct 2025 is missing.
- Caveats:
  - The page only lists FY2025-26 and FY2026-27 periods. Older monthly files are no longer linked, so the FY2010+ monthly history is not available from EPB here.
  - When a month shows up in more than one sheet, the script takes the median. Later sheets can revise numbers.
  - epb.gov.bd's TLS chain fails Python's CA bundle, so the listing page is fetched with system `curl`.
- Annual context: BGMEA publishes fiscal-year RMG and total export values from 1983-84 at https://www.bgmea.com.bd/page/Export_Performance (annual only; not downloaded by a script).

## UN Comtrade (mirror data)

- Endpoint: https://comtradeapi.un.org/public/v1/preview/C/A/HS
  with `partnerCode=50&period=<year>&cmdCode=61,62&flowCode=M&customsCode=C00&motCode=0&partner2Code=0&includeDesc=true`
- No API key. One period per call, 500-record cap (not reached; max was 305).
- Script: `src/download_comtrade.py`. Raw JSON per year in `data/raw/comtrade/`.
- Output: `data/processed/bd_apparel_by_market_annual.csv`, 2010 to 2025, 4,591 rows, 185 reporting markets.
- Caveats:
  - These are partner imports from Bangladesh (CIF), not Bangladesh's own exports (FOB). Totals run well above EPB: about USD 50 billion in 2023 against about USD 38 billion from EPB for FY2022-23. CIF margins, timing, and EU members recording goods that arrive via another member all contribute.
  - Do not add EU members to an EU total and also use an EU aggregate. The file has no EU aggregate row.
  - 2024 and 2025 have fewer reporters (269 and 228 rows) because some countries have not reported yet.
  - HS vintage (H3 to H6) changes over time; HS 61/62 at 2 digits are stable.

## Eurostat Comext (optional EU series)

- URL: https://ec.europa.eu/eurostat/api/comext/dissemination/statistics/1.0/data/DS-045409?format=JSON&reporter=EU27_2020&partner=BD&product=61&product=62&flow=1&freq=M&indicators=VALUE_IN_EUROS
- Written by `src/download_comtrade.py` (function `eurostat`). Raw JSON in `data/raw/eurostat/`.
- Output: `data/processed/eu_imports_bd_monthly.csv`, Jan 1999 to Aug 2026, 664 rows (HS 61 and 62).
- Caveats: values are in euros and have not been converted to USD. EU27_2020 is a fixed composition (the UK is excluded throughout).
