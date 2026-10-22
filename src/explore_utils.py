"""Helpers for notebooks/01_explore.ipynb: data loading, plot style, saving."""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "outputs" / "figures"
TAB = ROOT / "outputs" / "tables"

SRC_US = ("Source: UN Comtrade, US-reported imports from Bangladesh (same Census data OTEXA publishes), "
          "HS 61+62, CIF, nominal USD unless stated.")
SRC_EU = "Source: Eurostat Comext, EU27 imports from Bangladesh, HS 61+62, EUR converted at ECB monthly rate (CIF, nominal USD unless stated)."
SRC_MIRROR = ("Source: UN Comtrade mirror data (partner-reported imports, CIF basis), HS 61+62. "
              "Shares use a CIF denominator; 2024-25 provisional (missing reporters).")
REAL_NOTE = "Real values in 2025 USD, deflated by US CPI-U."

EVENTS = [  # (start, end, label)
    ("2013-04-01", "2013-05-01", "Rana Plaza"),
    ("2020-03-01", "2020-07-01", "COVID-19"),
    ("2024-07-01", "2024-09-01", "Unrest"),
]

# Month of Eid al-Fitr (approximate, Bangladesh calendar)
EID_FITR_MONTH = {2010: 9, 2011: 8, 2012: 8, 2013: 8, 2014: 7, 2015: 7, 2016: 7,
                  2017: 6, 2018: 6, 2019: 6, 2020: 5, 2021: 5, 2022: 5, 2023: 4,
                  2024: 4, 2025: 3, 2026: 3}

COLORS = {"US": "#1f4e79", "EU": "#c55a11"}


def set_style():
    plt.rcParams.update({
        "figure.dpi": 100, "savefig.dpi": 150, "font.size": 10,
        "axes.titlesize": 12, "axes.titleweight": "bold", "axes.spines.top": False,
        "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.3,
        "legend.frameon": False,
    })


def load_long():
    d = pd.read_csv(ROOT / "data/processed/rmg_long.csv", parse_dates=["date"])
    return d


def monthly_totals(d, start="2010-01-01"):
    """Wide frame of monthly totals: columns (US, EU) x (nominal, real), USD billions."""
    d = d[d.date >= start]
    g = d.groupby(["date", "market"])[["value_usd", "value_usd_real2025"]].sum() / 1e9
    return g.unstack("market")


def shade_events(ax, label=True):
    for s, e, name in EVENTS:
        ax.axvspan(pd.Timestamp(s), pd.Timestamp(e), color="grey", alpha=0.2, lw=0)
        if label:
            ax.text(pd.Timestamp(s), 1.0, " " + name, transform=ax.get_xaxis_transform(),
                    va="top", ha="left", fontsize=8, color="dimgray")


def save(fig, name, note):
    fig.text(0.01, 0.005, note, fontsize=7.5, color="dimgray", ha="left", va="bottom", wrap=True)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    path = FIG / f"{name}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    return path


def cagr(v0, v1, years):
    return (v1 / v0) ** (1 / years) - 1
