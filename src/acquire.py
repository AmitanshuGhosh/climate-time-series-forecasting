"""Acquire and cache the three climate time series (raw data preserved).

Sources (all public, tiny, no API key):
1. NASA GISTEMP — global land-ocean temperature anomaly, monthly, 1880-now
   https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.txt
2. NOAA GML — Mauna Loa CO2 (Keeling curve), monthly, 1958-now
   https://gml.noaa.gov/webdata/ccgg/trends/co2_mm_mlo.csv
3. SILSO — monthly sunspot numbers (natural solar variability), 1749-now
   https://www.sidc.be/silso/INFO/snmtotcsv.php

Files are downloaded once to data/raw/ and never modified.
"""
from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import requests

RAW = Path("data/raw")
RAW.mkdir(parents=True, exist_ok=True)

SOURCES = {
    "gistemp": "https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.txt",
    "co2": "https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_mlo.txt",
    "sunspots": "https://www.sidc.be/silso/INFO/snmtotcsv.php",
}


def fetch(name: str) -> pd.DataFrame:
    """Download (or read from cache) one dataset and return a tidy DataFrame."""
    cache = RAW / f"{name}.csv"
    if cache.exists():
        df = pd.read_csv(cache)
        for c in ("year", "month"):
            df[c] = df[c].astype(int)
        df["date"] = pd.to_datetime(df["date"])
        return df

    r = requests.get(SOURCES[name], timeout=120)
    r.raise_for_status()

    if name == "gistemp":
        # Format: each row is a year; columns 1..12 = Jan..Dec anomalies in
        # 0.01 degC. Skip header/blank lines by keeping rows whose first
        # token is a year (e.g. '1880').
        rows = [ln.split() for ln in r.text.splitlines()
                if ln and ln.split()[0].isdigit()]
        df = pd.DataFrame(rows).apply(pd.to_numeric, errors="coerce")
        df = df.rename(columns={0: "year"})
        df = df.dropna(subset=["year"])
        df["year"] = df["year"].astype(int)
        df = df.rename(columns={c: m for m, c in enumerate(range(1, 13), start=1)})
        df = df.melt(id_vars=["year"], value_vars=list(range(1, 13)),
                     var_name="month", value_name="anomaly")
        df["anomaly"] = df["anomaly"].where(df["anomaly"] > -999) / 100.0  # degC
        df["date"] = pd.to_datetime(dict(year=df["year"], month=df["month"], day=1))
    elif name == "co2":
        df = pd.read_csv(io.StringIO(r.text), comment="#", sep=r"\s+", header=None,
                         names=["year", "month", "dec_date", "average",
                                "interpolated", "trend", "days", "extra"])
        df = df.rename(columns={"average": "co2_ppm"})
        df = df[["year", "month", "co2_ppm"]]
        df["year"] = df["year"].astype(int)
        df["month"] = df["month"].astype(int)
        df["date"] = pd.to_datetime(dict(year=df["year"], month=df["month"], day=1))
    elif name == "sunspots":
        df = pd.read_csv(io.StringIO(r.text), sep=";", header=None)
        df = df.apply(pd.to_numeric, errors="coerce")
        df = df.dropna(subset=[0, 1])
        df = df.rename(columns={0: "year", 1: "month", 3: "ssn"})
        df = df[["year", "month", "ssn"]]
        df["year"] = df["year"].astype(int)
        df["month"] = df["month"].astype(int)
        df["date"] = pd.to_datetime(dict(year=df.year, month=df.month, day=1))

    df.to_csv(cache, index=False)
    print(f"  cached {name} -> {cache} ({len(df)} rows)")
    return df


def load_all():
    """Return dict of the three tidy DataFrames: gistemp, co2, sunspots."""
    return {name: fetch(name) for name in SOURCES}
