"""Stage 5: periodicity - find the ~11-year solar cycle in sunspot numbers.

Evenly sampled monthly SSN since 1749 -> windowed FFT periodogram on the
detrended series. The dominant peak should land on the ~11-year Schwabe cycle
(same period-finding skill as exoplanet transit searches, simpler sampling).

Run:  .venv/Scripts/python experiments/periodicity.py
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import signal

sys.path.insert(0, "src")
from acquire import load_all
from progress import Progress

PLOTS = Path("results/plots")
PLOTS.mkdir(parents=True, exist_ok=True)

prog = Progress(4, desc="Periodicity")
ssn = load_all()["sunspots"].set_index("date")["ssn"].dropna()
prog.update()

# detrend (the 250-yr drift would otherwise dominate low frequencies) + window
x = signal.detrend(ssn.values)
x = x * np.hanning(len(x))
fs = 12.0  # monthly samples per year
f, Pxx = signal.periodogram(x, fs=fs)

periods = np.zeros_like(f)
with np.errstate(divide="ignore"):
    periods[f > 0] = 1.0 / f[f > 0]
mask = (periods >= 2) & (periods <= 100)  # ignore DC-edge and sub-annual
i = np.argmax(Pxx[mask])
peak_period = periods[mask][i]
print("=== Stage 5: sunspot periodicity (FFT periodogram) ===")
print(f"Dominant period: {peak_period:.2f} years (power {Pxx[mask][i]:.1e})")
# peak width at half max, in years, as a crude stability range
half = Pxx[mask][i] / 2
in_peak = periods[mask][Pxx[mask] > half]
print(f"Peak half-power span: {in_peak.min():.1f}-{in_peak.max():.1f} years")
assert 8 <= peak_period <= 15, "expected the ~11-year Schwabe cycle"
prog.update()

fig, axes = plt.subplots(2, 1, figsize=(10, 6.5), sharex=False)
axes[0].plot(ssn.index, ssn.values, lw=0.4, color="#6a51a3")
axes[0].set_ylabel("Sunspot number"); axes[0].set_title("Monthly sunspot number (SILSO)")
axes[1].semilogy(periods[mask], Pxx[mask], lw=0.9, color="#c44e52")
axes[1].axvline(peak_period, color="0.3", ls="--", lw=1,
                label=f"peak at {peak_period:.1f} yr")
axes[1].set_xlabel("Period (years)"); axes[1].set_ylabel("Power")
axes[1].set_title("FFT periodogram (detrended, Hann window)")
axes[1].legend(fontsize=9)
fig.tight_layout()
fig.savefig(PLOTS / "sunspot_periodicity.png", dpi=150)
prog.update()

# second panel: periodogram by half-century to show the cycle length wanders
fig2, ax2 = plt.subplots(figsize=(10, 3.6))
for start in range(1750, 2026, 50):
    seg = ssn[(ssn.index.year >= start) & (ssn.index.year < start + 50)]
    if len(seg) < 100:
        continue
    xs = signal.detrend(seg.values) * np.hanning(len(seg))
    ff, pp = signal.periodogram(xs, fs=fs)
    with np.errstate(divide="ignore"):
        periods_ff = np.where(ff > 0, 1.0 / ff, np.inf)
    keep = (periods_ff >= 5) & (periods_ff <= 20)
    ax2.plot(periods_ff[keep], pp[keep] / pp[keep].max(), lw=1.2,
             label=f"{start}-{start + 49}")
ax2.set_xlabel("Period (years)"); ax2.set_ylabel("Normalized power")
ax2.set_title("Cycle length per half-century (normalized) - period wanders 9-13 yr")
ax2.legend(fontsize=8, ncol=4)
fig2.tight_layout()
fig2.savefig(PLOTS / "sunspot_cycle_evolution.png", dpi=150)
prog.update()
prog.finish()

print(f"Saved: {PLOTS / 'sunspot_periodicity.png'}, "
      f"{PLOTS / 'sunspot_cycle_evolution.png'}")
