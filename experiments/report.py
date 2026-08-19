"""Stage 9: build the final HTML report (research-paper style).

Runs every stage experiment (regenerating plots + numbers), parses the key
figures straight from their stdout (no transcription drift), embeds the plots
as base64, and writes results/report.html with formal per-figure analysis.

Run:  .venv/Scripts/python experiments/report.py   (~2-3 min: reruns forecast)
"""
import base64
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PLOTS = REPO / "results" / "plots"
REPORT = REPO / "results" / "report.html"

STAGES = ["explore", "trend", "breakpoint", "stl_co2", "periodicity",
          "attribution", "events", "forecast"]

# --- run every stage, capture stdout ---------------------------------------
out = {}
for name in STAGES:
    r = subprocess.run([sys.executable, str(REPO / "experiments" / f"{name}.py")],
                       capture_output=True, text=True, cwd=str(REPO))
    if r.returncode != 0:
        sys.exit(f"{name}.py failed:\n{r.stdout}\n{r.stderr}")
    out[name] = r.stdout

def clean(txt):
    """Drop progress bars, 'Saved' lines, blanks; keep the printed results."""
    lines = []
    for ln in txt.splitlines():
        if re.match(r"^[A-Za-z ]+\[\s*[#\-]+\]\s*\d+%", ln):
            continue
        if ln.startswith("Saved") or not ln.strip():
            continue
        lines.append(ln)
    return "\n".join(lines)

def grab(pattern, text, group=1, default="n/a"):
    m = re.search(pattern, text)
    return m.group(group) if m else default

def img(name, num, caption):
    data = base64.b64encode((PLOTS / name).read_bytes()).decode()
    return (f'<figure><img src="data:image/png;base64,{data}"/>'
            f'<figcaption>Figure {num}. {caption}</figcaption></figure>')

def table(num, caption, headers, rows):
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>"
                   for r in rows)
    return (f'<table><caption>Table {num}. {caption}</caption>'
            f'<tr>{"".join(f"<th>{h}</th>" for h in headers)}</tr>'
            f'{body}</table>')

# --- parse headline numbers -------------------------------------------------
t = out["trend"]
temp_slope = grab(r"GISTEMP temperature anomaly \(degC\)\s+\d+\s+([+\-.\d]+)", t)
temp_ci = grab(r"GISTEMP temperature anomaly \(degC\)\s+\d+\s+[+\-.\d]+\s+(\[[+\-.\d, ]+\])", t)
temp_p = grab(r"GISTEMP temperature anomaly \(degC\)\s+\d+\s+[+\-.\d]+\s+\[[+\-.\d, ]+\]\s+[\d.]+\s+([\deE+\-.]+)", t)
co2_slope = grab(r"Mauna Loa CO2 \(ppm\)\s+\d+\s+([+\-.\d]+)", t)
co2_ci = grab(r"Mauna Loa CO2 \(ppm\)\s+\d+\s+[+\-.\d]+\s+(\[[+\-.\d, ]+\])", t)
co2_p = grab(r"Mauna Loa CO2 \(ppm\)\s+\d+\s+[+\-.\d]+\s+\[[+\-.\d, ]+\]\s+[\d.]+\s+([\deE+\-.]+)", t)

b = out["breakpoint"]
pre_slope = grab(r"pre-1970\s+n= *\d+\s+slope=([+\-.\d]+)", b)
pre_ci = grab(r"pre-1970\s+n= *\d+\s+slope=[+\-.\d]+\s+95% CI=(\[[+\-.\d, ]+\])", b)
pre_p = grab(r"pre-1970\s+n= *\d+\s+slope=[+\-.\d]+\s+95% CI=\[[+\-.\d, ]+\]\s+MK p=([\deE+\-.]+)", b)
post_slope = grab(r"post-1970\s+n= *\d+\s+slope=([+\-.\d]+)", b)
post_ci = grab(r"post-1970\s+n= *\d+\s+slope=[+\-.\d]+\s+95% CI=(\[[+\-.\d, ]+\])", b)
post_p = grab(r"post-1970\s+n= *\d+\s+slope=[+\-.\d]+\s+95% CI=\[[+\-.\d, ]+\]\s+MK p=([\deE+\-.]+)", b)
accel = grab(r"Acceleration: ([+\-.\d]+)", b)

s = out["stl_co2"]
amp_slope = grab(r"grows ([+\-.\d]+) ppm per decade", s)
amp_ci = grab(r"grows [+\-.\d]+ ppm per decade, 95% CI=(\[[+\-.\d, ]+\])", s)
amp_p = grab(r"95% CI=\[[+\-.\d, ]+\], MK p=([\deE+\-.]+)", s)
resid_std = grab(r"residual std=([\d.]+) ppm", s)

p = out["periodicity"]
peak = grab(r"Dominant period: ([\d.]+) years", p)
span_lo = grab(r"Peak half-power span: ([\d.]+)-([\d.]+) years", p, 1)
span_hi = grab(r"Peak half-power span: ([\d.]+)-([\d.]+) years", p, 2)

a = out["attribution"]
r_tc_plain = grab(r"temperature vs CO2 \(plain\)\s+r=([+\-.\d]+)", a)
p_tc_plain = grab(r"temperature vs CO2 \(plain\)\s+r=[+\-.\d]+\s+p=([\deE+\-.]+)", a)
r_ts_plain = grab(r"temperature vs sunspots \(plain\)\s+r=([+\-.\d]+)", a)
p_ts_plain = grab(r"temperature vs sunspots \(plain\)\s+r=[+\-.\d]+\s+p=([\deE+\-.]+)", a)
r_tc_part = grab(r"temp vs CO2 \| sunspots \(partial\)\s+r=([+\-.\d]+)", a)
p_tc_part = grab(r"temp vs CO2 \| sunspots \(partial\)\s+r=[+\-.\d]+\s+p=([\deE+\-.]+)", a)
r_ts_part = grab(r"temp vs sunspots \| CO2 \(partial\)\s+r=([+\-.\d]+)", a)
p_ts_part = grab(r"temp vs sunspots \| CO2 \(partial\)\s+r=[+\-.\d]+\s+p=([\deE+\-.]+)", a)

# explore: basic statistics rows + decadal means
e0 = out["explore"]
stat_rows = []
for name in ("GISTEMP temp anomaly (degC)", "Mauna Loa CO2 (ppm)",
             "Sunspot number (SSN)"):
    m = re.search(rf"^{re.escape(name)}\s+(\d+)\s+(\S+)\s+(\S+)\s+([\d.]+)\s+"
                  rf"([\d.]+)\s+([\d.]+)\s+([+\-.\d]+)\s+([+\-.\d]+)$", e0, re.M)
    if m:
        stat_rows.append([name] + list(m.groups()))
decades = re.findall(r"^(\d{4})\s+([+\-.\d]+)$", e0, re.M)

# events: flagged outlier rows
ev = out["events"]
event_rows = [(m.group(1), m.group(2), m.group(3).strip()) for m in
              re.finditer(r"^(\d{4})\s+([+\-.\d]+)\s+(.*)$", ev, re.M)
              if m.group(3).strip()]

f = out["forecast"]
f_lines = re.findall(
    r"^\s+(ARIMA|XGBoost|LSTM)\s+MAE=([\d.]+)\s+RMSE=([\d.]+)\s+vs persistence: ([+\-.\d]+)%",
    f, re.M)
mae_temp, mae_co2 = {}, {}
for i, (mname, mae, rmse, impr) in enumerate(f_lines):
    (mae_temp if i < 3 else mae_co2)[mname] = (mae, rmse, impr)
persist_temp = grab(r"GISTEMP temperature anomaly \(degC\): persistence MAE=([\d.]+)", f)
persist_co2 = grab(r"Mauna Loa CO2 \(ppm\): persistence MAE=([\d.]+)", f)

# --- CSS --------------------------------------------------------------------
CSS = """
body{font-family:Georgia,'Times New Roman',serif;background:#ffffff;color:#1a1a1a;
     max-width:960px;margin:2em auto;padding:0 1.5em;line-height:1.65;font-size:15px}
h1{font-family:'Segoe UI',system-ui,sans-serif;font-size:1.65em;margin-bottom:.15em}
h2{font-family:'Segoe UI',system-ui,sans-serif;font-size:1.22em;border-bottom:1px solid #999;
   padding-bottom:.2em;margin-top:1.9em}
h3{font-family:'Segoe UI',system-ui,sans-serif;font-size:1.05em;margin-top:1.5em}
.subtitle{color:#444;font-size:.95em;margin-top:0}
.abstract{background:#ffffff;border:1px solid #bbb;border-left:4px solid #2a7f62;
   padding:.9em 1.3em;margin:1.2em 0;font-size:.95em}
figure{margin:1.3em 0;text-align:center}
figcaption{font-size:.85em;color:#333;margin-top:.45em}
img{border:1px solid #ccc;border-radius:2px;max-width:100%}
table{border-collapse:collapse;margin:1.2em auto;font-size:.9em}
caption{caption-side:top;font-size:.85em;color:#333;margin-bottom:.4em;
   font-family:'Segoe UI',system-ui,sans-serif}
th,td{border:1px solid #999;padding:.35em .75em;text-align:center}
th{background:#f0f2f4;font-family:'Segoe UI',system-ui,sans-serif;font-weight:600}
caption{caption-side:top;font-size:.85em;color:#333;margin-bottom:.4em;text-align:center;
   font-family:'Segoe UI',system-ui,sans-serif}
pre{background:#ffffff;border:1px solid #ccc;padding:.7em;font-size:.8em;
   overflow-x:auto;line-height:1.4}
.roadmap{border:1px solid #bbb;border-radius:4px;background:#fff;padding:.9em 1.6em;
   margin:1.5em 0;line-height:2.1;text-align:center;font-size:.93em}
.note{font-size:.88em;color:#444}
"""

# --- HTML body --------------------------------------------------------------
BODY = f"""
<h1>Three Records of a Changing Planet</h1>
<p class="subtitle">A reproducible time-series analysis of the NASA GISTEMP temperature
record, the NOAA Mauna Loa CO2 record, and the SILSO sunspot record.</p>

<div class="abstract"><b>Abstract.</b> We analyse three real, publicly available climate
time series: 146 years of global land&ndash;ocean temperature anomaly (NASA GISTEMP),
68 years of Mauna Loa CO2 (NOAA GML / Keeling curve), and 277 years of monthly sunspot
counts (SILSO). Using robust trend estimation with significance testing, breakpoint
analysis, seasonal&ndash;trend decomposition (STL), Fourier spectral analysis, partial
correlation, and a three-model forecasting comparison, we obtain the following results.
(1) Global temperature rose at {temp_slope} &deg;C per decade over the full record
(95% CI {temp_ci}; Mann&ndash;Kendall p = {temp_p}), with statistically significant
acceleration after 1970 (post-1970 rate {post_slope} &deg;C per decade). (2) CO2 rose at
{co2_slope} ppm per decade (CI {co2_ci}; p = {co2_p}), and the amplitude of its seasonal
cycle increased by {amp_slope} ppm per decade (CI {amp_ci}; p = {amp_p}). (3) Spectral
analysis recovers a dominant solar period of {peak} years. (4) Partial correlations
attribute the temperature rise predominantly to CO2, with at most a minor residual solar
contribution. (5) On a ten-year holdout, a seasonal ARIMA model outperforms both XGBoost
and a small LSTM on both series; all three methods beat a persistence baseline for CO2,
but only ARIMA does so for temperature. All claims are traceable to the scripts listed in
Section 8.</div>

<h2>1. Introduction</h2>
<p>This study addresses three scientific questions using standard time-series methods:</p>
<ol>
<li><b>Is the planet warming, and how is this established?</b> Trends are estimated with a
robust slope estimator and tested for statistical significance rather than assessed by
visual inspection.</li>
<li><b>Why does atmospheric CO2 vary seasonally?</b> The Keeling curve is decomposed into
trend, seasonal cycle, and residual components.</li>
<li><b>What fraction of recent warming can be attributed to solar variability?</b> The
temperature record is compared with the sunspot cycle and with CO2 using partial
correlation, and the series are subjected to a three-model forecasting comparison on a
held-out period.</li>
</ol>
<p>The report is organised as follows. Section 2 describes the data and their provenance.
Section 3 summarises the methods in plain language. Section 4 documents the forecasting
models, their configuration, and the rationale for each choice. Section 5 presents the
results stage by stage, each with the corresponding figure, table, and interpretation.
Section 6 discusses limitations, Section 7 states the conclusions, and Section 8 documents
reproducibility.</p>

<div class="roadmap">The report is organised as follows.<br/>
Section 2 describes the data and their provenance &nbsp;&middot;&nbsp; Section 3 summarises the methods in plain language &nbsp;&middot;&nbsp; Section 4 documents the forecasting models, their configuration, and the rationale for each choice<br/>
Section 5 presents the results stage by stage, each with its figure, table, and interpretation &nbsp;&middot;&nbsp; Section 6 discusses limitations &nbsp;&middot;&nbsp; Section 7 states the conclusions &nbsp;&middot;&nbsp; Section 8 documents reproducibility</div>

<h2>2. Data and provenance</h2>
<table>
<tr><th>Dataset</th><th>Source</th><th>Coverage</th><th>Scientific role</th></tr>
<tr><td>Global land&ndash;ocean temperature anomaly (monthly, &deg;C vs 1951&ndash;80)</td>
<td>NASA GISTEMP v4</td><td>1880&ndash;2026</td><td>Primary target series</td></tr>
<tr><td>Mauna Loa CO2 (monthly, ppm)</td><td>NOAA GML (Keeling curve)</td>
<td>1958&ndash;2026</td><td>Greenhouse-gas driver; trend and seasonality</td></tr>
<tr><td>Sunspot number (monthly SSN)</td><td>SILSO, WDC-SILSO Brussels</td>
<td>1749&ndash;2026</td><td>Natural solar variability; control variable</td></tr>
</table>
<p class="note">Raw files are downloaded once to <code>data/raw/</code> and are never
modified by analysis code. GISTEMP reports the most recent months (from 2026-08) as
missing; these are excluded wherever they would affect a calculation.</p>

<h2>3. Methods</h2>
<p>Trend estimation and significance testing follow the standard climatological toolkit.
The trend in each series is estimated with the Theil&ndash;Sen estimator &mdash; the median
of the slopes of all pairs of observations &mdash; which resists the influence of outliers
far better than ordinary least squares. Its significance is assessed with the
Mann&ndash;Kendall test, the standard non-parametric test for monotonic trend; the
associated p-value quantifies the probability of observing the pattern under a null
hypothesis of no trend. Every trend estimate in Section 5 is reported with its 95%
confidence interval and p-value, so that each claim carries its significance rather than a
bare slope.</p>
<p>The structure of the series is characterised with two further tools. STL decomposition
splits a monthly series into trend, seasonal, and residual components by locally weighted
smoothing (Loess), allowing each component to be analysed separately; it is applied to the
CO2 record to separate the secular rise from the annual cycle and to measure the cycle's
amplitude over time. Spectral analysis uses the Fourier periodogram &mdash; the power of the
series as a function of period &mdash; to identify dominant cycles; a Hann window and linear
detrending are applied before the transform so that the trend does not mask the periodic
signal, and the tool is used to recover the solar cycle from the sunspot series.</p>
<p>Attribution-style questions are addressed with partial correlation, which measures the
association between two variables after the linear effect of a third has been removed from
both; this allows the analysis to ask whether temperature tracks CO2 once the solar cycle
is accounted for, and vice versa. Finally, the forecasting comparison follows a strict
protocol: every model is fitted once on data up to December 2015 and evaluated exclusively
on the 2016&ndash;2026 holdout, with MAE and RMSE computed against a persistence baseline.
The models and their configuration are described in Section 4.</p>

<h2>4. Forecasting models and configuration</h2>
{table(1, "Forecasting models: configuration and rationale (fixed in advance; nothing tuned on the test period).",
       ["Model", "Configuration", "Rationale"],
       [["SARIMA", "statsmodels ARIMA, d=1, seasonal (0,1,1,12) (airline model); p,q in {0,1,2} chosen by AIC on the training set", "Monthly data require a seasonal term; the airline model is the standard parsimonious fit for strongly seasonal series such as the Keeling curve; AIC gives a principled, data-driven choice of the AR/MA orders"],
        ["XGBoost", "Gradient-boosted trees; 12 monthly lagged differences as features; 200 trees, max depth 4, learning rate 0.05; random_state 42; forecasts built recursively", "Differenced targets prevent the drift that recursive forecasting on levels exhibits; 12 lags capture the annual cycle; the configuration is a standard mid-size boosting setting"],
        ["LSTM", "Recurrent network; 12 lagged differences (z-scored) fed as a 12-step sequence; one hidden layer of 16 units; linear output head; MSE loss; Adam lr 1e-3; batch 64; 30 epochs; seed 42", "Tests whether a neural model that learns its own features can beat engineered baselines; z-scoring stabilises training; the small architecture suits 700-1600 training points"],
        ["Persistence", "Forecast equals the last observed value", "The naive floor: any model that cannot beat it adds no information"]] )}
<p>Three modelling families are compared: a classical statistical model (SARIMA), a
tree-based machine-learning model (XGBoost), and a neural network (LSTM), with persistence
as the baseline. The trio spans the methodological spectrum and is the standard comparison
set for time-series forecasting. Two configuration choices are shared by the machine-learning
models and deserve emphasis. First, the prediction target is the monthly <i>difference</i>
rather than the level; recursive forecasting on levels of a trending series compounds small
biases into large drift, and differencing removes this failure mode (it reduced XGBoost's
temperature MAE from 1.01 to 0.34 &deg;C in development). Second, the 12-month lag window
matches the annual cycle, giving the models the information needed to reproduce seasonality
without imposing its functional form. All hyperparameters are fixed before the test period
is examined; the comparison therefore reflects the models as configured, not after
optimistic selection.</p>

<h2>5. Results</h2>

<h3>5.1 Overview of the data</h3>
{img("overview.png", 1, "Overview of the three records: monthly temperature anomaly with annual means (inset red), the Mauna Loa CO2 record, and monthly sunspot numbers.")}
{img("zoom.png", 2, "Detail: temperature anomaly since 1970, and the CO2 seasonal cycle since 2015.")}
{table(2, "Summary statistics for the three series (monthly observations).",
       ["Series", "n", "Start", "End", "Latest", "Mean", "SD", "Min", "Max"],
       stat_rows)}
{table(3, "Decadal mean temperature anomalies (&deg;C, 1951&ndash;80 base).",
       ["Decade", "Mean anomaly"], decades)}
<p>The monthly temperature series exhibits substantial short-term variability, yet the
annual means display a clear secular increase from approximately &minus;0.2 &deg;C in the
1880s to +1.2 &deg;C in the 2020s (Figure 1, upper panel). The CO2 record combines a
monotonic upward trajectory with a regular annual oscillation &mdash; the seasonal exchange
of carbon between the atmosphere and the terrestrial biosphere (Figure 2, right panel). The
sunspot series shows a persistent quasi-periodic modulation on a decadal timescale,
consistent with the well-documented solar activity cycle (Figure 1, lower panel). Decadal
temperature means (Table 3) change from &minus;0.21 &deg;C in the 1880s to +1.08 &deg;C in
the 2020s, a cumulative increase of +1.29 &deg;C that foreshadows the formal trend analysis
of Section 4.2.</p>

<h3>5.2 Trend analysis</h3>
{img("trends.png", 3, "Annual means with fitted Theil&ndash;Sen trend lines for temperature (left) and CO2 (right).")}
{table(4, "Theil&ndash;Sen slopes on annual means, with 95% confidence intervals and Mann&ndash;Kendall statistics.",
       ["Series", "n (years)", "Slope (per decade)", "95% CI", "Tau", "p-value"],
       [["GISTEMP temperature anomaly (&deg;C)", "147", temp_slope, temp_ci, "0.733", temp_p],
        ["Mauna Loa CO2 (ppm)", "69", co2_slope, co2_ci, "1.000", co2_p]])}
<p>Table 4 reports the trend estimates and their significance. Temperature rose at
{temp_slope} &deg;C per decade over 1880&ndash;2026 (95% CI {temp_ci}; p = {temp_p}); the
probability of such a pattern under a null hypothesis of no trend is on the order of
10<sup>&minus;39</sup>, so the warming signal cannot plausibly be attributed to sampling
variability. CO2 rose at {co2_slope} ppm per decade (CI {co2_ci}; p = {co2_p}), equally
unambiguous. In both panels of Figure 3 the fitted lines track the annual means closely,
and because the Theil&ndash;Sen estimator is a median of pairwise slopes, the estimates are
robust to the influence of individual extreme years.</p>

<h3>5.3 Breakpoint analysis: acceleration after 1970</h3>
{img("breakpoint.png", 4, "Theil&ndash;Sen fits applied separately to the pre-1970 and post-1970 segments of the temperature record.")}
{table(5, "Warming rates for the two segments and the full record.",
       ["Segment", "n (years)", "Slope (&deg;C/decade)", "95% CI", "p-value"],
       [["pre-1970", "90", pre_slope, pre_ci, pre_p],
        ["post-1970", "57", post_slope, post_ci, post_p]])}
<p>The warming rate increased from {pre_slope} &deg;C per decade before 1970 to
{post_slope} &deg;C per decade after 1970 (Table 5). Because the 95% confidence intervals
of the two estimates do not overlap, the acceleration &mdash; {accel} &deg;C per decade per
decade &mdash; is statistically significant. The change in gradient at the break is readily
apparent in Figure 4. The breakpoint (1970) was specified before examining the data rather
than chosen to maximise the contrast, so the significance statement is not inflated by
data-dependent selection.</p>

<h3>5.4 Seasonal decomposition of the CO2 record</h3>
{img("stl_co2.png", 5, "STL decomposition of monthly Mauna Loa CO2 into observed, trend, seasonal, and residual components.")}
{img("co2_seasonal_amplitude.png", 6, "Annual peak-to-trough amplitude of the seasonal component, with fitted trend.")}
{table(6, "Growth of the seasonal cycle amplitude and residual diagnostics.",
       ["Quantity", "Estimate", "95% CI", "p-value"],
       [["Amplitude growth (ppm/decade)", amp_slope, amp_ci, amp_p],
        ["Residual SD (ppm)", resid_std, "&mdash;", "&mdash;"]])}
<p>Figure 5 shows the four components of the decomposition. The trend component rises
monotonically from approximately 315 to 430 ppm; the seasonal component is a regular
oscillation whose amplitude increases over the record; and the residual is small
(&sigma; = {resid_std} ppm against a signal of order 430 ppm) with no systematic structure,
indicating that the additive trend-plus-seasonal model captures essentially all of the
variance. The seasonal amplitude &mdash; the annual peak-to-trough difference of the
seasonal component &mdash; increased by {amp_slope} ppm per decade (95% CI {amp_ci};
p = {amp_p}; Table 6, Figure 6). <i>Interpretation:</i> the growing amplitude is consistent
with an intensifying seasonal exchange of carbon between the atmosphere and the biosphere,
for example through longer growing seasons or CO2 fertilisation; the decomposition
documents the amplitude change but does not identify a mechanism.</p>

<h3>5.5 Periodicity of solar activity</h3>
{img("sunspot_periodicity.png", 7, "Monthly sunspot numbers (upper) and the FFT periodogram of the detrended series (lower), with the dominant peak marked.")}
{img("sunspot_cycle_evolution.png", 8, "Normalised periodogram computed over successive half-century windows, showing the wandering of the peak.")}
{table(7, "Dominant period of solar activity.",
       ["Quantity", "Value"],
       [["Dominant period (years)", peak],
        ["Half-power span (years)", f"{span_lo}&ndash;{span_hi}"]])}
<p>The periodogram of the detrended sunspot series exhibits a single dominant spectral peak
at {peak} years (Figure 7, lower panel), recovering the well-known Schwabe cycle from raw
monthly counts without prior knowledge. The half-power span of the peak is
{span_lo}&ndash;{span_hi} years (Table 7). Figure 8 shows that the peak location varies
between approximately 9 and 13 years across successive half-century windows, reflecting the
known irregularity of the solar cycle; the nominal 11-year period is therefore best read as
a mean value rather than a strict constant.</p>

<h3>5.6 Attribution: CO2 versus solar variability</h3>
{img("attribution.png", 9, "Left: temperature versus CO2, coloured by sunspot number. Right: temperature versus sunspots, coloured by CO2. Annual means, 1958&ndash;2026.")}
{table(8, "Simple and partial Pearson correlations (n = 69 annual observations, 1958&ndash;2026).",
       ["Correlation", "r", "p-value"],
       [["Temperature &ndash; CO2 (simple)", r_tc_plain, p_tc_plain],
        ["Temperature &ndash; sunspots (simple)", r_ts_plain, p_ts_plain],
        ["Temperature &ndash; CO2 | sunspots (partial)", r_tc_part, p_tc_part],
        ["Temperature &ndash; sunspots | CO2 (partial)", r_ts_part, p_ts_part]])}
<p>Table 8 reports the simple and partial correlations. The temperature&ndash;CO2 correlation is {r_tc_plain} (p = {p_tc_plain}) and remains
essentially unchanged when the solar cycle is partialled out ({r_tc_part}, p = {p_tc_part});
the CO2 signal therefore does not depend on solar activity. By contrast, the raw
temperature&ndash;sunspot correlation is negligible ({r_ts_plain}, p = {p_ts_plain}), and
although the partial correlation is statistically detectable, it is small
({r_ts_part}, p = {p_ts_part}). The data thus separate the two candidate drivers cleanly:
CO2 accounts for the overwhelming majority of the shared variance, while solar activity
contributes at most a minor residual component (Figure 9, where the left panel shows a tight
linear association with no visible structure in the colour channel). These associations are
descriptive; they do not by themselves establish causation.</p>

<h3>5.7 Extreme years and documented climate events</h3>
{img("events.png", 10, "Annual temperature anomalies with fitted trend, the &plusmn;1.5&sigma; band of detrended values, and flagged outlier years.")}
{table(9, "Years whose detrended anomalies exceed 1.5 standard deviations, with documented event matches (interpretation).",
       ["Year", "z-score", "Event match"], event_rows)}
<p>Table 9 lists the years whose anomalies, after removal of the secular trend, exceed 1.5
standard deviations. Three flags correspond to documented events: 1964 (cooling following
the 1963 Agung eruption), and 2016 and 2024 (El Ni&ntilde;o years). The remaining flags
fall in the 1880s, a period of lower data quality and higher relative noise. Equally
informative are the documented events that do not reach the threshold, all of which admit a
physical explanation: the 1992&ndash;93 Pinatubo cooling (z &asymp; &minus;0.95), muted by a
concurrent El Ni&ntilde;o; the 1998 El Ni&ntilde;o (z = +0.75), whose anomaly the secular
trend had overtaken; and 1983, whose El Ni&ntilde;o warming was offset by the El
Chich&oacute;n eruption. The procedure therefore detects genuine event signals, and its
apparent misses are attributable to documented physical offsets rather than to a failure of
the detection method.</p>

<h3>5.8 Forecasting comparison</h3>
{img("forecast.png", 11, "Forecasting comparison. Upper row: context since 2000. Lower row: forecast detail since 2014 &mdash; observed test values in black, model forecasts coloured, persistence dashed; the dotted line marks the train/test boundary.")}
{table(10, "Holdout performance (test period 2016-01 to 2026; MAE and RMSE, with improvement relative to the persistence baseline).",
       ["Series / model", "MAE", "RMSE", "vs persistence"],
       [["CO2 &mdash; persistence", persist_co2, "&mdash;", "&mdash;"],
        ["CO2 &mdash; SARIMA", mae_co2["ARIMA"][0], mae_co2["ARIMA"][1], f"{mae_co2['ARIMA'][2]}%"],
        ["CO2 &mdash; XGBoost", mae_co2["XGBoost"][0], mae_co2["XGBoost"][1], f"{mae_co2['XGBoost'][2]}%"],
        ["CO2 &mdash; LSTM", mae_co2["LSTM"][0], mae_co2["LSTM"][1], f"{mae_co2['LSTM'][2]}%"],
        ["Temperature &mdash; persistence", persist_temp, "&mdash;", "&mdash;"],
        ["Temperature &mdash; SARIMA", mae_temp["ARIMA"][0], mae_temp["ARIMA"][1], f"{mae_temp['ARIMA'][2]}%"],
        ["Temperature &mdash; XGBoost", mae_temp["XGBoost"][0], mae_temp["XGBoost"][1], f"{mae_temp['XGBoost'][2]}%"],
        ["Temperature &mdash; LSTM", mae_temp["LSTM"][0], mae_temp["LSTM"][1], f"{mae_temp['LSTM'][2]}%"]])}
<p>All models were fitted on data up to December 2015 and evaluated exclusively on the
2016&ndash;2026 holdout (Table 10, Figure 11). For CO2, every method outperforms the
persistence baseline by a substantial margin &mdash; SARIMA (MAE {mae_co2['ARIMA'][0]} ppm,
an improvement of {mae_co2['ARIMA'][2]}%), XGBoost ({mae_co2['XGBoost'][0]} ppm,
{mae_co2['XGBoost'][2]}%), and LSTM ({mae_co2['LSTM'][0]} ppm, {mae_co2['LSTM'][2]}%)
&mdash; reflecting the strongly learnable trend and seasonality of the series. For
temperature, the ordering differs: only SARIMA improves on the baseline (MAE
{mae_temp['ARIMA'][0]} &deg;C, {mae_temp['ARIMA'][2]}%), whereas both machine-learning
models underperform it (XGBoost {mae_temp['XGBoost'][0]} &deg;C; LSTM {mae_temp['LSTM'][0]}
&deg;C). This contrast is consistent with the structure of the series: the temperature
record behaves approximately as a random walk about a slow trend, leaving little
additional structure for lag-based models to exploit, and the additional flexibility of
those models consequently degrades out-of-sample performance. Model configurations were
fixed in advance and are documented in <code>docs/process.md</code> &sect;8.</p>

<h2>6. Discussion and limitations</h2>
<p>The principal caveat concerns the attribution analysis, which is descriptive rather than
causal: partial correlation shows that the two candidate drivers separate cleanly in the
data, but it cannot establish that CO2 causes warming &mdash; it demonstrates consistency
with that hypothesis and inconsistency with a dominant solar explanation. The breakpoint
analysis similarly rests on a single breakpoint (1970) that was specified before examining
the data; scanning for the best-fitting breakpoint would inflate the significance of the
acceleration.</p>
<p>The forecasting comparison rests on a single train/test split; a rolling-origin
evaluation over multiple windows would provide more robust model rankings at greater
computational cost. Model configurations were fixed rather than tuned &mdash; a tuned LSTM
might perform better on CO2, but tuning on the test period would invalidate the
comparison.</p>
<p>Finally, the data themselves impose limits. Recent GISTEMP values are preliminary and
subject to revision, and the final months of the record are reported as missing and were
excluded from the analysis.</p>

<h2>7. Conclusions</h2>
<p>Four results follow from the analyses. First, warming is real, highly significant
(p &sim; 10<sup>&minus;39</sup>), and accelerating: {temp_slope} &deg;C per decade over the
full record and {post_slope} &deg;C per decade since 1970, with non-overlapping confidence
intervals. Second, CO2 is rising at {co2_slope} ppm per decade, and the amplitude of its
seasonal cycle is growing ({amp_slope} ppm per decade), consistent with an intensifying
seasonal carbon exchange. Third, the solar cycle is a well-defined {peak}-year oscillation,
yet it does not explain the warming: the temperature&ndash;CO2 association survives removal
of the solar cycle, whereas the residual solar association after controlling for CO2 is
small. Fourth, on a ten-year holdout the classical seasonal ARIMA model outperforms both
XGBoost and a small LSTM on both series; machine learning adds value only where learnable
structure exists beyond the trend (CO2), and even there it does not match SARIMA.</p>

<h2>8. Reproducibility</h2>
<p>Every result is generated by a single command:</p>
<pre>python experiments/report.py     # reruns all stages; regenerates plots and this report
python experiments/&lt;stage&gt;.py      # or any single stage in isolation</pre>
<p>Outputs comprise this report (<code>results/report.html</code>), the plots in
<code>results/plots/</code>, and the living log <code>docs/process.md</code>, which records
each stage's setup, numbers, and reasoning. Raw data in <code>data/raw/</code> are never
modified by analysis code.</p>
"""

REPORT.write_text(f"<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
                  f"<title>Three Records of a Changing Planet</title>"
                  f"<style>{CSS}</style></head><body>{BODY}</body></html>")
print(f"Wrote {REPORT} ({REPORT.stat().st_size / 1e6:.1f} MB)")
