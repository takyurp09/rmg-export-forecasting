# Bangladesh Garment Exports: Forecasts and Scenarios for the US and EU

Ready-made garments (RMG, HS chapters 61 and 62) are most of what Bangladesh exports, and the US and the EU buy most of them. This repo asks three questions a ministry analyst or a factory owner would ask. How have US and EU imports of Bangladeshi apparel moved since 2010? What will they be over the next 12 months, and how much better is that forecast than a naive guess? How much revenue is at risk if US demand falls, or if Bangladesh loses duty-free access to the EU after it leaves the UN list of Least Developed Countries (LDCs)?

All values are importer-reported (CIF) in nominal US dollars unless a table says otherwise.

## Key findings

- **Growth since 2010.** US imports from Bangladesh grew from $4.06bn in 2010 to $8.21bn in 2025 (4.8% a year). EU imports grew from $6.92bn to $21.90bn (8.0% a year). The EU27 took 54.6% of world imports from Bangladesh in 2023.
- **2022 was the peak.** Both markets peaked in 2022. By 2025 US imports were 16.5% below that peak ($9.83bn to $8.21bn) and EU imports 4.8% below ($23.00bn to $21.90bn). US sales also lean on one product: woven trousers and suits were 41.0% of US imports in 2025.
- **Next 12 months: US flat, EU up 8%.** The selected models forecast $7.95bn for the US (+0.7%, Aug 2026 to Jul 2027) and $22.53bn for the EU (+8.2%, Sep 2026 to Aug 2027). In a rolling-origin backtest both beat the seasonal naive forecast, with a relative MASE of 0.77 each. The error on the 12-month total was 14.0% for the US and 8.9% for the EU.
- **Revenue at risk.** A 10% fall in US apparel demand cuts US imports from Bangladesh by about $0.79bn (range $0.63bn to $1.18bn). A 12% EU duty once preferences end (not before about Nov 2029) cuts EU imports by $7.76bn in the mid case (range $5.90bn to $12.60bn). Read this as an upper bound: it assumes no GSP at all. A WTO study (Bekkers & Cariola 2022) puts the loss on all Bangladeshi goods to all preference-granting markets at $6.20bn. With standard GSP (a 9.6% duty) the mid case here is $6.54bn.
- **The 2024 unrest delayed shipments but did not lose them.** In all four market-chapter series, Jul-Aug 2024 imports came in 2.5% to 7.6% above what the first half of the year implied, and Sep-Oct 2024 was also above. In the importer data, a repeat of that shock costs $0.

![Monthly US and EU imports of apparel from Bangladesh](outputs/figures/fig01_monthly_us_eu.png)

| | |
|---|---|
| ![EU 12-month forecast with intervals](outputs/figures/fan_eu_total.png) | ![Revenue at risk by market and scenario](outputs/figures/fig_scen02_risk_by_market.png) |
| ![US product mix over time](outputs/figures/fig05_us_product_mix.png) | ![Backtest MASE by model](outputs/figures/backtest_mase_by_model.png) |

A Power BI version (overview, trends, forecast vs. actual, scenarios) is described in [dashboard/POWERBI_BUILD_GUIDE.md](dashboard/POWERBI_BUILD_GUIDE.md).

## Data

| Source | What | Period | Script |
|---|---|---|---|
| UN Comtrade, US as reporter | US monthly imports from Bangladesh, HS 61/62 by 4-digit heading | Jan 2010 to Jul 2026 | `src/download_us_comtrade.py` |
| Eurostat Comext (DS-045409) | EU27 monthly imports from Bangladesh, HS 61 and 62, converted from euros with ECB monthly rates | Jan 1999 to Aug 2026 | `src/download_comtrade.py` |
| UN Comtrade, all reporters | Annual imports from Bangladesh by market (185 markets; 2024-25 incomplete) | 2010 to 2025 | `src/download_comtrade.py` |
| Export Promotion Bureau (EPB) | Bangladesh's own RMG exports (FOB), monthly; only recent periods are online | Dec 2024 to Sep 2026 | `src/download_epb.py` |
| BLS | US CPI-U, for the real-dollar column | | `data/raw/fx/` |

All files were downloaded on 21 Oct 2026. Endpoints and caveats are in `data/raw/SOURCES_*.md`.

## Methods

- **Cleaning** (`src/clean.py`). One long table (`data/processed/rmg_long.csv`) with date, market, chapter, product group and value. US 4-digit headings map to 12 product groups. The same script writes the Power BI star schema to `data/processed/powerbi/`.
- **Description** (`01_explore.ipynb`). STL decomposition, seasonal index, year-on-year growth by product, product shares, and market concentration (HHI).
- **Models** (`02_forecast.ipynb`, `src/models.py`). Seasonal naive, ETS with damped trend, SARIMA (order by AIC), Prophet, LightGBM on lags, and two equal-weight ensembles, run on 16 series: the US total and 12 US product groups, plus EU total, knit and woven.
- **Backtest.** Rolling origin with 7 origins, every 6 months from Jul 2022 to Jul 2025, and a 12-month horizon. Metrics are MAPE, RMSE, MASE, relative MASE (model over seasonal naive) and the error on the 12-month total.
- **Selection rule.** Keep the models within 1 point of the lowest 12-month-total error, then take the one with the lowest MASE. Ties go to the simpler model. Results are in `outputs/tables/best_model_by_series.csv`.
- **Scenarios** (`03_scenarios.ipynb`, `src/scenarios.py`). Each shock is applied to the 12-month baseline. S1 is a 10% drop in US demand, scaled by each product group's past sensitivity. S2 is a 12% EU MFN duty after EBA ends, using published tariff elasticities (low, mid, high). S2b uses the 9.6% standard-GSP duty instead. S3 adds S1 and S2 as a stress test, and S4 repeats Jul-Aug 2024. Each assumption and its source is listed in `outputs/tables/scenario_assumptions.csv`.

## Reproduce

```bash
conda create -n rmg python=3.10 -y && conda activate rmg
pip install -r requirements.txt

# optional: download the raw data again (the repo already includes it)
python src/download_us_comtrade.py
python src/download_comtrade.py
python src/download_epb.py

python src/clean.py                                                               # about 41 s
jupyter nbconvert --to notebook --execute --inplace notebooks/01_explore.ipynb    # about 12 s
jupyter nbconvert --to notebook --execute --inplace notebooks/02_forecast.ipynb   # about 8 min
jupyter nbconvert --to notebook --execute --inplace notebooks/03_scenarios.ipynb  # about 6 s
```

The full run takes about 9 minutes on a laptop, most of it the backtest in 02.

## Repository structure

```
rmg-export-forecasting/
├── README.md
├── LICENSE
├── requirements.txt
├── src/
│   ├── download_us_comtrade.py   US monthly imports (Comtrade)
│   ├── download_comtrade.py      annual mirror data + Eurostat monthly
│   ├── download_epb.py           EPB monthly exports
│   ├── clean.py                  long table + Power BI tables
│   ├── explore_utils.py          plotting helpers
│   ├── models.py                 models, backtest, selection rule
│   └── scenarios.py              scenario engine
├── notebooks/
│   ├── 01_explore.ipynb
│   ├── 02_forecast.ipynb
│   └── 03_scenarios.ipynb
├── data/
│   ├── raw/                      downloads + SOURCES_*.md
│   └── processed/                clean tables; powerbi/ star schema
├── outputs/
│   ├── figures/
│   ├── tables/
│   └── archive_v1/               first model-selection run, kept for comparison
└── dashboard/
    └── POWERBI_BUILD_GUIDE.md
```

## Limitations

- **Mirror data, not Bangladesh's own exports.** The series are what the US and EU record as imports (CIF). They run above Bangladesh's FOB figures, and EPB no longer posts its monthly FOB history, so FOB totals are not modelled.
- **Monthly data are noisy.** Even the seasonal naive has MASE above 1 on the 2022-26 test period, and seven origins cannot separate models that score within a point of each other.
- **Levels do not add up exactly.** The US group forecasts sum to $7.90bn while the US total model gives $7.95bn. The EU gap is similar. The scenarios use the group sums.
- **Scenarios rest on assumptions.** The S1 elasticity is the analyst's choice. S2 assumes full pass-through and no GSP, and it sits on today's baseline although it could only apply after about Nov 2029. The LDC graduation date (24 Nov 2026, with a deferral requested) was not settled when this was run.

## Use in teaching

The repo works as a case for a business analytics or forecasting course, with data Bangladeshi students know.

- **Backtesting lab.** Students rerun `02_forecast.ipynb` with a different origin schedule or an extra model and check whether the selected model changes. The lesson is to judge a model against a naive benchmark on data it has not seen.
- **Scenario exercise.** Students change one assumption in `src/scenarios.py` (an elasticity, the duty rate, GSP or no GSP) and explain how revenue at risk moves, then compare their S2 number with the published WTO estimate.
- **Dashboard assignment.** Students build the Power BI report from `data/processed/powerbi/` with the build guide.

## License and citation

Code and documentation are under the MIT License (see `LICENSE`). Raw data belong to their publishers (UN Comtrade, Eurostat, EPB, BLS).

Tahmid, M. T. (2026). *Bangladesh garment exports: forecasts and scenarios for the US and EU* [Code and data]. https://github.com/takyurp09/rmg-export-forecasting
