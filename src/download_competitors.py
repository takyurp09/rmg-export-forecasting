"""Download apparel imports (HS 61+62) of the US and the EU from Bangladesh,
its main competitors and the world, monthly, 2010 onward.

US: UN Comtrade public preview API (no key), US as reporter, chapter totals
61 and 62, one call per month covering all partners. Raw JSON is cached in
data/raw/competitors/comtrade/; empty months are not cached.

EU: Eurostat Comext DS-045409, EU27_2020 imports by partner, chapters 61
and 62, in EUR. The extra-EU total (EXT_EU27_2020) is the denominator.
Converted to USD with the ECB monthly rate cached in data/raw/fx/.

Output: data/processed/competitor_imports_monthly.csv
Usage: python src/download_competitors.py [--start 2010-01] [--end 2026-12]
"""
import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from download_us_comtrade import COMTRADE_URL, get_json  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "competitors"
OUT = ROOT / "data" / "processed" / "competitor_imports_monthly.csv"

# ISO2, Comtrade code, name
COUNTRIES = [
    ("BD", 50, "Bangladesh"), ("CN", 156, "China"), ("VN", 704, "Vietnam"),
    ("IN", 699, "India"), ("KH", 116, "Cambodia"), ("PK", 586, "Pakistan"),
    ("TR", 792, "Türkiye"), ("ID", 360, "Indonesia"), ("LK", 144, "Sri Lanka"),
]
WORLD_CT, WORLD_EU = 0, "EXT_EU27_2020"
EUROSTAT = ("https://ec.europa.eu/eurostat/api/comext/dissemination/statistics/"
            "1.0/data/DS-045409")


def fetch_us(start, end):
    d = RAW / "comtrade"
    d.mkdir(parents=True, exist_ok=True)
    codes = {c: iso for iso, c, _ in COUNTRIES} | {WORLD_CT: "WORLD"}
    rows = []
    for p in pd.period_range(start, end, freq="M"):
        per = p.strftime("%Y%m")
        f = d / f"us_imports_hs61_62_{per}.json"
        if not f.exists():
            js = get_json(COMTRADE_URL, {
                "reporterCode": 842, "partnerCode": ",".join(map(str, codes)),
                "flowCode": "M", "cmdCode": "61,62", "period": per})
            time.sleep(2)
            if not js.get("data"):
                continue
            f.write_text(json.dumps(js))
        for r in json.loads(f.read_text())["data"]:
            if r.get("customsCode") != "C00" or r.get("motCode") != 0 \
                    or r.get("partner2Code") != 0:
                continue
            rows.append(dict(date=p.start_time.strftime("%Y-%m-%d"), market="US",
                             partner=codes[r["partnerCode"]], hs=r["cmdCode"],
                             value_usd=r["primaryValue"], value_eur=None))
    return rows


def fetch_eu():
    d = RAW / "eurostat"
    d.mkdir(parents=True, exist_ok=True)
    f = d / "comext_DS-045409_EU27_competitors_61_62_monthly.json"
    params = [("format", "JSON"), ("reporter", "EU27_2020"), ("flow", "1"),
              ("freq", "M"), ("indicators", "VALUE_IN_EUROS"),
              ("product", "61"), ("product", "62"), ("partner", WORLD_EU)]
    params += [("partner", iso) for iso, _, _ in COUNTRIES]
    for k in range(3):
        try:
            r = requests.get(EUROSTAT, params=params, timeout=(10, 120))
            r.raise_for_status()
            break
        except requests.RequestException:
            if k == 2:
                raise
            time.sleep(10)
    f.write_text(r.text)
    js = r.json()
    dims, sizes = js["id"], js["size"]
    labels = {k: sorted(js["dimension"][k]["category"]["index"].items(),
                        key=lambda kv: kv[1]) for k in dims}
    rows = []
    for k, v in js["value"].items():
        k, idx = int(k), {}
        for dim, n in zip(reversed(dims), reversed(sizes)):
            idx[dim] = labels[dim][k % n][0]
            k //= n
        date = pd.Period(idx["time"].replace("M", "-"), "M").start_time
        if date.year < 2010:
            continue
        rows.append(dict(date=date.strftime("%Y-%m-%d"), market="EU",
                         partner="WORLD" if idx["partner"] == WORLD_EU else idx["partner"],
                         hs=idx["product"], value_usd=None, value_eur=v))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2010-01")
    ap.add_argument("--end", default=pd.Timestamp.today().strftime("%Y-%m"))
    a = ap.parse_args()
    df = pd.DataFrame(fetch_us(a.start, a.end) + fetch_eu())
    fx = pd.read_csv(ROOT / "data/raw/fx/ECB_EXR_M_USD_EUR.csv")
    fx = dict(zip(pd.PeriodIndex(fx.TIME_PERIOD, freq="M").start_time.strftime("%Y-%m-%d"),
                  fx.OBS_VALUE))
    eu = df.market == "EU"
    df["usd_per_eur"] = df.date.map(fx).where(eu)
    df.loc[eu, "value_usd"] = df.loc[eu, "value_eur"] * df.loc[eu, "usd_per_eur"]
    df = df.dropna(subset=["value_usd"]).sort_values(["market", "partner", "hs", "date"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(df.groupby("market").date.agg(["min", "max", "count"]))


if __name__ == "__main__":
    main()
