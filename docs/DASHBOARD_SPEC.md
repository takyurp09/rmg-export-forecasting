# Dashboard specification

Four report pages, ordered by decision level: an overview, then strategic, tactical and operational pages. Each page opens with one line saying who uses it and for which decision. The web dashboard in `site/` follows the same structure. Canvas 1280 x 720 (16:9). Measures are in `dax/measures.dax`, fields in [DATA_DICTIONARY.md](DATA_DICTIONARY.md), colours in `theme/report_theme.json`. Step-by-step build instructions are in `dashboard/POWERBI_BUILD_GUIDE.md`.

## Global conventions

- **Header band** on every page: title (left, `[Title - Overview]` on page 1, plain text elsewhere), `[Latest Month Label]` in small grey text, slicers on the right in the same position on every page.
- **Footer** on every page: `[Data Note]` in a text box or card.
- **Market colours**, fixed everywhere: US `#1F4E79` (dark blue), EU `#0F8B8D` (teal). Set them per series in each visual's data colours, because legends sort EU before US and would otherwise take the theme colours in the wrong order.
- **Money**: cards in $bn with one decimal (`bn` measures); axes in $bn too. Percentages with one decimal.
- **Diverging colour** for growth and change: `#B5544B` (negative), `#F7F7F7` (zero), `#1F4E79` (positive), centred on 0.
- **Market slicer**: `dim_market[market]`, synced across all pages (View > Sync slicers).
- **Interactions**: by default, visuals cross-filter each other. Exceptions are listed per page.
- **Who-uses-this line**: a text box under the header on every page, for example "Exporter planning teams and BGMEA analysts: next year's capacity and order plans."
- **Accessibility**: alt text on every visual saying what it shows; minimum font 10 pt; growth and change also shown as signed numbers, not only by colour.

## Page 1. Overview

**Who uses it:** anyone new to the data.

**Question it answers:** how big are Bangladesh's garment sales to the US and EU now, and which way are they moving?

| Visual | Type | Fields and measures |
|---|---|---|
| Title | Card | `[Title - Overview]` |
| KPI: latest month | Card | `[Latest Month]` |
| KPI: last 12 months | Card | `[Rolling 12m (latest) bn]`, subtitle `[Rolling 12m Label]` |
| KPI: 12-month growth | Card | `[Rolling 12m (latest) YoY %]` |
| KPI: next 12 months | Card | `[Forecast 12m bn]`, subtitle `[Forecast Label]` |
| KPI: share of US market | Card | `[Bangladesh Share of Market]` with market = US and year = 2025 (check 10.0%), subtitle rank from `[Supplier Rank]` (3) |
| KPI: share of EU market | Card | Same with market = EU (check 20.5%, rank 2) |
| KPI: 2023 EU fall | Card | `[Value Change % (YoY)]` for 2023 (-20.4%), subtitle `[Volume Effect pp]` and `[Price Effect pp]` (-15.9 and -4.5) |
| KPI: concentration | Card | `[HHI Markets (US vs EU)]` with no market selected, or `[HHI Products]` with the US selected. The card title says which one |
| Monthly trend | Line chart | X: `dim_date[date]` (filtered to 2010 on); Y: `[Total Imports bn]`; legend: `dim_market[market]` |
| Market split | Donut or 100% bar | Legend: `dim_market[market]`; values: `[Share of Market]` for the last 12 months (visual-level filter on `dim_date[date]`, relative date: last 12 months up to the latest actual) |
| Top US groups | Clustered bar | Y: `dim_product[product_group]`; X: `[Rolling 12m (latest) bn]`; visual filter `dim_market[market] = "US"`; sorted descending |
| Key findings | Text box | Three or four findings from README.md |

- **Slicers:** market.
- **Interactions:** clicking a market in the donut filters the trend and cards. The US bar chart does not filter the cards (Edit interactions > None), since it is fixed to the US.

## Page 2. Strategic: markets and competitors

**Who uses it:** the ministry or BGMEA policy desk and exporters' boards. **Decision:** which markets and product lines to defend or grow over 3 to 5 years, and where trade-policy effort should go.

**Questions it answers:** is Bangladesh gaining or losing share against China, Vietnam and the rest? How concentrated are its markets and products?

| Visual | Type | Fields and measures |
|---|---|---|
| Share by supplier | Line chart | X: `dim_date[year]` (full years); Y: `[Share of Market (supplier)]`; legend: `dim_country[country]`; visual filter `dim_country[partner] <> "WORLD"`. Bangladesh line thicker |
| Ranking | Bar | Y: `dim_country[country]`; X: `[Supplier Imports]`; tooltip `[Supplier Rank]`, `[Share of Market (supplier)]`; year = 2025 |
| Share change | Table | `dim_country[country]`, `[Share of Market (supplier)]`, `[Share Change pp (YoY)]` |
| Shift-share 2022-2025 | Stacked column (optional table) | Load `outputs/tables/competitor_shift_share_2022_2025.csv`; X: country; Y: `market_size_effect_usd_bn`, `share_effect_usd_bn` |
| Product mix | 100% stacked column | X: `dim_date[year]`; Y: `[Product Share]`; legend: `dim_product[product_group]`; market = US |
| YoY heatmap | Matrix | Rows: `dim_product[product_label]`; columns: `dim_date[year]`; values: `[YoY %]`, diverging background |
| Concentration | Line chart | `[HHI Products]` (US) and `[HHI Markets (US vs EU)]`, from 2010 |

- **Slicers:** market (single select), `dim_date[year]`.
- **Checks:** 2025 Bangladesh share US 10.0% (rank 3), EU 20.5% (rank 2).

## Page 3. Tactical: forecast and scenarios

**Who uses it:** exporter planning teams and BGMEA analysts. **Decision:** next year's capacity, order and cash-flow plans, and how much revenue a demand fall or an EU duty would put at risk.


**Questions it answers:** what do the models expect for the next 12 months, and how sure are they?

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

### Scenario section (same page or a drill-through page)


**Question it answers:** how much import value is at risk under each shock, and where?

| Visual | Type | Fields and measures |
|---|---|---|
| KPI: revenue at risk | Card | `[Revenue at Risk bn]`, subtitle `[Scenario Label]` |
| KPI: share at risk | Card | `[Revenue at Risk %]` |
| Change by scenario | Clustered bar | Y: `fact_scenarios[scenario]`; X: `[Scenario Change bn]`; legend: `dim_market[market]` |
| Change by group | Bar | Y: `dim_product[product_label]`; X: `[Scenario Change bn]`; visual filter scenario = "S1 US demand -10% [mid]" |
| Scenario table | Table | `fact_scenarios[scenario]`, `dim_market[market]`, `fact_scenarios[window]`, `[Scenario Baseline bn]`, `[Scenario Value bn]`, `[Scenario Change bn]`, `[Scenario Change %]` |
| Notes | Text box | "S2 applies only after EBA ends (about Nov 2029). Without GSP+, 12% is the likely duty: standard GSP for apparel is suspended above a 14.5% section share, so the 9.6% case (S2b) is unlikely. S4: the Jul-Aug 2024 unrest shows no loss in importer data." |

- **Slicers:** `fact_scenarios[scenario]` (multi-select; visual-level filter removes S3, which stays in notebook 03 only), market.
- **Interactions:** clicking a scenario bar filters the group bar and table. The date slicer is not used here because `fact_scenarios` has no date.
- **Checks:** S1 mid, US = -$0.79bn (-10.0%); S2 mid, EU = -$7.76bn.

## Page 4. Operational: monthly tracking

**Who uses it:** the analyst who runs the monthly refresh. **Decision:** whether the newest months are on track, whether to flag a shortfall to the planning team, and whether a fall comes from prices or volumes.

| Visual | Type | Fields and measures |
|---|---|---|
| Latest months | Table | `dim_date[date]` (last 6 actual months), `[Total Imports]`, `[Imports LY]`, `[YoY %]` |
| Actual vs forecast | Line chart | X: `dim_date[date]` from 18 months back; Y: `[Actual (chart)]`, `[Imports LY]`, `[Forecast (level-safe)]`, `[Forecast lo80 (level-safe)]`, `[Forecast hi80 (level-safe)]` |
| Forecast check | Card | `[Actual vs Forecast %]`. Blank until months after the forecast start are loaded |
| EU monthly price and volume | Line chart | X: `dim_date[date]`; Y: `[Value Change % (YoY)]` and the YoY change of `[EU Volume kg]` and `[Unit Value EUR per kg]` |
| EU annual split | Stacked column | X: `dim_date[year]`; Y: `[Price Effect pp]`, `[Volume Effect pp]`; line: `[Value Change % (YoY)]` |
| Data status | Table | Load `site/data/refresh_status.json` (Power Query, JSON) and show step, path, status |

- **Slicers:** market (affects the tracking visuals; the price and volume visuals are EU only and ignore it).
- **Checks:** EU 2023: value -20.4%, volume -15.9 pp, price -4.5 pp. EU Jan-Aug 2026: value -11.7%, price -7.3 pp, volume -4.4 pp.
