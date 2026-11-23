"""SIMULATED part: 240 answers of a fictional model (120 tasks x EN/FR) and 3 simulated reviewers, seed 42.

No real language model is called. Answers are picked from the variants built with each task (correct answer or a
typical error computed from the same numbers). Outcome depends on item difficulty only; French items do not fail
more often at equal difficulty, but French versions were rated harder more often (composition effect).
Reviewers grade every answer twice: with guidelines v1, then v2 (clearer rules for the grey zones).
    python src/simulate_model.py
Writes data/processed/{tasks,model_answers,reviews}.csv and the answer key data/_hidden_truth*.csv (never published).
"""
import json

import numpy as np
import pandas as pd

from common import PROC, ROOT

rng = np.random.default_rng(42)
P_CORRECT = {1: 0.90, 2: 0.60, 3: 0.30}
SEVERITY = {"WRONG_WINDOW": "incorrect", "ARITHMETIC": "incorrect", "CONSTRAINT_IGNORED": "incorrect",
            "STALE_SOURCE": "incorrect", "HALLUCINATED_DETAIL": "incorrect", "FR_DECIMAL": "incorrect",
            "FR_BILLION": "incorrect", "FR_TERM": "incorrect", "PROVISIONAL_AS_FINAL": "partially_correct",
            "PCT_VS_POINTS": "partially_correct", "NUTS_LABEL": "partially_correct",
            "UNJUSTIFIED_STEP": "partially_correct", "MISSED_BLOCK": "partially_correct"}
EVENT = {"WRONG_WINDOW": 1, "PCT_VS_POINTS": 2, "CONSTRAINT_IGNORED": 3, "STALE_SOURCE": 4, "FR_DECIMAL": 5,
         "FR_BILLION": 5, "FR_TERM": 5, "PROVISIONAL_AS_FINAL": 6, "NUTS_LABEL": 7}
GREY = {"PROVISIONAL_AS_FINAL", "PCT_VS_POINTS", "NUTS_LABEL", "UNJUSTIFIED_STEP", "MISSED_BLOCK"}
CONFUSE = {"WRONG_WINDOW": "ARITHMETIC", "STALE_SOURCE": "HALLUCINATED_DETAIL", "FR_DECIMAL": "ARITHMETIC",
           "FR_BILLION": "ARITHMETIC", "FR_TERM": "HALLUCINATED_DETAIL", "PCT_VS_POINTS": "ARITHMETIC",
           "PROVISIONAL_AS_FINAL": "STALE_SOURCE", "NUTS_LABEL": "HALLUCINATED_DETAIL", "CONSTRAINT_IGNORED": "ARITHMETIC",
           "UNJUSTIFIED_STEP": "MISSED_BLOCK", "MISSED_BLOCK": "HALLUCINATED_DETAIL", "ARITHMETIC": "WRONG_WINDOW",
           "HALLUCINATED_DETAIL": "ARITHMETIC"}
COMMENT = {
    "": "Matches the reference; explanation complete.",
    "WRONG_WINDOW": "Growth measured from a single, atypical month; compare 3-month averages, full years or the same month.",
    "ARITHMETIC": "Calculation or reading error; recompute from the source values.",
    "CONSTRAINT_IGNORED": "Proposed order breaks one of the stated rules; check every rule before answering.",
    "STALE_SOURCE": "Figure comes from a stopped series or frozen dataset; cite the current series and its date.",
    "HALLUCINATED_DETAIL": "Adds a fact or location that is not in the source.",
    "FR_DECIMAL": "French decimal comma misread (in French, 11,035 means 11.035, not 11,035).",
    "FR_BILLION": "'billion' in French means 10^12; 10^9 is 'milliard'.",
    "FR_TERM": "French term confused (trimestre = quarter, semestre = half-year; avant-dernier = second-to-last).",
    "PROVISIONAL_AS_FINAL": "Right number, but the value is flagged provisional/estimated and is presented as final.",
    "PCT_VS_POINTS": "Change between two rates must be in percentage points, not %.",
    "NUTS_LABEL": "Confuses a NUTS 2 statistical region with a current administrative region.",
    "UNJUSTIFIED_STEP": "Right answer, but the explanation does not show how the rules lead to it.",
    "MISSED_BLOCK": "Incomplete: a block or item from the source is missing.",
}
VERDICTS = ["incorrect", "partially_correct", "correct"]


def build_tasks():
    d = pd.read_csv(PROC / "tasks_data.csv")
    p = pd.read_csv(PROC / "tasks_puzzles.csv")
    order = {"series_analysis": 0, "logic_puzzle": 1, "claim_check": 2, "summarise_chunk": 3}
    t = pd.concat([d, p], ignore_index=True)
    t["o"] = t.type.map(order)
    t = t.sort_values("o", kind="stable").drop(columns="o").reset_index(drop=True)
    t.insert(0, "task_id", [f"T{i + 1:03d}" for i in range(len(t))])
    # Item-level difficulty: the writer rated French versions harder more often (French-specific traps, longer phrasing)
    bump = np.where(t.fr_trap, rng.random(len(t)) < 0.9, rng.random(len(t)) < 0.3)
    t["difficulty_en"] = t.difficulty
    t["difficulty_fr"] = np.minimum(3, t.difficulty + bump.astype(int))
    return t


def answers(t):
    items = []
    for _, r in t.iterrows():
        for lang in ("en", "fr"):
            items.append({"task_id": r.task_id, "language": lang, "difficulty": r[f"difficulty_{lang}"],
                          "task_type": r.type, "variants": json.loads(r.variants)})
    a = pd.DataFrame(items)
    # Exact rates per (language, difficulty) stratum, so that language has no effect at equal difficulty
    a["is_correct"] = False
    for (lang, dif), g in a.groupby(["language", "difficulty"]):
        k = int(round(P_CORRECT[dif] * len(g)))
        a.loc[rng.choice(g.index, k, replace=False), "is_correct"] = True
    avail_n = pd.Series([c for v in a.variants for c in v if c != "correct"]).value_counts()
    codes, rows = [], []
    for i, r in a.iterrows():
        v = r.variants
        if r.is_correct:
            code = ""
        else:
            avail = [c for c in v if c != "correct" and r.language in v[c]]
            fr = [c for c in avail if c.startswith("FR_")]
            ev = [c for c in avail if c in EVENT and not c.startswith("FR_")]
            if fr and rng.random() < 0.7:
                code = str(rng.choice(fr))
            elif ev and rng.random() < 0.75:  # rarer error types get more weight so each event is visible
                w = np.array([1 / avail_n[c] for c in ev])
                code = str(rng.choice(ev, p=w / w.sum()))
            else:
                rest = [c for c in avail if not c.startswith("FR_")] or avail
                code = str(rng.choice(rest))
        ans, expl = v["correct" if code == "" else code][r.language]
        codes.append(code)
        rows.append((ans, expl))
    a["planted_code"] = codes
    a["answer"] = [x for x, _ in rows]
    a["explanation"] = [y for _, y in rows]
    a["true_verdict"] = [SEVERITY.get(c, "correct") if c else "correct" for c in codes]
    a.insert(0, "answer_id", [f"A{i + 1:03d}" for i in range(len(a))])
    a["n_words"] = (a.answer + " " + a.explanation).str.split().str.len()
    return a.drop(columns="variants")


def review(a):
    rows = []
    med = {"series_analysis": 300, "logic_puzzle": 240, "claim_check": 360, "summarise_chunk": 280}
    for rnd in ("v1", "v2"):
        for _, r in a.iterrows():
            tv, tc = r.true_verdict, r.planted_code
            for rv in ("R1", "R2", "R3"):
                u = rng.random()
                if rnd == "v1" and tc in GREY:  # no shared rule yet: strict and lenient reviewers diverge
                    v = {"R1": "incorrect" if u < .5 else tv, "R2": tv if u < .7 else ("correct" if u < .85 else "incorrect"),
                         "R3": "correct" if u < .5 else tv}[rv]
                elif rnd == "v1" and tc == "STALE_SOURCE" and rv != "R1" and u < .45:
                    v = "correct"  # the number looks right; series status not checked
                elif rnd == "v1" and tc.startswith("FR_") and rv == "R3" and u < .4:
                    v = "correct"  # French formats not checked
                else:
                    err = (.10 if tc in GREY else .04) if rnd == "v2" else .07
                    if u < err:
                        i = VERDICTS.index(tv)
                        v = VERDICTS[i - 1] if i == 2 else VERDICTS[i + 1] if i == 0 else VERDICTS[int(rng.choice([0, 2]))]
                    else:
                        v = tv
                if v == "correct":
                    code = ""
                elif tc and rng.random() < (0.92 if rnd == "v2" else 0.70):
                    code = tc
                else:
                    code = CONFUSE.get(tc, "ARITHMETIC") if tc else "ARITHMETIC"
                sec = med[r.task_type] * (1.4 if r.difficulty == 3 else 1.0) * (0.85 if rnd == "v2" else 1.0) \
                    * float(rng.lognormal(0, 0.35))
                rows.append({"answer_id": r.answer_id, "reviewer": rv, "guidelines": rnd, "verdict": v,
                             "error_code": code, "comment": COMMENT[code] if v != "correct" else COMMENT[""],
                             "seconds_spent": int(round(sec))})
    return pd.DataFrame(rows)


def main():
    t = build_tasks()
    a = answers(t)
    rv = review(a)
    keep = ["task_id", "type", "subtype", "difficulty_en", "difficulty_fr", "source", "series_code", "data_status",
            "prompt_en", "prompt_fr", "ref_en", "ref_fr", "expl_en", "expl_fr", "check", "puzzle", "fr_trap"]
    t[keep].to_csv(PROC / "tasks.csv", index=False, encoding="utf-8")
    t[["task_id", "variants"]].to_csv(PROC / "task_variants.csv", index=False, encoding="utf-8")
    pub = ["answer_id", "task_id", "language", "difficulty", "task_type", "answer", "explanation", "n_words"]
    a[pub].to_csv(PROC / "model_answers.csv", index=False, encoding="utf-8")
    rv.to_csv(PROC / "reviews.csv", index=False, encoding="utf-8")
    # answer key (removed before publishing)
    a[["answer_id", "task_id", "language", "difficulty", "planted_code", "true_verdict"]].assign(
        event_id=a.planted_code.map(EVENT)).to_csv(ROOT / "data" / "_hidden_truth_items.csv", index=False)
    ev = [(1, "Wrong comparison window (growth from one atypical month)", "issue"),
          (2, "Percent instead of percentage points", "issue"),
          (3, "Puzzle answer breaks one stated rule", "issue"),
          (4, "Claim confirmed with a stopped series / frozen dataset", "issue"),
          (5, "French-specific errors: decimal comma, billion vs milliard, trimestre vs semestre, avant-dernier", "issue"),
          (6, "REAL data issue: latest Eurostat values flagged p/e treated as final", "issue"),
          (7, "REAL data issue: NUTS 2 labels confused with current regions (old labels, encoding)", "issue"),
          (8, "FALSE SIGNAL: lower pass rate in French is a composition effect (harder French items)", "false_signal")]
    key = pd.DataFrame(ev, columns=["event_id", "description", "kind"])
    key["n_answers"] = key.event_id.map(a.planted_code.map(EVENT).value_counts()).fillna(0).astype(int)
    key.to_csv(ROOT / "data" / "_hidden_truth.csv", index=False)
    raw = a.groupby("language").is_correct.mean()
    print(f"tasks {len(t)} | answers {len(a)} | reviews {len(rv)}")
    print("pass rate (truth) EN {:.1%} FR {:.1%}".format(raw["en"], raw["fr"]))
    print("by difficulty:", a.groupby(["difficulty", "language"]).is_correct.mean().unstack().round(3).to_dict())
    print("difficulty mix:", a.groupby("language").difficulty.value_counts().unstack().to_dict("index"))
    print("events:", key.set_index("event_id").n_answers.to_dict())


if __name__ == "__main__":
    main()
