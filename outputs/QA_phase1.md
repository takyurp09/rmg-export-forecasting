# Phase 1 data QA

Reviewed 2026-10-21. Cleaning script: `src/clean.py`.

## Basic checks (all four files)

| Check | US monthly | EU monthly | Mirror annual | EPB monthly |
|---|---|---|---|---|
| Duplicate keys | 0 | 0 | 0 | 0 |
| Missing months | none (2010-01 to 2026-07) | none (1999-01 to 2026-08) | n/a | Oct 2025 missing |
| Zero or negative values | 0 | 0 | 0 | 0 |
| HS4 codes per month | 31 to 34 | n/a | n/a | n/a |

## Findings by severity

### High

1. **The mirror annual file overstates BD exports.** Partner-reported CIF totals are $50B (2023) and $58B (2022). EPB/BGMEA FOB figures are about $38-47B. The difference comes from CIF margins, timing, and EU re-routing. Use it for shares and concentration. Do not use it for export levels. *Remains (documented).*
2. **2024 and 2025 are incomplete in the mirror file.** 138 and 116 reporters, against about 155 normally. *Fixed:* `year_complete` flag in `rmg_market_annual.csv` and `hhi_by_year.csv`. HHI and shares for 2024-25 should be read as provisional.
3. **Monthly import data and EPB monthly exports do not line up month by month.** (US+EU)/EPB-world ranges from 0.55 to 1.19 over Dec 2024 to Jul 2026. The swings follow Eid months (e.g. Apr 2025, where EPB fell to $2.4B) and a shipping lag of about 4-8 weeks between FOB shipment and import entry. EPB only covers 21 months, so it cannot be used to calibrate. *Remains:* forecast the importer-side series as they are reported, and use EPB as a context check only.

### Medium

4. **US share looks lower than the "18-20%" usually quoted.** The mirror file gives 14-15% for 2017-2025 (24% in 2010) because its denominator is inflated CIF. On EPB's own figures the US share is about 18-20%. The EU27 share is 49-57%, which is consistent. Report which basis you are using.
5. **CIF vs. customs value.** US `value_usd` is CIF, a few percent above OTEXA/Census customs value. *Remains (documented).*
6. **FRED was unreachable on 2026-10-21** (maintenance page, then timeouts). *Fixed:* `clean.py` tries FRED first. It falls back to the ECB monthly average USD/EUR rate (EXR.M.USD.EUR.SP00.A, the same reference rate DEXUSEU averages) and to BLS CUSR0000SA0, which is the same CPI-U SA series as CPIAUCSL. The raw files are cached in `data/raw/fx/`. Re-run once FRED is back if strict FRED provenance matters. The source column records which one was used.
7. **CPI Oct 2025 was never published** (US government shutdown). *Fixed:* linearly interpolated for the real-value column only.

### Low

8. **Outliers are real events, not data errors.** US YoY was -68% in May 2020 (COVID) and +253% in May 2021 (base effect). 2022 is a peak across all sources, followed by a 2023 drop. Keep them, and use intervention dummies or start-date sensitivity checks in the models.
9. **Mirror market labels.** "USA" was renamed to "United States", and "Sudan (...2011)" was merged into "Sudan". There is no EU aggregate row, so EU27 is built from the 27 members (flag `eu27_member`). The UK is outside EU27 throughout.
10. **US quantity (kg net weight) is unreliable.** It is dropped from the clean outputs.
11. **EPB median-of-sheets.** Later sheets revise earlier months, so values may move on re-download.

## Plausibility of totals

- US imports from BD (HS61+62): $4.1B (2010), $9.8B (2022 peak), $8.2B (2025). Matches OTEXA's order of magnitude.
- EU27 imports from BD in USD: $16.8B (2019), $23.0B (2022), $21.9B (2025). Consistent with the EU being about half of BD RMG.
- Mirror EU27 share: 49-57%. HHI with EU as one bloc: 2,800-3,500, a concentrated market structure.

## Blocking for forecasting?

Nothing blocks it. The US monthly series (199 months) and the EU monthly series (332 months, 2010+ overlap 199) are complete and clean. Note that 2026 is partial (US to July, EU to August).
