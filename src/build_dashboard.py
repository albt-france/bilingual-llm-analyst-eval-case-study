"""Build dashboard/index.html: a self-contained Plotly dashboard with 5 tabs (works offline, no server).
Which grew the most? · Where the model slips · Claim checking · French gap & agreement · Gold set browser.
    python src/build_dashboard.py
"""
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

ROOT = Path(__file__).resolve().parents[1]
PROC, PUB = ROOT / "data" / "processed", ROOT / "data" / "public"
DASH = ROOT / "dashboard" / "index.html"
BLUE, ORANGE, GREY, TEAL, EN_C, FR_C, INK2 = "#1f4e79", "#d9822b", "#a9a8a2", "#00897b", "#1f4e79", "#7e57c2", "#52514e"
FOOT = "Independent case study based on public data · not affiliated with or endorsed by any AI company"
SIM, PUBT = "SIMULATED · fictional model and reviewers, no real language model called", "PUBLIC DATA"
r = lambda f, d=PROC: pd.read_csv(d / f"{f}.csv")
COUNTRY = {"FR": "France", "DE": "Germany", "ES": "Spain", "IT": "Italy", "NL": "Netherlands", "BE": "Belgium",
           "AT": "Austria", "PT": "Portugal", "PL": "Poland", "SE": "Sweden", "IE": "Ireland", "FI": "Finland"}
NUTS = {"FR10": "Île-de-France", "FRE1": "Nord-Pas-de-Calais", "FRH0": "Bretagne", "FRI1": "Aquitaine",
        "FRJ2": "Midi-Pyrénées", "FRK2": "Rhône-Alpes", "FRL0": "Provence-Alpes-Côte d'Azur", "FRM0": "Corse"}


def layout(fig, title, tag, h=360):
    fig.update_layout(title=dict(text=f"<b>{title}</b><br><span style='font-size:11px;color:{INK2}'>{tag}</span>", x=0.01),
                      template="plotly_white", height=h, margin=dict(l=50, r=20, t=70, b=40),
                      font=dict(family="Segoe UI, Arial", size=12), legend=dict(orientation="h", y=-0.18),
                      paper_bgcolor="#fcfcfb", plot_bgcolor="#fcfcfb")
    return fig


def html(fig):
    return pio.to_html(fig, include_plotlyjs=False, full_html=False, config={"displaylogo": False, "responsive": True})


def card(body, tag=None, title=None):
    t = f'<span class="tag {"pub" if tag == "pub" else "sim"}">{PUBT if tag == "pub" else SIM}</span>' if tag else ""
    return f'<div class="card">{t}{f"<h3>{title}</h3>" if title else ""}{body}</div>'


def table(df):
    head = "".join(f"<th>{c}</th>" for c in df.columns)
    rows = "".join("<tr>" + "".join(f"<td>{'–' if pd.isna(v) else v}</td>" for v in row) + "</tr>"
                   for row in df.itertuples(index=False))
    return f"<table><tr>{head}</tr>{rows}</table>"


def tab_window():
    ret = r("eurostat_retail", PUB)
    R = ret.pivot(index="time", columns="geo", values="value")
    fig = go.Figure()
    for g in R.columns:
        vis = True if g in ("ES", "PL", "IE", "FI") else "legendonly"
        fig.add_trace(go.Scatter(x=R.index, y=R[g], name=COUNTRY[g], visible=vis, mode="lines"))
    for a, b in (("2024-01", "2024-03"), ("2026-07", "2026-09")):
        fig.add_vrect(x0=a, x1=b, fillcolor="#e9e4d8", line_width=0, layer="below")
    layout(fig, "Retail trade volume index (seasonally and calendar adjusted, 2021 = 100)",
           "Eurostat sts_trtu_m, updated 2026-11-21 · click the legend to add countries · shaded: the 3-month windows of task T001", 420)
    names = ["ES", "PL", "IE", "FI"]
    a0, a1 = R.loc["2024-01":"2024-03", names].mean(), R.loc["2026-07":"2026-09", names].mean()
    rob, nai = (a1 / a0 - 1) * 100, (R.loc["2026-09", names] / R.loc["2024-01", names] - 1) * 100
    f2 = go.Figure([go.Bar(x=[COUNTRY[g] for g in names], y=rob, name="3-month averages (reference)", marker_color=BLUE,
                           text=[f"{v:+.1f}%" for v in rob], textposition="outside"),
                    go.Bar(x=[COUNTRY[g] for g in names], y=nai, name="Jan 2024 → Sep 2026 (endpoints)", marker_color=GREY,
                           text=[f"{v:+.1f}%" for v in nai], textposition="outside")])
    layout(f2, "Same data, two answers: Spain or Poland?", "Endpoint growth favours Poland because of one low month (Jan 2024)")
    n = r("eurostat_nights", PUB)
    N = n.pivot(index="time", columns="geo", values="value") / 1e6
    f3 = go.Figure([go.Scatter(x=N.index, y=N[g], name=NUTS[g], mode="lines",
                               visible=True if g in ("FR10", "FRL0", "FRI1") else "legendonly") for g in N.columns])
    layout(f3, "Tourist nights by NUTS 2 region, millions (raw, not seasonally adjusted)",
           "Eurostat tour_occ_nin2m, updated 2026-10-20 · compare full years, not single months · January 2022 still depressed")
    fl = r("retail_flags")
    fl["country"] = fl.geo.map(COUNTRY)
    return (card(html(fig), "pub") +
            f'<div class="grid2">{card(html(f2), "pub")}{card(html(f3), "pub")}</div>' +
            card("<p>Observation status in the retail extract: <b>p</b> = provisional, <b>e</b> = estimated. A reference "
                 "answer that uses these values says they may be revised.</p>" +
                 table(fl[["country", "provisional", "estimated", "values_total", "first_flagged"]]), "pub",
                 "Data status flags"))


def tab_slips():
    g = r("graded")
    pt = g.groupby(["task_type", "language"])["pass"].mean().unstack() * 100
    f1 = go.Figure([go.Bar(y=pt.index, x=pt[l], name=l.upper(), orientation="h", marker_color=c,
                           text=[f"{v:.0f}%" for v in pt[l]], textposition="outside") for l, c in (("en", EN_C), ("fr", FR_C))])
    layout(f1, "Pass rate by task type (consensus = correct)", "240 simulated answers, guidelines v2")
    c = r("error_code_totals").sort_values("answers")
    f2 = go.Figure([go.Bar(y=c.error_code, x=c.en, name="EN", orientation="h", marker_color=EN_C),
                    go.Bar(y=c.error_code, x=c.fr, name="FR", orientation="h", marker_color=FR_C)])
    f2.update_layout(barmode="stack")
    layout(f2, "What goes wrong (consensus error codes)", "Failed answers only; FR_* codes cannot occur in English", 440)
    s = r("accuracy_by_subtype")
    f3 = go.Figure(go.Bar(x=s.subtype, y=s.pass_pct, marker_color=[ORANGE if t == "series_analysis" else BLUE for t in s.task_type],
                          text=[f"{v:.0f}%" for v in s.pass_pct], textposition="outside"))
    layout(f3, "Pass rate by subtype", "Orange: series questions; 'who grew the most' (window, seasonal) are the hardest")
    return f'<div class="grid2">{card(html(f1), "sim")}{card(html(f2), "sim")}</div>' + card(html(f3), "sim")


def tab_claims():
    ins = pd.read_csv(PUB / "insee_series.csv", dtype={"idbank": str})
    f1 = go.Figure()
    for idb, nm, col, dash in (("001763852", "001763852 CPI base 2015 excl. tobacco (stopped)", GREY, "dash"),
                               ("011814630", "011814630 CPI base 2025 all items (current)", BLUE, "solid")):
        s = ins[ins.idbank == idb].set_index("period").value
        y = ((s / s.shift(12) - 1) * 100).dropna()
        f1.add_trace(go.Scatter(x=y.index, y=y, name=nm, line=dict(color=col, dash=dash)))
    layout(f1, "INSEE CPI, % year on year: stopped vs current series", "A '0.7% inflation' claim matches the stopped series → OUTDATED")
    h, ho = r("eurostat_hicp", PUB), r("eurostat_hicp_stopped", PUB)
    f2 = go.Figure()
    for g, col in (("FR", BLUE), ("ES", ORANGE), ("DE", TEAL)):
        a = h[h.geo == g]; b = ho[ho.geo == g]
        f2.add_trace(go.Scatter(x=a.time, y=a.value, name=f"{g} prc_hicp_minr", line=dict(color=col)))
        f2.add_trace(go.Scatter(x=b.time, y=b.value, name=f"{g} prc_hicp_manr (frozen)", line=dict(color=col, dash="dot")))
    layout(f2, "Eurostat HICP, annual rate: frozen dataset vs successor", "prc_hicp_manr stops at 2025-12 (last update 2026-02-06)")
    traps = pd.DataFrame([
        ("INSEE 001763852", "CPI base 2015 excl. tobacco, stopped at 2025-12", "OUTDATED · R5"),
        ("INSEE 001688526", "Unemployment, metropolitan France, stopped at 2026-Q1 (7.9%); current 001688527: 8.2% in 2026-Q3", "OUTDATED · R5"),
        ("Eurostat prc_hicp_manr", "Frozen at 2025-12; successor prc_hicp_minr", "OUTDATED · R5"),
        ("Eurostat sts_trtu_m", "p on every month for AT, BE, DE, ES; FR 2026-09 = e", "MISLEADING if called final · R4"),
        ("Eurostat tour_occ_nin2m", "NUTS 2 labels (Midi-Pyrénées, Aquitaine, Rhône-Alpes); months in a separate dimension", "MISLEADING · R6"),
    ], columns=["source", "trap", "verdict / rule"])
    steps = ("<ol><li>Restate: value, unit, geography, period, source.</li><li>Go to the primary source (dataset code, INSEE idbank).</li>"
             "<li>Check the series: title (stopped?), last period, last update, scope, base year.</li>"
             "<li>Read the observation status (p, e).</li><li>Recompute with the claim's definition.</li>"
             "<li>Verdict TRUE / FALSE / MISLEADING / OUTDATED, with code, period and extraction date.</li></ol>")
    return (f'<div class="grid2">{card(html(f1), "pub")}{card(html(f2), "pub")}</div>'
            f'<div class="grid2">{card(table(traps), "pub", "Real traps met while building the tasks (2026-11-23)")}'
            f'{card(steps, None, "Six-step claim-checking method")}</div>')


def tab_gap():
    raw, std, st = r("language_gap_raw"), r("language_gap_standardised"), r("language_gap_strata")
    f1 = go.Figure([go.Bar(x=["raw", "standardised (same difficulty mix)"],
                           y=[raw.set_index("language").pass_pct[l], std.set_index("language").standardised_pass_pct[l]],
                           name=l.upper(), marker_color=c, texttemplate="%{y:.1f}%", textposition="outside")
                    for l, c in (("en", EN_C), ("fr", FR_C))])
    layout(f1, "Is it worse in French? Raw vs standardised pass rate", "False signal: the raw 10-point gap disappears at equal difficulty")
    f2 = go.Figure([go.Bar(x=["easy", "medium", "hard"], y=st[f"pass_{l}"], name=l.upper(), marker_color=c,
                           texttemplate="%{y:.0f}%", textposition="outside") for l, c in (("en", EN_C), ("fr", FR_C))])
    layout(f2, "Pass rate by item difficulty", f"Hard items: {raw.set_index('language').pct_hard_items['fr']:.0f}% of French answers vs "
           f"{raw.set_index('language').pct_hard_items['en']:.0f}% of English ones")
    a = r("agreement")
    m = a.groupby(["scope", "guidelines"])[["observed_agreement", "cohen_kappa"]].mean().reset_index()
    f3 = go.Figure()
    for v, c in (("v1", GREY), ("v2", BLUE)):
        d = m[m.guidelines == v]
        f3.add_trace(go.Bar(x=d.scope + " · observed", y=d.observed_agreement, name=f"{v} observed", marker_color=c,
                            texttemplate="%{y:.2f}", textposition="outside"))
        d = d[d.scope == "all answers"]
        f3.add_trace(go.Bar(x=d.scope + " · kappa", y=d.cohen_kappa, name=f"{v} kappa", marker_color=c, opacity=0.6,
                            texttemplate="%{y:.2f}", textposition="outside"))
    layout(f3, "Reviewer agreement, guidelines v1 vs v2", "Kappa is unstable inside the grey-zone subset (prevalence), so observed agreement is shown there")
    fs = r("french_specific")
    txt = (f"<p>{int(fs.french_specific.iloc[-1])} of {int(fs.errors.iloc[-1])} failed French answers are French-specific: decimal comma "
           "(« 11,035 millions » read as 11 035 millions), « billion » used for 10^9 (milliard), trimestre/semestre, "
           "avant-dernier/dernier. What differs in French is the kind of error, not the rate.</p>")
    return (f'<div class="grid2">{card(html(f1), "sim")}{card(html(f2), "sim")}</div>'
            f'<div class="grid2">{card(html(f3), "sim")}{card(txt, "sim", "French-specific pitfalls")}</div>')


def tab_gold():
    items = [json.loads(l) for l in (ROOT / "eval" / "gold_set.jsonl").read_text(encoding="utf-8").splitlines()]
    keep = [{k: it[k] for k in ("id", "language", "task_type", "subtype", "difficulty", "prompt", "reference_answer",
                                 "reference_explanation", "source")} for it in items]
    data = json.dumps(keep, ensure_ascii=False).replace("</", "<\\/")
    return card(f"""<p>120 tasks × English/French. Filter, search, click a row to see the step-by-step explanation.</p>
<div class="filters"><select id="fl"><option value="">all languages</option><option>en</option><option>fr</option></select>
<select id="ft"><option value="">all task types</option><option>series_analysis</option><option>logic_puzzle</option>
<option>claim_check</option><option>summarise_chunk</option></select>
<input id="fq" placeholder="search (e.g. Spain, OUTDATED, Gare)"><span id="fn" class="note"></span></div>
<div class="scroll tall"><table id="gt"></table></div>
<script>const GOLD={data};
function esc(s){{return String(s??'').replace(/[&<>]/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;'}}[c]));}}
function draw(){{const l=fl.value,t=ft.value,q=fq.value.toLowerCase();
const rows=GOLD.filter(g=>(!l||g.language===l)&&(!t||g.task_type===t)&&(!q||JSON.stringify(g).toLowerCase().includes(q)));
fn.textContent=rows.length+' items';
gt.innerHTML='<tr><th>id</th><th>type</th><th>diff.</th><th>prompt</th><th>reference answer</th></tr>'+rows.map((g,i)=>
`<tr class="row" onclick="this.nextSibling.classList.toggle('open')"><td>${{g.id}}</td><td>${{g.subtype}}</td><td>${{g.difficulty}}</td><td>${{esc(g.prompt)}}</td><td>${{esc(g.reference_answer)}}</td></tr>`+
`<tr class="exp"><td colspan="5"><b>Explanation.</b> ${{esc(g.reference_explanation)}}<br><span class="note">Source: ${{esc(g.source)}}</span></td></tr>`).join('');}}
[fl,ft,fq].forEach(e=>e.addEventListener('input',draw));draw();</script>""", "pub", "Gold set browser")


CSS = """
:root { --bg:#f1efea; --card:#fcfcfb; --ink:#0b0b0b; --ink2:#52514e; --line:#e1e0d9; }
* { box-sizing:border-box; } body { margin:0; font-family:'Segoe UI',Arial,sans-serif; background:var(--bg); color:var(--ink); }
header { padding:18px 24px 6px; } h1 { margin:0; font-size:22px; } .sub { color:var(--ink2); margin:4px 0 0; font-size:13px; }
nav { display:flex; gap:6px; padding:10px 24px; flex-wrap:wrap; position:sticky; top:0; background:var(--bg); z-index:5; }
nav button { border:1px solid var(--line); background:var(--card); padding:8px 14px; border-radius:6px; cursor:pointer; font:inherit; font-size:13px; }
nav button.on { background:#1f3b57; color:#fff; border-color:#1f3b57; }
section { display:none; padding:0 24px 16px; } section.on { display:block; }
.grid2 { display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:12px; }
@media (max-width:1000px) { .grid2 { grid-template-columns:1fr; } }
.card { background:var(--card); border:1px solid var(--line); border-radius:8px; padding:10px 12px; min-width:0; margin-bottom:12px; }
.card h3 { margin:4px 0; font-size:15px; } .card p, .card li { font-size:13px; }
.tag { display:inline-block; font-size:11px; font-weight:700; letter-spacing:.05em; padding:3px 8px; border-radius:4px; margin:2px 0 6px; }
.sim { background:#fbe9e0; color:#9a3b12; } .pub { background:#e3eefb; color:#1c5cab; }
table { border-collapse:collapse; width:100%; font-size:12px; } th { text-align:left; color:var(--ink2); border-bottom:1px solid var(--line); padding:4px; position:sticky; top:0; background:var(--card); }
td { border-bottom:1px solid #efeee9; padding:4px; vertical-align:top; } .scroll { max-height:300px; overflow:auto; } .scroll.tall { max-height:640px; }
.note { color:#6b6a65; font-size:12px; } footer { padding:10px 24px 20px; color:#898781; font-size:12px; }
.filters { display:flex; gap:8px; flex-wrap:wrap; margin:6px 0 10px; } .filters select, .filters input { font:inherit; font-size:13px; padding:5px 8px; border:1px solid var(--line); border-radius:5px; }
.filters input { min-width:260px; } tr.row { cursor:pointer; } tr.row:hover { background:#f4f2ec; } tr.exp { display:none; background:#f7f5f0; } tr.exp.open { display:table-row; }
"""


def build():
    import plotly
    tabs = [("Which grew the most?", tab_window()), ("Where the model slips", tab_slips()), ("Claim checking", tab_claims()),
            ("French gap & agreement", tab_gap()), ("Gold set browser", tab_gold())]
    nav = "".join(f'<button class="{"on" if i == 0 else ""}" onclick="show({i})">{t}</button>' for i, (t, _) in enumerate(tabs))
    secs = "".join(f'<section class="{"on" if i == 0 else ""}">{b}</section>' for i, (_, b) in enumerate(tabs))
    js = plotly.offline.get_plotlyjs()
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bilingual LLM analyst evaluation</title><style>{CSS}</style><script>{js}</script></head><body>
<header><h1>Where language models slip on analyst questions</h1>
<p class="sub">A bilingual (EN/FR) gold set and grading rubric. PUBLIC DATA (Eurostat, INSEE, Wikipedia) for the 120 tasks and their
computed reference answers; SIMULATED answers of a fictional model and 3 simulated reviewers. No real language model was called.
· <a href="../report/LLM_analyst_eval.pdf">Report (PDF)</a> · <a href="https://github.com/albt-france/bilingual-llm-analyst-eval-case-study">Repository</a></p></header>
<nav>{nav}</nav>{secs}<footer>{FOOT}</footer>
<script>function show(i){{document.querySelectorAll('section').forEach((s,k)=>s.classList.toggle('on',k===i));
document.querySelectorAll('nav button').forEach((b,k)=>b.classList.toggle('on',k===i));
window.dispatchEvent(new Event('resize'));}}</script></body></html>"""
    DASH.parent.mkdir(exist_ok=True)
    DASH.write_text(page, encoding="utf-8")
    print(f"  wrote {DASH.relative_to(ROOT)} ({DASH.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    build()
