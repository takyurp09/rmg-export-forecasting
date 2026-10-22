"""Bangladesh apparel exports (HS 61, 62) by destination, from mirror data.

Bangladesh's own Comtrade reporting is patchy, so we use partner imports
from Bangladesh: every reporter's imports (flowCode M) with partner 50
(Bangladesh), HS 61 and 62, annual, 2010 onward.

API: UN Comtrade public preview endpoint (no key, one period per call,
max 500 records per call):
  https://comtradeapi.un.org/public/v1/preview/C/A/HS
Raw JSON per year is saved in data/raw/comtrade/.
Output: data/processed/bd_apparel_by_market_annual.csv
        columns: year, market, hs2, value_usd, flow_note

Also (optional EU series): Eurostat Comext DS-045409, monthly EU27_2020
imports of HS 61/62 from Bangladesh, in euros (not converted), saved to
data/processed/eu_imports_bd_monthly.csv
        columns: date, source, market, product_group, value_eur
"""
import json
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "comtrade"
OUT = ROOT / "data" / "processed" / "bd_apparel_by_market_annual.csv"
URL = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
YEARS = range(2010, 2026)


def get_year(year):
    dest = RAW / f"mirror_imports_from_BGD_HS61_62_{year}.json"
    if dest.exists():
        return json.loads(dest.read_text())
    params = dict(partnerCode=50, period=year, cmdCode="61,62", flowCode="M",
                  includeDesc="true", customsCode="C00", motCode=0,
                  partner2Code=0)
    for attempt in range(5):
        r = requests.get(URL, params=params, timeout=120)
        if r.status_code == 200:
            break
        time.sleep(10 * (attempt + 1))
    r.raise_for_status()
    data = r.json()
    dest.write_text(json.dumps(data))
    time.sleep(3)
    return data


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    rows = []
    for y in YEARS:
        data = get_year(y)
        recs = data.get("data") or []
        print(y, len(recs), data.get("error") or "")
        if len(recs) >= 500:
            print("  warning: hit preview record cap for", y)
        rows += recs
    df = pd.DataFrame(rows)
    df = df[(df.customsCode == "C00") & (df.motCode == 0) & (df.partner2Code == 0)]
    out = pd.DataFrame({
        "year": df.refYear,
        "market": df.reporterDesc,
        "hs2": df.cmdCode.astype(str),
        "value_usd": df.primaryValue,
        "flow_note": "mirror: reporter imports from Bangladesh (CIF, "
                     + df.classificationCode + ")",
    })
    out = out.sort_values(["year", "hs2", "value_usd"], ascending=[True, True, False])
    out.to_csv(OUT, index=False)
    print(len(out), "rows;", out.market.nunique(), "markets;",
          out.year.min(), "-", out.year.max())

    eurostat()


EUROSTAT = ("https://ec.europa.eu/eurostat/api/comext/dissemination/statistics/"
            "1.0/data/DS-045409?format=JSON&reporter=EU27_2020&partner=BD"
            "&product=61&product=62&flow=1&freq=M&indicators=VALUE_IN_EUROS")


def eurostat():
    raw = ROOT / "data" / "raw" / "eurostat"
    raw.mkdir(parents=True, exist_ok=True)
    r = requests.get(EUROSTAT, timeout=300)
    r.raise_for_status()
    (raw / "comext_DS-045409_EU27_BD_61_62_monthly.json").write_text(r.text)
    js = r.json()
    dims = js["id"]
    sizes = js["size"]
    labels = {d: sorted(js["dimension"][d]["category"]["index"].items(),
                        key=lambda kv: kv[1]) for d in dims}
    recs = []
    for k, v in js["value"].items():
        k, idx = int(k), {}
        for d, n in zip(reversed(dims), reversed(sizes)):
            idx[d] = labels[d][k % n][0]
            k //= n
        recs.append(dict(date=pd.Period(idx["time"].replace("M", "-"), "M")
                         .to_timestamp().strftime("%Y-%m-%d"),
                         source="Eurostat Comext DS-045409",
                         market="EU27_2020", product_group=idx["product"],
                         value_eur=v))
    out = pd.DataFrame(recs).sort_values(["product_group", "date"])
    out.to_csv(ROOT / "data" / "processed" / "eu_imports_bd_monthly.csv",
               index=False)
    print("eurostat", len(out), "rows", out.date.min(), "-", out.date.max())


if __name__ == "__main__":
    main()
