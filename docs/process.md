# Process Documentation

Living document for the project: what is analysed, where the data come
from, how the stages depend on each other, and the reasoning behind the
methodological choices.

## 1. Project questions

Three real, publicly available climate time series are analysed:

1. **Is the planet warming, and how do we know?** - trend estimation with
   statistical significance testing (Theil-Sen slope, Mann-Kendall test).
2. **Why does atmospheric CO2 rise and oscillate every year?** - seasonal
   decomposition of the Keeling curve into trend, seasonal cycle, and
   residual, and measurement of the cycle's amplitude over time.
3. **How much of recent warming is solar?** - comparing the temperature
   record against the sunspot cycle (natural variability) and against CO2
   (greenhouse forcing) with partial correlations, plus a three-model
   forecasting comparison.

## 2. Data

| Dataset | Source | Coverage |
|---|---|---|
| Global temperature anomaly (monthly, degC vs 1951-80) | NASA GISTEMP v4 | 1880-2026 |
| Mauna Loa CO2 (monthly, ppm) | NOAA GML (Keeling curve) | 1958-2026 |
| Sunspot number (monthly SSN) | SILSO, WDC-SILSO Brussels | 1749-2026 |

Raw files are downloaded once to `data/raw/` (three small public files, no
API keys) and are never modified by analysis code. The files are committed
to the repository, so the pipeline runs offline. All series are tidied to
(year, month, value, date) form by `src/acquire.py`; nothing else reads the
raw files directly.

## 3. Pipeline stages

| Stage | Script | What it does |
|---|---|---|
| 1 | `experiments/explore.py` | Overview plots and basic statistics |
| 2 | `experiments/trend.py` | Theil-Sen slope + Mann-Kendall test on annual means |
| 3 | `experiments/breakpoint.py` | Warming rate before/after 1970 |
| 4 | `experiments/stl_co2.py` | STL decomposition of CO2, seasonal amplitude trend |
| 5 | `experiments/periodicity.py` | FFT periodogram of sunspots, dominant period |
| 6 | `experiments/attribution.py` | Partial correlations of temperature vs CO2 / sunspots |
| 7 | `experiments/events.py` | Detrended annual anomalies, |z| > 1.5 flags vs documented events |
| 8 | `experiments/forecast.py` | SARIMA vs XGBoost vs LSTM vs persistence, 127-month holdout |
| 9 | `experiments/report.py` | Reruns all stages, parses their output, writes `results/report.html` |

Dependencies: stages 1-8 all read the tidied series from `data/raw/` via
`src/acquire.py`; stages 2, 3, 6, 7 use annual means, stages 4, 5, 8 use
monthly values. `experiments/report.py` runs the other eight as subprocesses
and parses the printed results directly from their stdout, so the report
cannot drift from what the stages compute. Plots are written to
`results/plots/`.

## 4. Method notes

- **Theil-Sen slope**: median of all pairwise slopes; resists outliers far
  better than ordinary least squares. Reported with a 95% confidence
  interval.
- **Mann-Kendall test**: standard non-parametric test for monotonic trend.
  The p-values assume independent observations; because climate series are
  autocorrelated they are anti-conservative, and the report includes an
  AR(1)-based effective-sample-size robustness check.
- **STL decomposition**: Seasonal-Trend decomposition using Loess, applied to
  monthly CO2 (period 12, robust).
- **FFT periodogram**: detrended, Hann-windowed spectrum of monthly sunspot
  numbers. (Lomb-Scargle would be needed for unevenly sampled data; this
  series is evenly sampled, so the FFT is used.)
- **Partial correlation**: correlation of two variables after the linear
  effect of a third is removed from both. Descriptive, not causal.
- **Forecasting**: fixed-origin 127-month holdout (2016-01 to 2026-07); each
  model fits once on the training window and is scored on the holdout only.

## 5. Key methodological decisions

- **Annual means for trend/attribution/events.** Aggregating removes the
  seasonal cycle so it cannot inflate autocorrelation or mask the trend.
- **Breakpoint at 1970.** Fixed by the project plan (the question was
  defined as the warming rate before/after ~1970); a single split, no
  candidate-year scanning. See the discussion in the report.
- **Differenced targets for XGBoost/LSTM.** Recursive forecasting on levels
  compounds small biases into drift; predicting monthly differences removes
  the gross drift (plain recursive XGBoost had temperature MAE 1.01 degC
  versus 0.34-0.67 with differences, depending on the data fix below).
- **Seasonal amplitude from full calendar years only.** A partial year
  misses one side of the seasonal peak-trough, biasing the amplitude (the
  partial 2026 year gave 3.4 ppm versus ~6.5 for full years).
- **Fixed hyperparameters.** No model configuration was tuned on the test
  period.

## 6. Rules

- Real public data only; `data/raw/` is never modified by analysis code.
- Every trend claim carries its significance (p-value / confidence
  interval).
- Observed results are separated from interpretation.
- All years in each dataset are used unless a reason is documented (e.g.
  partial calendar years for the seasonal amplitude).
- Each stage is reproducible with one command.

## 7. How to run

```bash
pip install -r requirements.txt
python experiments/report.py     # runs all stages, regenerates plots and the report
python experiments/trend.py      # any single stage on its own
```

## 8. Stage 8 - forecasting setup and results

**Task.** Forecast each series over the 127-month holdout 2016-01 to
2026-07 (fixed origin; train = everything before 2016-01). Same protocol
for every model, no leakage, no hyperparameter tuning on the test set.

**Protocol.** Each model fits once on the train window, then produces the
full-horizon forecast: SARIMA natively; XGBoost/LSTM recursively (predict
monthly difference, add to level, feed back). Baseline = persistence (last
train value). Metrics: MAE and RMSE on the test set only.

**Setup per model.**

| Model | Setup | Why |
|---|---|---|
| SARIMA | statsmodels `ARIMA`, d=1, seasonal `(0,1,1,12)` (airline model), grid p,q in {0,1,2}, best AIC on train | monthly data needs a seasonal term; the airline model is the standard fit for the Keeling curve |
| XGBoost | target = monthly difference; 12 lag-deltas as features; n_estimators=200, max_depth=4, lr=0.05, random_state=42; recursion rebuilds the level from predicted deltas | differencing prevents recursive drift |
| LSTM | same differenced target, z-scored; 12 lag-deltas as a 12-step sequence (1 feature/step) -> LSTM(hidden 16, 1 layer) -> linear(1); MSE loss, Adam lr=1e-3, batch 64, 30 epochs, seed 42 (torch) | z-scoring stabilizes training; the recurrence sees the 12-month history as a sequence |
| persistence | forecast = last observed train value | naive floor |

**Results (MAE / RMSE, % vs persistence).**

| Series | persistence | SARIMA | XGBoost | LSTM |
|---|---|---|---|---|
| CO2 (ppm) | 14.15 / 16.26 | 2.13 / 2.47 (+85%) | 4.55 / 5.47 (+68%) | 5.10 / 6.23 (+64%) |
| Temperature (degC) | 0.207 / 0.240 | 0.139 / 0.183 (+33%) | 0.673 / 0.736 (-225%) | 0.637 / 0.682 (-208%) |

SARIMA has the lowest error on both series. On CO2 every model beats
persistence; on temperature only SARIMA does. Rankings are conditional on
this single holdout and the fixed configurations.

## 9. Change log

- 2025-08-19: Project started. A previous exoplanet project was removed
  (its MAST downloads were the bottleneck); this climate project replaced
  it.
- 2025-08-19: Stages 0-9 completed - acquisition, exploration, trends,
  breakpoint, STL, periodicity, attribution, events, forecasting, report.
  Key numbers are in the README and the report.
- 2025-08-19: Correctness/reproducibility audit. Notable fixes:
  - GISTEMP parsing: the monthly series is now sorted chronologically after
    reshaping. `pd.melt` emits month-major rows, which corrupted the
    temperature forecasting series; the corrected temperature forecast
    numbers are SARIMA MAE 0.168 -> 0.139, XGBoost 0.341 -> 0.673, LSTM
    0.274 -> 0.637 (CO2 and sunspot results were unaffected).
  - CO2 seasonal amplitude restricted to full calendar years (n=67, MK
    p 6.8e-11 -> 8.9e-12; slope unchanged at +0.146 ppm/decade).
  - Summary statistics report the latest valid observation (GISTEMP ends
    2026-07-01, not 2026-12-01).
  - Event near-miss z-scores are computed, not hard-coded.
  - Report: inclusive year counts, 127-month holdout description, causal
    language tightened, r^2 and autocorrelation/detrending robustness
    checks added, alt text on figures.
- 2025-08-19: Public-release cleanup - removed unused exoplanet modules
  (`src/evaluation.py`, `src/models.py`), ASCII-only sources and docs,
  README rewrite, `.gitignore` and `requirements.txt` updated.
