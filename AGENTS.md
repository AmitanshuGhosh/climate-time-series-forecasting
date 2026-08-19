# AGENTS.md

Climate time-series analysis project: GISTEMP temperature, Keeling CO2, sunspot cycle.

## Layout
- `src/` - reusable logic (acquire, analysis helpers, models, evaluation, progress)
- `experiments/` - runnable analyses (one per stage)
- `data/raw/` - untouched source files; `data/processed/` - derived series
- `results/` - plots and metrics; `tests/` - self-checks; `docs/process.md` - living log

## Commands
- Install: `.venv/Scripts/python -m pip install -r requirements.txt`
- Acquire data: `.venv/Scripts/python -c "from src.acquire import load_all; load_all()"`

## Rules (from .pi/skills/scientific-ml)
- Real public data only; raw files never modified.
- Report trend significance, not just slopes; distinguish observed vs inferred.
- Imbalanced/eval rigour carries over from the exoplanet project.
- Every claim traceable to a reproducible step.

## Data
- GISTEMP: global land-ocean temp anomaly, monthly, 1880- (NASA GISS)
- CO2: Mauna Loa monthly ppm, 1958- (NOAA GML / Keeling)
- Sunspots: monthly SSN, 1749- (SILSO, WDC-SILSO Brussels)
