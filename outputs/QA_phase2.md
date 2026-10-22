# QA phase 2: forecasts, scenarios, figures, repo

Checked on 22 Oct 2026. Nothing was committed or pushed.

## Reproducibility

The pipeline ran start to finish from the processed data, in this order, with no errors. Nothing was downloaded again.

| Step | Time |
|---|---|
| `src/clean.py` | 41 s |
| `01_explore.ipynb` | 12 s |
| `02_forecast.ipynb` | about 8 min (the backtest takes most of it) |
| `03_scenarios.ipynb` | 6 s |
| Total | about 9 min |

Notebooks were run with `jupyter nbconvert --execute --inplace` on the `crop_env` kernel. After the fixes below I ran 01, 02 and 03 a second time (473 s in total), and the outputs matched.

## Headline numbers after the rerun

Baseline = sum of the 12 monthly point forecasts per series. US window Aug 2026 to Jul 2027; EU window Sep 2026 to Aug 2027. Importer-reported, CIF, nominal USD.

| Scenario | Market | Baseline | Change, mid | Range (low to high) |
|---|---|---|---|---|
| S1 US demand -10% | US | $7.90bn | -$0.79bn (-10.0%) | -$0.63bn to -$1.18bn |
| S2 EU 12% MFN duty (illustrative, post-2029) | EU | $22.40bn | -$4.54bn (-20.3%) | -$2.40bn to -$6.46bn | *(Superseded: after Phase 3 fixes the S2 mid case is -$7.76bn; see Phase 3 section.)*
| S3 S1 + S2 (mid) | US + EU | $30.30bn | -$5.33bn | n/a |
| S4 repeat of Jul-Aug 2024 | US + EU | $30.30bn | $0 | n/a |

The 03 rerun picked up the SARIMA forecast for US knit shirts and blouses. Its baseline moved from $271.2m to $276.8m, and its S1 mid loss from $35.5m to $36.2m. No other row changed. The S1 US total moved by less than $1m.

## Findings by severity

### High

1. **The US source was mislabelled on the figures.** `explore_utils.SRC_US` and the 03 figure notes said "US Census via OTEXA, imports for consumption". The data actually come from the UN Comtrade API with the US as reporter (`download_otexa.py` falls back to Comtrade because OTEXA has no download and the Census API needs a key). *Fixed:* the notes now say "UN Comtrade, US-reported imports (same Census data OTEXA publishes)". The file name `download_otexa.py` is still misleading. Renaming it is optional.
2. **The scenario window label was wrong.** Every row said "2026-08 to 2027-08", a 13-month span made by taking the earliest US month and the latest EU month. *Fixed* in `scenarios.py`: the window is now set per market (US 2026-08 to 2027-07, EU 2026-09 to 2027-08). The totals were already right. Only the label was wrong.
3. **S3 adds two shocks that cannot happen in the same year.** S1 is a near-term US demand shock. S2 only applies after EBA ends (about Nov 2029 at the earliest). Adding them to one 12-month baseline gives a number with no date attached. *Remains.* Either relabel S3 as "stress test, not a dated scenario" or drop it. I would drop it, since the chart already shows S1 and S2 side by side.

### Medium

4. **Power BI: 24 forecast rows have no product key.** In `fact_forecast.csv` the market-total rows (`level = Total`) leave `product_key` blank. Power BI will show them under "(Blank)", and a product slicer will mix totals with groups. All other keys in the three fact tables match their dimensions, with no orphans or duplicate dimension keys. *Remains:* add a "Total" member to `dim_product` (flagged so it is never summed with the groups), or move totals into their own fact table.
5. **Forecasts do not add up across levels.** The US groups sum to $7.90bn but the US total model gives $7.95bn. EU knit plus woven gives $22.40bn and the EU total model gives $22.53bn. The gaps are small (0.7% and 0.6%), but a committee member who checks the arithmetic will notice. The scenarios use the group sums. *Remains:* say so in 02, or reconcile bottom-up.
6. **S2 elasticity.** The mid case uses a price elasticity of 2 with full pass-through. Competitors such as Vietnam, Cambodia and India already pay the duty or have their own deals, so what matters is the elasticity of substitution between suppliers. Trade studies usually put that higher than 2. The 1 to 3 range is shown, but the text should say what it stands for and cite one estimate. *Remains.*
7. **S2 assumes no GSP at all.** If Bangladesh gets standard GSP, the duty is 9.6%, not 12%. If it gets GSP+, it is 0%. S2 is the worst case and is now labelled that way in the 03 notes. *Partly fixed.*
8. **S4 equals zero.** The importer data show no Jul-Aug 2024 shortfall, so S4 is $0. That is honest, but a reader can take it to mean "the unrest cost nothing". The likely reasons are a 4 to 8 week shipping lag and catch-up shipments, and the notebook already says this. *Remains:* either check Sep-Oct 2024 for a lagged dip or replace S4 with an assumed two-week factory loss, labelled as an assumption.
9. **MASE above 1.** Almost every model, including the seasonal naive, scores MASE above 1. The explanation in 02 is correct: the scale comes from the calmer training years, and the 2022-26 test period was rougher. A professor may still read "MASE > 1" as "worse than naive". *Remains:* also report a relative score (model MASE / seasonal-naive MASE on the same test origins) so that the comparison is direct.

### Low

10. **Figure notes did not say "nominal" or "CIF" on every chart.** *Fixed:* every figure note now states CIF and nominal USD. The 02 notes also say "importer-reported, not FOB exports". Real values are labelled on the one panel that uses them.
11. **Revenue-at-risk chart (fig_scen02).** The "0" labels on bars that do not apply (EU under S1, US under S2) read like results, and they overlapped the title. *Fixed:* they now read "n/a", with a key in the note, and the title has padding.
12. **Seasonal-index chart (fig03).** The x-axis label touched the three-line source note. *Fixed* by leaving more room at the bottom in `explore_utils.save`.
13. **fig04 heatmap and fig05 product mix** group knit and woven under the same names ("Coats & jackets", "Underwear & nightwear"). This is fine if intended, but the label does not say both chapters are combined. *Remains (cosmetic).*
14. **Clutter.** *Fixed:* all `*_v1` files (5 tables, 4 figures, 1 Power BI fact table) moved to `outputs/archive_v1/{tables,figures,powerbi}`. The one reference, in 02's intro, now points there.

## Fact check (S2 sources)

| Claim | Result | Source now in `scenario_assumptions.csv` |
|---|---|---|
| EU MFN duty on HS 61/62 is 12% | Correct for most lines, e.g. CN 6109 10 00 cotton T-shirts. A few lines are lower (about 6 to 8%), so 12% is the upper end. | EU Combined Nomenclature (Reg. (EEC) 2658/87, Annex I). The TARIC page did not render when I checked it, so the rate was checked with tariff lookups based on the CN. Check one code on Access2Markets by hand before submitting. |
| LDC graduation on 24 Nov 2026 | Correct as scheduled (UNGA res. 76/8, 2021). Bangladesh asked for a three-year deferral and ECOSOC sent it to the General Assembly to decide before 24 Nov 2026. I found no decision as of 22 Oct 2026. | UNGA 76/8; ECOSOC referral as reported by The Financial Express and The Daily Star |
| EBA continues for 3 years after graduation | Correct. | Regulation (EU) No 978/2012, Art. 17(2) |

The S2 notes in 03 now cite the GSP Regulation and TARIC alongside the press sources. **Check the UNGA decision again before 1 Nov**, because it may land any day and would move the EBA end date to about 2032.

## Number consistency

- Headline forecast table, backtest text in 02 (MASE 1.76 / 2.52 / 1.36 / 1.94; 12-month APE 14% and 9%; bias 5.5% and 6%) and `backtest_summary.csv` all agree.
- `key_facts.csv` matches the figures (2022 peak for both markets; EU27 share 54.6% in 2023).
- The 03 markdown gives no scenario totals, only method, so it cannot drift from the table. The charts read from the table.

## Repo size and .gitignore

- Repo folder: 22 MB (data/raw 14 MB, processed 2.9 MB, outputs 3.1 MB, notebooks 2.2 MB). No file is over 5 MB, so `data/raw` can stay tracked for reproducibility.
- `.gitignore` already covered `.venv/`, `__pycache__/`, `.ipynb_checkpoints/`, `.DS_Store`. I added `.env`, build and tool caches, logs, Office lock files, Power BI backups, and zip/7z archives under `data/raw`.
- `src/__pycache__` exists on disk but is ignored.

## Files changed

- `src/scenarios.py`: per-market window label; updated S2 source text.
- `src/explore_utils.py`: correct US source note; CIF and nominal on all notes; more bottom margin.
- `notebooks/02_forecast.ipynb`: figure notes; archive path. Re-executed.
- `notebooks/03_scenarios.ipynb`: source note, n/a labels, S2 notes and links. Re-executed.
- `notebooks/01_explore.ipynb`: re-executed.
- `.gitignore`: cache entries.
- Moved: `*_v1` files to `outputs/archive_v1/`.

## Phase 3 fixes (22 Oct 2026)

This pass closes the items listed as "Remains" above. Notebooks 01, 02 and 03 were re-executed with nbconvert (kernel `crop_env`) and ran without errors.

### 1. S3 is now a stress test (finding 3)

S3 is renamed "S3 Stress test S1 + S2 mid (not a dated forecast)" in `scenarios.py`, so the new name flows into `scenarios_revenue_at_risk.csv`, `fact_scenarios.csv` and both charts. The 03 intro, the fig_scen02 axis label ("S3 Stress test (not dated)") and its note say why: the EU duty in S2 cannot apply before EBA ends, about November 2029 at the earliest, while S1 is a shock inside the current window. I kept S3 rather than dropping it, because the label now says what it is.

### 2. S2 elasticities are now cited (findings 6 and 7)

The made-up 1 / 2 / 3 range is gone. The new cases are:

| Case | Knit (HS 61) | Woven (HS 62) | Source |
|---|---|---|---|
| Low | 2.7 | 2.7 | Broda and Weinstein (2006, QJE), median elasticity of substitution, US imports, SITC 5-digit, 1990-2001 (as reported in Fontagné, Guimbard and Orefice, fn 21) |
| Mid | 3.00 | 5.02 | Fontagné, Guimbard and Orefice (2022, JIE 137; CESifo WP 8491, Table A2), mean HS6 tariff elasticity by chapter |
| High | 7.3 | 7.3 | Same paper, median of all significant HS6 estimates, all products |

Those tariff elasticities are estimated on import values before duty, so value change = (1 + t)^(-e) - 1 applies directly to Eurostat values. A standard-GSP variant (S2b, 9.6% duty, mid elasticities) is added. GSP+ would be 0%.

New table `outputs/tables/s2_benchmark.csv` puts our S2 next to Bekkers and Cariola (2022, WTO ERSD-2022-05):

| Estimate | Loss, $bn | Loss, % |
|---|---|---|
| S2 low (12%) | 5.90 | 26.4% |
| S2 mid (12%) | 7.76 | 34.7% |
| S2 high (12%) | 12.61 | 56.3% |
| S2b mid (9.6% GSP) | 6.54 | 29.2% |
| WTO: exports to preference-granting markets (+7.9 pp effective tariff) | 6.20 | 23% |
| WTO: all Bangladesh exports, net of trade diversion | 5.37 | 14% |

Ours is larger because it applies the full 12% duty, assumes full pass-through, and lets no EU sales move to other markets. The WTO model has a smaller average tariff rise, an export supply elasticity of 7.7 (Bangladeshi prices fall and absorb part of the duty) and trade diversion. The 03 notes say S2 is an upper bound for the EU market alone. The S2b case is the closest to the WTO figure.

I did not find a verifiable UNCTAD figure. Press reports quote "14.28%" from the WTO-EIF 2020 report and $5.28bn from a 2022 FBCCI seminar paper, but I only cite the WTO working paper, whose Table 1 I read directly.

### 3. S4 lag check (finding 8)

New function `disruption_2024_lagged` checks Sep 2024, Oct 2024, Sep-Oct and Jul-Oct 2024 against the same expectation (2023 same months x H1 growth). Every series is above expectation: Sep-Oct by 23% to 42%, Jul-Oct by 12% to 22%. There is no lagged dip, so S4 stays at 0. The 03 text now says: importer data show no measurable loss; shipments were delayed, not lost. It also says part of the late-2024 rise is a weak late-2023 base, and that margin costs (lost factory days, air freight, discounts) do not show in import values.

### 4. Relative MASE (finding 9)

`backtest_summary.csv` has a new column `rel_MASE` = model MASE / seasonal-naive MASE for the same series over the same seven origins. The backtest figure has a third panel for it, with a dashed line at 1. The 02 text now gives it: US ETS and EU Prophet are both 0.77, ETS is below 1 on 15 of 16 series, and the chosen model beats the naive on every series except US woven coats and jackets, where the naive is the chosen model. Notebook 02 was re-run in full (about 8 minutes) because the new column, the Power BI fix and the coherence check all live in it. The backtest numbers did not change.

### 5. Power BI keys (finding 4)

`dim_product.csv` has a new row, product_key 15, "All products" (chapter "All", market_scope "US,EU"), and a new `is_total` column (1 for that row, 0 for the rest). `clean.py` writes the same row on rebuild. The 24 market-total rows in `fact_forecast.csv` now carry key 15, and 02 asserts that no product_key is blank. `fact_exports.csv` and `fact_scenarios.csv` had no blank keys. Filter `is_total = 0` before summing product groups.

### 6. Script rename (finding 1)

`src/download_otexa.py` is now `src/download_us_comtrade.py`. The reference in `data/raw/SOURCES_us.md` and the usage line in the script are updated. No notebook or README referred to it. The raw cache folder `data/raw/otexa/` keeps its name so the cached downloads still resolve, and the script's docstring says so.

### 7. fig04 and fig05 labels (finding 13)

Groups that exist in both chapters (coats and jackets, underwear and nightwear, other apparel) now read "(knit + woven)" on both charts and in `us_yoy_by_group.csv` and `us_product_share.csv`. Each figure note says these groups combine HS 61 and HS 62 lines of the same name.

### 8. Coherence (finding 5)

02 has a new section, "Do the groups add up to the totals?", with a table and an assert that the gap is under 1%. US groups sum to $7.90bn against $7.95bn from the total model (-0.7%). EU knit plus woven gives $22.40bn against $22.53bn (-0.6%). The text says the scenarios use group sums, the headline and fan charts use the total models, and no reconciliation is applied because the gap is well inside the intervals.

### Final scenario table (12-month totals)

| Scenario | Market | Baseline | Change | % |
|---|---|---|---|---|
| S1 US demand -10% [low] | US | $7.90bn | $-0.63bn | -8.0% |
| S2 EU 12% MFN duty (post-2029, no GSP) [low] | EU | $22.40bn | $-5.90bn | -26.4% |
| S1 US demand -10% [mid] | US | $7.90bn | $-0.79bn | -10.0% |
| S2 EU 12% MFN duty (post-2029, no GSP) [mid] | EU | $22.40bn | $-7.76bn | -34.7% |
| S1 US demand -10% [high] | US | $7.90bn | $-1.18bn | -15.0% |
| S2 EU 12% MFN duty (post-2029, no GSP) [high] | EU | $22.40bn | $-12.60bn | -56.3% |
| S2b EU 9.6% standard-GSP duty (post-2029) [mid] | EU | $22.40bn | $-6.54bn | -29.2% |
| S3 Stress test S1 + S2 mid (not a dated forecast) | EU | $22.40bn | $-7.76bn | -34.7% |
| S3 Stress test S1 + S2 mid (not a dated forecast) | US | $7.90bn | $-0.79bn | -10.0% |
| S4 Repeat Jul-Aug 2024 disruption | EU | $22.40bn | $+0.00bn | +0.0% |
| S4 Repeat Jul-Aug 2024 disruption | US | $7.90bn | $+0.00bn | +0.0% |

S1 and S4 are unchanged from phase 2. S2 moved because the elasticities changed (mid was 20.3%, now 34.7%). S3 is the sum of the S1 and S2 mid rows and has no date.
