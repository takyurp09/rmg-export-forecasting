"""Scenario analysis: revenue at risk versus the 12-month baseline forecast.

All scenarios are applied to the baseline point forecast in
outputs/tables/forecast_12m.csv, which is read at run time so the results
follow any re-run of 02_forecast.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
TABLES = ROOT / "outputs" / "tables"
FIGS = ROOT / "outputs" / "figures"
PBI = PROC / "powerbi"

US_SHOCK = -0.10            # S1: change in US apparel demand
E_TOTAL = {"low": 0.8, "mid": 1.0, "high": 1.5}   # BD-to-US-demand elasticity (assumed)
EU_MFN = 0.12               # S2: EU MFN duty on most HS 61/62 lines (no GSP at all)
EU_GSP = 0.096              # S2b: standard GSP rate (MFN cut by 20%)
# |Elasticity of import value to the duty factor (1 + t)|, by chapter. Sources:
#   low  2.7: Broda & Weinstein (2006, QJE) median elasticity of substitution, US imports,
#             SITC 5-digit, 1990-2001 (as reported in Fontagne, Guimbard & Orefice 2022, fn 21)
#   mid  knit 3.00 / woven 5.02: Fontagne, Guimbard & Orefice (2022, JIE; CESifo WP 8491,
#             Table A2) mean tariff elasticity of HS6 lines in HS 61 / HS 62
#   high 7.3: same paper, median over all significant HS6 estimates (all products)
EU_ELAST = {"low": {"Knit": 2.7, "Woven": 2.7},
            "mid": {"Knit": 3.00, "Woven": 5.02},
            "high": {"Knit": 7.3, "Woven": 7.3}}
# Published benchmark: Bekkers & Cariola (2022), WTO ERSD-2022-05, Tables 1-2
WTO_BENCH = dict(total_loss_usd=5.372738e9, total_pct=-0.14,
                 pref_loss_usd=6.199333e9, pref_pct=-0.23, pref_tariff_pp=7.90)
EU_LONG = {"Knit": "Knit (HS61, all)", "Woven": "Woven (HS62, all)"}

S1, S2, S3, S4 = ("S1 US demand -10%", "S2 EU 12% MFN duty (post-2029, no GSP)",
                  "S3 Stress test S1 + S2 mid (not a dated forecast)", "S4 Repeat Jul-Aug 2024 disruption")
S2G = "S2b EU 9.6% standard-GSP duty (post-2029)"


def load_history():
    d = pd.read_csv(PROC / "rmg_long.csv", parse_dates=["date"])
    return (d.groupby(["date", "market", "chapter", "product_group"], as_index=False)
             ["value_usd"].sum())


def load_baseline():
    """Product-group baseline: 12-month sum of point forecasts per series."""
    f = pd.read_csv(TABLES / "forecast_12m.csv", parse_dates=["date"])
    f = f[f["product_group"] != "Total"].copy()
    split = f["product_group"].str.split(": ", n=1, expand=True)
    f["chapter"] = split[0]
    f["product_group"] = np.where(f["market"] == "EU", f["chapter"].map(EU_LONG),
                                  split[1] if split.shape[1] > 1 else None)
    return f[["date", "market", "chapter", "product_group", "point"]]


def us_group_betas(hist):
    """Slope of each US group's annual log growth on BD-to-US total log growth."""
    us = hist[hist["market"] == "US"].copy()
    us["year"] = us["date"].dt.year
    full = us.groupby("year")["date"].nunique()
    us = us[us["year"].isin(full[full == 12].index)]
    g = us.groupby(["chapter", "product_group", "year"])["value_usd"].sum()
    tot = us.groupby("year")["value_usd"].sum()
    dt = np.log(tot).diff().dropna()
    rows = []
    for (ch, pg), s in g.groupby(level=[0, 1]):
        dg = np.log(s.droplevel([0, 1])).diff().dropna()
        x, y = dt.loc[dg.index], dg
        beta = np.polyfit(x, y, 1)[0]
        r = np.corrcoef(x, y)[0, 1]
        rows.append(dict(chapter=ch, product_group=pg, beta=beta, r2=r ** 2,
                         n_years=len(y), years=f"{y.index.min()}-{y.index.max()}"))
    return pd.DataFrame(rows)


def disruption_2024(hist):
    """Jul-Aug 2024 shortfall by market x chapter versus a growth-adjusted
    seasonal-naive expectation: value(m, 2023) * (H1 2024 / H1 2023)."""
    h = hist.groupby(["market", "chapter", "date"])["value_usd"].sum().reset_index()
    out = []
    for (m, ch), s in h.groupby(["market", "chapter"]):
        s = s.set_index("date")["value_usd"]
        h1 = s["2024-01":"2024-06"].sum() / s["2023-01":"2023-06"].sum()
        for mo in ("2024-07-01", "2024-08-01"):
            exp = s[pd.Timestamp(mo) - pd.DateOffset(years=1)] * h1
            out.append(dict(market=m, chapter=ch, month=mo[:7], actual=s[mo],
                            expected=exp, shortfall_pct=s[mo] / exp - 1))
    return pd.DataFrame(out)


def disruption_2024_lagged(hist):
    """Same expectation as disruption_2024, for Sep-Oct 2024 (shipping lag) and
    the Jul-Oct 2024 cumulative total."""
    h = hist.groupby(["market", "chapter", "date"])["value_usd"].sum().reset_index()
    out = []
    for (m, ch), s in h.groupby(["market", "chapter"]):
        s = s.set_index("date")["value_usd"]
        g = s["2024-01":"2024-06"].sum() / s["2023-01":"2023-06"].sum()
        for lab, a, b in [("Sep 2024", "2024-09", "2024-09"), ("Oct 2024", "2024-10", "2024-10"),
                          ("Sep-Oct 2024", "2024-09", "2024-10"), ("Jul-Oct 2024", "2024-07", "2024-10")]:
            act = s[a:b].sum()
            exp = s["2023" + a[4:]:"2023" + b[4:]].sum() * g
            out.append(dict(market=m, chapter=ch, period=lab, actual=act, expected=exp,
                            shortfall_pct=act / exp - 1))
    return pd.DataFrame(out)


def run():
    hist, base = load_history(), load_baseline()
    betas = us_group_betas(hist)
    shock24 = disruption_2024(hist)
    s4pct = shock24.groupby(["market", "chapter"])["shortfall_pct"].mean().clip(upper=0)  # gains not applied

    b = base.merge(betas[["chapter", "product_group", "beta"]], how="left",
                   on=["chapter", "product_group"])
    first2 = b.groupby(["market", "chapter", "product_group"])["date"].rank() <= 2

    def pct_s1(row, lvl):
        return US_SHOCK * row["beta"] * E_TOTAL[lvl] if row["market"] == "US" else 0.0

    def pct_s2(row, lvl, duty=EU_MFN):
        return (1 + duty) ** (-EU_ELAST[lvl][row["chapter"]]) - 1 if row["market"] == "EU" else 0.0

    scen = {}
    for lvl in ("low", "mid", "high"):
        scen[f"{S1} [{lvl}]"] = b.apply(pct_s1, axis=1, lvl=lvl)
        scen[f"{S2} [{lvl}]"] = b.apply(pct_s2, axis=1, lvl=lvl)
    scen[f"{S2G} [mid]"] = b.apply(pct_s2, axis=1, lvl="mid", duty=EU_GSP)
    scen[S3] = scen[f"{S1} [mid]"] + scen[f"{S2} [mid]"]
    scen[S4] = np.where(first2, b.set_index(["market", "chapter"]).index.map(s4pct), 0.0)

    rows = []
    for name, pct in scen.items():
        t = b.assign(scenario_usd=b["point"] * (1 + np.asarray(pct, float)))
        a = t.groupby(["market", "chapter", "product_group"], as_index=False)[["point", "scenario_usd"]].sum()
        a.insert(0, "scenario", name)
        rows.append(a)
    r = pd.concat(rows).rename(columns={"point": "baseline_usd"})
    r = r[~((r["market"] == "EU") & r["scenario"].str.startswith("S1"))]
    r = r[~((r["market"] == "US") & r["scenario"].str.startswith("S2"))]
    r["change_usd"] = r["scenario_usd"] - r["baseline_usd"]
    r["change_pct"] = r["change_usd"] / r["baseline_usd"]
    win = base.groupby("market")["date"].agg(lambda d: f"{d.min():%Y-%m} to {d.max():%Y-%m}")
    r["window"] = r["market"].map(win)
    return r.reset_index(drop=True), betas, shock24


def assumptions(betas, shock24):
    a = [
        ("S1", "US apparel demand shock", "-10%", "Scenario design (PLAN.md 1.3D)"),
        ("S1", "Elasticity of BD-to-US apparel imports to US apparel demand",
         "1.0 (range 0.8-1.5)",
         "Analyst assumption. FRED (DCAFRC1Q027SBEA) was unreachable (site maintenance, Oct 2026) and US imports from all countries are not in the repo"),
        ("S1", "Group sensitivity (beta) relative to BD-to-US total",
         "; ".join(f"{c}: {p} {v:.2f}" for c, p, v in betas[["chapter", "product_group", "beta"]].itertuples(index=False)),
         f"OLS of annual log growth, US-reported imports from BD, {betas['years'].iloc[0]} (rmg_long.csv)"),
        ("S2", "Bangladesh LDC graduation date", "24 Nov 2026 (deferral to 24 Nov 2029 requested; CDP supportive; UNGA decision still pending as of 24 Oct 2026)",
         "UNGA res. 76/8 (Nov 2021) set 24 Nov 2026; ECOSOC (2026) referred the 3-year deferral request to the UNGA for a decision before that date (The Financial Express; The Daily Star). Second Committee took up the request on 7 Oct 2026; the Commerce Minister said on 19 Oct that a decision was expected within October (BSS). No adopted resolution found as of 24 Oct 2026"),
        ("S2", "EU EBA transition after graduation", "3 years (EBA access to about Nov 2029; to about 2032 if graduation is deferred)",
         "Regulation (EU) No 978/2012 (GSP Regulation), Art. 17(2): the country is removed from EBA 'following a transitional period of three years' from the entry into force of the delegated act, in practice timed to the UN graduation date. EBA has no expiry date; the rest of the GSP Regulation runs to 31 Dec 2027 (Reg. (EU) 2023/2663)"),
        ("S2", "EU MFN duty on apparel (HS61/62) if no GSP+", "12% (most lines; upper end for the two chapters)",
         "EU Combined Nomenclature (Reg. (EEC) 2658/87, Annex I) conventional duty: 12% on most HS 61/62 lines, e.g. CN 6109 10 00 cotton T-shirts; a few lines are lower (about 6-8%). 12% confirmed for CN 6109 10 00 and 6205 20 00 on TARIC-based lookups (celna24.pl, 24 Oct 2026); the official TARIC and Access2Markets pages did not render. Under current GSP rules Bangladesh apparel would likely be graduated out of standard GSP (Annex VI point 2: 14.5% share threshold for sections S-11a/S-11b), so 12% is the likely rate without GSP+"),
        ("S2b", "EU duty under standard GSP", "9.6% (12% MFN cut by 20%)",
         "Regulation (EU) No 978/2012, Art. 7(2), second subparagraph: for GSP sections S-11a and S-11b the cut is 20% (not the 3.5 pp used for other sensitive goods), so 0.8 x 12% = 9.6%. Unlikely to apply: Art. 8 and Annex VI point 2 suspend S-11a/S-11b preferences when a country's share of GSP imports in the section exceeds 14.5%, which Bangladesh would. GSP+ would mean 0%"),
        ("S2", "|Elasticity of EU import value to the duty factor (1 + t)|",
         "low 2.7 (both chapters); mid knit 3.00, woven 5.02; high 7.3 (both)",
         "Low: Broda & Weinstein (2006, QJE 121(2)) median elasticity of substitution, US imports, SITC 5-digit, 1990-2001, as reported in Fontagne, Guimbard & Orefice (2022) fn 21. "
         "Mid: Fontagne, Guimbard & Orefice (2022, J. Int. Econ. 137; CESifo WP 8491, Table A2) mean HS6 tariff elasticity, HS 61 = -3.00, HS 62 = -5.02. "
         "High: same paper, median of all significant HS6 estimates across products = -7.3"),
        ("S2", "Pass-through and functional form", "Full duty pass-through; value change = (1 + t)^(-e) - 1",
         "Constant-elasticity import demand. The cited tariff elasticities are estimated on import values before duty, which is how Eurostat records them"),
        ("S2", "Published benchmark",
         "Bekkers & Cariola (2022): Bangladesh exports -14% (-$5.37bn of $37.6bn); exports to preference-granting markets -23% (-$6.20bn) for a +7.9 pp effective tariff",
         "WTO Staff Working Paper ERSD-2022-05, Tables 1-2 (actual preference use). Partial-equilibrium model with Fontagne et al. elasticities, export supply elasticity 7.7, and trade diversion to other markets"),
        ("S2", "Timing", "Applied to the current 12-month baseline as a stand-in for annual value; illustrative of post-2029 only",
         "Analyst assumption; no tariff change is expected inside the forecast window"),
        ("S3", "Combination", "S1 mid + S2 mid, additive. Stress test, not a dated forecast: S2 cannot apply before EBA ends (about Nov 2029)", "Analyst assumption"),
        ("S4", "Jul-Aug 2024 shortfall by market x chapter",
         "; ".join(f"{m} {c}: {v:+.1%}" for (m, c), v in shock24.groupby(["market", "chapter"])["shortfall_pct"].mean().items()),
         "Actual vs. 2023 same month x (H1 2024 / H1 2023) growth; rmg_long.csv. Sep-Oct 2024 (lag check) and Jul-Oct 2024 cumulative were also above expectation in all four series. Importer data show no measurable loss; shipments look delayed, not lost. Applied shock capped at 0"),
        ("S4", "Timing", "Shortfall applied to the first 2 months of each series' forecast window", "Analyst assumption"),
        ("All", "Baseline", "Sum of 12 monthly point forecasts per series", "outputs/tables/forecast_12m.csv (02_forecast)"),
    ]
    return pd.DataFrame(a, columns=["scenario", "assumption", "value", "source"])


def s2_benchmark(r):
    """Our S2 EU result next to the published WTO estimate."""
    rows = []
    for name in [f"{S2} [low]", f"{S2} [mid]", f"{S2} [high]", f"{S2G} [mid]"]:
        t = r[(r["scenario"] == name) & (r["market"] == "EU")]
        rows.append(dict(estimate=f"This repo: {name}", coverage="EU27 imports of HS 61+62, 12-month baseline",
                         loss_usd_bn=-t["change_usd"].sum() / 1e9,
                         loss_pct=-t["change_usd"].sum() / t["baseline_usd"].sum()))
    w = WTO_BENCH
    rows.append(dict(estimate="Bekkers & Cariola (2022), WTO ERSD-2022-05: preference-granting markets",
                     coverage=f"All goods, all preference-granting markets, +{w['pref_tariff_pp']} pp effective tariff",
                     loss_usd_bn=w["pref_loss_usd"] / 1e9, loss_pct=-w["pref_pct"]))
    rows.append(dict(estimate="Bekkers & Cariola (2022), WTO ERSD-2022-05: all markets",
                     coverage="All goods, all markets, net of trade diversion",
                     loss_usd_bn=w["total_loss_usd"] / 1e9, loss_pct=-w["total_pct"]))
    return pd.DataFrame(rows)


def to_powerbi(r):
    dp = pd.read_csv(PBI / "dim_product.csv")
    dm = pd.read_csv(PBI / "dim_market.csv")
    dp["market"] = dp["market_scope"]
    f = (r.merge(dm[["market_key", "market"]], on="market")
          .merge(dp[["product_key", "market", "chapter", "product_group"]],
                 on=["market", "chapter", "product_group"], how="left"))
    assert f["product_key"].notna().all(), "unmatched product keys"
    keys = {s: i + 1 for i, s in enumerate(dict.fromkeys(f["scenario"]))}
    f.insert(0, "scenario_key", f["scenario"].map(keys))
    return f[["scenario_key", "scenario", "market_key", "product_key", "window",
              "baseline_usd", "scenario_usd", "change_usd", "change_pct"]]
