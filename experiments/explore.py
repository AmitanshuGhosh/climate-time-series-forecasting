"""Stage 1: explore the three climate time series.

Overview plots + basic statistics for GISTEMP temperature, Mauna Loa CO2,
and sunspot numbers. Saves plots to results/plots/, prints stats.

Run:  .venv/Scripts/python experiments/explore.py
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, "src")
from acquire import load_all
from progress import Progress

PLOTS = Path("results/plots")
PLOTS.mkdir(parents=True, exist_ok=True)

prog = Progress(4, desc="Explore")
data = load_all()
prog.update()

g, c, s = data["gistemp"], data["co2"], data["sunspots"]

# --- basic statistics ------------------------------------------------------
def stats(df, col):
    v = df[col].dropna()
    return dict(n=len(v), start=df["date"].min().date(), end=df["date"].max().date(),
                latest=round(v.iloc[-1], 2), mean=round(v.mean(), 2),
                std=round(v.std(), 2), min=round(v.min(), 2), max=round(v.max(), 2))

rows = [pd.Series({"series": "GISTEMP temp anomaly (degC)", **stats(g, "anomaly")}),
        pd.Series({"series": "Mauna Loa CO2 (ppm)", **stats(c, "co2_ppm")}),
        pd.Series({"series": "Sunspot number (SSN)", **stats(s, "ssn")})]
stats_df = pd.DataFrame(rows).set_index("series")
print("=== Basic statistics ===")
print(stats_df.to_string())

# decadal temperature means (warmth check)
g["decade"] = (g["year"] // 10) * 10
dec = g.groupby("decade")["anomaly"].mean().round(2)
print("\n=== Decadal mean temperature anomaly (degC) ===")
print(dec.to_string())
print(f"1880s -> 2020s change: {dec[2020] - dec[1880]:+.2f} degC")

prog.update()

# --- plots -----------------------------------------------------------------
fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=False)

# 1. temperature
ax = axes[0]
ax.plot(g["date"], g["anomaly"], lw=0.4, color="0.7", label="monthly")
annual = g.groupby("year")["anomaly"].mean()
ax.plot(pd.to_datetime(annual.index, format="%Y"), annual.values, lw=1.5,
        color="#c44e52", label="annual mean")
ax.axhline(0, color="0.4", lw=0.7)
ax.set_ylabel("Anomaly (degC, 1951-80 base)")
ax.set_title("Global land-ocean temperature anomaly (NASA GISTEMP)")
ax.legend(loc="upper left", fontsize=8)

# 2. CO2
ax = axes[1]
ax.plot(c["date"], c["co2_ppm"], lw=0.7, color="#2a7f62")
ax.set_ylabel("CO2 (ppm)")
ax.set_title("Mauna Loa CO2 - the Keeling curve (NOAA GML)")

# 3. sunspots
ax = axes[2]
ax.plot(s["date"], s["ssn"], lw=0.4, color="#6a51a3")
ax.set_ylabel("Sunspot number")
ax.set_xlabel("Year")
ax.set_title("Monthly sunspot number - the ~11-year solar cycle (SILSO)")

fig.tight_layout()
fig.savefig(PLOTS / "overview.png", dpi=150)
prog.update()

# zoom: temperature since 1970, CO2 seasonal cycle zoom
fig2, axes2 = plt.subplots(1, 2, figsize=(11, 3.8))
ax = axes2[0]
recent = g[g["date"] >= "1970-01-01"]
ax.plot(recent["date"], recent["anomaly"], lw=0.4, color="0.7")
ann2 = recent.groupby("year")["anomaly"].mean()
ax.plot(pd.to_datetime(ann2.index, format="%Y"), ann2.values, lw=1.5, color="#c44e52")
ax.axhline(0, color="0.4", lw=0.7); ax.set_ylabel("Anomaly (degC)")
ax.set_title("Temperature since 1970")
ax = axes2[1]
recent_c = c[c["date"] >= "2015-01-01"]
ax.plot(recent_c["date"], recent_c["co2_ppm"], lw=0.8, color="#2a7f62")
ax.set_ylabel("CO2 (ppm)"); ax.set_title("CO2 seasonal cycle (2015-now)")
fig2.tight_layout()
fig2.savefig(PLOTS / "zoom.png", dpi=150)
prog.update()
prog.finish()

print(f"\nSaved plots: {PLOTS/'overview.png'}, {PLOTS/'zoom.png'}")
