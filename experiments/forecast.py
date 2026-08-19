"""Stage 8: forecasting — ARIMA vs XGBoost-on-lags vs LSTM.

Question: can we forecast CO2 and temperature ahead, and does a small LSTM
beat classical/ML baselines?

Protocol (identical for every model, no leakage):
  - train: series up to 2015-12; test: 2016-01 -> 2026-07 (127 months,
    "forecast the near future" multi-step task)
  - each model fits ONCE on the train window and forecasts the full test
    horizon recursively (XGBoost/LSTM feed their own predictions back as
    lags; ARIMA forecasts natively)
  - persistence (last train value) is the naive floor; MAE/RMSE on test only

Setup per model (hyperparameters fixed, not tuned on the test set):
  ARIMA     statsmodels SARIMA, d=1, seasonal (0,1,1,12) (airline model for
            monthly data), grid p,q in {0,1,2}, best AIC on train
  XGBoost   target = monthly difference; 12 lag-deltas as features;
            n_estimators=200, max_depth=4, lr=0.05, seed 42; recursion
            rebuilds the level from predicted deltas (prevents drift)
  LSTM      same differenced target, z-scored; 12 lag-deltas as a 12-step
            sequence (1 feature/step) -> LSTM(hidden 16, 1 layer) -> linear(1);
            MSE loss, Adam lr=1e-3, batch 64, 30 epochs, seed 42 (torch)
  baseline  persistence: forecast = last observed train value

Run:  .venv/Scripts/python experiments/forecast.py
"""
import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import xgboost as xgb
from statsmodels.tsa.arima.model import ARIMA

sys.path.insert(0, "src")
from acquire import load_all
from progress import Progress

PLOTS = Path("results/plots")
PLOTS.mkdir(parents=True, exist_ok=True)

SPLIT, LAGS = "2016-01-01", 12
SEED = 42


def split_series(s):
    s = s.dropna()
    tr = s[s.index < SPLIT].values.astype(float)
    te = s[s.index >= SPLIT].values.astype(float)
    return tr, te


def make_lags(v, k=LAGS):
    X = np.stack([v[i - k:i] for i in range(k, len(v))])
    return X, v[k:]


# --- models ----------------------------------------------------------------
def recurse_delta(predict_delta, tr, h):
    """Recursive forecast from a delta model: predict dY, add to level."""
    d = np.diff(tr)
    prev, dhist, out = tr[-1], list(d[-LAGS:]), []
    for _ in range(h):
        nxt = predict_delta(np.array(dhist[-LAGS:]).reshape(1, -1))[0]
        prev += nxt
        out.append(prev)
        dhist.append(nxt)
    return np.array(out)


def fit_arima(tr, h):
    best = None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for p in range(3):
            for q in range(3):
                try:
                    # airline-style SARIMA: seasonal diff+MA(12) fits monthly CO2
                    m = ARIMA(tr, order=(p, 1, q),
                              seasonal_order=(0, 1, 1, 12)).fit()
                    if best is None or m.aic < best.aic:
                        best = m
                except Exception:
                    pass
    return np.asarray(best.forecast(h))


def fit_xgb(tr, h):
    d = np.diff(tr)
    X, y = make_lags(d)
    m = xgb.XGBRegressor(n_estimators=200, max_depth=4, learning_rate=0.05,
                         random_state=SEED, verbosity=0)
    m.fit(X, y)
    return recurse_delta(m.predict, tr, h)


class LSTMNet(nn.Module):
    def __init__(self, k=LAGS, hidden=16):
        super().__init__()
        self.lstm = nn.LSTM(1, hidden, batch_first=True)  # 1 feature, k steps
        self.head = nn.Linear(hidden, 1)

    def forward(self, x):  # (B, k, 1) -> (B, 1)
        out, _ = self.lstm(x)
        return self.head(out[:, -1])


def fit_lstm(tr, h):
    torch.manual_seed(SEED)
    d = np.diff(tr)
    mu, sd = d.mean(), d.std()
    z = (d - mu) / sd
    X, y = make_lags(z)
    Xt = torch.tensor(X, dtype=torch.float32).unsqueeze(-1)  # (B, k, 1)
    yt = torch.tensor(y, dtype=torch.float32).unsqueeze(1)
    model = LSTMNet()
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    lossf = nn.MSELoss()
    model.train()
    for _ in range(30):  # 30 epochs, fixed
        perm = torch.randperm(len(Xt))
        for i in range(0, len(Xt), 64):
            idx = perm[i:i + 64]
            opt.zero_grad()
            lossf(model(Xt[idx]), yt[idx]).backward()
            opt.step()
    model.eval()

    def predict_delta(x):
        with torch.no_grad():
            t = torch.tensor(x, dtype=torch.float32).view(1, LAGS, 1)
            return np.array([model(t).item() * sd + mu])

    return recurse_delta(predict_delta, tr, h)


def fit_persist(tr, h):
    return np.full(h, tr[-1])


# --- evaluation ------------------------------------------------------------
def mae_rmse(obs, pred):
    return abs(obs - pred).mean(), np.sqrt(((obs - pred) ** 2).mean())


data = load_all()
series = {"GISTEMP temperature anomaly (degC)":
          data["gistemp"].set_index("date")["anomaly"],
          "Mauna Loa CO2 (ppm)": data["co2"].set_index("date")["co2_ppm"]}
models = {"ARIMA": fit_arima, "XGBoost": fit_xgb, "LSTM": fit_lstm,
          "persistence": fit_persist}

prog = Progress(len(series) * len(models) + 1, desc="Forecast")
rows = []
COLORS = {"ARIMA": "#c44e52", "XGBoost": "#2a7f62", "LSTM": "#6a51a3",
          "persistence": "0.5"}
fig, axes = plt.subplots(2, 2, figsize=(13, 8.2))
for col, (name, s) in enumerate(series.items()):
    tr, te = split_series(s)
    horizon = pd.date_range(SPLIT, periods=len(te), freq="MS")
    preds = {}
    for mname, fit in models.items():
        pred = fit(tr, len(te))
        mae, rmse = mae_rmse(te, pred)
        rows.append({"series": name, "model": mname, "mae": round(mae, 3),
                     "rmse": round(rmse, 3), "n_test": len(te)})
        preds[mname] = (pred, mae)
        prog.update()
    for row, xlim in ((0, "2000-01-01"), (1, "2014-01-01")):
        ax = axes[row, col]
        ax.plot(s.index, s.values, lw=0.4, color="0.75",
                label="observed (train)" if row == 0 else None)
        ax.plot(horizon, te, lw=1.6, color="0.1",
                label="observed (test)" if row == 0 else None)
        for mname, (pred, mae) in preds.items():
            ax.plot(horizon, pred, lw=1.3, color=COLORS[mname],
                    ls="--" if mname == "persistence" else "-",
                    label=f"{mname} (MAE {mae:.2f})" if row == 0 else None)
        ax.axvline(pd.Timestamp(SPLIT), color="0.4", ls=":", lw=1)
        ax.set_xlim(pd.Timestamp(xlim), s.index.max())
        ax.set_title(f"{name} - forecast detail" if row == 1 else name, fontsize=11)
        if row == 0:
            ax.legend(fontsize=8, ncol=3, loc="upper left")
axes[1, 0].set_xlabel("Year")
axes[1, 1].set_xlabel("Year")

results = pd.DataFrame(rows)
print("=== Stage 8: multi-step forecasts, test 2016-01 -> end ===")
for name, grp in results.groupby("series"):
    base = grp.set_index("model").loc["persistence"]
    print(f"\n{name}: persistence MAE={base['mae']}, RMSE={base['rmse']}")
    for _, r in grp[grp.model != "persistence"].iterrows():
        impr = (1 - r["mae"] / base["mae"]) * 100
        print(f"  {r['model']:8s} MAE={r['mae']:.3f}  RMSE={r['rmse']:.3f}  "
              f"vs persistence: {impr:+.1f}%")

fig.tight_layout()
fig.savefig(PLOTS / "forecast.png", dpi=150)
prog.update()
prog.finish()
print(f"\nSaved: {PLOTS / 'forecast.png'}")

# self-check: classical + ML baselines beat persistence on CO2 (trend+season)
for _, r in results[(results.series.str.contains("CO2"))
                    & (results.model.isin(["ARIMA", "XGBoost"]))].iterrows():
    assert r["mae"] < results[(results.series.str.contains("CO2"))
                              & (results.model == "persistence")]["mae"].iloc[0]
