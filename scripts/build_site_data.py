"""Turn the Power BI tables and output tables into compact JSON for the web dashboard.

Usage: python scripts/build_site_data.py
Writes site/data/{overview,products,forecast,scenarios,competitors,price_volume,tracking}.json. Uses only the CSVs in
data/processed/powerbi/ and outputs/tables/, so the page shows the same numbers as the README.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PBI = ROOT / "data" / "processed" / "powerbi"
TAB = ROOT / "outputs" / "tables"
OUT = ROOT / "site" / "data"


def r(x, nd=0):
    return None if pd.isna(x) else round(float(x), nd)


def dump(name, obj):
    p = OUT / f"{name}.json"
    p.write_text(json.dumps(obj, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    print(f"{p.relative_to(ROOT)}: {p.stat().st_size:,} bytes")


def ym(s):
    return pd.to_datetime(s).dt.strftime("%Y-%m")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    dm = pd.read_csv(PBI / "dim_market.csv")
    dp = pd.read_csv(PBI / "dim_product.csv")
    dd = pd.read_csv(PBI / "dim_date.csv")
    mk = dict(zip(dm.market_key, dm.market))
    dp["label"] = dp.chapter + ": " + dp.product_group

    fx = pd.read_csv(PBI / "fact_exports.csv").merge(dd[["date_key", "date"]], on="date_key")
    fx["market"] = fx.market_key.map(mk)
    fx = fx.merge(dp[["product_key", "chapter", "product_group", "label"]], on="product_key")
    fx["ym"] = ym(fx.date)
    fx["year"] = fx.ym.str[:4].astype(int)

    tot = fx.groupby(["market", "ym"]).value_usd.sum().unstack(0)
    tot = tot[tot.index >= "2010-01"]

    # ---------- Overview ----------
    kf = pd.read_csv(TAB / "key_facts.csv").set_index("fact")["value"]
    head = pd.read_csv(TAB / "forecast_headline.csv").set_index("series")
    best = pd.read_csv(TAB / "best_model_by_series.csv").set_index("series")
    ann = fx.groupby(["market", "year"]).value_usd.sum()
    kpi = {}
    for m in ("US", "EU"):
        s = tot[m].dropna()
        last12, prev12 = s.iloc[-12:].sum(), s.iloc[-24:-12].sum()
        h = head.loc[f"{m} | Total"]
        kpi[m] = dict(last12=r(last12), last12_end=s.index[-1], yoy=r(last12 / prev12 - 1, 4),
                      peak2022=r(ann[(m, 2022)]), y2025=r(ann[(m, 2025)]),
                      vs_peak=r(kf[f"{m} 2025 vs 2022 change (nominal)"] / 100, 4),
                      next12=r(h["next 12m ($bn)"] * 1e9), fc_change=r(h["change %"] / 100, 4),
                      fc_window=h["forecast window"], model=h["model"],
                      rel_mase=r(best.loc[f"{m} | Total", "rel_MASE"], 3),
                      ape12=r(best.loc[f"{m} | Total", "APE_12m"], 1),
                      cagr=r(kf[f"{m} CAGR 2010-2025 (nominal)"], 1))
    rk = pd.read_csv(TAB / "competitor_rank_2025.csv")
    sc_chg = pd.read_csv(TAB / "competitor_share_changes.csv")
    share_kpi = {}
    for m in ("US", "EU"):
        b = rk[(rk.market == m) & (rk.partner == "BD")].iloc[0]
        c = sc_chg[(sc_chg.market == m) & (sc_chg.partner == "BD")].iloc[0]
        share_kpi[m] = dict(share=r(b.share_pct, 1), rank=int(b["rank"]), n=int((rk.market == m).sum()),
                            s2010=r(c["2010"], 1), s2022=r(c["2022"], 1))
    pva = pd.read_csv(TAB / "price_volume_annual.csv")
    t23 = pva[(pva.currency == "EUR") & (pva["product"] == "TOTAL") & (pva.period == "2023")].iloc[0]
    pv2023 = dict(value=r(t23.value_chg_pct, 1), price_pp=r(t23.price_contrib_pp, 1), volume_pp=r(t23.volume_contrib_pp, 1))
    dump("overview", dict(
        months=list(tot.index), us=[r(v) for v in tot["US"]], eu=[r(v) for v in tot["EU"]], kpi=kpi,
        eu_share_2023=r(kf["EU27 share of world imports from BD, 2023"], 1),
        share=share_kpi, pv2023=pv2023,
        generated=datetime.now(timezone.utc).strftime("%Y-%m-%d")))

    # ---------- Products & markets ----------
    full = fx.groupby(["market", "year"]).ym.nunique()
    prod = {}
    for m in ("US", "EU"):
        d = fx[(fx.market == m) & (fx.year >= 2010)]
        yrs = sorted(y for y in d.year.unique() if full[(m, y)] == 12)
        a = d[d.year.isin(yrs)].groupby(["label", "year"]).value_usd.sum().unstack().reindex(columns=yrs)
        a = a.loc[a[yrs[-1]].sort_values(ascending=False).index]
        yoy = (a / a.shift(axis=1) - 1).iloc[:, 1:]
        prod[m] = dict(years=[int(y) for y in yrs], groups=list(a.index),
                       values=[[r(v) for v in row] for row in a.values],
                       yoy_years=[int(y) for y in yrs[1:]], yoy=[[r(v * 100, 1) for v in row] for row in yoy.values])
    top = pd.read_csv(TAB / "top10_markets_2023.csv")
    hhi = pd.read_csv(TAB / "hhi_by_year.csv")
    dump("products", dict(
        markets=prod,
        top10=dict(market=list(top.market), value=[r(v) for v in top.value_usd], share=[r(v, 1) for v in top.share]),
        hhi=dict(year=hhi.year.tolist(), bloc=[r(v) for v in hhi.hhi_eu_as_bloc],
                 countries=[r(v) for v in hhi.hhi_countries],
                 us_share=[r(v * 100, 1) for v in hhi.us_share], eu_share=[r(v * 100, 1) for v in hhi.eu27_share])))

    # ---------- Forecast ----------
    ff = pd.read_csv(PBI / "fact_forecast.csv").merge(dd[["date_key", "date"]], on="date_key")
    ff["market"] = ff.market_key.map(mk)
    ff = ff.merge(dp[["product_key", "label", "is_total"]], on="product_key")
    ff["ym"] = ym(ff.date)
    bt = pd.read_csv(TAB / "backtest_summary.csv")
    series = []
    for (m, pk), f in ff.groupby(["market", "product_key"]):
        f = f.sort_values("ym")
        tot_flag = f.is_total.iloc[0] == 1
        if tot_flag:
            name, hist = f"{m} | Total", tot[m].dropna()
        else:
            lab = f.label.iloc[0]
            name = f"EU | {lab.split(':')[0]}" if m == "EU" else f"US | {lab}"
            hist = fx[(fx.market == m) & (fx.product_key == pk)].groupby("ym").value_usd.sum()
        hist = hist.iloc[-48:]
        b = bt[bt.series == name].sort_values("MASE")
        series.append(dict(
            id=name, market=m, total=bool(tot_flag), model=f.model.iloc[0],
            hist_x=list(hist.index), hist=[r(v) for v in hist],
            fc_x=list(f.ym), point=[r(v) for v in f.point],
            lo80=[r(v) for v in f.lo80], hi80=[r(v) for v in f.hi80],
            lo95=[r(v) for v in f.lo95], hi95=[r(v) for v in f.hi95],
            last12=r(head.loc[name, "last 12m ($bn)"] * 1e9), next12=r(head.loc[name, "next 12m ($bn)"] * 1e9),
            change=r(head.loc[name, "change %"] / 100, 4), window=head.loc[name, "forecast window"],
            backtest=[[x.model, r(x.MASE, 3), r(x.rel_MASE, 3), r(x.APE_12m, 1)] for x in b.itertuples()]))
    order = {"US | Total": 0, "EU | Total": 1, "EU | Knit": 2, "EU | Woven": 3}
    series.sort(key=lambda s: (order.get(s["id"], 9), s["id"]))
    dump("forecast", dict(series=series))

    # ---------- Scenarios ----------
    sc = pd.read_csv(TAB / "scenarios_revenue_at_risk.csv")
    s1low = sc[sc.scenario == "S1 US demand -10% [low]"]
    # beta recovered exactly from the published S1 low case: change_pct = -0.10 * beta * 0.8
    us = [dict(group=f"{x.chapter}: {x.product_group}", base=r(x.baseline_usd),
               beta=round(x.change_pct / (-0.10 * 0.8), 4)) for x in s1low.itertuples()]
    eu = sc[sc.scenario.str.startswith("S2 EU 12% MFN") & sc.scenario.str.endswith("[mid]")]
    eu = [dict(chapter=x.chapter, base=r(x.baseline_usd)) for x in eu.itertuples()]
    sc = sc[~sc.scenario.str.startswith("S3")]  # S3 stress test stays in notebook 03 only
    summ = sc.groupby("scenario")[["baseline_usd", "change_usd"]].sum()
    bench = pd.read_csv(TAB / "s2_benchmark.csv")
    ass = pd.read_csv(TAB / "scenario_assumptions.csv")
    dump("scenarios", dict(
        us_groups=us, eu_chapters=eu,
        us_window=s1low.window.iloc[0], eu_window=sc[sc.market == "EU"].window.iloc[0],
        published={k: [r(v.baseline_usd), r(v.change_usd)] for k, v in summ.iterrows()},
        benchmark=[[x.estimate, x.coverage, r(x.loss_usd_bn, 3), r(x.loss_pct, 4)] for x in bench.itertuples()],
        assumptions=[[x.scenario, x.assumption, x.value, x.source] for x in ass.itertuples() if x.scenario != "S3"]))

    # ---------- Competitors (Strategic) ----------
    fc = pd.read_csv(PBI / "fact_competitors.csv")
    dc = pd.read_csv(PBI / "dim_country.csv")
    fc["year"] = fc.date.str[:4].astype(int)
    nmon = fc.groupby(["market", "year"]).date.nunique()
    comp = {}
    for m in ("US", "EU"):
        d = fc[fc.market == m]
        yrs = sorted(y for y in d.year.unique() if nmon[(m, y)] == 12)
        a = d[d.year.isin(yrs) & (d.partner != "WORLD")].groupby(["partner", "year"]).value_usd.sum().unstack()
        tot_m = d[d.year.isin(yrs)].groupby(["year", "date"]).market_total_usd.first().groupby("year").sum()
        sh = a.div(tot_m, axis=1) * 100
        sh = sh.loc[sh[yrs[-1]].sort_values(ascending=False).index]
        names = dict(zip(dc.partner, dc.country))
        ss = pd.read_csv(TAB / "competitor_shift_share_2022_2025.csv")
        ss = ss[ss.market == m].sort_values("change_usd_bn")
        rr = rk[rk.market == m].sort_values("rank")
        comp[m] = dict(
            years=[int(y) for y in yrs], countries=[names[p] for p in sh.index],
            share=[[r(v, 2) for v in row] for row in sh.values],
            market_total=[r(tot_m[y]) for y in yrs],
            rank=[[int(x.rank), x.country, r(x.value_usd_bn, 3), r(x.share_pct, 2)] for x in rr.itertuples()],
            shift=[[x.country, r(x.change_usd_bn, 3), r(x.market_size_effect_usd_bn, 3), r(x.share_effect_usd_bn, 3)] for x in ss.itertuples()],
            market_growth=r(ss.market_growth_pct.iloc[0], 1))
    dump("competitors", dict(markets=comp))

    # ---------- Price / volume, EU only (Operational) ----------
    fpv = pd.read_csv(PBI / "fact_price_volume.csv")
    fpv = fpv[fpv.hs_code.astype(str).isin(["61", "62"])].merge(dd[["date_key", "date"]], on="date_key")
    fpv["ym"] = ym(fpv.date)
    mth = fpv.groupby("ym")[["value_eur", "qty_kg"]].sum().sort_index()
    mth["uv"] = mth.value_eur / mth.qty_kg
    yo = mth.shift(12)
    ann_pv = pva[(pva.currency == "EUR") & (pva["product"] == "TOTAL")]
    dump("price_volume", dict(
        months=list(mth.index), value_eur=[r(v) for v in mth.value_eur], qty_kg=[r(v) for v in mth.qty_kg],
        unit_value=[r(v, 3) for v in mth.uv],
        value_yoy=[r(v * 100, 1) for v in mth.value_eur / yo.value_eur - 1],
        qty_yoy=[r(v * 100, 1) for v in mth.qty_kg / yo.qty_kg - 1],
        uv_yoy=[r(v * 100, 1) for v in mth.uv / yo.uv - 1],
        annual=[[x.period, r(x.value_chg_pct, 1), r(x.price_contrib_pp, 1), r(x.volume_contrib_pp, 1), r(x.unit_value, 2)]
                for x in sorted(ann_pv.itertuples(), key=lambda x: (x.year, x.months < 12)) if not pd.isna(x.value_chg_pct)]))

    # ---------- Monthly tracking (Operational) ----------
    trk = {}
    for s in series:
        if not s["total"]:
            continue
        m = s["market"]
        hist = tot[m].dropna()
        last = []
        for k in hist.index[-6:]:
            prev = f"{int(k[:4]) - 1}{k[4:]}"
            last.append([k, r(hist[k]), r(hist.get(prev)), r(hist[k] / hist[prev] - 1, 4) if prev in hist.index else None])
        nxt = []
        for i, k in enumerate(s["fc_x"][:6]):
            prev = f"{int(k[:4]) - 1}{k[4:]}"
            nxt.append([k, s["point"][i], s["lo80"][i], s["hi80"][i], r(hist.get(prev))])
        trk[m] = dict(last=last, next=nxt, model=s["model"])
    dump("tracking", trk)


if __name__ == "__main__":
    main()
