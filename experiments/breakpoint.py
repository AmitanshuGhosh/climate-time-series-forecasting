"""Stage 3: breakpoint analysis - warming rate before/after 1970.

Splits the GISTEMP annual record at 1970 and fits Theil-Sen + Mann-Kendall
to each segment. Non-overlapping slope CIs = the acceleration is real, not
sampling noise. (Sensitivity: also shows the pre-1970 and post-1970 windows.)

Run:  .venv/Scripts/python experiments/breakpoint.py
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from scipy.stats import theilslopes, kendalltau

sys.path.insert(0, "src")
from acquire import load_all
from progress import Progress

PLOTS = Path("results/plots")
PLOTS.mkdir(parents=True, exist_ok=True)

BREAK = 1970  # the documented question: pre- vs post-1970 warming

y = load_all()["gistemp"].groupby("year")["anomaly"].mean()
prog = Progress(4, desc="Breakpoint")

def fit(subset):
    x = subset.index.values.astype(float)
    slope, intercept, lo, hi = theilslopes(subset.values, x)
    _, p = kendalltau(x, subset.values)
    return dict(n=len(subset), slope_per_decade=slope * 10, ci=[lo * 10, hi * 10], p=p)

pre, post = y[y.index < BREAK], y[y.index >= BREAK]
segments = {"pre-1970": pre, "post-1970": post}
rows = {}
for name, subset in segments.items():
    rows[name] = fit(subset)
    prog.update()

full = fit(y)
rows["full record"] = full
prog.update()

print("=== Stage 3: warming rate before/after 1970 (degC per decade) ===")
for name, r in rows.items():
    print(f"{name:12s} n={r['n']:3d}  slope={r['slope_per_decade']:+.3f}  "
          f"95% CI=[{r['ci'][0]:+.3f}, {r['ci'][1]:+.3f}]  MK p={r['p']:.3g}")
accel = rows["post-1970"]["slope_per_decade"] - rows["pre-1970"]["slope_per_decade"]
print(f"\nAcceleration: {accel:+.3f} degC per decade per decade")
overlap = rows["post-1970"]["ci"][0] <= rows["pre-1970"]["ci"][1]
print("Post-1970 CI overlaps pre-1970 CI:", overlap,
      "->", "acceleration NOT significant" if overlap else "acceleration significant")
prog.update()
prog.finish()

fig, ax = plt.subplots(figsize=(10, 4.5))
ax.plot(y.index, y.values, lw=0.9, color="0.35", label="annual mean")
for name, subset in segments.items():
    x = subset.index.values.astype(float)
    s, i, *_ = theilslopes(subset.values, x)
    ax.plot(x, s * x + i, lw=1.8, label=f"{name}: {s * 10:+.2f} degC/decade")
ax.axvline(BREAK, color="0.5", ls=":", lw=1)
ax.set_xlabel("Year"); ax.set_ylabel("Anomaly (degC)")
ax.set_title("GISTEMP warming rate before/after 1970 (Theil-Sen fits)")
ax.legend(fontsize=9)
fig.tight_layout()
fig.savefig(PLOTS / "breakpoint.png", dpi=150)
print(f"\nSaved: {PLOTS / 'breakpoint.png'}")

# self-check: post-1970 slope is positive and significant
assert rows["post-1970"]["slope_per_decade"] > 0 and rows["post-1970"]["p"] < 0.05
