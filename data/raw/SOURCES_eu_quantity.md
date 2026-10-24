# EU imports from Bangladesh: value and quantity

Files: `data/raw/eurostat_qty/comext_EU27_BD_<product>_value_qty_monthly.json`, one per product.
Script: `src/download_eu_quantity.py`. Output: `data/processed/eu_bd_value_quantity_monthly.csv`.

## Source

Eurostat Comext, dataset DS-045409 ("EU trade since 1988 by HS2-4-6 and CN8"), dissemination API:

```
https://ec.europa.eu/eurostat/api/comext/dissemination/statistics/1.0/data/DS-045409
  ?format=JSON&reporter=EU27_2020&partner=BD&product=<code>&flow=1&freq=M
  &indicators=VALUE_IN_EUROS&indicators=QUANTITY_IN_100KG&sinceTimePeriod=2010-01
```

- Reporter: EU27_2020 (the current 27 members, applied back to 2010)
- Partner: BD (Bangladesh), flow 1 (imports)
- Products: HS chapters 61 and 62, and HS4 headings 6104, 6105, 6109, 6110, 6201, 6202, 6203, 6204, 6205
- Indicators: value in euros (CIF at the EU border) and net mass in 100 kg (multiplied by 100 in the script)
- Period: January 2010 to August 2026 (downloaded October 2026). Recent months are provisional and get revised.

## Notes

- Kg is net mass, not a count of garments. Unit value (EUR per kg) moves with prices and also with the product mix, since a jacket weighs more than a T-shirt. HS4 series help separate the two.
- USD figures use the ECB monthly USD/EUR rate in `data/raw/fx/ECB_EXR_M_USD_EUR.csv`.
- The HS61 and HS62 values match the value-only series in `data/raw/eurostat/`.

## US weight (checked, not used)

The UN Comtrade US import files in `data/raw/otexa/comtrade/` carry `netWgt`. It is zero for 2013-2015, nearly all of 2012 and about 22% of 2020 value. In the remaining years the implied USD per kg jumps around (14.6 in 2021, 29.6 in 2022, 16.2 in 2023, 25.4 in 2024), which points to reporting problems rather than price changes. The price and volume split is therefore EU only. The check is in `outputs/tables/price_volume_us_weight_check.csv`.
