# Monthly data refresh

`scripts/refresh_pipeline.py` rebuilds everything from the raw downloads to the dashboard data. A GitHub Actions workflow (`.github/workflows/refresh.yml`) runs it once a month.

## Steps

The steps run in this order. They are listed once, in `STEPS` at the top of the script. If a step's file does not exist, the script skips it, so adding a new downloader or notebook means adding one line to that list.

1. **Download.** Each source has its own script:
   - `src/download_us_comtrade.py`: US monthly imports from Bangladesh (UN Comtrade). Each month is cached as one JSON file in `data/raw/otexa/comtrade/`, and only months without a cached file are requested. Months that Comtrade has not published yet are not cached, so the next run asks for them again.
   - `src/download_comtrade.py`: annual mirror data by market (cached per year) and the EU monthly series from Eurostat (fetched in full each time, since it is a single request).
   - `src/download_eu_quantity.py` and `src/download_competitors.py`, when present.
   - FX and CPI: the cached files in `data/raw/fx/` are fetched again (FRED first, then ECB and BLS as fallbacks). Without this step `clean.py` would keep reading the old caches and never see new months.
2. **Clean.** `src/clean.py` builds `data/processed/rmg_long.csv`, the annual market table and the Power BI tables.
3. **Notebooks 01 to 05.** Each runs through `jupyter nbconvert --execute`. The executed copies go to a temporary folder, so the notebooks in the repo do not change; the tables, figures and Power BI files they write do. Notebook 02 runs the backtest and takes most of the time (about 10 minutes on a laptop).
4. **Validate.** `scripts/validate_model.py` checks the Power BI tables against `docs/SCHEMA.md`: keys, types, interval order, 12 forecast months per series, and that forecasts start the month after the last actual.
5. **Site data.** `scripts/build_site_data.py` writes the JSON files in `site/data/`.

At the end the script writes `site/data/refresh_status.json`:

```json
{"last_run_utc": "...", "latest_month_us": "2026-07", "latest_month_eu": "2026-08",
 "rows": 0, "checks_passed": true, "sources_stale": [], "steps": [...]}
```

The dashboard footer reads this file and shows the refresh date and the latest month for each market.

## Schedule

The workflow runs at 06:00 UTC on the 6th of each month. By then Eurostat and Comtrade have usually posted the previous month's figures. It can also be started by hand from the Actions tab ("Run workflow"), with an option to skip downloads.

When data files change, the workflow commits them to `main` as `github-actions[bot]` and then starts `pages.yml` to redeploy the site. A push made with the workflow's own token does not trigger other workflows, so the redeploy has to be started explicitly. If only the status timestamp changed, nothing is committed.

## When something fails

- **A source is down** (FRED, Eurostat, Comtrade). Download steps are allowed to fail. The script keeps the cached files, marks the step `failed (kept cache)`, lists it under `sources_stale`, and carries on. The footer then says that cached data was used.
- **Comtrade quota.** The public preview API limits how many calls you can make. When it returns 403 with a `Retry-After` header, the downloader waits that long and tries again. A normal month needs only a few calls. The job has a 120-minute limit.
- **Clean, a notebook, or validation fails.** The run stops there. Later steps are marked `not run`, the site data is not rebuilt, the script exits with an error, and the workflow run shows red. Nothing is committed, so the live site keeps the last good data.

## Running it locally

```bash
pip install -r requirements.txt          # or: conda run -n crop_env ...
python scripts/refresh_pipeline.py --dry-run        # list the steps, run nothing
python scripts/refresh_pipeline.py --skip-download  # rebuild from cached raw data
python scripts/refresh_pipeline.py                  # full refresh
```

`--skip-download` is the quickest way to check that a code change still produces the same outputs: run it, then `git diff --stat`.

If `CENSUS_API_KEY` is set (locally or as a repository secret), the US download uses the Census API instead of Comtrade.
