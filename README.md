# Climate Time-Series Analysis

A reproducible study of three real, publicly available climate records:
the global temperature anomaly (NASA GISTEMP), the Mauna Loa CO2 / Keeling
curve (NOAA GML), and monthly sunspot numbers (SILSO). The analysis covers
trend testing, breakpoint analysis, seasonal decomposition, spectral
periodicity, attribution-style partial correlations, event detection, and a
three-model forecasting comparison.

**Full report:** open `results/report.html` (self-contained; all figures
embedded) - or regenerate it with one command.

## Data

| Dataset | Source | Coverage |
|---|---|---|
| Global temperature anomaly (monthly, degC) | NASA GISTEMP v4 | 1880-2026 |
| Mauna Loa CO2 (monthly, ppm) | NOAA GML (Keeling curve) | 1958-2026 |
| Sunspot number (monthly SSN) | SILSO, WDC-SILSO Brussels | 1749-2026 |

Raw files are downloaded once to `data/raw/` (three small public files, no
API keys) and are never modified by analysis code.

## Pipeline

| Stage | Experiment | Finding |
|---|---|---|
| 1 | Exploration | Overview plots and basic statistics |
| 2 | Trends | Temperature +0.082 degC/decade (p~1e-39); CO2 +16.4 ppm/decade |
| 3 | Breakpoint | Post-1970 warming +0.204 degC/decade - significant acceleration |
| 4 | STL decomposition | CO2 seasonal amplitude growing +0.146 ppm/decade |
| 5 | Periodicity | Dominant solar period 11.1 years |
| 6 | Attribution | Temp-CO2 partial r=0.97; solar signal small (r=0.35) |
| 7 | Events | Agung, El Nino years flagged; Pinatubo/1998 explainable near-misses |
| 8 | Forecasting | SARIMA beats XGBoost and LSTM on a 127-month holdout |
| 9 | Report | `experiments/report.py` -> `results/report.html` |

## How to run

```bash
python -m pip install -r requirements.txt          # or .venv/Scripts/python
python experiments/report.py                        # reruns all stages, regenerates plots + report
python experiments/<stage>.py                       # any single stage in isolation
```

Outputs: `results/report.html` (the paper), `results/plots/` (figures), and
`docs/process.md` (living log with per-stage setup, numbers, and reasoning).

## Structure

- `src/` - reusable logic (data acquisition, progress reporting)
- `experiments/` - one runnable script per stage
- `data/raw/` - untouched source files
- `results/` - plots and the final report
- `docs/process.md` - living process documentation
