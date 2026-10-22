"""Download monthly US apparel imports from Bangladesh.

Source choice (checked 2026-10-21):
- OTEXA (trade.gov) now serves its data only through embedded Power BI
  reports (powerbi.trade.gov). There is no file or API download, so it
  cannot be scripted.
- The US Census international trade API now redirects every request
  without a key to a "missing key" page. If CENSUS_API_KEY is set, this
  script uses it (it gives quantities too).
- Otherwise it uses the UN Comtrade public preview API (no key), with the
  US as reporter and Bangladesh as partner, HS chapters 61 and 62 at the
  4-digit level. The preview allows one period per call and 500 rows.

Usage: python src/download_us_comtrade.py [--start 2000-01] [--end 2026-12]

Raw files go to data/raw/otexa/ (folder name kept from the first version so
the cached downloads still resolve).
"""
import argparse
import json
import os
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "otexa"
OUT = ROOT / "data" / "processed" / "us_imports_bd_monthly.csv"

HS4 = [f"61{i:02d}" for i in range(1, 18)] + [f"62{i:02d}" for i in range(1, 18)]
COMTRADE_URL = "https://comtradeapi.un.org/public/v1/preview/C/M/HS"
CENSUS_URL = "https://api.census.gov/data/timeseries/intltrade/imports/hs"


def months(start, end):
    return pd.period_range(start, end, freq="M")


def get_json(url, params, tries=60):
    """GET with retries. The Comtrade preview has a call-volume quota that
    refills on a timer; the 403 reply carries a Retry-After header."""
    for k in range(tries):
        r = requests.get(url, params=params, timeout=60)
        if r.status_code == 429:
            time.sleep(5)
            continue
        if r.status_code == 403 and "quota" in r.text.lower():
            wait = int(r.headers.get("Retry-After", 60)) + 5
            print(f"quota hit, waiting {wait}s", flush=True)
            time.sleep(wait)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"rate limited: {url} {params}")


def fetch_comtrade(start, end):
    d = RAW / "comtrade"
    d.mkdir(parents=True, exist_ok=True)
    rows = []
    for p in months(start, end):
        per = p.strftime("%Y%m")
        f = d / f"us_from_bd_hs61_62_{per}.json"
        if not f.exists():
            js = get_json(COMTRADE_URL, {
                "reporterCode": 842, "partnerCode": 50, "flowCode": "M",
                "cmdCode": ",".join(HS4), "period": per, "includeDesc": "true"})
            time.sleep(3)
            if not js.get("data"):
                continue  # not published (yet); do not cache empty results
            f.write_text(json.dumps(js))
        for r in json.loads(f.read_text())["data"]:
            if r.get("customsCode") != "C00" or r.get("motCode") != 0:
                continue
            rows.append({
                "date": p.start_time.strftime("%Y-%m-01"),
                "source": "UN Comtrade (US-reported imports)",
                "market": "US",
                "product_group": "HS61 knit" if r["cmdCode"].startswith("61") else "HS62 woven",
                "category_code": r["cmdCode"],
                "category_desc": r.get("cmdDesc"),
                "value_usd": r.get("primaryValue"),
                "quantity": r.get("netWgt"),
                "unit": "kg (net weight)",
            })
    return rows


def fetch_census(start, end, key):
    d = RAW / "census"
    d.mkdir(parents=True, exist_ok=True)
    rows = []
    for yr in range(int(start[:4]), int(end[:4]) + 1):
        f = d / f"census_hs4_bd_{yr}.json"
        if not f.exists():
            js = get_json(CENSUS_URL, {
                "get": "I_COMMODITY,I_COMMODITY_SDESC,GEN_VAL_MO,GEN_QY1_MO,UNIT_QY1",
                "CTY_CODE": "5380", "COMM_LVL": "HS4", "time": f"from {yr}-01 to {yr}-12",
                "key": key})
            f.write_text(json.dumps(js))
        js = json.loads(f.read_text())
        hdr = js[0]
        for vals in js[1:]:
            r = dict(zip(hdr, vals))
            c = r["I_COMMODITY"]
            if c[:2] not in ("61", "62"):
                continue
            rows.append({
                "date": r["time"] + "-01", "source": "US Census Bureau",
                "market": "US",
                "product_group": "HS61 knit" if c.startswith("61") else "HS62 woven",
                "category_code": c, "category_desc": r["I_COMMODITY_SDESC"],
                "value_usd": float(r["GEN_VAL_MO"]),
                "quantity": float(r["GEN_QY1_MO"] or 0), "unit": r["UNIT_QY1"],
            })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2010-01")
    ap.add_argument("--end", default=pd.Timestamp.today().strftime("%Y-%m"))
    a = ap.parse_args()
    key = os.environ.get("CENSUS_API_KEY")
    rows = fetch_census(a.start, a.end, key) if key else fetch_comtrade(a.start, a.end)
    df = pd.DataFrame(rows).sort_values(["date", "category_code"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"{len(df)} rows, {df.date.min()} to {df.date.max()} -> {OUT}")


if __name__ == "__main__":
    main()
