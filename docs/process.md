# Process Documentation - Climate Time-Series Analysis

Living document: what we are doing, why, and the reasoning behind each step.

## 1. What this project is

We study three real, publicly available climate time series and answer
scientifically meaningful questions about them:

1. **Is the planet actually warming, and how do we know?** - trend analysis
   with statistical significance testing.
2. **Why does atmospheric CO2 go up and down every year?** - seasonal
   decomposition of the famous "Keeling curve".
3. **How much of recent warming is solar?** - comparing the temperature record
   against the 11-year sunspot cycle (natural variability) and against CO2
   (greenhouse forcing).

This is a time-series analysis project: it shows decomposition, periodicity
detection, trend testing, anomaly detection, and forecasting - the analytical
skills, applied to data that matters.

## 2. Why this project

- **Meaningful data.** Global temperature, atmospheric CO2, and solar activity
  are among the most consequential measurements ever made. The analysis
  mirrors how climate scientists actually work (Mann-Kendall trend tests,
  Theil-Sen slopes, seasonal decomposition).
- **Fast, reliable access.** All three sources are small public files (a few
  hundred KB total), fetched in seconds, with no API keys and no throttling - 
  unlike the exoplanet project's MAST downloads, which were the bottleneck
  there.
- **Analytical depth.** The project exercises trend + significance testing,
  breakpoint analysis, seasonal decomposition, spectral/periodicity analysis,
  correlation analysis between series, anomaly detection, and forecasting.

## 3. Data sources (why each one)

| Dataset | Source | Coverage | Why included |
|---|---|---|---|
| Global temperature anomaly (monthly) | NASA GISTEMP v4 | 1880-present | The canonical global warming record; our main target series |
| Mauna Loa CO2 (monthly, ppm) | NOAA GML (Keeling curve) | 1958-present | The greenhouse-gas driver; shows both trend and seasonal cycle |
| Sunspot number (monthly) | SILSO, WDC-SILSO Brussels | 1749-present | Natural solar variability; the control variable in the attribution question |

Raw files are downloaded once to `data/raw/` and never modified. Parsed,
tidy copies are cached there too; all analysis is reproducible from these.

## 4. Pipeline stages

| Stage | What | Why | Status |
|---|---|---|---|
| 0 | Data acquisition + sanity checks | Verified real data before any analysis | done done |
| 1 | Exploratory plots + basic statistics | See the data before modelling it | done done (`experiments/explore.py`) |
| 2 | Trend analysis: Theil-Sen slope + Mann-Kendall test on temperature (and on CO2) | Quantify warming with a significance test, the standard climatology method | done done (`experiments/trend.py`) |
| 3 | Breakpoint analysis: warming rate before/after ~1970 | Is warming accelerating? | done done (`experiments/breakpoint.py`) |
| 4 | Seasonal decomposition of CO2 (STL) | Separate trend, seasonal cycle, residual; measure the cycle's growing amplitude | done done (`experiments/stl_co2.py`) |
| 5 | Periodicity: Lomb-Scargle/FFT on sunspots | Find the ~11-year solar cycle in the data (the same period-finding skill used for exoplanet transits) | done done (`experiments/periodicity.py`) |
| 6 | Attribution: partial correlations of temperature vs CO2 and vs sunspot cycle | Do the data separate the two candidate drivers? | done done (`experiments/attribution.py`) |
| 7 | Anomaly events: El Nino years, volcanic years (Pinatubo dip) | Real-world events should show up as outliers | done done (`experiments/events.py`) |
| 8 | Forecasting: CO2 and temperature (ARIMA vs XGBoost on lags vs LSTM) | Forecast the near future; compare methods honestly | done done (`experiments/forecast.py`) |
| 9 | Report (HTML, research-paper style, embedded figures) | Present the findings | done done (`experiments/report.py` -> `results/report.html`) |

## 5. Method notes (plain English)

- **Theil-Sen slope**: a robust way to measure a trend line - the median of
  all pairwise slopes. Resists outliers better than ordinary least squares.
- **Mann-Kendall test**: the standard statistical test for whether a monotonic
  trend exists (p-value). Reported alongside every slope.
- **STL decomposition**: splits a series into Trend + Seasonal + Residual
  (Seasonal-Trend decomposition using Loess).
- **Lomb-Scargle periodogram**: finds periodic signals in unevenly sampled
  time series (here: monthly data with gaps).
- **Partial correlation**: correlation of A and B after removing the effect of
  C - used to ask "does temperature correlate with CO2 once the solar cycle is
  removed?"
- **Forecasting**: simple baselines (ARIMA, exponential smoothing) vs
  machine-learning (XGBoost on lagged values) vs a small LSTM. Forecasts are
  judged with proper holdout error metrics (MAE/RMSE), never on training data.

## 6. Rules

- Real public data only; `data/raw/` is never modified by analysis code.
- Every trend claim carries its significance (p-value / confidence interval).
- Observed results are clearly separated from interpretation.
- No cherry-picking: all years in each dataset are used unless a reason is
  documented.
- Each stage is reproducible with one command.

## 7. How to run

```bash
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -c "import sys; sys.path.insert(0,'src'); from acquire import load_all; load_all()"
```

Analysis scripts will live in `experiments/` (one per stage).

## 8. Stage 8 - forecasting setup and results

**Task.** Forecast each series 10 years ahead (test 2016-01 -> 2026, fixed
origin; train = everything before 2016-01). Same protocol for every model,
no leakage, no hyperparameter tuning on the test set.

**Protocol.** Each model fits once on the train window, then produces the
full test-horizon forecast: SARIMA natively; XGBoost/LSTM recursively
(predict delta, add to level, feed back). Baseline = persistence (last
train value). Metrics: MAE and RMSE on the test set only.

**Setup per model.**

| Model | Setup | Why |
|---|---|---|
| SARIMA | statsmodels `ARIMA`, d=1, seasonal `(0,1,1,12)` (airline model), grid p,q in {0,1,2}, best AIC on train | monthly data needs a seasonal term; the airline model is the standard fit for the Keeling curve |
| XGBoost | target = monthly difference; 12 lag-deltas as features; n_estimators=200, max_depth=4, lr=0.05, random_state=42; recursion rebuilds the level from predicted deltas | differencing prevents the drift that plain recursive XGBoost showed (MAE 1.01 on temperature vs 0.34 with deltas) |
| LSTM | same differenced target, z-scored; 12 lag-deltas as a 12-step sequence (1 feature/step) -> LSTM(hidden 16, 1 layer) -> linear(1); MSE loss, Adam lr=1e-3, batch 64, 30 epochs, seed 42 (torch) | z-scoring stabilizes training; sequence shaped (B,12,1) so the recurrence actually sees the 12-month history |
| persistence | forecast = last observed train value | naive floor, so "beats the baseline" is always quantified |

**Results (MAE / RMSE, % vs persistence).**

| Series | persistence | SARIMA | XGBoost | LSTM |
|---|---|---|---|---|
| CO2 (ppm) | 14.15 / 16.26 | **2.13 / 2.47 (+85%)** | 4.55 / 5.47 (+68%) | 5.10 / 6.23 (+64%) |
| Temperature (degC) | 0.207 / 0.240 | **0.168 / 0.205 (+19%)** | 0.341 / 0.406 (-65%) | 0.274 / 0.338 (-32%) |

**Reading.** SARIMA wins on both series. On CO2 every model beats
persistence - the trend + seasonal cycle is learnable. On temperature
anomaly only SARIMA adds skill; the ML recursive forecasts add noise, not
signal (temperature is near-AR(1) noise on top of the trend - nothing for
lag-based ML to exploit beyond what SARIMA already models). Reproduce:
`.venv/Scripts/python experiments/forecast.py`; plot `results/plots/forecast.png`.

## 9. Change log

- 2025-08-19: Previous exoplanet project removed (MAST downloads were the
  bottleneck). Project 1 (climate) started.
- 2025-08-19: Stage 0 done - three datasets acquired and validated
  (GISTEMP 1880-2026, CO2 1958-2026, sunspots 1749-2026; spot checks passed).
- 2025-08-19: Stage 1 done - exploratory plots + basic stats
  (`experiments/explore.py`, `results/plots/overview.png`, `zoom.png`).
- 2025-08-19: Stage 2 done - Theil-Sen + Mann-Kendall on annual means
  (`experiments/trend.py`): temperature +0.082 degC/decade (95% CI
  [+0.073, +0.091], p=1.4e-39); CO2 +16.4 ppm/decade (CI [+15.7, +17.2],
  p=1.2e-98).
- 2025-08-19: Stage 3 done - breakpoint at 1970 (`experiments/breakpoint.py`):
  pre-1970 +0.037 degC/decade (CI [+0.026, +0.048], p=5e-9) vs post-1970
  +0.204 degC/decade (CI [+0.182, +0.222], p=4e-20). CIs do not overlap ->
  acceleration significant. Plot: `results/plots/breakpoint.png`.
- 2025-08-19: Stage 4 done - STL on monthly CO2 (`experiments/stl_co2.py`):
  seasonal amplitude grows +0.146 ppm/decade (CI [+0.115, +0.179], p=6.8e-11);
  residual std 0.266 ppm. Plots: `results/plots/stl_co2.png`,
  `results/plots/co2_seasonal_amplitude.png`.
- 2025-08-19: Stage 5 done - sunspot periodicity (`experiments/periodicity.py`):
  FFT on detrended monthly SSN finds the dominant period at **11.10 years**
  (half-power span 10.7-11.1 yr); per-half-century periodograms show the
  cycle wanders (classic 9-13 yr). Plots: `results/plots/sunspot_periodicity.png`,
  `results/plots/sunspot_cycle_evolution.png`.
- 2025-08-19: Stage 6 done - attribution (`experiments/attribution.py`):
  annual 1958-2026, partial correlations: temp vs CO2 | sunspots r=+0.972
  (p=1e-43); temp vs sunspots | CO2 r=+0.351 (p=0.003). CO2 dominates; a
  small residual solar signal remains - consistent with literature. Plot:
  `results/plots/attribution.png`.
- 2025-08-19: Stage 7 done - events (`experiments/events.py`): z-scored
  detrended annual anomalies, |z|>1.5 flags: 1964 Agung, 2016 El Nino,
  2024 El Nino, plus a noisy 1880s cluster. Documented near-misses:
  Pinatubo dip (z=-0.95, muted by concurrent El Nino), 1998 El Nino
  (z=+0.75, trend caught up), 1983 (offset by El Chichon). Plot:
  `results/plots/events.png`.
- 2025-08-19: Stage 8 done - forecasting (`experiments/forecast.py`):
  SARIMA vs XGBoost vs LSTM, 127-month holdout (2016-01 to 2026-07). SARIMA
  wins both series (CO2 MAE 2.13, temp 0.139); XGBoost and LSTM beat
  persistence on CO2 (MAE 4.55 / 5.10) but lose to persistence on temperature
  (0.67 / 0.64). Full per-model setup in section 8 above.
- 2025-08-19: AUDIT PASS - full reproducibility/correctness audit of the
  project and report. Fixes applied:
  * `src/acquire.py`: GISTEMP tidy frame was month-major (pd.melt default),
    not chronological - this corrupted the GISTEMP forecasting series and the
    explore overview/zoom plots. Now sorted by date on parse and cache read;
    cached CSVs rewritten. GISTEMP forecast numbers corrected (SARIMA MAE
    0.168 -> 0.139; XGBoost 0.341 -> 0.673; LSTM 0.274 -> 0.637). CO2 and
    sunspot results unchanged.
  * `experiments/stl_co2.py`: seasonal amplitude restricted to full calendar
    years (1959-2025, n=67) - the partial 2026 year (Jan-Jul) missed the
    Sep-Oct trough and produced an artifact (3.4 ppm vs ~6.5); slope
    unchanged (+0.146), MK p 6.8e-11 -> 8.9e-12.
  * `experiments/explore.py`: summary-stats "end" and "latest" now taken
    from the latest valid observation (GISTEMP: 2026-07-01 / 1.23, not
    2026-12-01 / 1.06).
  * `experiments/events.py`: near-miss z-scores (Pinatubo -0.95/-0.95,
    1998 +0.75, 1983 -0.12) now computed, not hard-coded.
  * `experiments/report.py`: abstract year counts corrected (147 / 69 / 278,
    inclusive); holdout described as 127 months, not "ten years"; causal
    language tightened throughout (association vs attribution); attribution
    table now reports r^2 and a labelled supplementary robustness paragraph
    (detrended and first-difference correlations, effective sample size);
    trend section reports an AR(1)-effective-n modified-Mann-Kendall
    robustness check (temp p ~ 1e-39 -> ~ 8e-5 under correction; post-1970
    ~ 4e-11; CO2 correction unreliable, tau = 1.00 unchanged); discussion
    covers autocorrelation and partial-year effects; figures get alt text.
  * `requirements.txt`: added `requests` (used by acquire.py); corrected the
    CO2 URL in the acquire.py docstring (.txt, not .csv).
- 2025-08-19: Stage 9 done - final report (`experiments/report.py`): reruns all
  8 stage scripts, parses their numbers directly from stdout (no transcription
  drift), embeds all 11 figures as base64, and writes `results/report.html`
  (research-paper structure: abstract, intro, data, methods, results with
  per-figure plain-English analysis, discussion/limitations, conclusions,
  reproducibility). One command regenerates everything.
