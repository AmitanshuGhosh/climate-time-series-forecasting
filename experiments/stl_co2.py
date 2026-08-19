"""Stage 4: STL decomposition of the Keeling curve + seasonal amplitude trend.

Splits monthly Mauna Loa CO2 into Trend + Seasonal + Residual (STL), then
measures the annual seasonal amplitude (max-min of the seasonal component
each year) and tests whether the cycle is growing - a fingerprint of the
biosphere's accelerating carbon uptake.

Run:  .venv/Scripts/python experiments/stl_co2.py
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import theilslopes, kendalltau
from statsmodels.tsa.seasonal import STL

sys.path.insert(0, "src")
from acquire import load_all
from progress import Progress

PLOTS = Path("results/plots")
PLOTS.mkdir(parents=True, exist_ok=True)

prog = Progress(4, desc="STL")
co2 = load_all()["co2"].set_index("date")["co2_ppm"].dropna()
stl = STL(co2, period=12, robust=True).fit()  # monthly -> period 12
prog.update()

df = pd.DataFrame({"obs": co2, "trend": stl.trend, "seasonal": stl.seasonal,
                   "resid": stl.resid})
df["year"] = df.index.year
# peak-trough amplitude needs a FULL year of seasonal values; the partial
# years 1958 (Mar-Dec) and 2026 (Jan-Jul) would understate the trough/peak
full = df.groupby("year")["seasonal"].apply(lambda v: v.max() - v.min() if len(v) == 12 else np.nan)
amp = full.dropna()

x = amp.index.values.astype(float)
slope, intercept, lo, hi = theilslopes(amp.values, x)
_, p = kendalltau(x, amp.values)
print("=== Stage 4: CO2 STL decomposition ===")
print(f"Seasonal amplitude (monthly ppm peak-trough): grows "
      f"{slope * 10:+.3f} ppm per decade, 95% CI=[{lo * 10:+.3f}, {hi * 10:+.3f}], "
      f"MK p={p:.3g}")
print(f"Series: {len(co2)} months, trend covers {df['trend'].notna().sum()} pts, "
      f"residual std={df['resid'].std():.3f} ppm, amplitude years: {len(amp)} "
      f"({amp.index.min()}-{amp.index.max()}, full calendar years only)")
prog.update()

fig, axes = plt.subplots(4, 1, figsize=(10, 9), sharex=True)
for ax, (col, color, lab) in zip(axes, [
        ("obs", "0.35", "observed (monthly ppm)"),
        ("trend", "#c44e52", "trend (STL)"),
        ("seasonal", "#2a7f62", "seasonal (ppm)"),
        ("resid", "#6a51a3", "residual (ppm)")]):
    ax.plot(df.index, df[col], lw=0.6, color=color)
    ax.set_ylabel(lab, fontsize=8)
axes[0].set_title("Mauna Loa CO2 - STL decomposition (period=12, robust)")
axes[-1].set_xlabel("Year")
fig.tight_layout()
fig.savefig(PLOTS / "stl_co2.png", dpi=150)
prog.update()

fig2, ax = plt.subplots(figsize=(10, 3.6))
ax.plot(amp.index, amp.values, "o", ms=3, color="0.4", label="annual amplitude")
ax.plot(amp.index, slope * amp.index.values + intercept, "r--", lw=1.6,
        label=f"Theil-Sen {slope * 10:+.2f} ppm/decade")
ax.set_xlabel("Year"); ax.set_ylabel("Seasonal amplitude (ppm)")
ax.set_title("Growing CO2 seasonal cycle (peak-trough of STL seasonal component)")
ax.legend(fontsize=9)
fig2.tight_layout()
fig2.savefig(PLOTS / "co2_seasonal_amplitude.png", dpi=150)
prog.update()
prog.finish()

print(f"Saved: {PLOTS / 'stl_co2.png'}, {PLOTS / 'co2_seasonal_amplitude.png'}")

# self-check: seasonal amplitude is growing, and it's significant
assert slope > 0 and p < 0.05
