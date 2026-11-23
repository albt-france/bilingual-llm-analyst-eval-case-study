"""Generate 30 route-order puzzles and prove each has exactly one solution (brute force over all orders).

A courier visits n stops once each. Rules are drawn from a hidden order, added until only one order fits,
then pruned to a minimal set (removing any rule leaves several orders). Minimality gives, for free, a
"near miss": an order that breaks exactly one rule, used as the simulated model's plausible wrong answer.
    python src/puzzle_solver.py   ->  data/processed/tasks_puzzles.csv
"""
import json
from itertools import permutations

import numpy as np
import pandas as pd

from common import PROC

STOPS = [("Harbour", "Port"), ("Market", "Marché"), ("Old Town", "Vieille-Ville"), ("Station", "Gare"),
         ("Hillside", "Colline"), ("Riverside", "Quais"), ("University", "Université"), ("Mill", "Moulin")]
ORD_EN = ["first", "second", "third", "fourth", "fifth", "sixth"]
ORD_FR = ["premier", "deuxième", "troisième", "quatrième", "cinquième", "sixième"]


def holds(rule, order):
    pos = {s: i for i, s in enumerate(order)}
    t, a, b = rule
    if t == "before":
        return pos[a] < pos[b]
    if t == "imm":
        return pos[a] == pos[b] + 1
    if t == "notadj":
        return abs(pos[a] - pos[b]) != 1
    if t == "gap":
        return abs(pos[a] - pos[b]) == 2
    if t == "pos":
        return pos[a] == b
    if t == "notpos":
        return pos[a] != b
    raise ValueError(t)


def solutions(n, rules):
    return [p for p in permutations(range(n)) if all(holds(r, p) for r in rules)]


def violated(puzzle, order_names):
    """Rules (as English text) broken by a proposed order of stop names. Used to grade model answers."""
    names = [STOPS[i][0] for i in range(puzzle["n"])]
    order = [names.index(x) for x in order_names]
    return [text(r, puzzle["n"], "en") for r in puzzle["rules"] if not holds(tuple(r), order)]


def text(rule, n, lang):
    t, a, b = rule
    A = STOPS[a][0 if lang == "en" else 1]
    B = STOPS[b][0 if lang == "en" else 1] if t in ("before", "imm", "notadj", "gap") else None
    if lang == "en":
        o = "last" if t in ("pos", "notpos") and b == n - 1 else "second-to-last" if t in ("pos", "notpos") and b == n - 2 \
            else ORD_EN[b] if t in ("pos", "notpos") else ""
        return {"before": f"{A} comes before {B} (not necessarily just before).",
                "imm": f"{A} comes immediately after {B}.", "notadj": f"{A} and {B} are not consecutive stops.",
                "gap": f"Exactly one stop separates {A} and {B}.", "pos": f"{A} is the {o} stop.",
                "notpos": f"{A} is not the {o} stop."}[t]
    o = "dernier" if t in ("pos", "notpos") and b == n - 1 else "avant-dernier" if t in ("pos", "notpos") and b == n - 2 \
        else ORD_FR[b] if t in ("pos", "notpos") else ""
    return {"before": f"L'arrêt {A} vient avant l'arrêt {B} (pas forcément juste avant).",
            "imm": f"L'arrêt {A} vient juste après l'arrêt {B}.", "notadj": f"Les arrêts {A} et {B} ne se suivent pas.",
            "gap": f"Un seul arrêt sépare {A} et {B}.", "pos": f"{A} est le {o} arrêt.",
            "notpos": f"{A} n'est pas le {o} arrêt."}[t]


def random_rule(rng, target):
    n = len(target)
    pos = {s: i for i, s in enumerate(target)}
    t = rng.choice(["before", "before", "imm", "notadj", "gap", "pos", "notpos"], p=[.2, .1, .2, .15, .15, .1, .1])
    a, b = (int(x) for x in rng.choice(n, 2, replace=False))
    if t == "before":
        return ("before", a, b) if pos[a] < pos[b] else ("before", b, a)
    if t == "imm":
        i = int(rng.integers(1, n))
        return ("imm", target[i], target[i - 1])
    if t == "gap":
        i = int(rng.integers(0, n - 2))
        return ("gap", target[i], target[i + 2])
    if t == "notadj":
        return ("notadj", a, b) if abs(pos[a] - pos[b]) != 1 else None
    if t == "pos":
        return ("pos", a, pos[a])
    k = int(rng.integers(0, n))
    return ("notpos", a, k) if pos[a] != k else None


def make(rng, n):
    while True:
        target = tuple(int(x) for x in rng.permutation(n))
        rules = []
        while len(solutions(n, rules)) > 1 and len(rules) < 12:
            r = random_rule(rng, target)
            if r and r not in rules:
                rules.append(r)
        if len(solutions(n, rules)) != 1:
            continue
        for r in list(rules):  # prune to a minimal set
            rest = [x for x in rules if x != r]
            if len(solutions(n, rest)) == 1:
                rules = rest
        npos = sum(r[0] == "pos" for r in rules)
        if npos <= 1 and len(rules) >= n - 1:
            assert solutions(n, rules) == [target]
            return target, rules


def explanation(n, rules, sol, lang):
    """Reproducible elimination chain: apply rules from most to least restrictive, count orders left."""
    left = list(permutations(range(n)))
    order = sorted(rules, key=lambda r: sum(holds(r, p) for p in left))
    steps = [f"{len(left)} possible orders" if lang == "en" else f"{len(left)} ordres possibles"]
    for r in order:
        left = [p for p in left if holds(r, p)]
        steps.append(f"'{text(r, n, lang)}' -> {len(left)}")
    names = " > ".join(STOPS[i][0 if lang == "en" else 1] for i in sol)
    if lang == "en":
        return ("Apply the most restrictive rules first and count the orders still possible: " + "; ".join(steps)
                + f". Only {names} remains; checking it against every rule confirms it.")
    return ("Appliquer d'abord les règles les plus restrictives et compter les ordres encore possibles : " + " ; ".join(steps)
            + f". Seul {names} reste ; le vérifier contre chaque règle le confirme.")


def main():
    rng = np.random.default_rng(42)
    rows = []
    for n, diff in [(4, 1)] * 10 + [(5, 2)] * 10 + [(6, 3)] * 10:
        sol, rules = make(rng, n)
        # near miss: breaks exactly one rule
        miss = None
        for p in permutations(range(n)):
            broken = [r for r in rules if not holds(r, p)]
            if len(broken) == 1:
                miss, broke = p, broken[0]
                break
        nm = lambda o, l: " > ".join(STOPS[i][0 if l == "en" else 1] for i in o)
        stops_en = ", ".join(STOPS[i][0] for i in range(n))
        stops_fr = ", ".join(STOPS[i][1] for i in range(n))
        p_en = (f"A courier makes one round through {n} neighbourhood stops ({stops_en}), visiting each exactly once. Rules: "
                + " ".join(f"({k + 1}) {text(r, n, 'en')}" for k, r in enumerate(rules)) + " In what order are the stops visited?")
        p_fr = (f"Un livreur fait une tournée unique par {n} arrêts de quartier ({stops_fr}), chacun desservi une seule fois. Règles : "
                + " ".join(f"({k + 1}) {text(r, n, 'fr')}" for k, r in enumerate(rules)) + " Dans quel ordre les arrêts sont-ils desservis ?")
        ex_en, ex_fr = explanation(n, rules, sol, "en"), explanation(n, rules, sol, "fr")
        var = {"correct": {"en": [nm(sol, "en"), ex_en], "fr": [nm(sol, "fr"), ex_fr]},
               "CONSTRAINT_IGNORED": {"en": [nm(miss, "en"), "This order satisfies all the rules."],
                                      "fr": [nm(miss, "fr"), "Cet ordre respecte toutes les règles."]},
               "UNJUSTIFIED_STEP": {"en": [nm(sol, "en"), "The order follows directly from the rules."],
                                    "fr": [nm(sol, "fr"), "L'ordre découle directement des règles."]}}
        trap = any(r[0] in ("pos", "notpos") and r[2] == n - 2 for r in rules)  # 'avant-dernier' wording in French
        if trap:
            r = next(r for r in rules if r[0] in ("pos", "notpos") and r[2] == n - 2)
            wrong = list(sol)
            i, j = wrong.index(r[1]), n - 1
            wrong[i], wrong[j] = wrong[j], wrong[i]
            var["FR_TERM"] = {"fr": [nm(wrong, "fr"), "J'ai lu « avant-dernier » comme « dernier »."]}
        puzzle = {"n": n, "rules": [list(r) for r in rules], "solution": list(sol)}
        rows.append(dict(type="logic_puzzle", subtype=f"route_{n}_stops", difficulty=diff,
                         source="Generated puzzle, solution proven unique by brute force (src/puzzle_solver.py)",
                         series_code="", data_status="final", prompt_en=p_en, prompt_fr=p_fr,
                         ref_en=nm(sol, "en"), ref_fr=nm(sol, "fr"), expl_en=ex_en, expl_fr=ex_fr,
                         check=f"unique_solutions=1; rules={len(rules)}; near_miss_breaks='{text(broke, n, 'en')}'",
                         variants=json.dumps(var, ensure_ascii=False), fr_trap=trap,
                         puzzle=json.dumps(puzzle)))
    df = pd.DataFrame(rows)
    # independent re-check of every puzzle before writing
    for pz in df.puzzle.map(json.loads):
        assert solutions(pz["n"], [tuple(r) for r in pz["rules"]]) == [tuple(pz["solution"])]
    df.to_csv(PROC / "tasks_puzzles.csv", index=False, encoding="utf-8")
    nr = df.puzzle.map(lambda x: len(json.loads(x)["rules"]))
    print(f"{len(df)} puzzles, all unique; rules per puzzle {nr.min()}-{nr.max()} (mean {nr.mean():.1f}); "
          f"French 'avant-dernier' wording in {int(df.fr_trap.sum())}")


if __name__ == "__main__":
    main()
