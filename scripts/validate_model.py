"""Validate data/processed/powerbi/ tables against docs/SCHEMA.md; exit non-zero on failure."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

MODEL = Path(__file__).resolve().parents[1] / "data" / "processed" / "powerbi"
SCHEMA: dict[str, list[str]] = {
    "dim_date": ["date_key", "date", "year", "quarter", "month", "month_name", "bd_fiscal_year"],
    "dim_market": ["market_key", "market", "market_name", "reporter_basis"],
    "dim_product": ["product_key", "chapter", "product_group", "hs4_codes", "market_scope", "is_total"],
    "fact_exports": ["date_key", "market_key", "product_key", "value_usd", "value_usd_real2025", "source"],
    "fact_forecast": ["date_key", "market_key", "product_key", "level", "model", "point",
                      "lo80", "hi80", "lo95", "hi95"],
    "fact_scenarios": ["scenario_key", "scenario", "market_key", "product_key", "window",
                       "baseline_usd", "scenario_usd", "change_usd", "change_pct"],
}
KEYS = {"dim_date": ["date_key"], "dim_market": ["market_key"], "dim_product": ["product_key"],
        "fact_exports": ["date_key", "market_key", "product_key"],
        "fact_forecast": ["date_key", "market_key", "product_key", "level"],
        "fact_scenarios": ["scenario_key", "market_key", "product_key"]}
INTS = {"dim_date": ["date_key", "year", "quarter", "month", "bd_fiscal_year"], "dim_market": ["market_key"],
        "dim_product": ["product_key", "is_total"], "fact_exports": ["date_key", "market_key", "product_key"],
        "fact_forecast": ["date_key", "market_key", "product_key"],
        "fact_scenarios": ["scenario_key", "market_key", "product_key"]}
NUMS = {"fact_exports": ["value_usd", "value_usd_real2025"],
        "fact_forecast": ["point", "lo80", "hi80", "lo95", "hi95"],
        "fact_scenarios": ["baseline_usd", "scenario_usd", "change_usd", "change_pct"]}
US_KEYS = {1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14}
EU_KEYS = {2, 12}
errors: list[str] = []


def check(cond: bool, msg: str) -> None:
    """Record a failed check."""
    if not cond:
        errors.append(msg)


def main() -> int:
    t = {n: pd.read_csv(MODEL / f"{n}.csv", dtype=str, keep_default_na=False) for n in SCHEMA}
    for n, cols in SCHEMA.items():
        check(list(t[n].columns) == cols, f"{n}: columns {list(t[n].columns)} != {cols}")
        for c in cols:
            check((t[n][c] != "").all(), f"{n}.{c}: blank values")
    # types
    for n, cols in INTS.items():
        for c in cols:
            check(t[n][c].str.fullmatch(r"-?\d+").all(), f"{n}.{c}: not whole numbers")
    for n, cols in NUMS.items():
        for c in cols:
            check(pd.to_numeric(t[n][c], errors="coerce").notna().all(), f"{n}.{c}: not numeric")
    if errors:  # later checks assume clean types
        return report(t)
    i = {n: df.copy() for n, df in t.items()}
    for n, cols in INTS.items():
        for c in cols:
            i[n][c] = i[n][c].astype(int)
    for n, cols in NUMS.items():
        for c in cols:
            i[n][c] = i[n][c].astype(float)
    # keys
    for n, k in KEYS.items():
        check(not i[n].duplicated(k).any(), f"{n}: duplicate keys on {k}")
    # orphans
    for f in ("fact_exports", "fact_forecast", "fact_scenarios"):
        for col, dim in [("market_key", "dim_market"), ("product_key", "dim_product")]:
            bad = set(i[f][col]) - set(i[dim][col])
            check(not bad, f"{f}: orphan {col} {sorted(bad)}")
    for f in ("fact_exports", "fact_forecast"):
        bad = set(i[f]["date_key"]) - set(i["dim_date"]["date_key"])
        check(not bad, f"{f}: date_key outside dim_date {sorted(bad)[:5]}")
    # dim_date
    d = i["dim_date"]
    dt = pd.to_datetime(t["dim_date"]["date"], format="%Y-%m-%d", errors="coerce")
    check(dt.notna().all() and (dt.dt.day == 1).all(), "dim_date.date: must be first of month, yyyy-mm-dd")
    check((dt.dt.strftime("%Y%m%d").astype(int) == d["date_key"]).all(), "dim_date: date_key != date")
    check((dt.dt.year == d["year"]).all() and (dt.dt.month == d["month"]).all()
          and (dt.dt.quarter == d["quarter"]).all(), "dim_date: year/month/quarter mismatch")
    check((dt.dt.strftime("%b") == d["month_name"]).all(), "dim_date: month_name mismatch")
    full = pd.date_range(dt.min(), dt.max(), freq="MS")
    check(len(full) == len(dt), "dim_date: gaps in month sequence")
    # dims
    check(i["dim_market"].set_index("market_key")["market"].to_dict() == {1: "US", 2: "EU"}, "dim_market: keys 1=US, 2=EU")
    p = i["dim_product"]
    check(p["is_total"].isin([0, 1]).all() and p.loc[p.is_total == 1, "product_key"].tolist() == [15],
          "dim_product: only key 15 is the total")
    check(p["chapter"].isin(["Knit", "Woven", "All"]).all(), "dim_product: chapter values")
    # facts
    e = i["fact_exports"]
    check((e["value_usd"] > 0).all() and (e["value_usd_real2025"] > 0).all(), "fact_exports: values must be > 0")
    check(15 not in set(e["product_key"]), "fact_exports: must not contain total rows (key 15)")
    check(set(e.loc[e.market_key == 1, "product_key"]) == US_KEYS, "fact_exports: US product keys")
    check(set(e.loc[e.market_key == 2, "product_key"]) == EU_KEYS, "fact_exports: EU product keys")
    for m in (1, 2):
        s = e[e.market_key == m]
        n_months = s["date_key"].nunique()
        check(len(s) == n_months * s["product_key"].nunique(), f"fact_exports: market {m} not a full month x product grid")
    fc = i["fact_forecast"]
    check(fc["level"].isin(["Total", "Product group"]).all(), "fact_forecast: level values")
    check((fc.loc[fc.level == "Total", "product_key"] == 15).all()
          and (fc.loc[fc.level == "Product group", "product_key"] != 15).all(), "fact_forecast: level vs product_key 15")
    check(((fc.lo95 <= fc.lo80) & (fc.lo80 <= fc.point) & (fc.point <= fc.hi80) & (fc.hi80 <= fc.hi95)).all(),
          "fact_forecast: interval order lo95 <= lo80 <= point <= hi80 <= hi95")
    check(fc.groupby(["market_key", "product_key", "level"]).size().eq(12).all(), "fact_forecast: 12 months per series")
    last = e.groupby("market_key")["date_key"].max()
    first = fc.groupby("market_key")["date_key"].min()
    for m in (1, 2):
        nxt = int((pd.to_datetime(str(last[m])) + pd.DateOffset(months=1)).strftime("%Y%m%d"))
        check(first[m] == nxt, f"fact_forecast: market {m} does not start the month after the last actual")
    sc = i["fact_scenarios"]
    check((sc.scenario_usd - sc.baseline_usd - sc.change_usd).abs().max() < 1, "fact_scenarios: change_usd != scenario - baseline")
    check(((sc.change_usd / sc.baseline_usd) - sc.change_pct).abs().max() < 1e-9, "fact_scenarios: change_pct != change/baseline")
    check(sc.groupby("scenario_key")["scenario"].nunique().eq(1).all(), "fact_scenarios: one name per scenario_key")
    check(sc["window"].str.fullmatch(r"\d{4}-\d{2} to \d{4}-\d{2}").all(), "fact_scenarios: window format")
    return report(t, i)


def report(t: dict, i: dict | None = None) -> int:
    print("Row counts:")
    for n in SCHEMA:
        print(f"  {n:16s} {len(t[n]):>7,}")
    if i is not None:
        e, fc, sc = i["fact_exports"], i["fact_forecast"], i["fact_scenarios"]
        for m, name in [(1, "US"), (2, "EU")]:
            s = e[e.market_key == m]
            lastk = s.date_key.max()
            lastd = pd.to_datetime(str(lastk))
            start = int((lastd - pd.DateOffset(months=11)).strftime("%Y%m%d"))
            a12 = s.loc[s.date_key >= start, "value_usd"].sum()
            f12 = fc.loc[(fc.market_key == m) & (fc.level == "Total"), "point"].sum()
            print(f"{name}: data {s.date_key.min()}-{lastk}, last 12m ${a12/1e9:.2f}bn, "
                  f"forecast 12m ${f12/1e9:.2f}bn ({(f12/a12-1)*100:+.1f}%)")
        for k, m in [(3, 1), (4, 2)]:
            r = sc[(sc.scenario_key == k) & (sc.market_key == m)]
            print(f"Scenario {r.scenario.iloc[0]}: change ${r.change_usd.sum()/1e9:+.2f}bn "
                  f"({r.change_usd.sum()/r.baseline_usd.sum()*100:+.1f}%)")
    if errors:
        print("\nVALIDATION FAILED:")
        for e in errors:
            print("  -", e)
        return 1
    print("\nValidation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
