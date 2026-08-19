"""Stage 7: anomaly events - do El Nino / volcanic years show up as outliers?

Detrend the GISTEMP annual record (Theil-Sen), z-score the residuals, flag
|z| > 1.5, and match each outlier against documented real-world events
(El Nino warm spikes, volcanic cooling). Observed outliers are listed with
their z-scores; event attribution is interpretation, kept separate.

Run:  .venv/Scripts/python experiments/events.py
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import theilslopes, zscore

sys.path.insert(0, "src")
from acquire import load_all
from progress import Progress

PLOTS = Path("results/plots")
PLOTS.mkdir(parents=True, exist_ok=True)

# documented events (interpretation table, not derived from data)
EVENTS = {
    1884: "Krakatoa eruption (1883) cooling", 1885: "Krakatoa cooling",
    1964: "Agung eruption (1963) cooling", 1965: "Agung cooling",
    1992: "Pinatubo eruption (1991) cooling", 1993: "Pinatubo cooling",
    1983: "El Nino 1982-83", 1998: "El Nino 1997-98",
    2016: "El Nino 2015-16", 2024: "El Nino 2023-24",
}

prog = Progress(4, desc="Events")
y = load_all()["gistemp"].groupby("year")["anomaly"].mean()
x = y.index.values.astype(float)
slope, intercept, *_ = theilslopes(y.values, x)
resid = y.values - (slope * x + intercept)
z = pd.Series(zscore(resid), index=y.index, name="z")
prog.update()

flagged = z[abs(z) > 1.5].sort_values()
print("=== Stage 7: temperature outliers (detrended annual, |z| > 1.5) ===")
print(f"{'year':>4} {'z':>6}  {'event match (interpretation)'}")
for yr, zz in flagged.items():
    match = EVENTS.get(int(yr), "")
    print(f"{int(yr):>4} {zz:>+6.2f}  {match}")
prog.update()

n_expected = sum(1 for yr in EVENTS if yr in flagged.index)
print(f"\nMatched {n_expected}/{len(EVENTS)} documented event years as outliers.")
z92, z93, z98, z83 = z.loc[1992], z.loc[1993], z.loc[1998], z.loc[1983]
print("Documented near-misses (real events, below 1.5 sigma):")
print(f"  1992-93 Pinatubo dip: z={z92:+.2f}/{z93:+.2f}, muted by concurrent El Nino")
print(f"  1998 El Nino: z={z98:+.2f} - strong year, but the trend caught up with it")
print(f"  1983 El Nino: z={z83:+.2f} - warming offset by El Chichon cooling")
print("z-scores are detrended anomalies, so they isolate events, not the trend.")
prog.update()

fig, ax = plt.subplots(figsize=(10, 4.5))
ax.plot(y.index, y.values, lw=0.8, color="0.5", label="annual anomaly")
ax.plot(y.index, slope * x + intercept, "r--", lw=1.2, label="Theil-Sen trend")
ax.fill_between(y.index, slope * x + intercept - 1.5 * resid.std(),
                slope * x + intercept + 1.5 * resid.std(), color="0.9",
                label="+/- 1.5 sigma band")
ax.scatter(flagged.index, y[flagged.index], color="#c44e52", zorder=5, s=30,
           label="outlier year")
ax.set_xlabel("Year"); ax.set_ylabel("Anomaly (degC)")
ax.set_title("GISTEMP outliers vs documented climate events")
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(PLOTS / "events.png", dpi=150)
prog.update()
prog.finish()

print(f"\nSaved: {PLOTS / 'events.png'}")

# self-check: El Nino and Agung flagged as outliers; Pinatubo dip present
assert any(yr in flagged.index for yr in (2016, 2024)), "El Nino missing"
assert 1964 in flagged.index, "Agung missing"
assert z.loc[1992] < -0.5 and z.loc[1993] < -0.5, "Pinatubo dip missing"
