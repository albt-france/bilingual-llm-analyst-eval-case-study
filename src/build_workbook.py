"""Build eval/llm_eval_workbook.xlsx (main evaluation tool, 7 tabs) and eval/gold_set.jsonl.
Run from the repository root:  python src/build_workbook.py
"""
import json
import os

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from content import VERDICTS, RULES_V2, V1_TO_V2, TAXONOMY

PROC = os.path.join("data", "processed")
os.makedirs("eval", exist_ok=True)
OUT = os.path.join("eval", "llm_eval_workbook.xlsx")
HEAD = PatternFill("solid", fgColor="E1E0D9")
BOLD, TITLE = Font(bold=True), Font(bold=True, size=14)
WRAP = Alignment(wrap_text=True, vertical="top")
FILL = {"correct": "D9EAD3", "partially_correct": "FFF2CC", "incorrect": "F4CCCC"}
FOOT = "Independent case study based on public data · not affiliated with or endorsed by any AI company"
r = lambda f: pd.read_csv(os.path.join(PROC, f + ".csv"), dtype={"series_code": str})

tasks, ans, rev, graded, agr, conf = r("tasks"), r("model_answers"), r("reviews"), r("graded"), r("agreement"), \
    r("confusion_r1_r3")
rev["error_code"] = rev.error_code.fillna("")
graded["error_code"] = graded.error_code.fillna("")


def table(ws, df, start_row=1, widths=None, wrap=False):
    for j, col in enumerate(df.columns, 1):
        c = ws.cell(start_row, j, col); c.fill = HEAD; c.font = BOLD; c.alignment = WRAP
    for i, row in enumerate(df.itertuples(index=False), start_row + 1):
        for j, v in enumerate(row, 1):
            c = ws.cell(i, j, None if (isinstance(v, float) and v != v) else v)
            if wrap:
                c.alignment = WRAP
    for j, col in enumerate(df.columns, 1):
        ws.column_dimensions[get_column_letter(j)].width = (widths or {}).get(col, max(10, min(40, len(str(col)) + 4)))
    return start_row + len(df)


wb = Workbook()
# ---------------- README
ws = wb.active; ws.title = "README"
lines = [
    ("Bilingual LLM analyst evaluation workbook", TITLE),
    ("PUBLIC DATA (Eurostat, INSEE, Wikipedia revisions) for the 120 gold tasks + SIMULATED (240 answers of a fictional "
     "model, 3 simulated reviewers). No real language model was called; no answer is attributed to any product.", None),
    ("", None),
    ("How to use", BOLD),
    ("1. Read 'Rubric' (3 verdicts + 8 decision rules) and 'Error taxonomy' (13 codes, with French-specific pitfalls).", None),
    ("2. 'Gold set': each task in English and French, with the reference answer, a step-by-step explanation, the "
     "source and series code, and how the answer was verified (column 'check').", None),
    ("3. 'Review log': one row per model answer. Blind test: hide columns L onwards, fill 'your_verdict' and "
     "'your_code' (drop-down lists) for 10 rows, then unhide and compare with the consensus.", None),
    ("4. 'Agreement': Cohen's kappa between the 3 simulated reviewers, guidelines v1 vs v2.", None),
    ("5. 'Summary': formulas (COUNTIFS) on the Review log, plus native charts. Filter or edit and it updates.", None),
    ("", None),
    ("Task families", BOLD),
    ("series_analysis (40): which country/region grew the most, year-on-year ranking, points vs %, seasonality.", None),
    ("logic_puzzle (30): courier route orders with 4-6 stops; every solution proven unique by brute force.", None),
    ("claim_check (25): verdict TRUE / FALSE / MISLEADING / OUTDATED against the primary series.", None),
    ("summarise_chunk (25): chunking, lead summary, dates, locating a topic, longest block (Wikipedia, fixed revisions).", None),
    ("", None),
    ("Sources", BOLD),
    ("Eurostat sts_trtu_m, tour_occ_nin2m, prc_hicp_minr (current), prc_hicp_manr (stopped), une_rt_m: reuse authorised "
     "with acknowledgement of the source (Eurostat copyright and reuse policy).", None),
    ("INSEE BDM series 011814630, 001763852 (stopped), 001688527, 001688526 (stopped): Licence Ouverte / Etalab 2.0.", None),
    ("Wikipedia articles at fixed revision ids (see Gold set): CC BY-SA 4.0. Only short excerpts and our own summaries.", None),
    ("Extracted 2026-11-23. Values flagged p (provisional) or e (estimated) are labelled as such.", None),
    ("", None),
    (FOOT, Font(italic=True, color="7A756B")),
]
for i, (t, f) in enumerate(lines, 1):
    c = ws.cell(i, 1, t); c.alignment = Alignment(wrap_text=True, vertical="top")
    if f:
        c.font = f
ws.column_dimensions["A"].width = 130

# ---------------- Gold set
ws = wb.create_sheet("Gold set")
g = tasks[["task_id", "type", "subtype", "difficulty_en", "difficulty_fr", "prompt_en", "prompt_fr", "ref_en", "ref_fr",
           "expl_en", "expl_fr", "source", "series_code", "data_status", "check"]]
last = table(ws, g, widths={"prompt_en": 50, "prompt_fr": 50, "ref_en": 40, "ref_fr": 40, "expl_en": 55, "expl_fr": 55,
                            "source": 30, "series_code": 22, "check": 30, "subtype": 16, "type": 15}, wrap=True)
ws.auto_filter.ref = f"A1:{get_column_letter(g.shape[1])}{last}"
ws.freeze_panes = "B2"

# ---------------- Rubric
ws = wb.create_sheet("Rubric")
ws.cell(1, 1, "Verdicts").font = TITLE
row = table(ws, pd.DataFrame(VERDICTS, columns=["verdict", "definition", "counts as"]), 2,
            widths={"verdict": 20, "definition": 100, "counts as": 14}, wrap=True)
ws.cell(row + 2, 1, "Decision rules (guidelines v2)").font = TITLE
row = table(ws, pd.DataFrame(RULES_V2, columns=["rule", "text"]), row + 3, wrap=True)
ws.column_dimensions["B"].width = 100
ws.cell(row + 2, 1, "What changed from v1 to v2").font = BOLD
ws.cell(row + 3, 1, V1_TO_V2).alignment = WRAP
ws.merge_cells(start_row=row + 3, start_column=1, end_row=row + 3, end_column=3)
ws.row_dimensions[row + 3].height = 45
ex = [("Which country grew the most? (series)", "Spain, +5.6% on 3-month averages; endpoint growth would favour Poland "
       "because of one atypical month; Spanish values flagged p.", "Poland, +6.3% (January vs September).",
       "incorrect - WRONG_WINDOW (R2)"),
      ("Unemployment change (points vs %)", "+0.5 percentage points (8.0% -> 8.5%), +6.3% relative.", "+0.5%.",
       "partially_correct - PCT_VS_POINTS (R3)"),
      ("Claim with a stopped series", "OUTDATED: series 001763852 stopped in 2025-12; current series 011814630.",
       "TRUE, confirmed by series 001763852.", "incorrect - STALE_SOURCE (R5)"),
      ("Affirmation en français", "VRAI : 11,03 millions de nuitées en 2025.", "FAUX : 11 030 millions est impossible.",
       "incorrect - FR_DECIMAL (R7)")]
ws.cell(row + 5, 1, "Worked examples").font = BOLD
table(ws, pd.DataFrame(ex, columns=["case", "reference", "model answer", "verdict"]), row + 6, wrap=True)
ws.column_dimensions["C"].width = 40; ws.column_dimensions["D"].width = 34

# ---------------- Error taxonomy
ws = wb.create_sheet("Error taxonomy")
tx = pd.DataFrame(TAXONOMY, columns=["code", "family", "default_verdict", "definition", "example_en", "example_fr", "fix"])
last = table(ws, tx, widths={"code": 22, "family": 15, "default_verdict": 17, "definition": 45, "example_en": 45,
                             "example_fr": 45, "fix": 40}, wrap=True)
for i in range(2, last + 1):
    if str(ws.cell(i, 2).value) == "French-specific":
        for j in range(1, 8):
            ws.cell(i, j).fill = PatternFill("solid", fgColor="CFE2F3")
ws.freeze_panes = "B2"

# ---------------- Review log
ws = wb.create_sheet("Review log")
t2 = tasks.set_index("task_id")
w = rev[rev.guidelines == "v2"].pivot(index="answer_id", columns="reviewer", values="verdict")
cmt = rev[rev.guidelines == "v2"].sort_values("reviewer").groupby("answer_id").comment.first()
log = ans.merge(graded[["answer_id", "verdict", "error_code"]], on="answer_id")
log["prompt"] = [t2.at[t, f"prompt_{l}"] for t, l in zip(log.task_id, log.language)]
log["reference"] = [t2.at[t, f"ref_{l}"] for t, l in zip(log.task_id, log.language)]
log = log.assign(R1=log.answer_id.map(w.R1), R2=log.answer_id.map(w.R2), R3=log.answer_id.map(w.R3),
                 comment=log.answer_id.map(cmt).where(log.verdict != "correct", "Matches the reference."))
log = log[["answer_id", "task_id", "language", "task_type", "difficulty", "prompt", "answer", "explanation", "reference",
           "your_verdict" if False else "n_words", "R1", "R2", "R3", "verdict", "error_code", "comment"]]
log = log.rename(columns={"verdict": "consensus_verdict", "error_code": "consensus_code"})
log.insert(10, "your_verdict", ""); log.insert(11, "your_code", "")
log["match"] = ""
last = table(ws, log, widths={"prompt": 45, "answer": 35, "explanation": 40, "reference": 40, "comment": 40,
                              "consensus_verdict": 18, "consensus_code": 22, "your_verdict": 16, "your_code": 20}, wrap=True)
col = {c: get_column_letter(i + 1) for i, c in enumerate(log.columns)}
for i in range(2, last + 1):
    ws[f"{col['match']}{i}"] = f'=IF({col["your_verdict"]}{i}="","",IF({col["your_verdict"]}{i}={col["consensus_verdict"]}{i},"agree","differs"))'
dv = DataValidation(type="list", formula1='"correct,partially_correct,incorrect"', allow_blank=True)
dv2 = DataValidation(type="list", formula1=f"'Error taxonomy'!$A$2:$A${len(TAXONOMY) + 1}", allow_blank=True)
ws.add_data_validation(dv); ws.add_data_validation(dv2)
dv.add(f"{col['your_verdict']}2:{col['your_verdict']}{last}"); dv2.add(f"{col['your_code']}2:{col['your_code']}{last}")
for c in ["R1", "R2", "R3", "consensus_verdict", "your_verdict"]:
    L = col[c]
    for v, f in FILL.items():
        ws.conditional_formatting.add(f"{L}2:{L}{last}", CellIsRule(operator="equal", formula=[f'"{v}"'],
                                                                    fill=PatternFill("solid", fgColor=f)))
L = col["match"]
ws.conditional_formatting.add(f"{L}2:{L}{last}", FormulaRule(formula=[f'{L}2="differs"'],
                                                             fill=PatternFill("solid", fgColor="F4CCCC")))
ws.auto_filter.ref = f"A1:{get_column_letter(log.shape[1])}{last}"
ws.freeze_panes = "C2"
n_log = last

# ---------------- Agreement
ws = wb.create_sheet("Agreement")
ws.cell(1, 1, "Reviewer agreement, guidelines v1 vs v2 (SIMULATED reviewers)").font = TITLE
row = table(ws, agr, 2, widths={"scope": 20, "pair": 10})
ws.cell(row + 2, 1, "Mean kappa").font = BOLD
mk = agr.groupby(["scope", "guidelines"]).agg(kappa=("cohen_kappa", "mean"), observed=("observed_agreement", "mean")) \
    .round(3).reset_index()
r0 = row + 3
row = table(ws, mk, r0)
ws.cell(row + 1, 1, "Within grey-zone answers almost every verdict is partially_correct after v2, so kappa is unstable "
                    "there (prevalence effect); read observed agreement for that subset.").alignment = WRAP
ch = BarChart(); ch.type = "col"; ch.title = "Mean Cohen's kappa, all answers (SIMULATED)"; ch.y_axis.title = "kappa"
data = Reference(ws, min_col=3, min_row=r0, max_row=r0 + 2)
cats = Reference(ws, min_col=2, min_row=r0 + 1, max_row=r0 + 2)
ch.add_data(data, titles_from_data=True); ch.set_categories(cats); ch.height, ch.width = 7, 12; ch.legend = None
ws.add_chart(ch, "J2")
ws.cell(row + 3, 1, "Confusion matrix R1 (strict) x R3 (lenient)").font = BOLD
table(ws, conf, row + 4)

# ---------------- Summary (formulas on the Review log)
ws = wb.create_sheet("Summary")
ws.cell(1, 1, "Pass rate (consensus = correct), SIMULATED model, formulas on 'Review log'").font = TITLE
RL = "'Review log'!"
rng_ = lambda c: f"{RL}${col[c]}$2:${col[c]}${n_log}"
types = ["series_analysis", "logic_puzzle", "claim_check", "summarise_chunk"]
hdr = ["task type", "answers EN", "pass EN", "answers FR", "pass FR"]
for j, h in enumerate(hdr, 1):
    c = ws.cell(3, j, h); c.fill = HEAD; c.font = BOLD
for i, tname in enumerate(types + ["all"], 4):
    ws.cell(i, 1, tname)
    for k, lang in enumerate(["en", "fr"]):
        crit = f',{rng_("task_type")},"{tname}"' if tname != "all" else ""
        n = f'COUNTIFS({rng_("language")},"{lang}"{crit})'
        p = f'COUNTIFS({rng_("language")},"{lang}",{rng_("consensus_verdict")},"correct"{crit})'
        ws.cell(i, 2 + 2 * k, f"={n}")
        ws.cell(i, 3 + 2 * k, f"=IFERROR({p}/{n},0)").number_format = "0%"
ws.cell(10, 1, "Same, by item difficulty (the French gap disappears at equal difficulty)").font = BOLD
for j, h in enumerate(["difficulty", "answers EN", "pass EN", "answers FR", "pass FR"], 1):
    c = ws.cell(11, j, h); c.fill = HEAD; c.font = BOLD
for i, d in enumerate([1, 2, 3], 12):
    ws.cell(i, 1, d)
    for k, lang in enumerate(["en", "fr"]):
        n = f'COUNTIFS({rng_("language")},"{lang}",{rng_("difficulty")},{d})'
        p = f'COUNTIFS({rng_("language")},"{lang}",{rng_("difficulty")},{d},{rng_("consensus_verdict")},"correct")'
        ws.cell(i, 2 + 2 * k, f"={n}")
        ws.cell(i, 3 + 2 * k, f"=IFERROR({p}/{n},0)").number_format = "0%"
ws.cell(17, 1, "Error codes (consensus, failed answers)").font = BOLD
for j, h in enumerate(["code", "EN", "FR"], 1):
    c = ws.cell(18, j, h); c.fill = HEAD; c.font = BOLD
for i, (code, *_) in enumerate(TAXONOMY, 19):
    ws.cell(i, 1, code)
    ws.cell(i, 2, f'=COUNTIFS({rng_("consensus_code")},"{code}",{rng_("language")},"en")')
    ws.cell(i, 3, f'=COUNTIFS({rng_("consensus_code")},"{code}",{rng_("language")},"fr")')
for c_, wdt in zip("ABCDE", [22, 12, 10, 12, 10]):
    ws.column_dimensions[c_].width = wdt
ch = BarChart(); ch.type = "col"; ch.title = "Pass rate by task type (SIMULATED)"; ch.y_axis.number_format = "0%"
for cidx in (3, 5):
    ch.add_data(Reference(ws, min_col=cidx, min_row=3, max_row=7), titles_from_data=True)
ch.set_categories(Reference(ws, min_col=1, min_row=4, max_row=7)); ch.height, ch.width = 7.5, 14
ws.add_chart(ch, "G3")
ch = BarChart(); ch.type = "col"; ch.title = "Pass rate by difficulty (SIMULATED)"; ch.y_axis.number_format = "0%"
for cidx in (3, 5):
    ch.add_data(Reference(ws, min_col=cidx, min_row=11, max_row=14), titles_from_data=True)
ch.set_categories(Reference(ws, min_col=1, min_row=12, max_row=14)); ch.height, ch.width = 7.5, 14
ws.add_chart(ch, "G19")
ch = BarChart(); ch.type = "bar"; ch.stacked = True; ch.grouping = "stacked"; ch.overlap = 100
ch.title = "Error codes, EN vs FR (SIMULATED)"
ch.add_data(Reference(ws, min_col=2, max_col=3, min_row=18, max_row=18 + len(TAXONOMY)), titles_from_data=True)
ch.set_categories(Reference(ws, min_col=1, min_row=19, max_row=18 + len(TAXONOMY))); ch.height, ch.width = 9, 14
ws.add_chart(ch, "G35")
ws.cell(34, 1, FOOT).font = Font(italic=True, color="7A756B")

wb.properties.creator = ""; wb.properties.lastModifiedBy = ""; wb.properties.title = ""
wb.save(OUT)

# ---------------- gold_set.jsonl : one line per (task, language)
with open(os.path.join("eval", "gold_set.jsonl"), "w", encoding="utf-8") as f:
    for _, t in tasks.iterrows():
        for lang in ("en", "fr"):
            f.write(json.dumps({"id": f"{t.task_id}-{lang}", "task_id": t.task_id, "language": lang, "task_type": t.type,
                                "subtype": t.subtype, "difficulty": int(t[f"difficulty_{lang}"]),
                                "prompt": t[f"prompt_{lang}"], "reference_answer": t[f"ref_{lang}"],
                                "reference_explanation": t[f"expl_{lang}"], "source": t.source,
                                "series_code": None if pd.isna(t.series_code) else t.series_code,
                                "data_status": t.data_status, "verification": t.check}, ensure_ascii=False) + "\n")
print(f"saved {OUT} ({len(wb.sheetnames)} tabs: {', '.join(wb.sheetnames)}) and eval/gold_set.jsonl ({2 * len(tasks)} lines)")
