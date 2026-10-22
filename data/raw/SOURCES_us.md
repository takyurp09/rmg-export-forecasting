# US imports of apparel from Bangladesh: sources

Download date: 2026-10-21. Script: `src/download_us_comtrade.py`.

## What was used

**UN Comtrade public preview API (no key)**

- Endpoint: `https://comtradeapi.un.org/public/v1/preview/C/M/HS`
- Query: `reporterCode=842` (USA), `partnerCode=50` (Bangladesh), `flowCode=M` (imports), monthly (`M`), HS 4-digit codes 6101 to 6117 and 6201 to 6217, one month per call (`period=YYYYMM`).
- Raw files: `data/raw/otexa/comtrade/us_from_bd_hs61_62_YYYYMM.json`, one per month.
- Tidy file: `data/processed/us_imports_bd_monthly.csv`.
- Coverage: 2010-01 to 2026-07 (199 months, 6,546 rows, 31 to 34 HS4 codes per month). Comtrade monthly data begins 2010-01. Aug to Oct 2026 were not yet available on 2026-10-21. Annual totals: about $4.1B in 2010 and $8.2B in 2025.

These are the US's own reported import figures (Census data passed on to Comtrade), so they should match OTEXA's dollar values for HS chapters 61 and 62 closely.

## Caveats

- `value_usd` is Comtrade's `primaryValue`, which equals `cifvalue` in these rows (CIF, not the customs value OTEXA reports, so a few percent higher). Check it against OTEXA or Census totals before using it as "customs value". The definitions may differ slightly.
- Comtrade's preview returns no unit quantities (dozens, pieces) for these rows. `quantity` holds net weight in kg instead. OTEXA's square-meter-equivalent (SME) quantities are not available here.
- The products are HS chapters, not OTEXA textile categories. `product_group` is just "HS61 knit" or "HS62 woven". The finer grouping (trousers, knit tops, sweaters and so on) should be built from the HS4 codes in `clean.py`.
- HS61/62 leave out some items OTEXA counts as apparel (for example, some made-ups and plastic apparel), so totals will be a bit lower than OTEXA's apparel figures.
- The preview API has a call-volume quota that refills on a timer. The script waits and retries, so a full run takes a while. Raw months are cached and are not downloaded twice.
- Recent months may be missing or revised later. Months with no data are not cached, so re-running picks them up.

## What was tried and not used

- **OTEXA (trade.gov).** The old `otexa.trade.gov` pages are gone (TLS name mismatch and a redirect to an unrelated login). The current pages, for example `https://www.trade.gov/otexa-import-data` and `https://www.trade.gov/data-visualization/us-textile-apparel-imports-category-or-country`, embed Power BI reports (`https://powerbi.trade.gov/#/workspace/OTEXA-PRODUCTION-PUBLIC/report/...`). There is no CSV/Excel link or public data API, so OTEXA data can only be exported by hand from the Power BI views. That is the way to get OTEXA category codes and SME quantities if they are needed.
- **US Census international trade API** (`https://api.census.gov/data/timeseries/intltrade/imports/hs`, `CTY_CODE=5380`). Without a key it now redirects to `missing_key.html`. A key is free (https://api.census.gov/data/key_signup.html). If `CENSUS_API_KEY` is set, the script uses Census instead and gets unit quantities (`GEN_QY1_MO`, `UNIT_QY1`).
