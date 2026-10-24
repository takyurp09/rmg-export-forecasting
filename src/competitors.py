"""Competitor benchmark: Bangladesh vs other apparel suppliers in US and EU
imports (HS 61+62). Used by notebooks/04_competitors.ipynb.

Input: data/processed/competitor_imports_monthly.csv (src/download_competitors.py)
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from explore_utils import FIG, ROOT, TAB, save, set_style  # noqa: E402,F401
from download_competitors import COUNTRIES  # noqa: E402

NAMES = {iso: n for iso, _, n in COUNTRIES}
PALETTE = {"BD": "#1b7837", "CN": "#c0392b", "VN": "#e69f00", "IN": "#0072b2",
           "KH": "#cc79a7", "PK": "#56b4e9", "TR": "#7f7f7f", "ID": "#8c564b",
           "LK": "#b8a000"}
YEARS = [2010, 2019, 2022, 2025]
SRC = {"US": ("Source: UN Comtrade, US-reported imports, HS 61+62, "
              "CIF as filed in Comtrade, nominal USD. Shares of US imports from all countries."),
       "EU": ("Source: Eurostat Comext DS-045409, EU27 imports from outside the EU, HS 61+62, "
              "CIF, EUR converted at ECB monthly rate. Intra-EU trade excluded.")}


def load():
    d = pd.read_csv(ROOT / "data/processed/competitor_imports_monthly.csv", parse_dates=["date"])
    return d


def full_years(d):
    """Calendar years with 12 months of world data in each market."""
    w = d[d.partner == "WORLD"].assign(year=d.date.dt.year)
    n = w.groupby(["market", "year"]).date.nunique()
    return set(n[n == 12].index)


def annual(d):
    """Annual USD by market, year, partner (HS 61+62 combined), with share of world."""
    ok = full_years(d)
    a = d.assign(year=d.date.dt.year).groupby(["market", "year", "partner"]).value_usd.sum()
    a = a.unstack("partner")
    a = a[[k in ok for k in a.index]]
    share = a.div(a["WORLD"], axis=0) * 100
    return a, share


def share_table(share):
    rows = []
    for (m, y), r in share.iterrows():
        if y in YEARS:
            for p, v in r.drop("WORLD").items():
                rows.append(dict(market=m, year=y, partner=p, country=NAMES[p], share_pct=round(v, 2)))
    t = pd.DataFrame(rows).pivot_table(index=["market", "partner", "country"], columns="year",
                                       values="share_pct").reset_index()
    t["chg_2010_2025_pp"] = t[2025] - t[2010]
    t["chg_2022_2025_pp"] = t[2025] - t[2022]
    return t.round(2)


def rank_table(a, share, year):
    rows = []
    for m in ["US", "EU"]:
        s = share.loc[m].loc[year].drop("WORLD").sort_values(ascending=False)
        for i, (p, v) in enumerate(s.items(), 1):
            rows.append(dict(market=m, year=year, rank=i, partner=p, country=NAMES[p],
                             value_usd_bn=round(a.loc[(m, year), p] / 1e9, 3),
                             share_pct=round(v, 2)))
    return pd.DataFrame(rows)


def shift_share(a, y0=2022, y1=2025, partner="BD"):
    """X = s*M. dX = s0*dM (market-size effect) + ds*M1 (share effect); sums exactly."""
    rows = []
    for m in ["US", "EU"]:
        M0, M1 = a.loc[(m, y0), "WORLD"], a.loc[(m, y1), "WORLD"]
        for p in [c for c in a.columns if c != "WORLD"]:
            X0, X1 = a.loc[(m, y0), p], a.loc[(m, y1), p]
            s0, s1 = X0 / M0, X1 / M1
            rows.append(dict(market=m, partner=p, country=NAMES[p], y0=y0, y1=y1,
                             value_y0_usd_bn=X0 / 1e9, value_y1_usd_bn=X1 / 1e9,
                             change_usd_bn=(X1 - X0) / 1e9,
                             market_size_effect_usd_bn=s0 * (M1 - M0) / 1e9,
                             share_effect_usd_bn=(s1 - s0) * M1 / 1e9,
                             market_growth_pct=(M1 / M0 - 1) * 100,
                             share_y0_pct=s0 * 100, share_y1_pct=s1 * 100))
    return pd.DataFrame(rows).round(3)


def plot_shares(share, market, name):
    set_style()
    s = share.loc[market].drop(columns="WORLD")
    fig, ax = plt.subplots(figsize=(9, 5))
    for p in s.columns:
        lw = 2.8 if p == "BD" else 1.4
        ax.plot(s.index, s[p], color=PALETTE[p], lw=lw, label=NAMES[p])
        ax.text(s.index[-1] + 0.15, s[p].iloc[-1], NAMES[p], color=PALETTE[p], fontsize=8,
                va="center", fontweight="bold" if p == "BD" else None)
    ax.set_xlim(s.index[0], s.index[-1] + 2)
    ax.set_ylabel("Share of imports (%)")
    title = {"US": "US apparel imports", "EU": "EU27 extra-EU apparel imports"}[market]
    ax.set_title(f"{title}: supplier shares, HS 61+62, {s.index[0]}-{s.index[-1]}")
    return save(fig, name, SRC[market])


def plot_shift_share(ss, name):
    set_style()
    d = ss.set_index(["market", "country"])
    fig, axes = plt.subplots(1, 2, figsize=(11, 5), sharey=False)
    for ax, m in zip(axes, ["US", "EU"]):
        x = d.loc[m].sort_values("change_usd_bn")
        y = range(len(x))
        ax.barh(y, x.market_size_effect_usd_bn, color="#bdbdbd", label="Market-size effect")
        ax.barh(y, x.share_effect_usd_bn, left=x.market_size_effect_usd_bn.where(
            x.share_effect_usd_bn * x.market_size_effect_usd_bn > 0, 0),
            color=[PALETTE[p] for p in x.partner], label="Share effect")
        ax.scatter(x.change_usd_bn, y, color="black", zorder=3, s=14, label="Total change")
        ax.set_yticks(list(y), x.index)
        ax.axvline(0, color="black", lw=0.8)
        ax.set_title(f"{m}: change in imports {x.y0.iloc[0]}-{x.y1.iloc[0]}")
        ax.set_xlabel("USD bn")
    axes[0].legend(loc="lower right", fontsize=8)
    note = ("Change = s0 x (M1 - M0) [market-size effect] + (s1 - s0) x M1 [share effect]; "
            "M = imports from all suppliers, s = supplier share.\n" + SRC["US"] + "\n" + SRC["EU"])
    return save(fig, name, note)


def plot_china_plus_one(share, name, y0=2010, y1=2025):
    set_style()
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    for ax, m in zip(axes, ["US", "EU"]):
        s = share.loc[m].drop(columns="WORLD")
        chg = (s.loc[y1] - s.loc[y0]).sort_values()
        ax.barh([NAMES[p] for p in chg.index], chg, color=[PALETTE[p] for p in chg.index])
        ax.axvline(0, color="black", lw=0.8)
        ax.set_title(f"{m}: share change {y0}-{y1} (pp)")
        rest = 100 - s.sum(axis=1)
        ax.text(0.98, 0.04, f"All other suppliers: {rest.loc[y1] - rest.loc[y0]:+.1f} pp",
                transform=ax.transAxes, ha="right", fontsize=8, color="dimgray")
    return save(fig, name, SRC["US"] + "\n" + SRC["EU"])
