# Global Temperature, Atmospheric CO2, and Solar Variability

A reproducible time-series analysis of three public climate records: NASA
GISTEMP temperatures, the Mauna Loa CO2 (Keeling) curve, and SILSO sunspot
numbers. The full report is a self-contained HTML document with embedded
figures: `results/report.html`.

## Overview

The three datasets cover the symptom, the candidate cause, and the control
for the question of recent warming:

- GISTEMP: monthly global land-ocean temperature anomaly, 1880-2026
- Mauna Loa CO2: monthly atmospheric CO2, 1958-2026
- SILSO sunspots: monthly sunspot number, 1749-2026

The analysis asks three questions. Is the planet warming, and is the trend
statistically significant? What drives the annual CO2 cycle, and is it
changing? How much of the warming can be attributed to solar variability
rather than to greenhouse gases?

## Methods

- Theil-Sen trend estimation with 95% confidence intervals
- Mann-Kendall significance testing (with an autocorrelation robustness check)
- Breakpoint analysis of the warming rate before/after 1970
- STL decomposition of the CO2 record
- FFT periodogram for the solar cycle
- Partial correlations for attribution, with detrended and first-difference
  robustness checks
- Forecasting: SARIMA, XGBoost, LSTM, persistence baseline

## Key Results

- Global temperature trend: +0.082 degC per decade (95% CI [+0.073, +0.091])
- Post-1970 trend: +0.204 degC per decade - significant acceleration
- CO2 trend: +16.42 ppm per decade
- CO2 seasonal amplitude: growing +0.146 ppm per decade
- Dominant solar period: 11.10 years
- The temperature-CO2 association survives controlling for sunspots,
  detrending, and first-differencing; the solar association is small and not
  robust to first-differencing
- SARIMA produced the lowest forecast error on both series under the tested
  127-month holdout

These are observational results. Correlations and partial correlations
quantify association, not causation.

## Data

All data are public and small (about 200 KB total). Raw files are downloaded
once to `data/raw/` and never modified by analysis code.

| Dataset | Source | Coverage |
|---|---|---|
| Global temperature anomaly (monthly, degC) | NASA GISTEMP v4 | 1880-2026 |
| Mauna Loa CO2 (monthly, ppm) | NOAA GML (Keeling curve) | 1958-2026 |
| Sunspot number (monthly SSN) | SILSO, WDC-SILSO Brussels | 1749-2026 |

## Reproduction

```bash
pip install -r requirements.txt
python experiments/report.py     # runs all stages, regenerates plots and the report
```

Individual stages can be run on their own (about 2-3 minutes for the full
pipeline, most of it the LSTM training):

```bash
python experiments/trend.py
```

Outputs: `results/report.html` (the report), `results/plots/` (figures), and
`docs/process.md` (a process log with per-stage setup, numbers, and
reasoning).

## Limitations

- Observational data: partial correlation does not establish causation.
- The 1970 breakpoint is a single pre-specified split, not a data-driven
  search across candidate years.
- Significance tests assume independent observations; climate series are
  autocorrelated, and the report includes effective-sample-size checks.
- The forecasting comparison uses a single train/test split; model rankings
  are conditional on that holdout and on the fixed configurations.
- Recent GISTEMP months are preliminary; the 2026 annual value is partial
  (January-July).

## Structure

- `src/` - data acquisition and helpers
- `experiments/` - one runnable script per stage
- `data/raw/` - untouched source files
- `results/` - plots and the final report
- `docs/process.md` - process log
