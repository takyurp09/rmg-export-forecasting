# Data dictionary

Every column in the six model tables. Power BI types are the ones set in `powerquery/*.pq`. Source files are in `data/processed/powerbi/`.

## dim_date

One row per month from Jan 1999 to Aug 2027 (344 rows). The range covers the EU history and the end of the EU forecast.

| Column | Power BI type | Description | Example |
|---|---|---|---|
| `date_key` | Whole number | Key, `yyyymmdd` of the first day of the month | `20260701` |
| `date` | Date | First day of the month | `2026-07-01` |
| `year` | Whole number | Calendar year | `2026` |
| `quarter` | Whole number | Calendar quarter, 1-4 | `3` |
| `month` | Whole number | Month number, 1-12. Sort key for `month_name` | `7` |
| `month_name` | Text | Three-letter month name | `Jul` |
| `bd_fiscal_year` | Whole number | Bangladesh fiscal year (July to June), labelled by the year it ends. Jul 2026 is FY2027 | `2027` |

## dim_market

| Column | Power BI type | Description | Example |
|---|---|---|---|
| `market_key` | Whole number | Key. 1 = US, 2 = EU | `1` |
| `market` | Text | Short name for slicers and legends | `US` |
| `market_name` | Text | Full name | `European Union (EU27_2020)` |
| `reporter_basis` | Text | How the values are reported | `US-reported imports, CIF` |

## dim_product

15 rows: 12 US product groups, 2 EU chapter rows, 1 total row.

| Column | Power BI type | Description | Example |
|---|---|---|---|
| `product_key` | Whole number | Key | `7` |
| `chapter` | Text | `Knit` (HS 61), `Woven` (HS 62) or `All` | `Knit` |
| `product_group` | Text | Product group name. Some names repeat across chapters | `T-shirts & vests (knit)` |
| `hs4_codes` | Text | HS codes in the group. Keep as text | `6109`, `6101,6102`, `other 61xx` |
| `market_scope` | Text | Market that uses this key: `US`, `EU`, or `US,EU` for the total | `US` |
| `is_total` | Whole number | 1 for key 15 (All products), else 0 | `0` |
| `product_label` | Text | Added in Power Query: `chapter & " - " & product_group`. Not in the CSV | `Knit - Coats & jackets` |

## fact_exports

Monthly imports from Bangladesh, HS 61-62, as reported by the importer. US from Jan 2010 to Jul 2026; EU from Jan 1999 to Aug 2026.

| Column | Power BI type | Description | Example |
|---|---|---|---|
| `date_key` | Whole number | FK to `dim_date` | `20260701` |
| `market_key` | Whole number | FK to `dim_market` | `1` |
| `product_key` | Whole number | FK to `dim_product`. Never 15 | `7` |
| `value_usd` | Decimal number | Import value, nominal USD, CIF | `55583059.98` |
| `value_usd_real2025` | Decimal number | Same value in 2025 prices | `108731619.06` |
| `source` | Text | Data source. `UN Comtrade US imports (CIF)` or `Eurostat Comext EU27 imports (EUR->USD, ECB EXR monthly avg)` | |

## fact_forecast

12-month forecasts per series with 80% and 95% intervals. US Aug 2026 to Jul 2027; EU Sep 2026 to Aug 2027.

| Column | Power BI type | Description | Example |
|---|---|---|---|
| `date_key` | Whole number | FK to `dim_date`, forecast month | `20260901` |
| `market_key` | Whole number | FK to `dim_market` | `2` |
| `product_key` | Whole number | FK to `dim_product`. 15 when `level = "Total"` | `15` |
| `level` | Text | `Total` (market total) or `Product group`. Do not sum the two together | `Total` |
| `model` | Text | Model picked for the series in the backtest: `ETS`, `Prophet`, `SARIMA` or `Seasonal naive` | `Prophet` |
| `point` | Decimal number | Point forecast, nominal USD | `2081661443.77` |
| `lo80` | Decimal number | Lower bound of the 80% interval | |
| `hi80` | Decimal number | Upper bound of the 80% interval | |
| `lo95` | Decimal number | Lower bound of the 95% interval | |
| `hi95` | Decimal number | Upper bound of the 95% interval | |

Interval bounds do not add up across product groups. Show them for one series at a time or for the `Total` row.

## fact_scenarios

Scenario results over a 12-month window, by market and product group (72 rows, 9 scenarios).

| Column | Power BI type | Description | Example |
|---|---|---|---|
| `scenario_key` | Whole number | Scenario id, 1-9. Not unique by itself | `3` |
| `scenario` | Text | Scenario name, including the low/mid/high variant | `S1 US demand -10% [mid]` |
| `market_key` | Whole number | FK to `dim_market` | `1` |
| `product_key` | Whole number | FK to `dim_product` | `7` |
| `window` | Text | 12-month window the scenario applies to | `2026-08 to 2027-07` |
| `baseline_usd` | Decimal number | Baseline imports over the window, USD | `106451451.85` |
| `scenario_usd` | Decimal number | Imports under the scenario, USD | `98272770.29` |
| `change_usd` | Decimal number | `scenario_usd - baseline_usd` | `-8178681.56` |
| `change_pct` | Decimal number | `change_usd / baseline_usd`, a fraction (-0.10 = -10%) | `-0.0768` |

Scenarios in the file:

| Key | Scenario | Markets |
|---|---|---|
| 1, 3, 5 | S1 US demand -10% [low / mid / high] | US |
| 2, 4, 6 | S2 EU 12% MFN duty (post-2029, no GSP) [low / mid / high] | EU |
| 7 | S2b EU 9.6% standard-GSP duty (post-2029) [mid] | EU |
| 8 | S3 Stress test S1 + S2 mid (not a dated forecast) | US, EU |
| 9 | S4 Repeat Jul-Aug 2024 disruption | US, EU |
