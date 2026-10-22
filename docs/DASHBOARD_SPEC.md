# Dashboard specification

Four report pages. Canvas 1280 x 720 (16:9). Measures are in `dax/measures.dax`, fields in [DATA_DICTIONARY.md](DATA_DICTIONARY.md), colours in `theme/report_theme.json`. Step-by-step build instructions are in `dashboard/POWERBI_BUILD_GUIDE.md`.

## Global conventions

- **Header band** on every page: title (left, `[Title - Overview]` on page 1, plain text elsewhere), `[Latest Month Label]` in small grey text, slicers on the right in the same position on every page.
- **Footer** on every page: `[Data Note]` in a text box or card.
- **Market colours**, fixed everywhere: US `#1F4E79` (dark blue), EU `#0F8B8D` (teal). Set them per series in each visual's data colours, because legends sort EU before US and would otherwise take the theme colours in the wrong order.
- **Money**: cards in $bn with one decimal (`bn` measures); axes in $bn too. Percentages with one decimal.
- **Diverging colour** for growth and change: `#B5544B` (negative), `#F7F7F7` (zero), `#1F4E79` (positive), centred on 0.
- **Market slicer**: `dim_market[market]`, synced across all four pages (View > Sync slicers).
- **Interactions**: by default, visuals cross-filter each other. Exceptions are listed per page.
- **Accessibility**: alt text on every visual saying what it shows; minimum font 10 pt; growth and change also shown as signed numbers, not only by colour.

## Page 1. Overview

**Question it answers:** how big are Bangladesh's garment sales to the US and EU now, and which way are they moving?

| Visual | Type | Fields and measures |
|---|---|---|
| Title | Card | `[Title - Overview]` |
| KPI: latest month | Card | `[Latest Month]` |
| KPI: last 12 months | Card | `[Rolling 12m (latest) bn]`, subtitle `[Rolling 12m Label]` |
| KPI: 12-month growth | Card | `[Rolling 12m (latest) YoY %]` |
| KPI: next 12 months | Card | `[Forecast 12m bn]`, subtitle `[Forecast Label]` |
| KPI: concentration | Card | `[HHI Markets (US vs EU)]` with no market selected, or `[HHI Products]` with the US selected. The card title says which one |
| Monthly trend | Line chart | X: `dim_date[date]` (filtered to 2010 on); Y: `[Total Imports bn]`; legend: `dim_market[market]` |
| Market split | Donut or 100% bar | Legend: `dim_market[market]`; values: `[Share of Market]` for the last 12 months (visual-level filter on `dim_date[date]`, relative date: last 12 months up to the latest actual) |
| Top US groups | Clustered bar | Y: `dim_product[product_group]`; X: `[Rolling 12m (latest) bn]`; visual filter `dim_market[market] = "US"`; sorted descending |
| Key findings | Text box | Three or four findings from README.md |

- **Slicers:** market.
- **Interactions:** clicking a market in the donut filters the trend and cards. The US bar chart does not filter the cards (Edit interactions > None), since it is fixed to the US.

## Page 2. Products and markets

**Question it answers:** which product groups drive the totals, and how has the mix changed?

| Visual | Type | Fields and measures |
|---|---|---|
| Trend by group | Line chart | X: `dim_date[date]`; Y: `[Total Imports bn]`; legend: `dim_product[product_label]` |
| Product mix | 100% stacked column | X: `dim_date[year]`; Y: `[Product Share]`; legend: `dim_product[product_group]`; visual filter market = US |
| YoY heatmap | Matrix | Rows: `dim_product[product_label]`; columns: `dim_date[year]`; values: `[YoY %]` with diverging background colour, centre 0 |
| Group table | Table | `dim_product[product_label]`, `dim_product[hs4_codes]`, `[Rolling 12m (latest) bn]`, `[Rolling 12m (latest) YoY %]`, `[Product Share]` |
| Concentration | Line chart | X: `dim_date[year]`; Y: `[HHI Products]` (US) and `[HHI Markets (US vs EU)]`, from 2010. Subtitle: "Product HHI uses 12 US groups; market HHI is US vs EU only" |
| Value basis toggle | Field parameter slicer (optional) | Switches between `[Total Imports]` and `[Total Imports (real 2025)]` |

- **Slicers:** market, `dim_product[chapter]`, `dim_product[product_label]`, `dim_date[year]` (between).
- **Interactions:** selecting a row in the matrix or table highlights that group in the trend; the product-mix chart ignores the product slicer (Edit interactions > None) so it always shows the full mix.
- **Note:** EU data only have knit and woven chapters. With market = EU, the group visuals show two rows.

## Page 3. Forecast

**Question it answers:** what do the models expect for the next 12 months, and how sure are they?

| Visual | Type | Fields and measures |
|---|---|---|
| Actual and forecast | Line chart | X: `dim_date[date]` from Jan 2022; Y: `[Actual (chart)]`, `[Forecast (level-safe)]`, `[Forecast lo80 (level-safe)]`, `[Forecast hi80 (level-safe)]`. Bounds in a light tint of the market colour, dashed. Alternative: error bars on the forecast line (upper hi80, lower lo80) |
| KPI: last 12m | Card | `[Actual Last 12m bn]` |
| KPI: next 12m | Card | `[Forecast 12m bn]` |
| KPI: change | Card | `[Forecast vs Last 12m %]`, subtitle `[Forecast Interval Label]` |
| Forecast table | Table | `dim_date[date]`, `fact_forecast[model]`, `[Forecast (level-safe)]`, `[Forecast lo80 (level-safe)]`, `[Forecast hi80 (level-safe)]`, `[Forecast lo95 (level-safe)]`, `[Forecast hi95 (level-safe)]` |
| Backtest | Table (optional extra table) | Load `outputs/tables/best_model_by_series.csv`; show `series, model, rel_MASE, APE_12m`. Title: "Backtest: 7 origins, 12-month horizon. rel. MASE < 1 beats seasonal naive." |
| Actual vs forecast | Card or column (for later refreshes) | `[Actual vs Forecast]`, `[Actual vs Forecast %]`. Blank until months after the forecast start are loaded |

- **Slicers:** market (single select), `dim_product[product_label]` (single select, blank = market total).
- **Interactions:** the level-safe measures use the `Total` rows when no product is selected and the group rows when one is. Interval bounds are shown only for the total or a single group.
- **Checks:** US +0.7%, EU +8.2% on `[Forecast vs Last 12m %]` (see `outputs/tables/forecast_headline.csv`).

## Page 4. Scenarios

**Question it answers:** how much import value is at risk under each shock, and where?

| Visual | Type | Fields and measures |
|---|---|---|
| KPI: revenue at risk | Card | `[Revenue at Risk bn]`, subtitle `[Scenario Label]` |
| KPI: share at risk | Card | `[Revenue at Risk %]` |
| Change by scenario | Clustered bar | Y: `fact_scenarios[scenario]`; X: `[Scenario Change bn]`; legend: `dim_market[market]` |
| Change by group | Bar | Y: `dim_product[product_label]`; X: `[Scenario Change bn]`; visual filter scenario = "S1 US demand -10% [mid]" |
| Scenario table | Table | `fact_scenarios[scenario]`, `dim_market[market]`, `fact_scenarios[window]`, `[Scenario Baseline bn]`, `[Scenario Value bn]`, `[Scenario Change bn]`, `[Scenario Change %]` |
| Notes | Text box | "S2 assumes no GSP and applies only after EBA ends (about Nov 2029). Treat it as an upper bound. S3 is a stress test, not a dated forecast. S4: the Jul-Aug 2024 unrest shows no loss in importer data." |

- **Slicers:** `fact_scenarios[scenario]` (multi-select; default all except S3), market.
- **Interactions:** clicking a scenario bar filters the group bar and table. The date slicer is not used here because `fact_scenarios` has no date.
- **Checks:** S1 mid, US = -$0.79bn (-10.0%); S2 mid, EU = -$7.76bn.
