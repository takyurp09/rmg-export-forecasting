# Sources: competitor benchmark (HS 61+62)

Downloaded 2026-10-24 by `src/download_competitors.py`. Output: `data/processed/competitor_imports_monthly.csv`.

Suppliers: Bangladesh, China, Vietnam, India, Cambodia, Pakistan, Türkiye, Indonesia, Sri Lanka, plus the total from all suppliers.

## US imports

- UN Comtrade public preview API, no key: `https://comtradeapi.un.org/public/v1/preview/C/M/HS?reporterCode=842&partnerCode=0,50,156,704,699,116,586,792,360,144&flowCode=M&cmdCode=61,62&period=YYYYMM`
- One call per month, chapter totals 61 and 62. Raw JSON cached in `data/raw/competitors/comtrade/`.
- Rows kept: customsCode C00, motCode 0, partner2Code 0 (all procedures, all transport modes).
- Partner 0 is the world total. India is code 699 in Comtrade.
- Values are US-reported imports in USD. Comtrade files `primaryValue` as the CIF value (`cifvalue`; `fobvalue` is empty). It is the same basis for every supplier, so shares are comparable, but levels can differ a little from OTEXA tables, which use customs value.

## EU imports

- Eurostat Comext, dataset DS-045409: `https://ec.europa.eu/eurostat/api/comext/dissemination/statistics/1.0/data/DS-045409?format=JSON&reporter=EU27_2020&flow=1&freq=M&indicators=VALUE_IN_EUROS&product=61&product=62&partner=EXT_EU27_2020&partner=BD&partner=CN&...`
- Raw JSON saved in `data/raw/competitors/eurostat/`.
- Reporter is the EU27 (2020 composition) for the whole period, including years before the UK left.
- Denominator is EXT_EU27_2020, imports from outside the EU. Intra-EU trade (for example Italy to Germany, or re-exports through the Netherlands) is not in the market total, so EU shares here are shares of extra-EU imports.
- Values are CIF in EUR, converted to USD with the ECB monthly average rate in `data/raw/fx/ECB_EXR_M_USD_EUR.csv`. Months without an ECB rate yet are dropped.

## Caveats

- Both markets are on a CIF basis, so supplier values include freight and insurance. Freight swings (for example 2021-22) move values without any change in garments shipped. Shares within a market are fine; comparing levels across markets is rough.
- Values are nominal. A share change can come from prices (unit values) as well as volumes.
- Annual shares use only calendar years with 12 months of data for the market total.
- Only nine named suppliers. The rest (Mexico, Central America, Italy for the US, Morocco and others for the EU) sit in "all other suppliers".
- Recent months can be revised by both agencies.
