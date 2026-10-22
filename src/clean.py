"""Clean Phase 1 data into analysis and Power BI tables.

Inputs : data/processed/{us,eu}_imports_bd_monthly.csv, bd_apparel_by_market_annual.csv
Outputs: data/processed/rmg_long.csv, rmg_market_annual.csv, powerbi/*.csv,
         outputs/tables/hhi_by_year.csv. FX and CPI from FRED (no key), cached in data/raw/fx/.
"""
from pathlib import Path
import io
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
PROC, RAW_FX = ROOT / "data/processed", ROOT / "data/raw/fx"
EU27 = ["Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czechia", "Denmark", "Estonia",
        "Finland", "France", "Germany", "Greece", "Hungary", "Ireland", "Italy", "Latvia",
        "Lithuania", "Luxembourg", "Malta", "Netherlands", "Poland", "Portugal", "Romania",
        "Slovakia", "Slovenia", "Spain", "Sweden"]

# US HS4 -> readable product group
HS4_GROUP = {
    6109: "T-shirts & vests (knit)",
    6110: "Sweaters & pullovers (knit)",
    6103: "Knit suits & trousers", 6104: "Knit suits & trousers",
    6203: "Woven trousers & suits", 6204: "Woven trousers & suits",
    6205: "Woven shirts & blouses", 6206: "Woven shirts & blouses",
    6105: "Knit shirts & blouses", 6106: "Knit shirts & blouses",
    6107: "Underwear & nightwear", 6108: "Underwear & nightwear",
    6207: "Underwear & nightwear", 6208: "Underwear & nightwear", 6212: "Underwear & nightwear",
    6101: "Coats & jackets", 6102: "Coats & jackets", 6201: "Coats & jackets", 6202: "Coats & jackets",
}
OTHER = "Other apparel"
EU_GROUP = {61: "Knit (HS61, all)", 62: "Woven (HS62, all)"}


def fred(series):
    f = RAW_FX / f"{series}.csv"
    if not f.exists():
        f.write_text(_get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}").text)
    d = pd.read_csv(f)
    d.columns = ["date", series]
    s = pd.to_numeric(d[series], errors="coerce").set_axis(pd.to_datetime(d["date"]))
    return s.resample("MS").mean()


def _get(url):
    r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    if r.text.lstrip().startswith("<"):
        raise ValueError(f"HTML instead of data from {url}")
    return r


def ecb_usd_per_eur():
    """Fallback: ECB monthly average reference rate, USD per EUR (EXR.M.USD.EUR.SP00.A)."""
    f = RAW_FX / "ECB_EXR_M_USD_EUR.csv"
    if not f.exists():
        f.write_text(_get("https://data-api.ecb.europa.eu/service/data/EXR/M.USD.EUR.SP00.A"
                          "?format=csvdata&startPeriod=1999-01").text)
    d = pd.read_csv(f)
    return d.set_index(pd.to_datetime(d.TIME_PERIOD)).OBS_VALUE.astype(float)


def bls_cpi():
    """Fallback: BLS CPI-U SA, CUSR0000SA0 (same series as FRED CPIAUCSL). v1 API, 10 yrs/call."""
    f = RAW_FX / "BLS_CUSR0000SA0.csv"
    if not f.exists():
        rows = []
        for y0 in range(1999, 2027, 10):
            j = requests.post("https://api.bls.gov/publicAPI/v1/timeseries/data/", timeout=60,
                              json={"seriesid": ["CUSR0000SA0"], "startyear": str(y0),
                                    "endyear": str(min(y0 + 9, 2026))}).json()
            rows += [(f"{x['year']}-{x['period'][1:]}-01", x["value"])
                     for x in j["Results"]["series"][0]["data"] if x["period"] != "M13"]
        pd.DataFrame(rows, columns=["date", "CPIAUCSL"]).sort_values("date").to_csv(f, index=False)
    d = pd.read_csv(f, parse_dates=["date"])
    s = pd.to_numeric(d.set_index("date").CPIAUCSL, errors="coerce")  # '-' = not published
    s = s.asfreq("MS")
    return s.interpolate(limit_area="inside")  # fills Oct 2025 (not published, gov shutdown)


def get_series(primary, fallback):
    try:
        return primary(), "FRED"
    except Exception as e:  # FRED was down for maintenance on 2026-10-21
        print(f"FRED failed ({e}); using fallback")
        return fallback(), "fallback"


def main():
    fx, fx_src = get_series(lambda: fred("DEXUSEU"), ecb_usd_per_eur)  # USD per EUR, monthly avg
    cpi, _ = get_series(lambda: fred("CPIAUCSL"), bls_cpi)
    fx_label = "FRED DEXUSEU" if fx_src == "FRED" else "ECB EXR monthly avg"

    us = pd.read_csv(PROC / "us_imports_bd_monthly.csv", parse_dates=["date"])
    us = us.assign(market="US", hs4=us.category_code.astype(int),
                   product_group=us.category_code.astype(int).map(HS4_GROUP).fillna(OTHER),
                   chapter=us.category_code.astype(str).str[:2].map({"61": "Knit", "62": "Woven"}),
                   source="UN Comtrade US imports (CIF)")
    eu = pd.read_csv(PROC / "eu_imports_bd_monthly.csv", parse_dates=["date"])
    eu = eu[eu.date >= "1999-01-01"].copy()
    eu["usd_per_eur"] = eu.date.map(fx)
    if eu.usd_per_eur.isna().any():
        raise ValueError(f"Missing FX for {eu.loc[eu.usd_per_eur.isna(), 'date'].unique()}")
    eu = eu.assign(market="EU", hs4=pd.NA, value_usd=eu.value_eur * eu.usd_per_eur,
                   product_group=eu.product_group.astype(int).map(EU_GROUP),
                   chapter=eu.product_group.astype(int).map({61: "Knit", 62: "Woven"}),
                   source=f"Eurostat Comext EU27 imports (EUR->USD, {fx_label})")
    cols = ["date", "market", "chapter", "product_group", "hs4", "value_usd", "source"]
    long = pd.concat([us[cols], eu[cols]], ignore_index=True)
    base = cpi[cpi.index.year == 2025].mean()
    long["value_usd_real2025"] = long.value_usd * base / long.date.map(cpi)  # NaN if CPI not out yet
    long = long.sort_values(["market", "date", "product_group", "hs4"])
    long.to_csv(PROC / "rmg_long.csv", index=False, date_format="%Y-%m-%d")

    # annual market file: drop dup/defunct labels, flag incomplete years, add EU27 aggregate
    a = pd.read_csv(PROC / "bd_apparel_by_market_annual.csv")
    a = a.groupby(["year", "market", "hs2"], as_index=False).value_usd.sum()
    a["market"] = a.market.replace({"USA": "United States", "Sudan (...2011)": "Sudan"})
    a = a.groupby(["year", "market"], as_index=False).value_usd.sum()
    a["eu27_member"] = a.market.isin(EU27)
    a["n_reporters"] = a.groupby("year").market.transform("nunique")
    a["year_complete"] = a.year <= 2023
    a["share"] = a.value_usd / a.groupby("year").value_usd.transform("sum")
    a.to_csv(PROC / "rmg_market_annual.csv", index=False)
    # HHI with EU27 as one bloc (trade-policy unit) and with members separate
    blk = a.assign(m=a.market.where(~a.eu27_member, "EU27")).groupby(["year", "m"]).value_usd.sum()
    sh = blk / blk.groupby(level=0).transform("sum")
    sh2 = a.share
    hhi = pd.DataFrame({
        "hhi_eu_as_bloc": (sh ** 2).groupby(level=0).sum() * 10000,
        "hhi_countries": (sh2 ** 2).groupby(a.year).sum() * 10000,
        "us_share": sh.xs("United States", level=1), "eu27_share": sh.xs("EU27", level=1),
        "n_reporters": a.groupby("year").market.nunique(),
        "year_complete": a.groupby("year").year_complete.first()}).round(4)
    hhi.index.name = "year"
    (ROOT / "outputs/tables").mkdir(parents=True, exist_ok=True)
    hhi.to_csv(ROOT / "outputs/tables/hhi_by_year.csv")

    # Power BI star schema
    pb = PROC / "powerbi"; pb.mkdir(exist_ok=True)
    dm = pd.DataFrame({"market_key": [1, 2], "market": ["US", "EU"],
                       "market_name": ["United States", "European Union (EU27_2020)"],
                       "reporter_basis": ["US-reported imports, CIF", "EU-reported imports, CIF, converted to USD"]})
    prods = long[["market", "chapter", "product_group"]].drop_duplicates().sort_values(["chapter", "product_group"])
    dp = prods[["chapter", "product_group"]].drop_duplicates().reset_index(drop=True)
    dp.insert(0, "product_key", dp.index + 1)
    def codes(r):
        ch = "61" if r.chapter == "Knit" else "62"
        if r.product_group in EU_GROUP.values():
            return ch
        if r.product_group == OTHER:
            return f"other {ch}xx"
        return ",".join(str(k) for k, v in HS4_GROUP.items() if v == r.product_group and str(k)[:2] == ch)
    dp["hs4_codes"] = dp.apply(codes, axis=1)
    dp["market_scope"] = dp.product_group.map(lambda g: "EU" if g in EU_GROUP.values() else "US")
    agg = long.groupby(["date", "market", "chapter", "product_group", "source"], as_index=False)[
        ["value_usd", "value_usd_real2025"]].sum(min_count=1)
    f = agg.merge(dm[["market_key", "market"]]).merge(dp[["product_key", "chapter", "product_group"]])
    f["date_key"] = f.date.dt.strftime("%Y%m%d").astype(int)
    f[["date_key", "market_key", "product_key", "value_usd", "value_usd_real2025", "source"]].sort_values(
        ["date_key", "market_key", "product_key"]).to_csv(pb / "fact_exports.csv", index=False)
    d = pd.DataFrame({"date": pd.date_range(long.date.min(), long.date.max(), freq="MS")})
    d["date_key"] = d.date.dt.strftime("%Y%m%d").astype(int)
    d["year"], d["quarter"], d["month"] = d.date.dt.year, d.date.dt.quarter, d.date.dt.month
    d["month_name"] = d.date.dt.strftime("%b")
    d["bd_fiscal_year"] = d.year + (d.month >= 7)   # FY ends June; FY2025 = Jul24-Jun25
    d[["date_key", "date", "year", "quarter", "month", "month_name", "bd_fiscal_year"]].to_csv(
        pb / "dim_date.csv", index=False, date_format="%Y-%m-%d")
    dm.to_csv(pb / "dim_market.csv", index=False)
    # "All products" member, used only by market-total rows (fact_forecast level = Total).
    # Filter is_total = 0 before summing product groups.
    dp["is_total"] = 0
    dp.loc[len(dp)] = dict(product_key=dp.product_key.max() + 1, chapter="All", product_group="All products",
                           hs4_codes="61,62", market_scope="US,EU", is_total=1)
    dp.to_csv(pb / "dim_product.csv", index=False)

    for p in [PROC / "rmg_long.csv", PROC / "rmg_market_annual.csv", ROOT / "outputs/tables/hhi_by_year.csv",
              *sorted(pb.glob("*.csv"))]:
        print(p.relative_to(ROOT), len(pd.read_csv(p)))


if __name__ == "__main__":
    main()
