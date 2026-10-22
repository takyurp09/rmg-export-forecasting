"""Download EPB monthly export summary sheets and build a monthly RMG series.

Source page: https://epb.gov.bd/site/view/epb_export_data/-
Each reporting period on that page links several Excel files. The small
"Summary Sheet" file has, for RMG (HS 61 & 62), knitwear (61) and woven (62):
the current month, the previous month and the same month a year earlier
(million USD). We read all summary sheets and keep one value per month.

Output: data/processed/bd_rmg_exports_monthly.csv
        columns: date, source, market, product_group, value_usd
"""
import re
import subprocess
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "epb"
OUT = ROOT / "data" / "processed" / "bd_rmg_exports_monthly.csv"
PAGE = "https://epb.gov.bd/site/view/epb_export_data/-"
MAX_BYTES = 150_000  # summary sheets are ~20-40 KB; big files are HS detail
ROWS = {"(18) RMG": "total", "(a) Knitwear": "knit", "(b) Woven": "woven"}
# Month headers look like "Export Performance for June 2026",
# "... for Feb. 2025" or "... for September 2026-27" (fiscal-year suffix).
MONTH_RE = re.compile(r"Export Performance for\s+([A-Za-z]+)\.?\s+(\d{4})(?:-(\d{2,4}))?\s*$")
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def header_month(text):
    m = MONTH_RE.match(" ".join(str(text).split()))
    if not m or m.group(1)[:3].lower() not in MONTHS:
        return None
    mon, yr = MONTHS[m.group(1)[:3].lower()], int(m.group(2))
    if m.group(3) and mon <= 6:  # "January 2025-26" is January 2026
        yr += 1
    return pd.Timestamp(yr, mon, 1)


def list_files():
    # Python's bundled CA store rejects epb.gov.bd's certificate chain, while
    # the macOS system curl accepts it, so the listing page is fetched with curl.
    html = subprocess.run(["curl", "-sL", "-m", "60", PAGE], check=True,
                          capture_output=True, text=True).stdout
    (RAW / "epb_export_data_page.html").write_text(html)
    return sorted(set(re.findall(r'href="(https://[^"]+office-epb/[^"]+\.xlsx?)"', html)))


def fetch(url):
    dest = RAW / url.rsplit("/", 1)[-1]
    if dest.exists():
        return dest
    size = int(requests.head(url, timeout=60).headers.get("Content-Length", 0))
    if size > MAX_BYTES:
        return None
    dest.write_bytes(requests.get(url, timeout=120).content)
    return dest


def parse_summary(path):
    recs = []
    for d in pd.read_excel(path, sheet_name=None, header=None).values():
        if d.shape[0] > 6 and "Summary Sheet" in str(d.iat[1, 0]):
            recs += parse_sheet(d, path.name)
    return recs


def parse_sheet(d, fname):
    recs = []
    for col in range(1, d.shape[1]):
        date = header_month(d.iat[4, col])
        if date is None:
            continue
        for i in range(5, d.shape[0]):
            label = " ".join(str(d.iat[i, 0]).split())
            for key, grp in ROWS.items():
                if label.startswith(key):
                    recs.append(dict(date=date, product_group=grp,
                                     value_usd=float(d.iat[i, col]) * 1e6,
                                     file=fname))
    return recs


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    recs = []
    for url in list_files():
        p = fetch(url)
        if p is not None:
            try:
                recs += parse_summary(p)
            except Exception as e:  # noqa: BLE001
                print("skip", p.name, e)
    df = pd.DataFrame(recs)
    # A month can appear in up to three sheets (as current, previous, or
    # year-ago month). Values may be revised; take the median across sheets.
    df = (df.groupby(["date", "product_group"], as_index=False)["value_usd"]
            .median())
    df["source"] = "EPB"
    df["market"] = "World"
    df = df[["date", "source", "market", "product_group", "value_usd"]]
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    df.sort_values(["product_group", "date"]).to_csv(OUT, index=False)
    print(len(df), "rows", df.date.min(), df.date.max())


if __name__ == "__main__":
    main()
