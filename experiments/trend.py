"""Stage 2: trend analysis - Theil-Sen slope + Mann-Kendall significance.

Quantifies warming in GISTEMP and CO2 growth in Mauna Loa with the standard
climatology toolkit: robust Theil-Sen slope (with CI) and Kendall's tau
(Mann-Kendall) significance test. Uses annual means so the seasonal cycle
doesn't inflate autocorrelation.

Run:  .venv/Scripts/python experiments/trend.py
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

data = load_all()
annual = {
    "GISTEMP temperature anomaly (degC)": data["gistemp"].groupby("year")["anomaly"].mean(),
    "Mauna Loa CO2 (ppm)": data["co2"].groupby("year")["co2_ppm"].mean(),
}

prog = Progress(len(annual) + 1, desc="Trends")
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
rows = []
for ax, (name, y) in zip(axes, annual.items()):
    x = y.index.values.astype(float)
    slope, intercept, lo, hi = theilslopes(y.values, x)
    tau, p = kendalltau(x, y.values)  # Mann-Kendall statistic + significance
    rows.append({"series": name, "n_years": len(y),
                 "slope_per_decade": round(slope * 10, 3),
                 "ci95_per_decade": f"[{lo * 10:+.3f}, {hi * 10:+.3f}]",
                 "mk_tau": round(tau, 3), "mk_p": f"{p:.3g}"})

    ax.plot(x, y, lw=0.9, color="0.35", label="annual mean")
    ax.plot(x, slope * x + intercept, "r--", lw=1.6, label="Theil-Sen fit")
    ax.set_xlabel("Year")
    ax.set_title(f"{name}\nslope {slope * 10:+.2f} per decade, MK p={p:.3g}",
                 fontsize=10)
    ax.legend(fontsize=8)
    prog.update()

fig.tight_layout()
fig.savefig(PLOTS / "trends.png", dpi=150)
prog.update()
prog.finish()

print("=== Stage 2: trends on annual means (Theil-Sen + Mann-Kendall) ===")
print(pd.DataFrame(rows).set_index("series").to_string())

# self-check: both trends are positive and significant
assert all(r["slope_per_decade"] > 0 for r in rows)
assert all(float(r["mk_p"]) < 0.05 for r in rows)
print(f"\nSaved: {PLOTS / 'trends.png'}")
