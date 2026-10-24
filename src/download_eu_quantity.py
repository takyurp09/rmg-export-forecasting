"""EU27 monthly imports from Bangladesh with value (EUR) and quantity (100 kg).

Source: Eurostat Comext DS-045409, reporter EU27_2020, partner BD, flow import.
Products: HS chapters 61 and 62 plus the largest HS4 headings.
Raw JSON is cached in data/raw/eurostat_qty/ (one file per product).
Output: data/processed/eu_bd_value_quantity_monthly.csv
    columns: date, product, value_eur, qty_kg
"""
import json
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "eurostat_qty"
OUT = ROOT / "data" / "processed" / "eu_bd_value_quantity_monthly.csv"
BASE = ("https://ec.europa.eu/eurostat/api/comext/dissemination/statistics/1.0/"
        "data/DS-045409")
PRODUCTS = ["61", "62", "6109", "6110", "6104", "6105", "6203", "6204",
            "6205", "6201", "6202"]


def fetch(product, refresh=False):
    dest = RAW / f"comext_EU27_BD_{product}_value_qty_monthly.json"
    if dest.exists() and not refresh:
        return json.loads(dest.read_text())
    params = [("format", "JSON"), ("reporter", "EU27_2020"), ("partner", "BD"),
              ("product", product), ("flow", "1"), ("freq", "M"),
              ("indicators", "VALUE_IN_EUROS"), ("indicators", "QUANTITY_IN_100KG"),
              ("sinceTimePeriod", "2010-01")]
    for attempt in range(5):
        r = requests.get(BASE, params=params, timeout=300)
        if r.status_code == 200:
            break
        time.sleep(10 * (attempt + 1))
    r.raise_for_status()
    dest.write_text(r.text)
    time.sleep(2)
    return r.json()


def parse(js):
    dims, sizes = js["id"], js["size"]
    labels = {d: sorted(js["dimension"][d]["category"]["index"].items(),
                        key=lambda kv: kv[1]) for d in dims}
    recs = []
    for k, v in js["value"].items():
        k, idx = int(k), {}
        for d, n in zip(reversed(dims), reversed(sizes)):
            idx[d] = labels[d][k % n][0]
            k //= n
        recs.append(dict(time=idx["time"], product=idx["product"],
                         indicator=idx["indicators"], v=v))
    return pd.DataFrame(recs)


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    df = pd.concat([parse(fetch(p)) for p in PRODUCTS])
    w = df.pivot_table(index=["time", "product"], columns="indicator",
                       values="v").reset_index()
    w["date"] = pd.PeriodIndex(w["time"], freq="M").to_timestamp()
    w["qty_kg"] = w["QUANTITY_IN_100KG"] * 100
    out = (w.rename(columns={"VALUE_IN_EUROS": "value_eur"})
           [["date", "product", "value_eur", "qty_kg"]]
           .sort_values(["product", "date"]))
    out = out[out.date >= "2010-01-01"]
    out.to_csv(OUT, index=False)
    print(len(out), "rows", out.date.min().date(), "-", out.date.max().date())


if __name__ == "__main__":
    main()
