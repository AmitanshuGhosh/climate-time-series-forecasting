# Global Temperature, Atmospheric CO2, and Solar Variability

A reproducible time-series analysis of three public climate records: NASA
GISTEMP temperatures, the Mauna Loa CO2 (Keeling) curve, and SILSO sunspot
numbers. Every stage is a runnable script, and the final report is a
self-contained HTML document: `results/report.html`.

## Overview

The three datasets cover the symptom, the candidate cause, and the control
for the question of recent warming:

- GISTEMP: monthly global land-ocean temperature anomaly, 1880-2026
- Mauna Loa CO2: monthly atmospheric CO2, 1958-2026
- SILSO sunspots: monthly sunspot number, 1749-2026

The analysis asks three questions. Is the planet warming, and is the trend
statistically significant? What drives the annual CO2 cycle, and is it
changing? How strongly are the observed warming trends associated with CO₂ and solar variability?

## Key Results

- Global temperature trend: +0.082 degC per decade (95% CI [+0.073, +0.091])
- Post-1970 trend: +0.204 degC per decade, a statistically significant
  acceleration
- CO2 trend: +16.42 ppm per decade
- CO2 seasonal amplitude: growing +0.146 ppm per decade
- Dominant solar period: 11.10 years
- The temperature-CO2 association survives controlling for sunspots,
  detrending, and first-differencing; the solar association is small and not
  robust to first-differencing

Forecasting (127-month holdout, 2016-01 to 2026-07, MAE):

| Model | Temperature (degC) | CO2 (ppm) |
|---|---|---|
| SARIMA | 0.139 | 2.13 |
| XGBoost | 0.673 | 4.55 |
| LSTM | 0.637 | 5.10 |
| Persistence | 0.207 | 14.15 |

These are observational results. Correlations and partial correlations
quantify association, not causation.

## Methods

- Theil-Sen trend estimation with 95% confidence intervals
- Mann-Kendall significance testing (with an autocorrelation robustness check)
- Breakpoint analysis of the warming rate before/after 1970
- STL decomposition of the CO2 record
- FFT periodogram for the solar cycle
- Partial correlations for attribution, with detrended and first-difference
  robustness checks
- Forecasting: SARIMA, XGBoost, LSTM, persistence baseline

## Data

All three datasets are public and small (about 200 KB total). Raw files are
downloaded once to `data/raw/` and never modified by analysis code. The
datasets were collected and published by their respective institutions, not
by this project.

| Dataset | Source | Coverage | URL |
|---|---|---|---|
| Global temperature anomaly (monthly, degC) | NASA GISTEMP v4 | 1880-2026 | https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.txt |
| Mauna Loa CO2 (monthly, ppm) | NOAA GML (Keeling curve) | 1958-2026 | https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_mlo.txt |
| Sunspot number (monthly SSN) | SILSO, WDC-SILSO Brussels | 1749-2026 | https://www.sidc.be/silso/INFO/snmtotcsv.php |

## Reproduction

Requires Python 3.10 or newer (developed and tested on 3.10).

```bash
pip install -r requirements.txt
python experiments/report.py     # runs all 8 stages, regenerates plots, HTML and PDF report
```

`report.py` reruns every analysis from the raw data and takes about 2-3
minutes, most of it LSTM training. Individual stages can be run on their own:

```bash
python experiments/trend.py
python experiments/forecast.py
```

Outputs: `results/report.html` and `results/report.pdf` (the report),
`results/plots/` (figures), and `docs/process.md` (process log).

## Project Structure

```
src/               data loading and helpers
experiments/       one runnable script per analysis stage
data/raw/          downloaded source files (committed, never modified)
results/           plots and report.html
docs/process.md    process log
```

## Limitations

- Observational data: partial correlation does not establish causation.
- The 1970 breakpoint is a single planned split (fixed by the project plan),
  not a data-driven search across candidate years.
- Significance tests assume independent observations; climate series are
  autocorrelated, and the report includes effective-sample-size robustness
  checks.
- The partial solar correlation (r = 0.35) rests on a limited effective
  sample size and does not survive first-differencing.
- The forecasting comparison uses a single fixed holdout; model rankings are
  conditional on that holdout and on the fixed model configurations.
- The growing CO2 seasonal amplitude is measured directly, but its biological
  mechanism is not established by this dataset.
- Recent GISTEMP months are preliminary; the 2026 annual value is partial
  (January-July).

## Report

- `results/report.html` - full report, self-contained with all figures embedded
- `results/report.pdf` - PDF version, printed from the HTML

Both are produced by `python experiments/report.py` and document the data,
methods, results, limitations, and reproducibility in research-paper style.
The PDF step uses headless Chrome/Edge from the system (no Python
dependency); if neither browser is installed, only the HTML is produced.
