# Power BI build guide

This builds the 4-page report in PLAN.md 1.3E from the CSVs in `data/processed/powerbi/`. Save the file as `dashboard/rmg_dashboard.pbix`. Allow about two hours.

## 0. Design files

These text files hold the model and report design. The steps below use them.

| File | What it is |
|---|---|
| `powerquery/pDataFolder.pq` | Parameter: the folder that holds the six CSVs |
| `powerquery/<table>.pq` | One query per table, with column types set |
| `dax/measures.dax` | Full measure library, grouped by display folder |
| `theme/report_theme.json` | Report theme (US `#1F4E79`, EU `#0F8B8D`) |
| `docs/SCHEMA.md` | Star schema, keys and relationships |
| `docs/DATA_DICTIONARY.md` | Every column of every table |
| `docs/DASHBOARD_SPEC.md` | Visuals, fields, slicers and interactions for the four pages |
| `scripts/validate_model.py` | Checks keys, orphans, duplicates and types in the CSVs |

Run `python scripts/validate_model.py` before building. It should end with "Validation passed." and print the forecast and scenario check values used below.

## 1. The tables

| File | Rows | Columns |
|---|---|---|
| `dim_date.csv` | 344 | `date_key, date, year, quarter, month, month_name, bd_fiscal_year` (Jan 1999 to Aug 2027) |
| `dim_market.csv` | 2 | `market_key, market, market_name, reporter_basis` (1 = US, 2 = EU) |
| `dim_product.csv` | 15 | `product_key, chapter, product_group, hs4_codes, market_scope, is_total` (15 = "All products", `is_total = 1`) |
| `fact_exports.csv` | 3,052 | `date_key, market_key, product_key, value_usd, value_usd_real2025, source` |
| `fact_forecast.csv` | 192 | `date_key, market_key, product_key, level, model, point, lo80, hi80, lo95, hi95` |
| `fact_scenarios.csv` | 72 | `scenario_key, scenario, market_key, product_key, window, baseline_usd, scenario_usd, change_usd, change_pct` |

Things to know before you start:

- US product keys (1, 3-11, 13, 14) are the 12 US groups. EU keys 2 and 12 are knit and woven for the whole chapter. Key 15 is only used by forecast rows with `level = Total`.
- `fact_exports` has no total rows. Totals come from summing.
- `fact_forecast` mixes group rows and total rows. Filter `level` so they are not summed together.
- `change_pct` in `fact_scenarios` is a fraction (-0.10 = -10%).
- `fact_scenarios` has no date. Its `window` column is text.

## 2. Import

1. Home > Transform data. Create the `pDataFolder` parameter from `powerquery/pDataFolder.pq` and set it to your full path to `data/processed/powerbi/` (ending with a slash).
2. For each table, New Source > Blank Query > Advanced Editor, paste the matching `powerquery/<table>.pq`, and name the query after the file. The queries already set the types below. (Or use Get data > Text/CSV for each file and set the types by hand.)
3. The types to expect:
   - `date_key`, `market_key`, `product_key`, `scenario_key`: Whole number.
   - `dim_date[date]`: Date.
   - `value_usd`, `value_usd_real2025`, `point`, `lo80` ... `hi95`, `baseline_usd`, `scenario_usd`, `change_usd`: Decimal number.
   - `change_pct`: Decimal number, then format as percentage in the model.
   - `hs4_codes`: Text (Power BI may try to read "61" as a number).
4. Close & Apply.

## 3. Relationships

Model view. Delete any relationships Power BI guessed, then create these. All are many-to-one, single direction (dimension filters fact).

| From (many) | To (one) |
|---|---|
| `fact_exports[date_key]` | `dim_date[date_key]` |
| `fact_exports[market_key]` | `dim_market[market_key]` |
| `fact_exports[product_key]` | `dim_product[product_key]` |
| `fact_forecast[date_key]` | `dim_date[date_key]` |
| `fact_forecast[market_key]` | `dim_market[market_key]` |
| `fact_forecast[product_key]` | `dim_product[product_key]` |
| `fact_scenarios[market_key]` | `dim_market[market_key]` |
| `fact_scenarios[product_key]` | `dim_product[product_key]` |

Then:

- Select `dim_date` > Table tools > Mark as date table > column `date`.
- Sort `dim_date[month_name]` by `month`.
- Hide the key columns in the fact tables (right-click > Hide in report view).
- Create a `Measures` table: Home > Enter data, one dummy column, name it `_Measures`. Put every measure below in it.

## 4. DAX measures

The full library is in `dax/measures.dax`, with display folders and format strings. You can apply it with Tabular Editor or type the measures in by hand. Its names are capitalised slightly differently (for example `Total Imports`) and it adds level-safe forecast measures, revenue at risk, a two-market HHI and text labels. The short versions below are enough for a first build.

Format money measures as currency with 0 decimals, or use the `bn` versions in cards.

```DAX
Total imports = SUM ( fact_exports[value_usd] )

Total imports (real 2025) = SUM ( fact_exports[value_usd_real2025] )

Total imports bn = DIVIDE ( [Total imports], 1e9 )

Imports LY =
CALCULATE ( [Total imports], SAMEPERIODLASTYEAR ( dim_date[date] ) )

YoY % = DIVIDE ( [Total imports] - [Imports LY], [Imports LY] )

Rolling 12m =
CALCULATE (
    [Total imports],
    DATESINPERIOD ( dim_date[date], MAX ( dim_date[date] ), -12, MONTH )
)

Rolling 12m LY =
CALCULATE ( [Rolling 12m], SAMEPERIODLASTYEAR ( dim_date[date] ) )

Rolling 12m YoY % = DIVIDE ( [Rolling 12m] - [Rolling 12m LY], [Rolling 12m LY] )

Latest month =
CALCULATE ( MAX ( dim_date[date] ), FILTER ( fact_exports, fact_exports[value_usd] > 0 ) )

Share of market =
DIVIDE (
    [Total imports],
    CALCULATE ( [Total imports], ALL ( dim_product ) )
)
```

`Share of market` gives a product group's share of its market's imports. Use it with a market slicer set to one market.

**HHI.** The repo's HHI (`outputs/tables/hhi_by_year.csv`) is across all importing countries and uses annual mirror data that is not in the Power BI tables. Two options:

- Load `outputs/tables/hhi_by_year.csv` as a seventh table (no relationships) and show `hhi_eu_as_bloc` by `year` on a line chart. This matches the README.
- Or compute product concentration of US imports from the fact table:

```DAX
HHI products (US) =
VAR total = [Total imports]
RETURN
    SUMX (
        VALUES ( dim_product[product_key] ),
        VAR s = DIVIDE ( CALCULATE ( [Total imports] ), total )
        RETURN ( s * 100 ) ^ 2
    )
```

Use it with market = US and a year on the axis. Say on the page which HHI is shown.

**Forecast measures.** Use the `level` filter on the visual or in the measure:

```DAX
Forecast = SUM ( fact_forecast[point] )
Forecast lo80 = SUM ( fact_forecast[lo80] )
Forecast hi80 = SUM ( fact_forecast[hi80] )
Forecast lo95 = SUM ( fact_forecast[lo95] )
Forecast hi95 = SUM ( fact_forecast[hi95] )

Forecast total (market level) =
CALCULATE ( [Forecast], fact_forecast[level] = "Total" )

Forecast 12m bn = DIVIDE ( [Forecast total (market level)], 1e9 )

Actual last 12m bn =
VAR lastActual =
    CALCULATE ( MAX ( dim_date[date] ), FILTER ( ALL ( fact_exports ), fact_exports[value_usd] > 0 ),
        VALUES ( dim_market[market_key] ) )
RETURN
    DIVIDE (
        CALCULATE ( [Total imports], DATESINPERIOD ( dim_date[date], lastActual, -12, MONTH ) ),
        1e9
    )

Forecast change % = DIVIDE ( [Forecast 12m bn] - [Actual last 12m bn], [Actual last 12m bn] )
```

With one market selected, `Forecast change %` should show about +0.7% for the US and +8.2% for the EU (check against `outputs/tables/forecast_headline.csv`). The US and EU forecast windows differ by a month (US Aug 2026 to Jul 2027, EU Sep 2026 to Aug 2027), because the US data end in Jul 2026.

**Scenario measures:**

```DAX
Baseline bn = DIVIDE ( SUM ( fact_scenarios[baseline_usd] ), 1e9 )
Scenario bn = DIVIDE ( SUM ( fact_scenarios[scenario_usd] ), 1e9 )
Change bn = DIVIDE ( SUM ( fact_scenarios[change_usd] ), 1e9 )
Change % = DIVIDE ( [Change bn], [Baseline bn] )
```

Do not average `change_pct`; use `Change %`, which weights by baseline. Check: S1 mid for the US should give about -0.79bn (-10.0%), S2 mid for the EU about -7.76bn.

## 5. Pages

Use one canvas size (16:9, 1280 x 720) and the same slicer position on every page. Add a text box at the bottom of each page: "Importer-reported (CIF), nominal USD. Sources: UN Comtrade (US), Eurostat Comext (EU)."

### Page 1: Overview

- Slicers: market (`dim_market[market]`).
- Cards: `Latest month`, `Rolling 12m` (in bn), `Rolling 12m YoY %`, HHI (latest year from the HHI table, or `HHI products (US)`).
- Line chart: `Total imports` by `dim_date[date]`, legend `dim_market[market]`, from 2010.
- Clustered bar: `Rolling 12m` by `dim_product[product_group]` for the US.
- Text box with the three or four key findings from the README.

### Page 2: Trends by product and market

- Slicers: market, `dim_product[chapter]`, `dim_product[product_group]`, `dim_date[year]` (between).
- Line chart: `Total imports` by date, legend `product_group`.
- 100% stacked column: `Total imports` by `year`, legend `product_group` (US only). This mirrors `fig05_us_product_mix.png`.
- Matrix: rows `product_group`, columns `year`, values `YoY %`, with conditional formatting (background colour, diverging red-white-blue, centre 0). This mirrors `fig04_us_yoy_heatmap.png`.
- Optional toggle: a field parameter to switch between `Total imports` and `Total imports (real 2025)`.

### Page 3: Forecast vs. actual

- Slicers: market; `fact_forecast[level]` (single select, default "Total"); `product_group` (for US groups).
- Line chart: x `dim_date[date]` from 2022, values `Total imports` and `Forecast`. Add `Forecast lo80` and `Forecast hi80` as lines in a light colour, or use the error-bar option on the `Forecast` line (Format > Error bars, upper `Forecast hi80`, lower `Forecast lo80`).
- Cards: `Actual last 12m bn`, `Forecast 12m bn`, `Forecast change %`.
- Table: load `outputs/tables/best_model_by_series.csv` as an extra table and show `series, model, rel_MASE, APE_12m`. Title it "Backtest: 7 origins, 12-month horizon. rel. MASE < 1 beats seasonal naive."

### Page 4: Scenarios

- Slicer: `fact_scenarios[scenario]` (multi-select). Leave S3 out of the default selection and label it "stress test, not a dated forecast".
- Clustered bar: `Change bn` by `scenario`, legend `market`.
- Bar: `Change bn` by `product_group` for S1 mid (filter on the visual). This mirrors `fig_scen01_risk_by_group.png`.
- Table: `scenario, market, Baseline bn, Scenario bn, Change bn, Change %`.
- Text box: "S2 assumes no GSP and applies only after EBA ends (about Nov 2029). Treat it as an upper bound. WTO benchmark (Bekkers & Cariola 2022): -$6.20bn on all goods to preference-granting markets. S4: the Jul-Aug 2024 unrest shows no loss in importer data."
- Optional: load `outputs/tables/scenario_assumptions.csv` as a table visual, or link to it.

## 6. Formatting

- View > Themes > Browse for themes > `theme/report_theme.json`. Use one colour per market everywhere: US `#1F4E79`, EU `#0F8B8D`. Legends sort EU first, so set the two colours in each visual's data colours.
- Show money in bn with one decimal on cards; keep the axis in bn too.
- Turn off gridlines you do not need and the visual borders. Titles should say what the chart shows ("US imports by product group, $bn").
- Format `YoY %`, `Share of market`, `Change %` as percentages with one decimal.
- Check each page with no slicers selected. Forecast visuals should not double count (`level` filter), and scenario totals should match the numbers in section 4.

## 7. Screenshots for the README

Export each page at full size (File > Export > Export to PDF and crop, or use the Windows Snipping Tool on the page in Reading view). Save them as:

```
dashboard/screenshots/p1_overview.png
dashboard/screenshots/p2_trends.png
dashboard/screenshots/p3_forecast.png
dashboard/screenshots/p4_scenarios.png
```

Then add this under the Power BI line in `README.md`:

```markdown
| | |
|---|---|
| ![Overview](dashboard/screenshots/p1_overview.png) | ![Trends](dashboard/screenshots/p2_trends.png) |
| ![Forecast vs. actual](dashboard/screenshots/p3_forecast.png) | ![Scenarios](dashboard/screenshots/p4_scenarios.png) |
```

Commit `rmg_dashboard.pbix` as well. The `.gitignore` already skips Power BI backup files.
