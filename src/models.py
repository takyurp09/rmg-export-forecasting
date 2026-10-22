"""Forecasting models and backtest helpers for Bangladesh RMG import series.

All model functions share one signature:
    fit_predict(y, h) -> np.ndarray of length h (point forecast, USD)
where y is a monthly pd.Series (freq MS) in USD. Models other than the
seasonal naive work on log(y) and back-transform with exp().
"""
from __future__ import annotations

import itertools
import logging
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
logging.getLogger("prophet").setLevel(logging.ERROR)
logging.getLogger("cmdstanpy").disabled = True

COVID_START, COVID_END = "2020-03-01", "2020-08-01"
H = 12


# ----------------------------------------------------------------- data
def load_series(path: str) -> dict[str, pd.Series]:
    """Return {series_name: monthly USD series}. Names: 'US | Total',
    'EU | Total', 'US | Knit: T-shirts & vests (knit)', 'EU | Knit', ..."""
    df = pd.read_csv(path, parse_dates=["date"])
    out = {}
    for mkt, g in df.groupby("market"):
        out[f"{mkt} | Total"] = g.groupby("date")["value_usd"].sum().asfreq("MS")
        for (ch, pg), gg in g.groupby(["chapter", "product_group"]):
            name = f"{mkt} | {ch}" if mkt == "EU" else f"{mkt} | {ch}: {pg}"
            out[name] = gg.groupby("date")["value_usd"].sum().asfreq("MS")
    return out


def covid_dummy(index: pd.DatetimeIndex) -> np.ndarray:
    return ((index >= COVID_START) & (index <= COVID_END)).astype(float)


def future_index(y: pd.Series, h: int) -> pd.DatetimeIndex:
    return pd.date_range(y.index[-1] + pd.offsets.MonthBegin(), periods=h, freq="MS")


# --------------------------------------------------------------- models
def seasonal_naive(y, h=H):
    return np.resize(y.values[-12:], h)


def ets(y, h=H):
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    ly = np.log(y)
    m = ExponentialSmoothing(ly, trend="add", damped_trend=True, seasonal="add",
                             seasonal_periods=12).fit()
    return np.exp(m.forecast(h).values)


SARIMA_GRID = [((p, 1, q), (P, 1, Q, 12))
               for p, q, P, Q in itertools.product([0, 1], [0, 1], [0, 1], [1])] + \
              [((1, 1, 1), (1, 1, 0, 12)), ((0, 1, 1), (1, 1, 0, 12))]


def _sarima_fit(ly, exog, order=None):
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    best = None
    for o, so in ([order] if order else SARIMA_GRID):
        try:
            r = SARIMAX(ly, exog=exog, order=o, seasonal_order=so,
                        enforce_stationarity=False, enforce_invertibility=False
                        ).fit(disp=False)
        except Exception:
            continue
        if best is None or r.aic < best[0].aic:
            best = (r, (o, so))
    return best


def sarima(y, h=H, return_model=False):
    ly = np.log(y)
    res, order = _sarima_fit(ly, covid_dummy(y.index))
    fc = res.get_forecast(h, exog=np.zeros(h))
    if return_model:
        return fc, order
    return np.exp(fc.predicted_mean.values)


def prophet(y, h=H):
    from prophet import Prophet
    hol = pd.DataFrame({"holiday": "covid", "ds": pd.date_range(COVID_START, COVID_END, freq="MS")})
    m = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False,
                holidays=hol, seasonality_mode="additive", interval_width=0.8)
    m.fit(pd.DataFrame({"ds": y.index, "y": np.log(y.values)}))
    fut = pd.DataFrame({"ds": future_index(y, h)})
    return np.exp(m.predict(fut)["yhat"].values)


LAGS = [1, 2, 3, 6, 12]


def _features(ly: pd.Series) -> pd.DataFrame:
    X = pd.DataFrame(index=ly.index)
    for l in LAGS:
        X[f"lag{l}"] = ly.shift(l)
    X["roll3"] = ly.shift(1).rolling(3).mean()
    X["roll12"] = ly.shift(1).rolling(12).mean()
    X["month"] = ly.index.month
    X["covid"] = covid_dummy(ly.index)
    # base-effect flag: lag 12 fell in the COVID window (e.g. 2021 rebound)
    X["covid_lag12"] = pd.Series(X["covid"].values, index=ly.index).shift(12).fillna(0)
    X["t"] = np.arange(len(ly))
    return X


def lightgbm(y, h=H):
    """Recursive multi-step LightGBM on log level differences from lag 12
    (target = log y_t - log y_{t-12}), which keeps trees from having to
    extrapolate the level."""
    import lightgbm as lgb
    ly = np.log(y).copy()
    X = _features(ly)
    tgt = ly - ly.shift(12)
    ok = X.notna().all(axis=1) & tgt.notna()
    model = lgb.LGBMRegressor(n_estimators=300, learning_rate=0.03, num_leaves=8,
                              min_child_samples=8, subsample=0.8, subsample_freq=1,
                              colsample_bytree=0.8, verbose=-1, random_state=0)
    model.fit(X[ok].drop(columns="t"), tgt[ok])
    hist = ly.copy()
    for d in future_index(y, h):
        hist.loc[d] = np.nan
        xf = _features(hist).loc[[d]].drop(columns="t")
        hist.loc[d] = hist.loc[d - pd.DateOffset(months=12)] + model.predict(xf)[0]
    return np.exp(hist.iloc[-h:].values)


MODELS = {"Seasonal naive": seasonal_naive, "ETS": ets, "SARIMA": sarima,
          "Prophet": prophet, "LightGBM": lightgbm}
# complexity rank for tie-breaks (lower = simpler)
COMPLEXITY = {"Seasonal naive": 0, "ETS": 1, "SARIMA": 2, "Prophet": 3, "LightGBM": 4}


def available_models() -> dict:
    try:
        import prophet as _  # noqa: F401
        return dict(MODELS)
    except ImportError:
        return {k: v for k, v in MODELS.items() if k != "Prophet"}


# -------------------------------------------------------------- metrics
def mase_scale(train: pd.Series) -> float:
    return float(np.mean(np.abs(train.values[12:] - train.values[:-12])))


def metrics(actual, pred, scale) -> dict:
    a, p = np.asarray(actual), np.asarray(pred)
    e = a - p
    return {"MAPE": float(np.mean(np.abs(e / a)) * 100),
            "RMSE": float(np.sqrt(np.mean(e ** 2))),
            "MASE": float(np.mean(np.abs(e)) / scale)}


# ------------------------------------------------------------- backtest
def backtest(series: dict[str, pd.Series], origins, models=None, h=H):
    """Rolling-origin backtest. Each origin is the last training month.
    Returns (metrics_df, errors_df); errors_df has per-horizon log errors
    log(actual/pred) used for empirical intervals."""
    models = models or available_models()
    rows, errs = [], []
    for name, y in series.items():
        for o in pd.to_datetime(origins):
            train, test = y[:o], y[o + pd.offsets.MonthBegin():].iloc[:h]
            if len(test) < h:
                continue
            sc = mase_scale(train)
            for mname, f in models.items():
                p = f(train, h)
                rows.append({"series": name, "model": mname, "origin": o.date(),
                             **metrics(test.values, p, sc)})
                for k in range(h):
                    errs.append({"series": name, "model": mname, "origin": o.date(),
                                 "h": k + 1, "actual": test.values[k], "pred": p[k],
                                 "scale": sc, "log_err": np.log(test.values[k] / p[k])})
    return pd.DataFrame(rows), pd.DataFrame(errs)


def pick_best(summary: pd.DataFrame) -> pd.DataFrame:
    """Lowest mean MASE per series; ties (within 0.005) go to the simpler model."""
    s = summary.copy()
    s["cx"] = s["model"].map(COMPLEXITY)
    s["MASE_r"] = s["MASE"].round(2)
    return (s.sort_values(["series", "MASE_r", "cx"]).groupby("series").head(1)
            .drop(columns=["cx", "MASE_r"]).reset_index(drop=True))


# ------------------------------------------------------------ ensemble
ENSEMBLES = {"Ensemble": ["ETS", "SARIMA", "Prophet", "LightGBM"],
             "Ensemble (no LGBM)": ["ETS", "SARIMA", "Prophet"]}
COMPLEXITY.update({"Ensemble (no LGBM)": 5, "Ensemble": 6})


def add_ensembles(errs: pd.DataFrame, ensembles=None) -> pd.DataFrame:
    """Append equal-weight ensembles to the backtest error table. The
    ensemble forecast is the mean of member log forecasts (a geometric mean
    in USD). Members are fixed in advance, not chosen from the backtest."""
    ensembles = ensembles or ENSEMBLES
    key = ["series", "origin", "h"]
    out = [errs]
    for ename, members in ensembles.items():
        e = errs[errs.model.isin(members)].copy()
        e["lp"] = np.log(e["pred"])
        g = e.groupby(key).agg(actual=("actual", "first"), scale=("scale", "first"),
                               lp=("lp", "mean"), n=("model", "size")).reset_index()
        g = g[g.n == len(members)]
        g["pred"] = np.exp(g["lp"])
        g["log_err"] = np.log(g["actual"] / g["pred"])
        out.append(g.assign(model=ename).drop(columns=["lp", "n"]))
    return pd.concat(out, ignore_index=True)


def metrics_from_errors(errs: pd.DataFrame) -> pd.DataFrame:
    """Per series x model x origin: monthly MAPE, RMSE, MASE, plus
    APE_12m = |sum(actual) - sum(pred)| / sum(actual) over the 12-month
    horizon, and APE_q = mean abs % error of the four quarterly totals."""
    rows = []
    for (s, m, o), g in errs.sort_values("h").groupby(["series", "model", "origin"]):
        a, p = g["actual"].values, g["pred"].values
        r = {"series": s, "model": m, "origin": o, **metrics(a, p, g["scale"].iloc[0])}
        r["APE_12m"] = float(abs(a.sum() - p.sum()) / a.sum() * 100)
        qa, qp = a.reshape(-1, 3).sum(1), p.reshape(-1, 3).sum(1)
        r["APE_q"] = float(np.mean(np.abs(qa - qp) / qa) * 100)
        r["bias_12m"] = float((p.sum() / a.sum() - 1) * 100)
        rows.append(r)
    return pd.DataFrame(rows)


def pick_best_total(summary: pd.DataFrame, tol=1.0) -> pd.DataFrame:
    """Selection rule (v2): among models whose mean 12-month-total APE is
    within `tol` percentage points of the lowest, pick the lowest mean
    monthly MASE; remaining ties go to the simpler model."""
    s = summary.copy()
    s["cx"] = s["model"].map(COMPLEXITY)
    s = s[s["APE_12m"] <= s.groupby("series")["APE_12m"].transform("min") + tol]
    return (s.sort_values(["series", "MASE", "cx"]).groupby("series").head(1)
            .drop(columns="cx").reset_index(drop=True))


def point_forecast(y: pd.Series, model: str, h=H) -> np.ndarray:
    if model in ENSEMBLES:
        return np.exp(np.mean([np.log(MODELS[m](y, h)) for m in ENSEMBLES[model]], axis=0))
    return MODELS[model](y, h)


# ------------------------------------------------------ final forecast
def empirical_intervals(point, log_errs: pd.DataFrame, levels=(0.8, 0.95), window=2):
    """Interval from backtest log errors. For horizon k, pool errors at
    horizons k-window..k+window and take quantiles (split-conformal style)."""
    out = {}
    for lv in levels:
        lo_q, hi_q = (1 - lv) / 2, 1 - (1 - lv) / 2
        lo, hi = [], []
        for k in range(1, len(point) + 1):
            e = log_errs.loc[(log_errs.h >= k - window) & (log_errs.h <= k + window), "log_err"]
            lo.append(point[k - 1] * np.exp(np.quantile(e, lo_q)))
            hi.append(point[k - 1] * np.exp(np.quantile(e, hi_q)))
        tag = int(lv * 100)
        out[f"lo{tag}"], out[f"hi{tag}"] = np.array(lo), np.array(hi)
    return out


def final_forecast(y: pd.Series, model: str, log_errs: pd.DataFrame, h=H) -> pd.DataFrame:
    """Refit on all data. SARIMA uses its own Gaussian intervals on the log
    scale; other models use empirical intervals from backtest errors."""
    idx = future_index(y, h)
    if model == "SARIMA":
        fc, _ = sarima(y, h, return_model=True)
        d = {"point": np.exp(fc.predicted_mean.values)}
        for lv in (0.8, 0.95):
            ci = fc.conf_int(alpha=1 - lv)
            d[f"lo{int(lv*100)}"] = np.exp(ci.iloc[:, 0].values)
            d[f"hi{int(lv*100)}"] = np.exp(ci.iloc[:, 1].values)
    else:
        p = point_forecast(y, model, h)
        d = {"point": p, **empirical_intervals(p, log_errs)}
    return pd.DataFrame(d, index=idx)[["point", "lo80", "hi80", "lo95", "hi95"]]
