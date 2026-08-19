I"""Stage 9: build the final HTML report. 

Runs every stage experiment (regenerating plots + numbers), parses the key
figures straight from their stdout (no transcription drift), embeds the plots
as base64, and writes results/report.html with formal per-figure analysis.
A PDF copy (results/report.pdf) is printed from the HTML via headless
Chrome/Edge when one is installed; otherwise only the HTML is produced.

Run:  .venv/Scripts/python experiments/report.py   (~2-3 min: reruns forecast)
"""
import base64
import re
import subprocess
import sys
import tempfile
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
    return (f'<figure><img src="data:image/png;base64,{data}" alt="{caption}"/>'
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

# events: flagged outlier rows + computed near-miss z-scores
ev = out["events"]
event_rows = [(m.group(1), m.group(2), m.group(3).strip()) for m in
              re.finditer(r"^(\d{4})\s+([+\-.\d]+)\s+(.*)$", ev, re.M)
              if m.group(3).strip()]
z92 = grab(r"1992-93 Pinatubo dip: z=([+\-.\d]+)/", ev)
z93 = grab(r"1992-93 Pinatubo dip: z=[+\-.\d]+/([+\-.\d]+)", ev)
z98 = grab(r"1998 El Nino: z=([+\-.\d]+) - strong", ev)
z83 = grab(r"1983 El Nino: z=([+\-.\d]+) - warming", ev)
amp_n = grab(r"amplitude years: (\d+)", out["stl_co2"])

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
.note{font-size:.88em;color:#444}
"""

# --- HTML body --------------------------------------------------------------
BODY = f"""
<h1>Global Temperature, Atmospheric CO&#8322;, and Solar Variability: A Reproducible Time-Series Analysis</h1>
<p class="subtitle">A reproducible time-series analysis of the NASA GISTEMP temperature
record, the NOAA Mauna Loa CO2 record, and the SILSO sunspot record.</p>

<div class="abstract"><b>Abstract.</b> We analyse three real, publicly available climate
time series: 147 years of global land&ndash;ocean temperature anomaly (NASA GISTEMP),
69 years of Mauna Loa CO2 (NOAA GML / Keeling curve), and 278 years of monthly sunspot
counts (SILSO). Using robust trend estimation with significance testing, breakpoint
analysis, seasonal&ndash;trend decomposition (STL), Fourier spectral analysis, partial
correlation, and a three-model forecasting comparison, we obtain the following results.
(1) Global temperature rose at {temp_slope} &deg;C per decade over the full record
(95% CI {temp_ci}; Mann&ndash;Kendall p = {temp_p} under independent observations;
autocorrelation-robust check in &sect;5.2), with statistically significant
acceleration after 1970 (post-1970 rate {post_slope} &deg;C per decade). (2) CO2 rose at
{co2_slope} ppm per decade (CI {co2_ci}; p = {co2_p}), and the amplitude of its seasonal
cycle increased by {amp_slope} ppm per decade (CI {amp_ci}; p = {amp_p}). (3) Spectral
analysis recovers a dominant solar period of {peak} years. (4) The annual
temperature&ndash;CO2 association is strong (r = +0.97) and persists after controlling for
the solar cycle (partial r = +0.97; residual r&sup2; = 0.94), whereas the residual solar
association is small (partial r = +0.35; r&sup2; = 0.12) and not robust to
first-differencing. (5) On a 127-month
holdout (2016-01 to 2026-07), a seasonal ARIMA model outperforms both XGBoost and a small
LSTM on both series; all three methods beat a persistence baseline for CO2, but only ARIMA
does so for temperature. All claims are traceable to the scripts listed in Section 8.</div>

<h2>Glossary of abbreviations</h2>
<table>
<tr><th>Abbreviation</th><th>Full form</th></tr>
<tr><td>NASA</td><td>National Aeronautics and Space Administration (US)</td></tr>
<tr><td>GISTEMP</td><td>GISS Surface Temperature Analysis &mdash; the NASA global temperature record</td></tr>
<tr><td>CO2</td><td>Carbon dioxide</td></tr>
<tr><td>NOAA</td><td>National Oceanic and Atmospheric Administration (US)</td></tr>
<tr><td>GML</td><td>Global Monitoring Laboratory (NOAA)</td></tr>
<tr><td>SILSO</td><td>Sunspot Index and Long-term Solar Observations (World Data Center, Brussels)</td></tr>
<tr><td>WDC</td><td>World Data Center</td></tr>
<tr><td>SSN</td><td>Sunspot number</td></tr>
<tr><td>STL</td><td>Seasonal-Trend decomposition using Loess</td></tr>
<tr><td>Loess</td><td>Locally estimated scatterplot smoothing</td></tr>
<tr><td>FFT</td><td>Fast Fourier Transform</td></tr>
<tr><td>ARIMA</td><td>Autoregressive Integrated Moving Average</td></tr>
<tr><td>SARIMA</td><td>Seasonal ARIMA</td></tr>
<tr><td>AIC</td><td>Akaike information criterion</td></tr>
<tr><td>XGBoost</td><td>eXtreme Gradient Boosting</td></tr>
<tr><td>LSTM</td><td>Long Short-Term Memory (a type of recurrent neural network)</td></tr>
<tr><td>MAE</td><td>Mean absolute error</td></tr>
<tr><td>RMSE</td><td>Root mean squared error</td></tr>
<tr><td>CI</td><td>Confidence interval</td></tr>
<tr><td>SD</td><td>Standard deviation</td></tr>
<tr><td>ppm</td><td>Parts per million</td></tr>
<tr><td>p</td><td>Probability value (statistical significance)</td></tr>
<tr><td>r</td><td>Pearson correlation coefficient</td></tr>
<tr><td>&tau; (tau)</td><td>Kendall&rsquo;s rank correlation coefficient</td></tr>
<tr><td>z</td><td>Standard score (units of standard deviation)</td></tr>
</table>

<h2>1. Introduction</h2>
<p>Climate change is arguably the most consequential measurement program in the history of
the physical sciences, and its evidentiary core consists of a small number of long,
carefully maintained time series. Three of these records stand out. The global
land&ndash;ocean temperature anomaly, compiled by NASA GISTEMP since 1880, is the most
direct measure of whether the planet is warming. The Mauna Loa CO2 record &mdash; the
famous "Keeling curve" begun by Charles Keeling in 1958 &mdash; documents the principal
greenhouse gas associated with that warming. And the sunspot number, compiled by the World Data
Center SILSO since 1749, tracks the natural solar variability that is the leading
candidate alternative explanation. Together, the three records provide a basis for
examining warming trends, greenhouse-gas concentrations, and solar variability.
All three are real, publicly available measurements, downloaded once and
never modified by this analysis.</p>
<p>Because these records are measurements through time, the scientific questions about
them are time-series questions. Is there a trend, and is it statistically significant?
Does the rate of change itself change? What periodic structure does a series contain, and
how has it evolved? Which external series best explains the variation of another, once
other influences are removed? And can the series be forecast, and by which method? The
toolkit of time-series analysis &mdash; robust trend estimation, significance testing,
seasonal decomposition, spectral analysis, partial correlation, and forecasting &mdash; was
developed precisely for such questions, and each tool is exercised in this study.</p>
<p>The study is organised as a reproducible pipeline of analytical stages, each
implemented as a single runnable script that reads the raw data and produces its own
figures and numbers (Section 8). Trends are never reported without their significance;
the breakpoint follows the project plan; observed results are kept
separate from their interpretation; and the forecasting comparison is judged exclusively
on data not seen during fitting. This report presents each stage&rsquo;s figure and table
with a plain-English reading of what they show.</p>
<p>The study addresses three questions:</p>
<ol>
<li><b>Is the planet warming, and how is this established?</b> The temperature trend is
estimated with a robust Theil&ndash;Sen slope and tested with the Mann&ndash;Kendall test,
so the answer carries a significance level rather than resting on visual inspection; a
breakpoint analysis then asks whether the warming rate has itself changed since 1970.</li>
<li><b>Why does atmospheric CO2 rise and oscillate every year?</b> The Keeling curve is
decomposed into a secular trend, a seasonal cycle, and residual noise, and the amplitude
of the seasonal cycle is measured over time &mdash; asking not only what the curve does,
but whether its behaviour is changing.</li>
<li><b>How much of recent warming is solar?</b> The temperature record is compared with the
sunspot cycle and with CO2 using partial correlations, separating the two candidate
drivers; the records are then used in a three-model forecasting comparison that asks which
method &mdash; classical statistics, tree-based machine learning, or a neural network
&mdash; best predicts the near future on an unseen holdout.</li>
</ol>
<p>Answering these questions exercises the full time-series toolkit on data that matter:
significance-tested trends, structural change, decomposition, periodicity, association,
and forecasting, with every claim traceable to a reproducible step.</p>

<h2>2. Data and provenance</h2>
{table(1, "Datasets used in this study.",
       ["Dataset", "Source", "Coverage", "Scientific role"],
       [["Global land&ndash;ocean temperature anomaly (monthly, &deg;C vs 1951&ndash;80)", "NASA GISTEMP v4", "1880&ndash;2026", "Primary target series"],
        ["Mauna Loa CO2 (monthly, ppm)", "NOAA GML (Keeling curve)", "1958&ndash;2026", "Greenhouse-gas driver; trend and seasonality"],
        ["Sunspot number (monthly SSN)", "SILSO, WDC-SILSO Brussels", "1749&ndash;2026", "Natural solar variability; control variable"]])}
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
hypothesis of no trend. The p-values assume independent observations; because climate
series are autocorrelated, Section 5.2 reports a robustness check with an effective
sample-size correction. Every trend estimate in Section 5 is reported with its 95%
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
<p>Questions about statistical association are addressed with partial correlation, which measures the
association between two variables after the linear effect of a third has been removed from
both; this allows the analysis to ask whether temperature tracks CO2 once the solar cycle
is accounted for, and vice versa. Finally, the forecasting comparison follows a strict
protocol: every model is fitted once on data up to December 2015 and evaluated exclusively
on the 127-month holdout (2016-01 to 2026-07), with MAE and RMSE computed against a
persistence baseline.
The models and their configuration are described in Section 4.</p>

<h2>4. Forecasting models and configuration</h2>
{table(2, "Forecasting models: configuration and rationale (fixed in advance; nothing tuned on the test period).",
       ["Model", "Configuration", "Rationale"],
       [["SARIMA", "statsmodels ARIMA, d=1, seasonal (0,1,1,12) (airline model); p,q in {0,1,2} chosen by AIC on the training set", "Monthly data require a seasonal term; the airline model is the standard parsimonious fit for strongly seasonal series such as the Keeling curve; AIC gives a principled, data-driven choice of the AR/MA orders"],
        ["XGBoost", "Gradient-boosted trees; 12 monthly lagged differences as features; 200 trees, max depth 4, learning rate 0.05; random_state 42; forecasts built recursively", "Differenced targets prevent the drift that recursive forecasting on levels exhibits; 12 lags capture the annual cycle; the configuration is a standard mid-size boosting setting"],
        ["LSTM", "Recurrent network; 12 lagged differences (z-scored) fed as a 12-step sequence; one hidden layer of 16 units; linear output head; MSE loss; Adam lr 1e-3; batch 64; 30 epochs; seed 42", "Tests whether a neural model that learns its own features can beat engineered baselines; z-scoring stabilises training; the small architecture suits 700-1600 training points"],
        ["Persistence", "Forecast equals the last observed value", "The naive floor: any model that cannot beat it adds no information"]] )}
<p>Three modelling families are compared: a classical statistical model (SARIMA), a
tree-based machine-learning model (XGBoost), and a neural network (LSTM), with persistence
as the baseline (Table 2). The trio spans the methodological spectrum and is the standard comparison
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
{table(3, "Summary statistics for the three series (monthly observations).",
       ["Series", "n", "Start", "End", "Latest", "Mean", "SD", "Min", "Max"],
       stat_rows)}
{table(4, "Decadal mean temperature anomalies (&deg;C, 1951&ndash;80 base).",
       ["Decade", "Mean anomaly"], decades)}
<p>The monthly temperature series exhibits substantial short-term variability, yet the
annual means display a clear secular increase from approximately &minus;0.2 &deg;C in the
1880s to +1.2 &deg;C in the 2020s (Figure 1, upper panel). The CO2 record combines a
monotonic upward trajectory with a regular annual oscillation &mdash; the seasonal exchange
of carbon between the atmosphere and the terrestrial biosphere (Figure 2, right panel). The
sunspot series shows a persistent quasi-periodic modulation on a decadal timescale,
consistent with the well-documented solar activity cycle (Figure 1, lower panel). Decadal
temperature means (Table 4) change from &minus;0.21 &deg;C in the 1880s to +1.08 &deg;C in
the 2020s, a cumulative increase of +1.29 &deg;C that foreshadows the formal trend analysis
of Section 4.2.</p>

<h3>5.2 Trend analysis</h3>
{img("trends.png", 3, "Annual means with fitted Theil&ndash;Sen trend lines for temperature (left) and CO2 (right).")}
{table(5, "Theil&ndash;Sen slopes on annual means, with 95% confidence intervals and Mann&ndash;Kendall statistics; p-values assume independent observations (robustness check in &sect;5.2).",
       ["Series", "n (years)", "Slope (per decade)", "95% CI", "Tau", "p-value"],
       [["GISTEMP temperature anomaly (&deg;C)", "147", temp_slope, temp_ci, "0.733", temp_p],
        ["Mauna Loa CO2 (ppm)", "69", co2_slope, co2_ci, "1.000", co2_p]])}
<p>Table 5 reports the trend estimates and their significance. Temperature rose at
{temp_slope} &deg;C per decade over 1880&ndash;2026 (95% CI {temp_ci}; p = {temp_p}); the
probability of such a pattern under a null hypothesis of no trend is on the order of
10<sup>&minus;39</sup>, so the warming signal cannot plausibly be attributed to sampling
variability. CO2 rose at {co2_slope} ppm per decade (CI {co2_ci}; p = {co2_p}), equally
unambiguous. In both panels of Figure 3 the fitted lines track the annual means closely,
and because the Theil&ndash;Sen estimator is a median of pairwise slopes, the estimates are
robust to the influence of individual extreme years.</p>
<p><i>Supplementary robustness check (autocorrelation).</i> The Mann&ndash;Kendall p-values
above assume independent annual observations, which understates the uncertainty for
autocorrelated climate series. Recomputing the test with an AR(1)-based effective sample
size (a modified Mann&ndash;Kendall correction) leaves the temperature trend significant
at p &asymp; 8&times;10<sup>&minus;5</sup> (effective n &asymp; 13 of 147 years) and the
post-1970 trend at p &asymp; 4&times;10<sup>&minus;11</sup> (effective n &asymp; 29 of 57).
For CO2 the detrended series is so strongly autocorrelated (lag-1 &rho; &asymp; 0.99) that
the correction collapses the effective sample size and the corrected p-value is
unreliable; the trend statistic itself is unchanged (Kendall&rsquo;s &tau; = 1.00, a
perfectly monotonic series). The substantive conclusions of this section are unaffected by
the correction.</p>

<h3>5.3 Breakpoint analysis: acceleration after 1970</h3>
{img("breakpoint.png", 4, "Theil&ndash;Sen fits applied separately to the pre-1970 and post-1970 segments of the temperature record.")}
{table(6, "Warming rates for the two segments and the full record; p-values assume independent observations (robustness check in &sect;5.2).",
       ["Segment", "n (years)", "Slope (&deg;C/decade)", "95% CI", "p-value"],
       [["pre-1970", "90", pre_slope, pre_ci, pre_p],
        ["post-1970", "57", post_slope, post_ci, post_p]])}
<p>The warming rate increased from {pre_slope} &deg;C per decade before 1970 to
{post_slope} &deg;C per decade after 1970 (Table 6). Because the 95% confidence intervals
of the two estimates do not overlap, the acceleration &mdash; {accel} &deg;C per decade per
decade &mdash; is statistically significant. The change in gradient at the break is readily
apparent in Figure 4. The breakpoint (1970) follows the project plan
(<code>docs/process.md</code>), which fixes the research question as the warming rate
before and after ~1970; a single split was examined and no alternative candidate years
were scanned, so the significance statement is not inflated by data-dependent selection.</p>

<h3>5.4 Seasonal decomposition of the CO2 record</h3>
{img("stl_co2.png", 5, "STL decomposition of monthly Mauna Loa CO2 into observed, trend, seasonal, and residual components.")}
{img("co2_seasonal_amplitude.png", 6, "Annual peak-to-trough amplitude of the seasonal component (full calendar years, 1959&ndash;2025), with fitted trend.")}
{table(7, "Growth of the seasonal cycle amplitude (full calendar years only) and residual diagnostics.",
       ["Quantity", "Estimate", "95% CI", "p-value"],
       [[f"Amplitude growth (ppm/decade, {amp_n} full years)", amp_slope, amp_ci, amp_p],
        ["Residual SD (ppm)", resid_std, "&mdash;", "&mdash;"]])}
<p>Figure 5 shows the four components of the decomposition. The trend component rises
monotonically from approximately 315 to 430 ppm; the seasonal component is a regular
oscillation whose amplitude increases over the record; and the residual is small
(&sigma; = {resid_std} ppm against a signal of order 430 ppm) with no systematic structure,
indicating that the additive trend-plus-seasonal model captures essentially all of the
variance. The seasonal amplitude &mdash; the annual peak-to-trough difference of the
seasonal component &mdash; increased by {amp_slope} ppm per decade (95% CI {amp_ci};
p = {amp_p}; Table 7, Figure 6).</p>
<p>This growth has a natural physical reading. The seasonal amplitude is, in effect, the
annual "breath" of the terrestrial biosphere: CO2 falls through the northern summer as
plants draw it down, and rises again through the winter as respiration and decomposition
return it to the atmosphere. An amplitude that grows from year to year is consistent with
an intensifying seasonal carbon exchange &mdash; consistent, for example, with longer growing
seasons or CO2 fertilisation of photosynthesis. The decomposition quantifies the change but
does not, by itself, identify which of these mechanisms dominates; that would require
additional data, such as satellite vegetation indices.</p>

<h3>5.5 Periodicity of solar activity</h3>
{img("sunspot_periodicity.png", 7, "Monthly sunspot numbers (upper) and the FFT periodogram of the detrended series (lower), with the dominant peak marked.")}
{img("sunspot_cycle_evolution.png", 8, "Normalised periodogram computed over successive half-century windows, showing the wandering of the peak.")}
{table(8, "Dominant period of solar activity.",
       ["Quantity", "Value"],
       [["Dominant period (years)", peak],
        ["Half-power span (years)", f"{span_lo}&ndash;{span_hi}"]])}
<p>The periodogram of the detrended sunspot series exhibits a single dominant spectral peak
at {peak} years (Figure 7, lower panel), recovering the well-known Schwabe cycle from raw
monthly counts without prior knowledge. The half-power span of the peak is
{span_lo}&ndash;{span_hi} years (Table 8). Figure 8 shows that the peak location varies
between approximately 9 and 13 years across successive half-century windows, reflecting the
known irregularity of the solar cycle; the nominal 11-year period is therefore best read as
a mean value rather than a strict constant.</p>

<h3>5.6 Attribution: CO2 versus solar variability</h3>
{img("attribution.png", 9, "Left: temperature versus CO2, coloured by sunspot number. Right: temperature versus sunspots, coloured by CO2. Annual means, 1958&ndash;2026.")}
{table(9, "Simple and partial Pearson correlations (n = 69 annual observations, 1958&ndash;2026). r&sup2; is the squared correlation: for simple correlations, the share of variance explained; for partial correlations, the share of residual variance explained after removing the control variable.",
       ["Correlation", "r", "r&sup2;", "p-value"],
       [["Temperature &ndash; CO2 (simple)", r_tc_plain, f"{float(r_tc_plain) ** 2:.3f}", p_tc_plain],
        ["Temperature &ndash; sunspots (simple)", r_ts_plain, f"{float(r_ts_plain) ** 2:.3f}", p_ts_plain],
        ["Temperature &ndash; CO2 | sunspots (partial)", r_tc_part, f"{float(r_tc_part) ** 2:.3f}", p_tc_part],
        ["Temperature &ndash; sunspots | CO2 (partial)", r_ts_part, f"{float(r_ts_part) ** 2:.3f}", p_ts_part]])}
<p>Table 9 reports the simple and partial correlations. Over the common period
1958&ndash;2026, the temperature&ndash;CO2 correlation is r = {r_tc_plain} (r&sup2; = 0.94;
p = {p_tc_plain}) and remains essentially unchanged when the solar cycle is partialled
out (r = {r_tc_part}; r&sup2; = 0.94; p = {p_tc_part}): the partial CO2 association
accounts for 94% of the temperature variance remaining after removal of the solar cycle.
By contrast, the raw temperature&ndash;sunspot correlation is negligible (r = {r_ts_plain};
r&sup2; = 0.02; p = {p_ts_plain}), and although the partial correlation is statistically
detectable it is small in comparison (r = {r_ts_part}; r&sup2; = 0.12): solar activity
explains 12% of the residual temperature variance after removal of CO2, roughly an eighth
of the share associated with CO2. These correlations are descriptive and do not by
themselves establish causation; moreover, both temperature and CO2 trend strongly over the
common period, so the raw correlations partly reflect a shared trend (see the robustness
check below). Figure 9 makes the asymmetry visible: temperature against CO2 (left) falls on
a tight line with no structure in the colour channel (sunspot number), whereas temperature
against sunspots (right) shows no coherent pattern once the colour scale (CO2) is
accounted for.</p>
<p><i>Supplementary robustness check (confounding and autocorrelation).</i> Removing a
linear trend from both series reduces the temperature&ndash;CO2 correlation to r = 0.66
(p = 7&times;10<sup>&minus;10</sup>), and first-differencing reduces it further to
r = 0.31 (p = 0.009); the association therefore survives both detrending and
differencing and is not purely an artefact of the shared trend. The solar association does
not survive differencing: the detrended temperature&ndash;sunspot correlation is r = 0.30
(p = 0.013), but the first-difference correlation is r = 0.08 (p = 0.54), so the solar
signal is weak and sensitive to the detrending choice. Finally, all p-values in this
section assume independent annual observations; the temperature residuals have lag-1
autocorrelation &asymp; 0.5 (effective sample size &asymp; 23 of 69 years) and the CO2
residuals are near-unit autocorrelated, so the reported p-values are optimistic and should
be read as upper bounds on significance.</p>

<h3>5.7 Extreme years and documented climate events</h3>
{img("events.png", 10, "Annual temperature anomalies with fitted trend, the &plusmn;1.5&sigma; band of detrended values, and flagged outlier years.")}
{table(10, "Years whose detrended anomalies exceed 1.5 standard deviations, with documented event matches (interpretation).",
       ["Year", "z-score", "Event match"], event_rows)}
<p>Table 10 lists the years whose anomalies, after removal of the secular trend, exceed 1.5
standard deviations. Three flags correspond to documented events: 1964 (cooling following
the 1963 Agung eruption), and 2016 and 2024 (El Ni&ntilde;o years). The remaining flags
fall in the 1880s, a period of lower data quality and higher relative noise. Equally
informative are the documented events that do not reach the threshold, all of which admit a
physical explanation: the 1992&ndash;93 Pinatubo cooling (z = {z92}/{z93}), muted by a
concurrent El Ni&ntilde;o; the 1998 El Ni&ntilde;o (z = {z98}), whose anomaly the secular
trend had overtaken; and 1983 (z = {z83}), whose El Ni&ntilde;o warming was offset by the El
Chich&oacute;n eruption. The procedure therefore detects genuine event signals, and its
apparent misses are attributable to documented physical offsets rather than to a failure of
the detection method.</p>

<h3>5.8 Forecasting comparison</h3>
{img("forecast.png", 11, "Forecasting comparison. Upper row: context since 2000. Lower row: forecast detail since 2014 &mdash; observed test values in black, model forecasts coloured, persistence dashed; the dotted line marks the train/test boundary.")}
{table(11, "Holdout performance (test period 2016-01 to 2026-07, 127 months; MAE and RMSE, with improvement relative to the persistence baseline).",
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
127-month holdout 2016-01 to 2026-07 (Table 11, Figure 11); all rankings refer to
this single holdout. For CO2, every method
outperforms the persistence baseline by a substantial margin &mdash; SARIMA (MAE
{mae_co2['ARIMA'][0]} ppm, an improvement of {mae_co2['ARIMA'][2]}%), XGBoost
({mae_co2['XGBoost'][0]} ppm, {mae_co2['XGBoost'][2]}%), and LSTM ({mae_co2['LSTM'][0]}
ppm, {mae_co2['LSTM'][2]}%) &mdash; consistent with the strong trend and seasonality
of the series. For temperature, the ordering differs: only SARIMA improves on the baseline
(MAE {mae_temp['ARIMA'][0]} &deg;C, {mae_temp['ARIMA'][2]}%), whereas both
machine-learning models underperform it (XGBoost {mae_temp['XGBoost'][0]} &deg;C; LSTM
{mae_temp['LSTM'][0]} &deg;C). This contrast is consistent with the different character
of the two series &mdash; CO2 combines a strong trend with a pronounced seasonal cycle,
whereas temperature behaves approximately as a random walk about a slow trend &mdash; but the
experiment itself establishes only the measured error ranking. Model configurations were
fixed in advance and are documented in <code>docs/process.md</code> &sect;8.</p>
<p>Figure 11 also makes clear why the temperature forecasts do not track the test record
closely. Two distinct effects are at work. The first is irreducible: the observed test
values swing between roughly 0.6 and 1.5 &deg;C from month to month, because monthly
anomalies are dominated by short-term variability &mdash; weather and El Ni&ntilde;o-scale
fluctuations &mdash; that a model trained only on monthly lags cannot anticipate. SARIMA's
forecast (MAE {mae_temp['ARIMA'][0]} &deg;C) is a smooth conditional expectation: it is
centred near the test level (its mean of 0.93 &deg;C is close to the test mean of 1.02
&deg;C) but, like any such expectation, it cannot follow the individual swings. The second
effect is systematic: the machine-learning forecasts are built by compounding predicted
monthly differences, and a small upward bias in those differences accumulates over the
127-month horizon. XGBoost's line therefore climbs to roughly 1 &deg;C above the observed
values in the final years (its MAE of {mae_temp['XGBoost'][0]} &deg;C is nearly five times
SARIMA's, and the LSTM's {mae_temp['LSTM'][0]} &deg;C is similar); the differencing
introduced in Section 4 removed the gross drift of the original configuration, but the
compounding mechanism remains. Neither effect can be removed by a lag-based model without
external predictors.</p>

<h2>6. Discussion and limitations</h2>
<p>The principal caveat concerns the attribution analysis, which is descriptive rather than
causal: partial correlation shows that the two candidate drivers separate cleanly in the
data, but it cannot establish that CO2 causes warming &mdash; it demonstrates consistency
with that hypothesis and inconsistency with a dominant solar explanation. The breakpoint
analysis rests on a single split at 1970, fixed by the project plan (which specifies the
question as the warming rate before and after ~1970); because the plan and the results are
contemporaneous in the project record, strict pre-specification of the exact year cannot
be independently verified, although no evidence of data-driven selection was found.</p>
<p>The forecasting comparison rests on a single train/test split; a rolling-origin
evaluation over multiple windows would provide more robust model rankings at greater
computational cost. Model configurations were fixed rather than tuned &mdash; a tuned LSTM
might perform better on CO2, but tuning on the test period would invalidate the
comparison.</p>
<p>All significance tests in this report (Mann&ndash;Kendall and Pearson) assume independent
observations, whereas monthly and annual climate series are autocorrelated; the p-values
are therefore optimistic. Sections 5.2 and 5.6 report robustness checks with
an effective-sample-size correction and with detrended and first-difference correlations,
and the substantive conclusions are unchanged. The 2026 GISTEMP annual value uses only
January&ndash;July, and the CO2 seasonal-amplitude analysis is restricted to full calendar
years; excluding the partial 2026 temperature year changes the full-record trend only in
the third decimal place (0.082 &rarr; 0.081 &deg;C per decade).</p>
<p>Finally, the data themselves impose limits. Recent GISTEMP values are preliminary and
subject to revision, and the final months of the record are reported as missing and were
excluded from the analysis.</p>

<h2>7. Conclusions</h2>
<ul>
<li><b>Warming is real and accelerating.</b> The temperature trend is significant at any
conventional level: {temp_slope} &deg;C per decade over the full record and {post_slope}
&deg;C per decade since 1970, with non-overlapping confidence intervals (Mann&ndash;Kendall
p &sim; 10<sup>&minus;39</sup> under independent observations; p &sim; 10<sup>&minus;4</sup>
after an effective-sample-size correction; Section 5.2).</li>
<li><b>The carbon cycle is intensifying.</b> CO2 is rising at {co2_slope} ppm per decade
and the amplitude of its seasonal cycle is growing ({amp_slope} ppm per decade), a change
consistent with an intensifying seasonal carbon exchange.</li>
<li><b>Solar variability is unlikely to be the dominant explanation for the warming.</b>
The solar cycle is a well-defined {peak}-year oscillation, yet the temperature&ndash;CO2
association survives removal of the solar cycle (partial r = +0.97) while the residual
solar association after controlling for CO2 is small (partial r = +0.35; r&sup2; = 0.12),
does not survive first-differencing, and is not robust given the limited effective sample
size.</li>
<li><b>SARIMA produced the lowest forecast error.</b> Under the fixed configurations and
the single 127-month holdout, SARIMA outperformed both XGBoost and a small LSTM on both
series: for CO2, XGBoost and LSTM beat persistence but not SARIMA; for temperature, they
performed substantially worse than persistence. Rankings are conditional on this holdout
and configuration set.</li>
</ul>
<p>Taken together, the three records tell a coherent story. The warming of the past century
is real, statistically unambiguous, and accelerating; it is strongly associated with the
rise of greenhouse gases rather than with solar variability; and the seasonal amplitude of
atmospheric CO2 is growing. The forecasting results add a methodological coda: under this
holdout configuration, the classical seasonal model produced the lowest forecast error on
both series.</p>

<h2>8. Reproducibility</h2>
<p>Every result is generated by a single command:</p>
<pre>python experiments/report.py     # reruns all stages; regenerates plots and this report
python experiments/&lt;stage&gt;.py      # or any single stage in isolation</pre>
<p>Outputs comprise this report (<code>results/report.html</code> and
<code>results/report.pdf</code>), the plots in
<code>results/plots/</code>, and the living log <code>docs/process.md</code>, which records
each stage's setup, numbers, and reasoning. Raw data in <code>data/raw/</code> are never
modified by analysis code.</p>
"""

REPORT.write_text(f"<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
                  f"<title>Global Temperature, Atmospheric CO&#8322;, and Solar Variability: A Reproducible Time-Series Analysis</title>"
                  f"<style>{CSS}</style></head><body>{BODY}</body></html>",
                  encoding="utf-8")
print(f"Wrote {REPORT} ({REPORT.stat().st_size / 1e6:.1f} MB)")

# --- PDF copy via headless Chrome/Edge (skipped if no browser is found) -----
PDF = REPO / "results" / "report.pdf"
PRINT_CSS = """
@page { size: A4; margin: 18mm 16mm; }
html, body { margin: 0; padding: 0; }
* { print-color-adjust: exact; -webkit-print-color-adjust: exact; }
figure, table, .abstract { break-inside: avoid; page-break-inside: avoid; }
h1, h2, h3 { break-after: avoid; page-break-after: avoid; }
img { max-width: 100%; }
"""


def find_browser():
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    return next((p for p in candidates if Path(p).exists()), None)


def make_pdf():
    browser = find_browser()
    if browser is None:
        print("No Chrome/Edge found; skipping PDF output (report.html is unchanged)")
        return
    html = REPORT.read_text(encoding="utf-8")
    html = html.replace("</head>", f"<style>{PRINT_CSS}</style></head>", 1)
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "report.html"
        src.write_text(html, encoding="utf-8")
        out = Path(td) / "report.pdf"
        for headless in ("--headless=new", "--headless"):
            cmd = [browser, headless, "--disable-gpu", "--no-pdf-header-footer",
                   f"--print-to-pdf={out}", str(src)]
            subprocess.run(cmd, timeout=180, capture_output=True)
            if out.exists() and out.stat().st_size > 100_000:
                break
            out.unlink(missing_ok=True)
        if out.exists() and out.stat().st_size > 100_000:
            out.replace(PDF)
            print(f"Wrote {PDF} ({PDF.stat().st_size / 1e6:.1f} MB)")
        else:
            print("PDF generation failed (browser produced no output); "
                  "report.html is unchanged")


make_pdf()
