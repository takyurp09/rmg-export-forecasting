"""Price (unit value) and volume (kg) split of Bangladesh apparel imports.

EU: Eurostat Comext monthly value and quantity (src/download_eu_quantity.py).
US: net weight in the cached UN Comtrade US-import JSON
    (data/raw/otexa/comtrade) was checked and rejected. Weight is missing for
    2013-2015, most of 2012 and part of 2020, and in the years where it is
    present the implied USD/kg jumps by 50-100% from one year to the next
    (14.6 in 2021, 29.6 in 2022, 16.2 in 2023, 25.4 in 2024). That is a
    reporting artefact, not a price signal, so the split is EU only. The US
    check is saved as outputs/tables/price_volume_us_weight_check.csv.

Decomposition: value V = P x Q with P = V/kg. For any two periods,
    ln(V1/V0) = ln(P1/P0) + ln(Q1/Q0)
holds exactly. Each term is also reported as its share of the percentage
value change (log shares), so the two parts add up to the % change.

Run: python src/price_volume.py   (writes tables, figures, Power BI table)
"""
import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from explore_utils import COLORS, FIG, TAB, save, set_style, shade_events  # noqa: E402

PBI = ROOT / "data" / "processed" / "powerbi"
FULL_YEARS = range(2010, 2026)

NAMES = {"61": "Knit (HS61)", "62": "Woven (HS62)", "TOTAL": "Total HS61+62",
         "6109": "T-shirts (6109)", "6110": "Sweaters (6110)",
         "6104": "Women's knit suits/trousers (6104)",
         "6105": "Men's knit shirts (6105)", "6201": "Men's coats (6201)",
         "6202": "Women's coats (6202)", "6203": "Men's trousers/suits (6203)",
         "6204": "Women's trousers/suits (6204)", "6205": "Men's woven shirts (6205)"}

SRC_EU = ("Source: Eurostat Comext DS-045409, EU27 imports from Bangladesh, value (CIF) and "
          "net mass. USD at ECB monthly rate. Kg is a weight proxy, not a garment count.")


def fx():
    f = pd.read_csv(ROOT / "data/raw/fx/ECB_EXR_M_USD_EUR.csv",
                    usecols=["TIME_PERIOD", "OBS_VALUE"])
    f["date"] = pd.PeriodIndex(f.TIME_PERIOD, freq="M").to_timestamp()
    return f.set_index("date").OBS_VALUE.rename("usd_per_eur")


def load_eu():
    d = pd.read_csv(ROOT / "data/processed/eu_bd_value_quantity_monthly.csv",
                    parse_dates=["date"], dtype={"product": str})
    tot = (d[d["product"].isin(["61", "62"])].groupby("date")[["value_eur", "qty_kg"]]
           .sum().reset_index().assign(product="TOTAL"))
    d = pd.concat([d, tot])
    d = d.join(fx(), on="date")
    d["value_usd"] = d.value_eur * d.usd_per_eur
    d["market"] = "EU"
    return d


def load_us():
    rows = []
    for f in sorted(glob.glob(str(ROOT / "data/raw/otexa/comtrade/*.json"))):
        for x in json.load(open(f)).get("data", []):
            rows.append((x["period"], x["cmdCode"], x["netWgt"] or 0.0, x["primaryValue"]))
    d = pd.DataFrame(rows, columns=["period", "hs4", "qty_kg", "value_usd"])
    d["date"] = pd.to_datetime(d.period, format="%Y%m")
    d["product"] = d.hs4.str[:2]
    cover = (d.assign(ok=d.value_usd.where(d.qty_kg > 0, 0))
             .groupby(d.date.dt.year)[["ok", "value_usd"]].sum())
    good = cover.index[cover.ok / cover.value_usd >= 0.99]
    d = d[d.date.dt.year.isin(good) & (d.qty_kg > 0)]
    keep = ["61", "62", "6109", "6110", "6104", "6105", "6201", "6202", "6203", "6204", "6205"]
    parts = [d.groupby(["date", "product"])[["value_usd", "qty_kg"]].sum().reset_index(),
             d[d.hs4.isin(keep)].groupby(["date", "hs4"])[["value_usd", "qty_kg"]].sum()
             .reset_index().rename(columns={"hs4": "product"}),
             d.groupby("date")[["value_usd", "qty_kg"]].sum().reset_index().assign(product="TOTAL")]
    out = pd.concat(parts)
    out["market"] = "US"
    return out, cover.assign(share=cover.ok / cover.value_usd)


def annual(d, cur):
    """Calendar-year sums for full years plus a year-to-date row for the latest year."""
    d = d.copy()
    d["year"] = d.date.dt.year
    last = d.date.max()
    a = d[d.year.isin(FULL_YEARS)].groupby(["market", "product", "year"])[[cur, "qty_kg"]].sum()
    a["months"] = 12
    a = a.reset_index()
    if last.month < 12:  # YTD comparison for the latest partial year
        m = last.month
        ytd = (d[(d.date.dt.month <= m) & (d.year >= last.year - 1)]
               .groupby(["market", "product", "year"])[[cur, "qty_kg"]].sum().reset_index())
        ytd["months"] = m
        a = pd.concat([a, ytd])
    a["unit_value"] = a[cur] / a.qty_kg
    return a


def decompose(a, cur):
    a = a.sort_values(["market", "product", "months", "year"]).copy()
    g = a.groupby(["market", "product", "months"])
    prev_year = g.year.shift()
    a["dlnV"] = np.log(a[cur] / g[cur].shift())
    a["dlnP"] = np.log(a.unit_value / g.unit_value.shift())
    a["dlnQ"] = np.log(a.qty_kg / g.qty_kg.shift())
    gap = prev_year != a.year - 1
    a.loc[gap, ["dlnV", "dlnP", "dlnQ"]] = np.nan
    a["value_chg_pct"] = np.expm1(a.dlnV) * 100
    a["price_chg_pct"] = np.expm1(a.dlnP) * 100
    a["volume_chg_pct"] = np.expm1(a.dlnQ) * 100
    share = a.dlnP / a.dlnV
    a["price_contrib_pp"] = a.value_chg_pct * share
    a["volume_contrib_pp"] = a.value_chg_pct * (1 - share)
    return a


def run():
    set_style()
    eu = load_eu()
    us, us_cover = load_us()

    eu_eur = decompose(annual(eu, "value_eur"), "value_eur")
    eu_usd = decompose(annual(eu, "value_usd"), "value_usd")
    us_chk = annual(us, "value_usd")
    us_chk = us_chk[(us_chk["product"] == "TOTAL") & (us_chk.months == 12)]
    us_chk = us_chk.set_index("year")[["value_usd", "qty_kg", "unit_value"]].join(
        us_cover.share.rename("value_share_with_weight"), how="right")
    us_chk.round(4).to_csv(TAB / "price_volume_us_weight_check.csv", index_label="year")

    def tidy(t, cur, label):
        t = t.rename(columns={cur: "value"}).assign(currency=label)
        t["product_name"] = t["product"].map(NAMES)
        t["period"] = np.where(t.months == 12, t.year.astype(str),
                               t.year.astype(str) + " Jan-" +
                               t.months.map(lambda m: pd.Timestamp(2000, int(m), 1).strftime("%b")))
        return t
    allt = pd.concat([tidy(eu_eur, "value_eur", "EUR"), tidy(eu_usd, "value_usd", "USD")])
    cols = ["market", "currency", "product", "product_name", "period", "year", "months",
            "value", "qty_kg", "unit_value", "value_chg_pct", "price_chg_pct",
            "volume_chg_pct", "dlnV", "dlnP", "dlnQ", "price_contrib_pp", "volume_contrib_pp"]
    allt = allt[cols].sort_values(["market", "currency", "product", "months", "year"])
    allt.round(6).to_csv(TAB / "price_volume_annual.csv", index=False)

    facts = key_facts(allt)
    facts.to_csv(TAB / "price_volume_key_facts.csv", index=False)

    figures(eu, allt)
    powerbi(eu)
    return allt, facts


def row(t, market, cur, product, year, months=12):
    return t[(t.market == market) & (t.currency == cur) & (t["product"] == product)
             & (t.year == year) & (t.months == months)].iloc[0]


def key_facts(t):
    f = []
    r23 = row(t, "EU", "EUR", "TOTAL", 2023)
    f.append(("EU 2023 value change (EUR)", r23.value_chg_pct, "%",
              f"Volume (kg) {r23.volume_chg_pct:+.1f}%, unit value EUR/kg {r23.price_chg_pct:+.1f}%. "
              f"Of the {r23.value_chg_pct:.1f}% fall, {r23.volume_contrib_pp:.1f} pp is volume and "
              f"{r23.price_contrib_pp:.1f} pp is price (log shares). HS61+62, 2023 vs 2022."))
    r22 = row(t, "EU", "EUR", "TOTAL", 2022)
    f.append(("EU 2022 value change (EUR)", r22.value_chg_pct, "%",
              f"Volume {r22.volume_chg_pct:+.1f}%, unit value {r22.price_chg_pct:+.1f}%; "
              f"{r22.price_contrib_pp:.1f} pp price, {r22.volume_contrib_pp:.1f} pp volume. 2022 vs 2021."))
    d22 = row(t, "EU", "USD", "TOTAL", 2022)
    f.append(("EU 2022 unit value change in USD", d22.price_chg_pct, "%",
              f"In USD the 2022 unit value rose {d22.price_chg_pct:.1f}% against {r22.price_chg_pct:.1f}% in EUR; "
              f"the euro fell against the dollar. Value in USD {d22.value_chg_pct:+.1f}%, volume {d22.volume_chg_pct:+.1f}%."))
    a, b = row(t, "EU", "EUR", "TOTAL", 2019), row(t, "EU", "EUR", "TOTAL", 2025)
    f.append(("EU unit value 2025 vs 2019 (EUR/kg)", (b.unit_value / a.unit_value - 1) * 100, "%",
              f"{a.unit_value:.2f} EUR/kg in 2019 to {b.unit_value:.2f} in 2025; kg "
              f"{(b.qty_kg / a.qty_kg - 1) * 100:+.1f}% over the same years."))
    y = t[(t.market == "EU") & (t.currency == "EUR") & (t["product"] == "TOTAL") & (t.months < 12)
          ].dropna(subset=["dlnV"]).iloc[-1]
    f.append((f"EU {y.period} value change (EUR, vs same months a year earlier)", y.value_chg_pct, "%",
              f"Volume {y.volume_chg_pct:+.1f}%, unit value {y.price_chg_pct:+.1f}%; "
              f"{y.price_contrib_pp:.1f} pp price, {y.volume_contrib_pp:.1f} pp volume. Provisional months."))
    return pd.DataFrame(f, columns=["fact", "value", "unit", "method"]).round({"value": 2})


def roll12(d, cur):
    d = d.sort_values("date").set_index("date")
    r = d[[cur, "qty_kg"]].rolling(12).sum()
    return (r[cur] / r.qty_kg).dropna()


def figures(eu, t):
    # fig_pv01: rolling 12-month unit value, EUR and USD per kg
    fig, ax = plt.subplots(figsize=(9, 4))
    for p, ls in [("61", "-"), ("62", "--")]:
        s = eu[eu["product"] == p]
        ax.plot(roll12(s, "value_eur"), ls, color=COLORS["EU"], label=f"EUR/kg, {NAMES[p]}")
        ax.plot(roll12(s, "value_usd"), ls, color=COLORS["US"], label=f"USD/kg, {NAMES[p]}")
    ax.set_title("EU imports from Bangladesh: unit value")
    ax.set_ylabel("per kg, 12-month rolling")
    ax.legend(fontsize=8)
    shade_events(ax)
    save(fig, "fig_pv01_unit_value_trend", SRC_EU)
    plt.close(fig)

    # fig_pv02: EU total YoY split into price and volume (EUR), plus US
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for ax, (m, cur) in zip(axes, [("EU", "EUR"), ("EU", "USD")]):
        s = t[(t.market == m) & (t.currency == cur) & (t["product"] == "TOTAL")
              & (t.months == 12)].dropna(subset=["dlnV"])
        x = s.year.values
        ax.bar(x, s.volume_contrib_pp, color="#7f9fbf", label="Volume (kg)")
        ax.bar(x, s.price_contrib_pp, bottom=np.where((s.price_contrib_pp > 0) == (s.volume_contrib_pp > 0),
                                                      s.volume_contrib_pp, 0),
               color="#e3a76f", label="Price (unit value)")
        ax.plot(x, s.value_chg_pct, "ko", ms=4, label="Value change")
        ax.axhline(0, color="black", lw=0.8)
        ax.set_title(f"{m}: yearly value change split ({cur})")
        ax.set_ylabel("% change, split by log shares")
    axes[0].legend(fontsize=8)
    save(fig, "fig_pv02_yoy_price_volume_split",
         SRC_EU + " Split: ln(V1/V0)=ln(P1/P0)+ln(Q1/Q0), each part scaled to the % value change.")
    plt.close(fig)

    # fig_pv03: EU unit value by HS4, 2019 vs 2022 vs 2025
    hs4 = [p for p in NAMES if len(p) == 4]
    s = t[(t.market == "EU") & (t.currency == "EUR") & t["product"].isin(hs4)
          & t.year.isin([2019, 2022, 2025]) & (t.months == 12)]
    w = s.pivot(index="product", columns="year", values="unit_value").sort_values(2025)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    yy = np.arange(len(w))
    for i, (yr, c) in enumerate([(2019, "#bbbbbb"), (2022, "#7f9fbf"), (2025, COLORS["EU"])]):
        ax.barh(yy + (i - 1) * 0.27, w[yr], height=0.27, color=c, label=str(yr))
    ax.set_yticks(yy, [NAMES[p] for p in w.index], fontsize=8)
    ax.set_xlabel("EUR per kg")
    ax.set_title("EU unit value by product, imports from Bangladesh")
    ax.legend()
    save(fig, "fig_pv03_eu_unit_value_by_product", SRC_EU)
    plt.close(fig)

    # fig_pv04: volume and unit value index, EU total, 2019 = 100
    s = t[(t.market == "EU") & (t.currency == "EUR") & (t["product"] == "TOTAL") & (t.months == 12)]
    s = s.set_index("year")
    fig, ax = plt.subplots(figsize=(8, 4))
    for col, lab, c in [("value", "Value (EUR)", "black"), ("qty_kg", "Volume (kg)", "#7f9fbf"),
                        ("unit_value", "Unit value (EUR/kg)", "#e3a76f")]:
        ax.plot(s.index, s[col] / s.loc[2019, col] * 100, "-o", ms=3, color=c, label=lab)
    ax.axhline(100, color="grey", lw=0.8)
    ax.set_title("EU imports from Bangladesh, index 2019 = 100")
    ax.legend()
    save(fig, "fig_pv04_eu_index_value_volume_price", SRC_EU)
    plt.close(fig)


def powerbi(eu):
    pk = {"61": 2, "62": 12, "TOTAL": 15}
    e = eu[["date", "product", "value_usd", "value_eur", "qty_kg"]].assign(market_key=2)
    f = e
    f["date_key"] = f.date.dt.strftime("%Y%m%d").astype(int)
    f["product_key"] = f["product"].map(pk).astype("Int64")
    f["hs_code"] = f["product"].replace({"TOTAL": "61+62"})
    f["unit_value_usd_per_kg"] = f.value_usd / f.qty_kg
    f["unit_value_eur_per_kg"] = f.value_eur / f.qty_kg
    f["source"] = "Eurostat Comext DS-045409 (EUR->USD, ECB monthly)"
    cols = ["date_key", "market_key", "product_key", "hs_code", "value_usd", "value_eur", "qty_kg",
            "unit_value_usd_per_kg", "unit_value_eur_per_kg", "source"]
    f[cols].sort_values(["market_key", "hs_code", "date_key"]).to_csv(
        PBI / "fact_price_volume.csv", index=False)


if __name__ == "__main__":
    allt, facts = run()
    pd.set_option("display.width", 200, "display.max_colwidth", 200)
    print(facts)
