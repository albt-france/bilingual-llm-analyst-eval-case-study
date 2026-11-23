"""Build report/LLM_analyst_eval.pdf (6 pages): HTML + inline SVG charts -> Edge headless -> pypdf (metadata emptied).
The intermediate HTML goes to data/raw/report_build/ (not published).
Run from the repository root:  python src/build_pdf.py
"""
import io
import os
import subprocess

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from pypdf import PdfReader, PdfWriter

PROC, PUB = os.path.join("data", "processed"), os.path.join("data", "public")
BUILD = os.path.join("data", "raw", "report_build")
OUT = os.path.join("report", "LLM_analyst_eval.pdf")
os.makedirs(BUILD, exist_ok=True); os.makedirs("report", exist_ok=True)
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
plt.rcParams.update({"font.family": "Segoe UI", "font.size": 9, "svg.fonttype": "none", "axes.spines.top": False,
                     "axes.spines.right": False, "axes.edgecolor": "#999999", "axes.labelcolor": "#444444",
                     "xtick.color": "#444444", "ytick.color": "#444444", "axes.titlesize": 9.5})
BLUE, ORANGE, GREY, RED, GREEN = "#1f4e79", "#d9822b", "#b0aca3", "#c62828", "#2e7d32"
EN_C, FR_C = "#1f4e79", "#7e57c2"
r = lambda f, d=PROC: pd.read_csv(os.path.join(d, f + ".csv"))
FOOT = "Independent case study based on public data · not affiliated with or endorsed by any AI company"
AI = ("AI-assisted workflow: I used Claude, mainly to write scripts faster. I drove the project: I defined the questions, "
      "chose and validated the data sources, made the analytical decisions and checked every result.")


def svg(fig):
    buf = io.StringIO(); fig.savefig(buf, format="svg", bbox_inches="tight", transparent=True); plt.close(fig)
    s = buf.getvalue()
    return s[s.find("<svg"):]


# ------------------------------------------------------------------ data
retail, nights = r("eurostat_retail", PUB), r("eurostat_nights", PUB)
hicp, hicp_old = r("eurostat_hicp", PUB), r("eurostat_hicp_stopped", PUB)
ins = pd.read_csv(os.path.join(PUB, "insee_series.csv"), dtype={"idbank": str})
acc, codes, gap, strata, std = r("accuracy_by_type"), r("error_code_totals"), r("language_gap_raw"), \
    r("language_gap_strata"), r("language_gap_standardised")
agr, flags, tpr, graded, fs = r("agreement"), r("retail_flags"), r("time_per_review"), r("graded"), r("french_specific")
k = agr.groupby(["scope", "guidelines"]).cohen_kappa.mean().round(2)
po = agr.groupby(["scope", "guidelines"]).observed_agreement.mean()
pass_all = graded["pass"].mean() * 100
g = gap.set_index("language").pass_pct
sd = std.set_index("language").standardised_pass_pct
hard = gap.set_index("language").pct_hard_items
med_v2 = tpr[tpr.guidelines == "v2"].set_index("task_type").median_s
R = retail.pivot(index="time", columns="geo", values="value")
N = nights.pivot(index="time", columns="geo", values="value")

charts = {}
# p1a: retail index, T001
fig, ax = plt.subplots(figsize=(4.7, 2.0))
sub = R.loc["2023-07":"2026-09", ["ES", "PL", "IE", "FI"]]
names = {"ES": "Spain", "PL": "Poland", "IE": "Ireland", "FI": "Finland"}
cols = {"ES": BLUE, "PL": ORANGE, "IE": "#00897b", "FI": GREY}
x = range(len(sub))
for c in sub:
    ax.plot(x, sub[c], color=cols[c], lw=1.4 if c in ("ES", "PL") else 1, label=names[c])
i0, i1 = list(sub.index).index("2024-01"), list(sub.index).index("2026-07")
ax.axvspan(i0, i0 + 2, color="#e9e4d8"); ax.axvspan(i1, i1 + 2, color="#e9e4d8")
ax.scatter([i0], [sub.at["2024-01", "PL"]], color=ORANGE, zorder=5, s=18)
ax.annotate("Poland, Jan 2024:\none low month", (i0, sub.at["2024-01", "PL"]), (i0 + 3, 103.4), fontsize=7.5,
            arrowprops=dict(arrowstyle="-", color="#888"))
ax.set_xticks([list(sub.index).index(t) for t in ["2024-01", "2025-01", "2026-01"]], ["Jan 2024", "Jan 2025", "Jan 2026"])
ax.set_ylabel("index, 2021 = 100"); ax.legend(frameon=False, fontsize=7.5, ncol=4, loc="upper left")
ax.set_ylim(sub.min().min() - 1, sub.max().max() + 3)
charts["p1a"] = svg(fig)
# p1b: endpoint vs 3-month growth
a0 = R.loc["2024-01":"2024-03", list(names)].mean(); a1 = R.loc["2026-07":"2026-09", list(names)].mean()
rob = (a1 / a0 - 1) * 100; nai = (R.loc["2026-09", list(names)] / R.loc["2024-01", list(names)] - 1) * 100
fig, ax = plt.subplots(figsize=(4.0, 2.1))
order = rob.sort_values().index
y = range(len(order))
ax.barh([i + 0.2 for i in y], rob[order], 0.38, color=BLUE, label="3-month averages (reference)")
ax.barh([i - 0.2 for i in y], nai[order], 0.38, color=GREY, label="Jan 2024 -> Sep 2026 (endpoints)")
for i, c in enumerate(order):
    ax.text(rob[c] + 0.1, i + 0.2, f"{rob[c]:+.1f}%", va="center", fontsize=7.5)
    ax.text(nai[c] + 0.1, i - 0.2, f"{nai[c]:+.1f}%", va="center", fontsize=7.5, color="#666")
ax.set_yticks(list(y), [names[c] for c in order]); ax.set_xlim(0, 8); ax.set_xlabel("growth, %")
ax.legend(frameon=False, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.28), ncol=2)
charts["p1b"] = svg(fig)
# p1c: nights seasonality
fig, ax = plt.subplots(figsize=(4.7, 2.0))
for c, col, lab in [("FR10", BLUE, "Île-de-France"), ("FRL0", ORANGE, "Provence-Alpes-Côte d'Azur"),
                    ("FRI1", "#00897b", "Aquitaine")]:
    ax.plot(range(len(N)), N[c] / 1e6, color=col, lw=1.2, label=lab)
ax.set_xticks(range(0, len(N), 12), [t[:4] for t in N.index[::12]]); ax.set_ylabel("nights, millions")
ax.annotate("Jan 2022: depressed", (0, N.iloc[0]["FR10"] / 1e6), (2, 0.6), fontsize=7.5,
            arrowprops=dict(arrowstyle="-", color="#888"))
ax.legend(frameon=False, fontsize=7, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.17))
charts["p1c"] = svg(fig)
# p2a: pass by type and language
pt = graded.groupby(["task_type", "language"])["pass"].mean().unstack() * 100
lab = {"series_analysis": "Series analysis", "logic_puzzle": "Logic puzzles", "claim_check": "Claim checks",
       "summarise_chunk": "Summaries & chunking"}
pt = pt.loc[["series_analysis", "logic_puzzle", "claim_check", "summarise_chunk"]]
fig, ax = plt.subplots(figsize=(3.4, 2.3))
yy = range(len(pt))
ax.barh([i + 0.2 for i in yy], pt.en, 0.38, color=EN_C, label="English")
ax.barh([i - 0.2 for i in yy], pt.fr, 0.38, color=FR_C, label="French")
for i, (e, f) in enumerate(zip(pt.en, pt.fr)):
    ax.text(e + 1, i + 0.2, f"{e:.0f}%", va="center", fontsize=7.5); ax.text(f + 1, i - 0.2, f"{f:.0f}%", va="center", fontsize=7.5)
ax.set_yticks(list(yy), [lab[t] for t in pt.index]); ax.invert_yaxis(); ax.set_xlim(0, 105)
ax.set_xlabel("pass rate (consensus = correct), %"); ax.legend(frameon=False, fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, 1.13), ncol=2)
charts["p2a"] = svg(fig)
# p2b: error codes
cd = codes.set_index("error_code").sort_values("answers")
fig, ax = plt.subplots(figsize=(3.4, 4.0))
colc = [FR_C if c.startswith("FR_") else ORANGE if c in ("PROVISIONAL_AS_FINAL", "NUTS_LABEL", "STALE_SOURCE") else BLUE
        for c in cd.index]
ax.barh(cd.index, cd.answers, color=colc, height=0.65)
for i, v in enumerate(cd.answers):
    ax.text(v + 0.3, i, str(v), va="center", fontsize=7.5)
ax.set_xlabel("failed answers (consensus code)"); ax.tick_params(axis="y", labelsize=7.5)
charts["p2b"] = svg(fig)
# p2c: series questions, pass rate by subtype
ss = graded[graded.task_type == "series_analysis"].groupby("subtype")["pass"].mean().sort_values() * 100
labs = {"seasonal_growth": "grew most (seasonal)", "growth_window": "grew most (window)", "yoy_ranking": "y/y ranking",
        "points_vs_percent": "points vs %", "peak_month": "peak month", "largest_fall": "largest fall"}
fig, ax = plt.subplots(figsize=(3.4, 1.9))
ax.barh([labs[i] for i in ss.index], ss, color=[ORANGE if "grow" in i else BLUE for i in ss.index], height=0.6)
for i, v in enumerate(ss):
    ax.text(v + 1, i, f"{v:.0f}%", va="center", fontsize=7.5)
ax.set_xlim(0, 105); ax.set_xlabel("series questions: pass rate, %"); ax.tick_params(axis="y", labelsize=7.5)
charts["p2c"] = svg(fig)
# p3a: INSEE CPI stopped vs current (y/y)
old = ins[ins.idbank == "001763852"].set_index("period").value
cur = ins[ins.idbank == "011814630"].set_index("period").value
yo = (old / old.shift(12) - 1).dropna() * 100; yc = (cur / cur.shift(12) - 1).dropna() * 100
yo = yo[yo.index >= "2024-01"]
allp = sorted(set(yo.index) | set(yc.index)); pos = {p: i for i, p in enumerate(allp)}
fig, ax = plt.subplots(figsize=(4.5, 2.0))
ax.plot([pos[p] for p in yo.index], yo, color=GREY, lw=1.5, label="001763852 base 2015, excl. tobacco (stopped)")
ax.plot([pos[p] for p in yc.index], yc, color=BLUE, lw=1.5, label="011814630 base 2025, all items (current)")
ax.scatter([pos["2025-12"]], [yo["2025-12"]], color=GREY, s=16, zorder=5)
ax.annotate(f"last point 2025-12: {yo['2025-12']:.1f}%", (pos["2025-12"], yo["2025-12"]), (pos["2025-12"] - 9, 2.6),
            fontsize=7.5, arrowprops=dict(arrowstyle="-", color="#888"))
ax.annotate(f"2026-10: {yc['2026-10']:.1f}%", (pos["2026-10"], yc["2026-10"]), (pos["2026-10"] - 6, yc["2026-10"] + 0.6),
            fontsize=7.5)
ax.set_xticks([pos[p] for p in allp if p.endswith("-01")], [p[:4] for p in allp if p.endswith("-01")])
ax.set_ylabel("CPI, % y/y"); ax.legend(frameon=False, fontsize=6.8, loc="upper left"); ax.set_ylim(-0.5, 5.2)
charts["p3a"] = svg(fig)
# p3b: HICP manr vs minr, France
ho = hicp_old[hicp_old.geo == "FR"].set_index("time").value; hn = hicp[hicp.geo == "FR"].set_index("time").value
pp = sorted(set(ho.index) | set(hn.index)); ps = {p: i for i, p in enumerate(pp)}
fig, ax = plt.subplots(figsize=(4.5, 2.0))
ax.plot([ps[p] for p in hn.index], hn, color=BLUE, lw=1.5, label="prc_hicp_minr (current)")
ax.plot([ps[p] for p in ho.index], ho, color=GREY, lw=1.5, ls="--", label="prc_hicp_manr (frozen at 2025-12)")
ax.set_xticks([ps[p] for p in pp if p.endswith("-01")], [p[:4] for p in pp if p.endswith("-01")])
ax.set_ylabel("HICP France, % y/y"); ax.legend(frameon=False, fontsize=7, loc="upper center")
charts["p3b"] = svg(fig)
# p4a: raw vs standardised
fig, ax = plt.subplots(figsize=(3.6, 2.7))
xs = [0, 1, 3, 4]
vals = [g["en"], g["fr"], sd["en"], sd["fr"]]
ax.bar(xs, vals, color=[EN_C, FR_C, EN_C, FR_C], width=0.8)
for xx, v in zip(xs, vals):
    ax.text(xx, v + 1.2, f"{v:.0f}%", ha="center", fontsize=8)
ax.set_xticks([0.5, 3.5], ["raw pass rate", "standardised\n(same difficulty mix)"]); ax.set_ylim(0, 80)
ax.set_ylabel("%"); ax.text(0, 4, "EN", ha="center", color="w", fontsize=8); ax.text(1, 4, "FR", ha="center", color="w", fontsize=8)
charts["p4a"] = svg(fig)
# p4b: by difficulty + mix
fig, axs = plt.subplots(1, 2, figsize=(4.8, 2.6), gridspec_kw={"width_ratios": [1.3, 1]})
ax = axs[0]
for j, (lang, col) in enumerate([("en", EN_C), ("fr", FR_C)]):
    ax.bar([d + (j - 0.5) * 0.38 for d in strata.difficulty], strata[f"pass_{lang}"], 0.38, color=col, label=lang.upper())
ax.set_xticks([1, 2, 3], ["easy", "medium", "hard"]); ax.set_ylabel("pass rate, %"); ax.set_title("Pass rate by difficulty")
ax.legend(frameon=False, fontsize=7)
ax = axs[1]
mix = graded.groupby(["language", "difficulty"]).size().unstack()
mix = mix.div(mix.sum(axis=1), axis=0) * 100
left = [0, 0]
for d, col in zip([1, 2, 3], ["#d7d2c6", "#a9a294", "#5c574d"]):
    ax.barh(["EN", "FR"], mix[d], left=left, color=col, label=["easy", "medium", "hard"][d - 1])
    left = [l + v for l, v in zip(left, mix[d])]
ax.set_title("Difficulty mix, %"); ax.legend(frameon=False, fontsize=6.5, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.12))
ax.set_xlim(0, 100)
charts["p4b"] = svg(fig)
# p4c: kappa v1 v2
fig, ax = plt.subplots(figsize=(3.4, 1.9))
vals = [k[("all answers", "v1")], k[("all answers", "v2")]]
ax.bar(["guidelines v1", "guidelines v2"], vals, color=[GREY, BLUE], width=0.55)
for i, v in enumerate(vals):
    ax.text(i, v + 0.02, f"{v:.2f}", ha="center", fontsize=8.5)
ax.set_ylim(0, 1); ax.set_ylabel("mean Cohen's kappa")
charts["p4c"] = svg(fig)

# ------------------------------------------------------------------ html
CSS = """
@page { size: 297mm 210mm; margin: 0; }
* { box-sizing: border-box; }
body { margin: 0; font-family: 'Segoe UI', sans-serif; color: #222; background: #ebe8e1; }
.page { width: 297mm; height: 210mm; padding: 9mm 11mm 7mm; background: #ebe8e1; page-break-after: always;
        display: flex; flex-direction: column; overflow: hidden; }
.page:last-child { page-break-after: auto; }
.kicker { font-size: 9pt; color: #6b665c; letter-spacing: .04em; text-transform: uppercase; }
h1 { font-size: 19pt; margin: 1mm 0 1mm; font-weight: 600; line-height: 1.15; }
h2 { font-size: 10.5pt; margin: 0 0 1.5mm; font-weight: 600; padding-right: 21mm; }
.sub { font-size: 9.5pt; color: #4a463e; margin-bottom: 3mm; }
.grid { display: grid; gap: 4mm; flex: 1; min-height: 0; }
.card { background: #fff; border-radius: 3mm; padding: 3.5mm 4mm; box-shadow: 0 .3mm 1mm rgba(0,0,0,.07);
        overflow: hidden; position: relative; }
.card svg { width: 100%; height: auto; max-height: 100%; }
.tag { position: absolute; top: 3mm; right: 3.5mm; font-size: 6.5pt; font-weight: 700; letter-spacing: .05em;
       padding: .6mm 1.6mm; border-radius: 1mm; }
.pub { background: #dde8f3; color: #1f4e79; } .sim { background: #fbe5c8; color: #8a4b00; }
.note { font-size: 8pt; color: #555; margin-top: 1mm; line-height: 1.35; }
.kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 4mm; margin-bottom: 4mm; }
.kpi { background: #fff; border-radius: 3mm; padding: 3mm 4mm; position: relative; }
.kpi b { display: block; font-size: 20pt; font-weight: 600; color: #1f4e79; }
.kpi span { font-size: 8.3pt; color: #444; }
ul, ol { margin: 0; padding-left: 4.5mm; font-size: 8.8pt; line-height: 1.42; }
li { margin-bottom: .8mm; }
table { border-collapse: collapse; width: 100%; font-size: 8pt; }
td, th { border-bottom: .2mm solid #e3e0d8; padding: .9mm 1.2mm; text-align: left; vertical-align: top; }
th { color: #6b665c; font-weight: 600; }
.foot { display: flex; justify-content: space-between; font-size: 7pt; color: #7a756b; margin-top: 2.5mm; }
p { font-size: 8.8pt; line-height: 1.42; margin: 0 0 1.5mm; }
.ex { font-size: 8.2pt; background: #f6f4ef; border-radius: 1.5mm; padding: 1.5mm 2mm; margin: 1mm 0; line-height: 1.38; }
"""


def page(n, kicker, title, sub, body):
    return f"""<section class="page"><div class="kicker">{kicker}</div><h1>{title}</h1><div class="sub">{sub}</div>
{body}<div class="foot"><span>{FOOT}</span><span>Bilingual LLM analyst evaluation · {n + 1} / 6</span></div></section>"""


def card(title, content, tag="pub", note=""):
    t = '<span class="tag pub">PUBLIC DATA</span>' if tag == "pub" else '<span class="tag sim">SIMULATED</span>' \
        if tag == "sim" else ""
    return f'<div class="card">{t}<h2>{title}</h2>{content}{f"<div class=note>{note}</div>" if note else ""}</div>'


fl = flags.set_index("geo")
tk = r("tasks")
win = tk[tk.subtype.isin(["growth_window", "seasonal_growth"])].check.str.extract(r"winner_\w+=(\w+); winner_\w+=(\w+)")
n_win, n_flip = len(win), int((win[0] != win[1]).sum())
T1 = tk.set_index("task_id").loc["T001"]
cdi = codes.set_index("error_code").answers
pages = []
pages.append(page(0, "Overview · LLM training analyst case study",
    "Where language models slip on analyst questions: a bilingual gold set and grading rubric",
    "120 gold tasks in English and French built from Eurostat, INSEE and Wikipedia · answers computed and verified · "
    "240 answers of a simulated model · 3 simulated reviewers",
    f"""<div class="kpis">
<div class="kpi"><span class="tag pub">PUBLIC DATA</span><b>120 × 2</b><span>gold tasks (40 series, 30 puzzles, 25 claim checks, 25 summaries), each written in English and in French</span></div>
<div class="kpi"><span class="tag pub">PUBLIC DATA</span><b>100%</b><span>of reference answers computed by script, SQL or solver; every puzzle proven to have exactly one solution</span></div>
<div class="kpi"><span class="tag sim">SIMULATED</span><b>{pass_all:.0f}%</b><span>of the 240 simulated answers fully correct; series analysis ({acc.set_index('task_type').pass_pct['series_analysis']:.0f}%) and puzzles ({acc.set_index('task_type').pass_pct['logic_puzzle']:.0f}%) are where it slips</span></div>
<div class="kpi"><span class="tag sim">SIMULATED</span><b>{k[('all answers', 'v1')]:.2f} → {k[('all answers', 'v2')]:.2f}</b><span>reviewer agreement (Cohen's kappa) after 7 decision rules for the grey zones</span></div>
</div>
<div class="grid" style="grid-template-columns: 1fr 1.25fr 1fr;">
{card("Five questions", '''<ol><li>Which country or region "grew the most", and over which window?</li>
<li>Where does a model slip on analyst questions: series, puzzles, claims, summaries?</li>
<li>Can a claim be confirmed with the first series found, or is that series stopped?</li>
<li>Is the model worse in French, or does it only look that way?</li>
<li>Do reviewers agree on a verdict, and what makes them agree?</li></ol>''', tag="")}
{card("Recommendations", '''<ol><li><b>Ask for the window before the answer.</b> Growth from one month can flip the ranking (Spain vs Poland, page 2).</li>
<li><b>Check the source's status, not just its value:</b> 3 of the first series reached for were stopped or frozen; recent Eurostat values carry p/e flags.</li>
<li><b>Units are part of the answer:</b> percentage points vs %, milliard vs billion, decimal comma.</li>
<li><b>Prove puzzle answers against every rule;</b> a solver flags the broken rule in one line.</li>
<li><b>Stratify before comparing languages:</b> the 10-point French gap was a difficulty mix.</li></ol>''', tag="")}
{card("Method", '''<ul><li><b>Real part:</b> Eurostat (retail volume, tourist nights, HICP, unemployment), INSEE (CPI, unemployment), Wikipedia at fixed revisions.</li>
<li><b>Workflow:</b> write the task → compute the reference → step-by-step explanation → error taxonomy → rubric → reviewer agreement → better guidelines.</li>
<li><b>Simulated part:</b> a fictional model with planted errors; 3 simulated reviewers, guidelines v1 then v2. No real model was called.</li>
<li><b>Deliverables:</b> evaluation workbook (7 tabs), gold_set.jsonl, rubric, taxonomy, claim-checking and chunking guides, notebook.</li></ul>''', tag="")}
</div>
<div class="grid" style="grid-template-columns: 1fr; margin-top: 4mm; flex: 0 0 46mm;">
{card("One gold task, two languages (T001)", f'''<div style="display:grid; grid-template-columns: 1fr 1fr; gap: 5mm;">
<div><p><b>EN task.</b> {T1.prompt_en}</p><p><b>Reference.</b> {T1.ref_en}</p></div>
<div><p><b>Tâche FR.</b> {T1.prompt_fr}</p><p><b>Référence.</b> {T1.ref_fr}</p></div></div>
<p class="note">The explanation adds the window, the computation, the trap (endpoint growth favours Poland) and the data status (values flagged p). Not a word-for-word translation: French number format, French terms (CVS-CJO).</p>''')}
</div>"""))

pages.append(page(1, "1 · The window decides the winner",
    "Which country grew the most? It depends on the window",
    "The offer's own example, redone on real data: a ranking built on one atypical month flips when the comparison uses 3-month averages or full years",
    f"""<div class="grid" style="grid-template-columns: 1.15fr 1fr; grid-template-rows: 1fr 1fr;">
{card("Retail volume index, Jan 2024 → Sep 2026", charts["p1a"], note="Seasonally and calendar adjusted, 2021 = 100. Shaded: the two 3-month windows of the reference. Eurostat sts_trtu_m, updated 2026-11-21, extracted 2026-11-23.")}
{card("Same data, two answers", charts["p1b"], note="Poland's January 2024 (106.5) sits 1.4 points under its own 3-month average.")}
{card("Tourist nights: raw, strongly seasonal", charts["p1c"], note="Not seasonally adjusted: compare full years or the same month. January 2022 was still depressed (Île-de-France 3.4 M nights vs 6.0 M in January 2023). Eurostat tour_occ_nin2m, NUTS 2 regions.")}
{card("What the reference answer must say", f'''<p><b>Answer:</b> "Spain grew the most, +5.6% on 3-month averages (Jan-Mar 2024 vs Jul-Sep 2026)."</p>
<p><b>Why this window:</b> one month is noisy; endpoint growth would favour Poland because of one low month.</p>
<p><b>Data status:</b> Spain's values are flagged <b>p</b> (provisional) on all {int(fl.at['ES', 'values_total'])} months, like Austria, Belgium and Germany; France's latest value (2026-09) is <b>e</b> (estimated). The answer may be revised.</p>
<div class="ex">FR : « Le pays qui a le plus progressé est l'Espagne : +5,6 % (moyennes sur 3 mois). » Same steps, French number format.</div>
<p>Of {n_win} "who grew the most" tasks, {n_flip} were built so that the naive window gives a <b>different</b> winner.</p>''')}
</div>"""))

pages.append(page(2, "2 · Error analysis (simulated model)",
    "Where the model slips: windows, rules and data status, more than arithmetic",
    "240 simulated answers graded with guidelines v2 (majority of 3 reviewers); a brute-force solver re-checks every puzzle answer",
    f"""<div class="grid" style="grid-template-columns: 1fr 1fr 1fr;">
{card("Pass rate by task type", charts["p2a"] + charts["p2c"], tag="sim", note="Series questions fail most where the window matters (orange): 'who grew the most' is the hardest family.")}
{card("What goes wrong (consensus error codes)", charts["p2b"], tag="sim", note="Orange: data-status and source errors (real issues in the public data). Purple: French-specific errors.")}
{card("Puzzles: a solver proves the broken rule", f'''<p>Each puzzle is generated from a hidden order, rules are added until one order fits, then pruned to a minimal set.
Minimality gives a plausible wrong answer for free: an order that breaks exactly <b>one</b> rule.</p>
<div class="ex"><b>T053</b> Rules: (1) Hillside before Market (2) Market before Harbour (3) Old Town right after Market (4) Station first.<br>
<b>Model (FR):</b> Gare > Port > Colline > Marché > Vieille-Ville, « cet ordre respecte toutes les règles ».<br>
<b>Solver:</b> breaks rule 2. <b>Reference:</b> Station > Hillside > Market > Old Town > Harbour.</div>
<p>29 of 60 puzzle answers break a rule; the solver flags all 29 (25 coded CONSTRAINT_IGNORED, 3 FR_TERM for « avant-dernier » read as « dernier », 1 miscoded).</p>
<p><b>Explanation standard:</b> apply the most restrictive rule first and count the orders left (120 → 24 → 6 → 3 → 1).</p>''', tag="sim")}
</div>"""))

pages.append(page(3, "3 · Claim checking",
    "Checking claims against the source: the number can match and still be wrong",
    "Three of the first series reached for were stopped or frozen; recent values carry provisional flags; region labels are statistical units",
    f"""<div class="grid" style="grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr;">
{card("INSEE CPI: stopped series vs current series", charts["p3a"], note="A claim of '0.7% inflation' matches series 001763852, which INSEE marks as stopped (base 2015, excluding tobacco). Verdict: OUTDATED.")}
{card("Eurostat HICP France: frozen dataset vs successor", charts["p3b"], note="prc_hicp_manr stops at 2025-12 (last update 2026-02-06). prc_hicp_minr (ECOICOP ver.2) gives 3.7% for October 2026.")}
{card("Real traps met while building the tasks (2026-11-23)", f'''<table><tr><th>Source</th><th>Trap</th><th>Verdict / rule</th></tr>
<tr><td>INSEE 001763852</td><td>CPI base 2015 excl. tobacco, stopped at 2025-12</td><td>OUTDATED · R5</td></tr>
<tr><td>INSEE 001688526</td><td>Unemployment metro. France, stopped at 2026-Q1 (7.9%); current 001688527: 8.2% in 2026-Q3</td><td>OUTDATED · R5</td></tr>
<tr><td>Eurostat sts_trtu_m</td><td>p on every month for AT, BE, DE, ES; FR 2026-09 = e</td><td>MISLEADING if called final · R4</td></tr>
<tr><td>Eurostat tour_occ_nin2m</td><td>Midi-Pyrénées, Aquitaine, Rhône-Alpes are NUTS 2 units, not today's regions; months sit in a separate dimension</td><td>MISLEADING · R6</td></tr>
<tr><td>Labels</td><td>UTF-8 read as cp1252: "Midi-PyrÃ©nÃ©es"; typographic apostrophe in "Côte d’Azur"</td><td>join on codes</td></tr></table>''')}
{card("Six-step method (claim_checking_method.md)", '''<ol><li>Restate: value, unit, geography, period, source.</li>
<li>Go to the primary source (dataset code or INSEE idbank), not to a quote of it.</li>
<li>Check the series: title (stopped?), last period, last update, scope, base year.</li>
<li>Read the observation status (Eurostat <i>status</i>: p, e; INSEE OBS_STATUS).</li>
<li>Recompute with the claim's definition (points vs %, sum of months).</li>
<li>Verdict TRUE / FALSE / MISLEADING / OUTDATED, with code, period and extraction date.</li></ol>
<div class="ex">"Unemployment rose by 0.5%" (France, Oct 2025 → Sep 2026): MISLEADING. 8.0% → 8.5% is +0.5 percentage points, +6.2% relative.</div>''')}
</div>"""))

pages.append(page(4, "4 · Language comparison and reviewer agreement",
    "Is it worse in French? Not once you control for difficulty",
    "The raw pass rate is 10 points lower in French; French items were rated hard far more often. At equal difficulty the gap disappears",
    f"""<div class="grid" style="grid-template-columns: 0.9fr 1.2fr 1fr;">
{card("Raw vs standardised pass rate", charts["p4a"], tag="sim", note=f"Raw: EN {g['en']:.0f}% vs FR {g['fr']:.0f}%. Standardised on the pooled difficulty mix: {sd['en']:.1f}% vs {sd['fr']:.1f}%. <b>False signal, not reported as a finding.</b>")}
{card("Composition effect", charts["p4b"], tag="sim", note=f"Hard items: {hard['fr']:.0f}% of French answers vs {hard['en']:.0f}% of English ones. Within each difficulty level the gap is within ±2 points.")}
{card("What does differ in French: the kind of error", f'''<p>{int(fs.set_index('language').french_specific['fr'])} of {int(fs.set_index('language').errors['fr'])} failed French answers ({fs.set_index('language').pct['fr']:.0f}%) are French-specific:</p>
<ul><li><b>Decimal comma:</b> « 11,035 millions » read as 11 035 millions.</li>
<li><b>milliard / billion:</b> « 0,31 billion » means 10^12 in French.</li>
<li><b>trimestre / semestre</b>, <b>avant-dernier / dernier</b>.</li>
<li><b>points de pourcentage</b> vs %.</li></ul>
<p class="note">These are worth a dedicated rule (R7) and French examples in the guidelines.</p>''', tag="sim")}
</div>
<div class="grid" style="grid-template-columns: 0.9fr 2.2fr; margin-top: 4mm; flex: 0 0 52mm;">
{card("Reviewer agreement", charts["p4c"], tag="sim")}
{card("What made the reviewers agree", f'''<p>Guidelines v1 only defined the three verdicts. Agreement was {po[('all answers', 'v1')] * 100:.0f}% (kappa {k[('all answers', 'v1')]:.2f}), and {po[('grey-zone answers', 'v1')] * 100:.0f}% on grey-zone answers: the strict reviewer failed them, the lenient one passed them.
Two checks were skipped: series status (stopped series confirmed as TRUE) and French formats.</p>
<p>v2 added 7 decision rules (period, units, data status, source currency, geography, French formats, puzzles). Agreement rose to {po[('all answers', 'v2')] * 100:.0f}% (kappa {k[('all answers', 'v2')]:.2f}), {po[('grey-zone answers', 'v2')] * 100:.0f}% on grey-zone answers; median time per review {med_v2.median() / 60:.1f} min (simulated).</p>''', tag="sim")}
</div>"""))

pages.append(page(5, "5 · Methods, limits & AI note",
    "Methods, limits and sources",
    "Everything can be re-run from the repository: python scripts, DuckDB SQL 01-05, one executed notebook",
    f"""<div class="grid" style="grid-template-columns: 1.2fr 1fr 1fr;">
{card("Sources (extracted 2026-11-23)", '''<table><tr><th>Source</th><th>Use</th><th>Licence</th></tr>
<tr><td>Eurostat sts_trtu_m (updated 2026-11-21)</td><td>retail volume, 12 countries</td><td rowspan="3">Eurostat reuse policy: free reuse with source acknowledged</td></tr>
<tr><td>Eurostat tour_occ_nin2m (2026-10-20)</td><td>nights, 8 NUTS 2 regions</td></tr>
<tr><td>Eurostat prc_hicp_minr / manr, une_rt_m</td><td>HICP, unemployment</td></tr>
<tr><td>INSEE BDM 011814630, 001763852, 001688527, 001688526</td><td>CPI, unemployment</td><td>Licence Ouverte 2.0</td></tr>
<tr><td>Wikipedia, 5 articles at fixed revisions</td><td>summaries, chunking</td><td>CC BY-SA 4.0</td></tr></table>
<p class="note">Collection: official APIs only, at most 1 request per second, raw responses cached and not published. Only short excerpts of texts are quoted; summaries are our own.</p>''', tag="pub")}
{card("Method & assumptions", '''<ul><li>Python (pandas, DuckDB SQL 01-05, openpyxl, matplotlib); one executed notebook re-verifies the references (SQL for growth tasks, solver for puzzles, number check for summaries).</li>
<li>"Grew the most": 3-month averages at each end (seasonally adjusted series) or full calendar years (raw series).</li>
<li>Puzzles: 4-6 stops, minimal rule sets, uniqueness proven by brute force.</li>
<li>Simulated model: outcome depends on item difficulty only (90 / 60 / 30% correct), seed 42; 8 hidden events (7 issues, 1 false signal) checked against an answer key opened last.</li>
<li>Consensus = majority of 3 reviewers (guidelines v2).</li></ul>''', tag="")}
{card("Limits & AI note", f'''<ul><li><b>The model is simulated:</b> no real language model was called and no answer is attributed to any product. Error rates illustrate the method; they measure nothing real.</li>
<li>Reviewers are simulated; kappa values illustrate the method, not real people.</li>
<li>Errors and checks were designed together, so detection is optimistic.</li>
<li>Item difficulty is a writer's rating, not a measured property.</li>
<li>Latest Eurostat values are provisional and may be revised after 2026-11-23.</li></ul>
<p style="margin-top:2.5mm"><b>{AI}</b></p>''', tag="")}
</div>
<div class="grid" style="grid-template-columns: 1fr 1fr; margin-top: 4mm; flex: 0 0 40mm;">
{card("How to re-run (from the repository root)", '''<ol style="font-family: Consolas, monospace; font-size: 7.8pt;">
<li>pip install -r requirements.txt</li><li>python src/fetch_public.py · python src/build_series_tasks.py · python src/puzzle_solver.py</li>
<li>python src/simulate_model.py · python src/run_sql.py · python src/build_workbook.py</li>
<li>jupyter nbconvert --to notebook --execute --inplace notebooks/llm_analyst_eval.ipynb</li><li>python src/build_pdf.py</li></ol>''', tag="")}
{card("What is in the repository", '''<ul><li><b>eval/llm_eval_workbook.xlsx</b>: README, Gold set, Rubric, Error taxonomy, Review log (blind-test columns), Agreement, Summary (formulas, native charts).</li>
<li><b>eval/gold_set.jsonl</b>: 240 lines (task × language) with prompt, reference, explanation, source, verification.</li>
<li><b>docs/</b>: writing a gold answer, rubric, error taxonomy (French pitfalls), claim checking, chunking guide, data issues log.</li></ul>''', tag="")}
</div>"""))

html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>LLM analyst evaluation</title>
<style>{CSS}</style></head><body>{''.join(pages)}</body></html>"""
src = os.path.abspath(os.path.join(BUILD, "report.html"))
open(src, "w", encoding="utf-8").write(html)
tmp = os.path.abspath(os.path.join(BUILD, "report_raw.pdf"))
subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--run-all-compositor-stages-before-draw",
                f"--print-to-pdf={tmp}", "file:///" + src.replace("\\", "/")], check=True,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
rd = PdfReader(tmp); wr = PdfWriter()
for pg in rd.pages:
    wr.add_page(pg)
wr.add_metadata({"/Producer": "", "/Creator": "", "/Title": "", "/Author": ""})
with open(OUT, "wb") as f:
    wr.write(f)
print(f"saved {OUT}: {len(rd.pages)} pages")
