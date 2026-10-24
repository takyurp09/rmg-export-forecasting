"""Monthly data refresh: download -> clean -> notebooks -> validate -> site data.

Usage:
  python scripts/refresh_pipeline.py                 # full run
  python scripts/refresh_pipeline.py --skip-download # rebuild from cached raw data
  python scripts/refresh_pipeline.py --dry-run       # print the plan, run nothing

Steps are listed once in STEPS below. A step whose file does not exist is
skipped, so new downloaders or notebooks only need a line here.

Download steps are "soft": if a source is down, the step is marked
"failed (kept cache)" and the run continues on the cached files. Every other
step is "hard": a non-zero exit stops the run, and validation failure stops
it before the site data is rebuilt. The status goes to
site/data/refresh_status.json either way, then the script exits non-zero if
a hard step failed.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
STATUS = ROOT / "site" / "data" / "refresh_status.json"

# (name, kind, path, soft). kind: script | notebook | fx
STEPS = [
    ("download US monthly (Comtrade)", "script", "src/download_us_comtrade.py", True),
    ("download annual mirror + EU monthly", "script", "src/download_comtrade.py", True),
    ("download EU quantities", "script", "src/download_eu_quantity.py", True),
    ("download competitors", "script", "src/download_competitors.py", True),
    ("refresh FX/CPI cache", "fx", "data/raw/fx", True),
    ("clean", "script", "src/clean.py", False),
    ("notebook 01 explore", "notebook", "notebooks/01_explore.ipynb", False),
    ("notebook 02 forecast", "notebook", "notebooks/02_forecast.ipynb", False),
    ("notebook 03 scenarios", "notebook", "notebooks/03_scenarios.ipynb", False),
    ("notebook 04 competitors", "notebook", "notebooks/04_competitors.ipynb", False),
    ("notebook 05 price/volume", "notebook", "notebooks/05_price_volume.ipynb", False),
    ("validate model", "script", "scripts/validate_model.py", False),
    ("build site data", "script", "scripts/build_site_data.py", False),
]
DOWNLOAD_KINDS = {"fx"}
FX_FILES = ["DEXUSEU.csv", "CPIAUCSL.csv", "ECB_EXR_M_USD_EUR.csv", "BLS_CUSR0000SA0.csv"]


def is_download(name, kind):
    return kind in DOWNLOAD_KINDS or name.startswith("download")


def run(cmd, timeout):
    print("  $", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run(cmd, cwd=ROOT, timeout=timeout).returncode


def refresh_fx():
    """Re-fetch the FX and CPI caches. clean.py reads whatever is cached, so
    without this the caches would never pick up new months. On any failure
    the old files are put back."""
    sys.path.insert(0, str(ROOT / "src"))
    import clean  # noqa: E402
    fx_dir = ROOT / "data" / "raw" / "fx"
    bak = Path(tempfile.mkdtemp())
    for f in FX_FILES:
        if (fx_dir / f).exists():
            shutil.move(fx_dir / f, bak / f)
    try:
        clean.get_series(lambda: clean.fred("DEXUSEU"), clean.ecb_usd_per_eur)
        clean.get_series(lambda: clean.fred("CPIAUCSL"), clean.bls_cpi)
        return 0
    except Exception as e:
        print("  FX/CPI refresh failed:", e)
        for f in FX_FILES:
            (fx_dir / f).unlink(missing_ok=True)
            if (bak / f).exists():
                shutil.move(bak / f, fx_dir / f)
        return 1


def run_notebook(path, outdir):
    # Executed copies go to a temp folder, so the committed notebooks stay as they are.
    # The kernel still runs in notebooks/, so relative paths inside them work.
    return run([PY, "-m", "jupyter", "nbconvert", "--to", "notebook", "--execute",
                "--ExecutePreprocessor.timeout=3600", "--ExecutePreprocessor.kernel_name=python3",
                "--output-dir", str(outdir), str(ROOT / path)], timeout=3900)


def latest_months():
    import pandas as pd
    p = ROOT / "data" / "processed" / "rmg_long.csv"
    if not p.exists():
        return None, None, 0
    d = pd.read_csv(p, usecols=["date", "market"])
    last = d.groupby("market").date.max().str[:7]
    return last.get("US"), last.get("EU"), len(d)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-download", action="store_true", help="use cached raw data only")
    ap.add_argument("--dry-run", action="store_true", help="print the steps and exit")
    a = ap.parse_args()

    log, hard_fail, checks = [], False, None
    outdir = Path(tempfile.mkdtemp(prefix="nb_exec_"))
    for name, kind, path, soft in STEPS:
        entry = {"step": name, "path": path}
        log.append(entry)
        if not (ROOT / path).exists():
            entry["status"] = "skipped (file not found)"
        elif a.skip_download and is_download(name, kind):
            entry["status"] = "skipped (--skip-download)"
        elif hard_fail:
            entry["status"] = "not run (earlier step failed)"
        elif a.dry_run:
            entry["status"] = "would run"
        else:
            print(f"\n== {name}", flush=True)
            t0 = time.time()
            try:
                if kind == "fx":
                    rc = refresh_fx()
                elif kind == "notebook":
                    rc = run_notebook(path, outdir)
                else:
                    rc = run([PY, path], timeout=5400 if soft else 3600)
            except subprocess.TimeoutExpired:
                rc = "timeout"
            entry["seconds"] = round(time.time() - t0)
            if rc == 0:
                entry["status"] = "ok"
            elif soft:
                entry["status"] = f"failed (kept cache; exit {rc})"
            else:
                entry["status"] = f"FAILED (exit {rc})"
                hard_fail = True
            if path == "scripts/validate_model.py":
                checks = rc == 0
        print(f"   {name}: {entry['status']}", flush=True)

    if a.dry_run:
        return 0
    us, eu, rows = latest_months()
    status = {
        "last_run_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "latest_month_us": us, "latest_month_eu": eu, "rows": rows,
        "checks_passed": checks,
        "sources_stale": [e["step"] for e in log if e["status"].startswith("failed")],
        "steps": log,
    }
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    STATUS.write_text(json.dumps(status, indent=1) + "\n")
    print(f"\nstatus -> {STATUS.relative_to(ROOT)}")
    if hard_fail:
        print("REFRESH FAILED: see steps above.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
