"""Build the data-based gold tasks from the public extracts: 40 series analyses, 25 claim checks, 25 text tasks.

Every reference answer is computed here from data/public/*.csv (no answer is typed by hand except the five lead
summaries, whose figures are checked against the source text). Each task also carries the answer variants used
by the simulated model (correct + typical errors), so that the errors are built from the same numbers.
    python src/build_series_tasks.py   ->  data/processed/tasks_data.csv
"""
import json
import re

import numpy as np
import pandas as pd

from common import PUB, PROC, NUTS, num, pct, pts, ym, cname, cshort, join

rng = np.random.default_rng(42)
FLAG = {"p": "provisional", "e": "estimated"}
FLAG_FR = {"p": "provisoire", "e": "estimée"}


def pivot(f):
    d = pd.read_csv(PUB / f, dtype={"time": str})
    return d.pivot(index="time", columns="geo", values="value"), \
        d.pivot(index="time", columns="geo", values="status").fillna(""), d


R, RS, rdf = pivot("eurostat_retail.csv")
N, _, ndf = pivot("eurostat_nights.csv")
H, _, hdf = pivot("eurostat_hicp.csv")
HO, _, hodf = pivot("eurostat_hicp_stopped.csv")
U, _, udf = pivot("eurostat_unemployment.csv")
INS = pd.read_csv(PUB / "insee_series.csv", dtype={"idbank": str})
EXTR = rdf.extracted.iloc[0]
UPD = {"sts_trtu_m": rdf.dataset_updated.iloc[0], "tour_occ_nin2m": ndf.dataset_updated.iloc[0],
       "prc_hicp_minr": hdf.dataset_updated.iloc[0], "prc_hicp_manr": hodf.dataset_updated.iloc[0],
       "une_rt_m": udf.dataset_updated.iloc[0]}
TASKS = []


def sh(t, k):
    return str(pd.Period(t, "M") + k)


def V(en_a, en_e, fr_a, fr_e):
    return {"en": [en_a, en_e], "fr": [fr_a, fr_e]}


def add(**kw):
    kw.setdefault("fr_trap", False)
    kw["variants"] = {k: v for k, v in kw["variants"].items() if v is not None}
    kw["variants"] = json.dumps(kw["variants"], ensure_ascii=False)
    TASKS.append(kw)


def src(code):
    return f"Eurostat {code} (updated {UPD[code]}, extracted {EXTR})"


def status_note(cells, lang):
    """cells: list of (geo, time) used; returns a sentence on provisional/estimated flags, or ''."""
    fl = sorted({(g, t, RS.at[t, g]) for g, t in cells if RS.at[t, g]})
    if not fl:
        return ""
    by = {}
    for g, t, s in fl:
        by.setdefault(s, set()).add(g)
    if lang == "en":
        parts = [f"{FLAG[s]} ('{s}') for {join([cname(g, 'en') for g in sorted(gs)], 'en')}" for s, gs in by.items()]
        return "Data status: values used are flagged " + "; ".join(parts) + ", so the result may be revised."
    parts = [f"« {FLAG_FR[s]} » ('{s}') pour {join([cname(g, 'fr') for g in sorted(gs)], 'fr')}" for s, gs in by.items()]
    return "Statut des données : valeurs signalées " + " ; ".join(parts) + ", donc susceptibles d'être révisées."


# ---------------------------------------------------------------- S1: which country grew the most? (window choice)
def s1():
    starts = ["2022-01", "2022-04", "2022-07", "2023-01", "2023-04", "2023-10", "2024-01", "2024-07", "2025-01"]
    ends = ["2025-06", "2025-12", "2026-03", "2026-06", "2026-09"]
    geos = [g for g in R.columns]
    diff, same, used = [], [], set()
    for _ in range(6000):
        s, e = str(rng.choice(starts)), str(rng.choice(ends))
        if (pd.Period(e, "M") - pd.Period(s, "M")).n < 12 or (s, e) in used:
            continue
        pool = [g for g in geos if not (g == "SE" and s < "2023-01")]
        cs = sorted(rng.choice(pool, 4, replace=False).tolist())
        a0 = {c: R.loc[[s, sh(s, 1), sh(s, 2)], c].mean() for c in cs}
        a1 = {c: R.loc[[sh(e, -2), sh(e, -1), e], c].mean() for c in cs}
        rob = {c: (a1[c] / a0[c] - 1) * 100 for c in cs}
        nai = {c: (R.at[e, c] / R.at[s, c] - 1) * 100 for c in cs}
        rw, nw = max(rob, key=rob.get), max(nai, key=nai.get)
        mr = sorted(rob.values())[-1] - sorted(rob.values())[-2]
        mn = sorted(nai.values())[-1] - sorted(nai.values())[-2]
        if rw != nw and mr > 0.3 and mn > 0.3 and len(diff) < 8:
            diff.append((s, e, cs, a0, a1, rob, nai, rw, nw)); used.add((s, e))
        elif rw == nw and mr > 1.0 and len(same) < 2:
            same.append((s, e, cs, a0, a1, rob, nai, rw, nw)); used.add((s, e))
        if len(diff) == 8 and len(same) == 2:
            break
    for s, e, cs, a0, a1, rob, nai, rw, nw in diff + same:
        rank = sorted(cs, key=rob.get, reverse=True)
        cells = [(c, t) for c in cs for t in (sh(e, -2), sh(e, -1), e)]
        p_en = (f"Using Eurostat's monthly retail trade volume index (seasonally and calendar adjusted, 2021 = 100), "
                f"which of these countries grew the most between {ym(s, 'en')} and {ym(e, 'en')}: "
                f"{join([cshort(c, 'en') for c in cs], 'en')}? Explain your choice of period.")
        p_fr = (f"D'après l'indice mensuel du volume des ventes du commerce de détail d'Eurostat (CVS-CJO, base 2021 = 100), "
                f"lequel de ces pays a le plus progressé entre {ym(s, 'fr')} et {ym(e, 'fr')} : "
                f"{join([cshort(c, 'fr') for c in cs], 'fr')} ? Justifie le choix de la période.")
        rk_en = "; ".join(f"{cshort(c, 'en')} {pct(rob[c], 'en')}" for c in rank)
        rk_fr = " ; ".join(f"{cshort(c, 'fr')} {pct(rob[c], 'fr')}" for c in rank)
        ref_en = f"{cshort(rw, 'en')} grew the most: {pct(rob[rw], 'en')} (3-month averages). Ranking: {rk_en}."
        ref_fr = f"Le pays qui a le plus progressé est {cname(rw, 'fr')} : {pct(rob[rw], 'fr')} (moyennes sur 3 mois). Classement : {rk_fr}."
        st_en, st_fr = status_note(cells, "en"), status_note(cells, "fr")
        trap_en = (f"Endpoint-to-endpoint growth would put {cshort(nw, 'en')} first ({pct(nai[nw], 'en')}) because its "
                   f"{ym(s, 'en')} value ({num(R.at[s, nw], 'en')}) differs from its 3-month average "
                   f"({num(a0[nw], 'en')}): one atypical month drives the ranking."
                   if rw != nw else "Endpoint-to-endpoint growth gives the same winner, so the conclusion is robust.")
        trap_fr = (f"Une comparaison point à point placerait {cname(nw, 'fr')} en tête ({pct(nai[nw], 'fr')}) car sa valeur "
                   f"de {ym(s, 'fr')} ({num(R.at[s, nw], 'fr')}) s'écarte de sa moyenne sur 3 mois ({num(a0[nw], 'fr')}) : "
                   f"un seul mois atypique fait le classement."
                   if rw != nw else "La comparaison point à point donne le même gagnant : la conclusion est robuste.")
        ex_en = (f"1) Period: a single month is noisy, so compare the average of {ym(s, 'en')}-{ym(sh(s, 2), 'en')} with the "
                 f"average of {ym(sh(e, -2), 'en')}-{ym(e, 'en')}. 2) Compute: {cshort(rw, 'en')} {num(a0[rw], 'en')} -> "
                 f"{num(a1[rw], 'en')}, i.e. {pct(rob[rw], 'en')}. 3) Trap: {trap_en} {st_en}").strip()
        ex_fr = (f"1) Période : un mois isolé est bruité, on compare la moyenne {ym(s, 'fr')}-{ym(sh(s, 2), 'fr')} à la moyenne "
                 f"{ym(sh(e, -2), 'fr')}-{ym(e, 'fr')}. 2) Calcul : {cshort(rw, 'fr')} {num(a0[rw], 'fr')} -> "
                 f"{num(a1[rw], 'fr')}, soit {pct(rob[rw], 'fr')}. 3) Piège : {trap_fr} {st_fr}").strip()
        var = {"correct": V(ref_en, ex_en, ref_fr, ex_fr)}
        if rw != nw:
            var["WRONG_WINDOW"] = V(
                f"{cshort(nw, 'en')} grew the most ({pct(nai[nw], 'en')}).",
                f"I compared the index in {ym(s, 'en')} with the index in {ym(e, 'en')} for each country.",
                f"Le pays qui a le plus progressé est {cname(nw, 'fr')} ({pct(nai[nw], 'fr')}).",
                f"J'ai comparé l'indice de {ym(s, 'fr')} à celui de {ym(e, 'fr')} pour chaque pays.")
        if st_en:
            var["PROVISIONAL_AS_FINAL"] = V(ref_en, ex_en.split(" Data status")[0] + " These are final official figures.",
                                            ref_fr, ex_fr.split(" Statut")[0] + " Ce sont des chiffres officiels définitifs.")
        r2 = rank[1]
        var["ARITHMETIC"] = V(f"{cshort(r2, 'en')} grew the most: {pct(rob[rw] + 0.4, 'en')}.",
                              f"3-month averages: {cshort(r2, 'en')} {num(a0[r2], 'en')} -> {num(a1[rw] + 1, 'en')}.",
                              f"Le pays qui a le plus progressé est {cname(r2, 'fr')} : {pct(rob[rw] + 0.4, 'fr')}.",
                              f"Moyennes sur 3 mois : {cshort(r2, 'fr')} {num(a0[r2], 'fr')} -> {num(a1[rw] + 1, 'fr')}.")
        add(type="series_analysis", subtype="growth_window", difficulty=3 if rw != nw else 2, source=src("sts_trtu_m"),
            series_code="sts_trtu_m (VOL_SLS, G47, SCA, I21)", data_status="p/e flags" if st_en else "final",
            prompt_en=p_en, prompt_fr=p_fr, ref_en=ref_en, ref_fr=ref_fr, expl_en=ex_en, expl_fr=ex_fr,
            check=f"winner_3m_avg={rw}; winner_endpoint={nw}; growth={rob[rw]:.2f}", variants=var)


# ---------------------------------------------------------------- S2: nights, seasonality and an atypical first month
def s2():
    A = N.groupby(N.index.str[:4]).sum()
    spans = [(2022, 2025), (2022, 2024), (2022, 2023), (2023, 2025), (2023, 2024), (2024, 2025)]
    regs = list(N.columns)
    diff, same, used = [], [], set()
    for _ in range(6000):
        s, e = spans[rng.integers(len(spans))]
        rs = sorted(rng.choice(regs, 4, replace=False).tolist())
        key = (s, e, tuple(rs))
        if key in used:
            continue
        rob = {r: (A.at[str(e), r] / A.at[str(s), r] - 1) * 100 for r in rs}
        nai = {r: (N.at[f"{e}-01", r] / N.at[f"{s}-01", r] - 1) * 100 for r in rs}
        rw, nw = max(rob, key=rob.get), max(nai, key=nai.get)
        mr = sorted(rob.values())[-1] - sorted(rob.values())[-2]
        if rw != nw and mr > 0.5 and len(diff) < 6 and sum(1 for d in diff if d[:2] == (s, e)) < 2:
            diff.append((s, e, rs, rob, nai, rw, nw)); used.add(key)
        elif rw == nw and mr > 1.0 and len(same) < 2 and s != 2022:
            same.append((s, e, rs, rob, nai, rw, nw)); used.add(key)
        if len(diff) == 6 and len(same) == 2:
            break
    for s, e, rs, rob, nai, rw, nw in diff + same:
        nm = lambda r: NUTS[r][0]
        p_en = (f"Eurostat publishes monthly nights spent in tourist accommodation by NUTS 2 region. Which of these regions "
                f"grew the most from {s} to {e}: {join([nm(r) for r in rs], 'en')}? Say which months you compare and why.")
        p_fr = (f"Eurostat publie les nuitées mensuelles dans l'hébergement touristique par région NUTS 2. Laquelle de ces "
                f"régions a le plus progressé de {s} à {e} : {join([nm(r) for r in rs], 'fr')} ? Précise les mois comparés et pourquoi.")
        rank = sorted(rs, key=rob.get, reverse=True)
        ref_en = (f"{nm(rw)} grew the most: {pct(rob[rw], 'en')} in annual nights ({num(A.at[str(s), rw] / 1e6, 'en', 2)} M in {s} "
                  f"-> {num(A.at[str(e), rw] / 1e6, 'en', 2)} M in {e}). Ranking: "
                  + "; ".join(f"{nm(r)} {pct(rob[r], 'en')}" for r in rank) + ".")
        ref_fr = (f"La région qui a le plus progressé est {nm(rw)} : {pct(rob[rw], 'fr')} en nuitées annuelles ({num(A.at[str(s), rw] / 1e6, 'fr', 2)} M "
                  f"en {s} -> {num(A.at[str(e), rw] / 1e6, 'fr', 2)} M en {e}). Classement : "
                  + " ; ".join(f"{nm(r)} {pct(rob[r], 'fr')}" for r in rank) + ".")
        trap_en = (f"Comparing January {s} with January {e} would put {nm(nw)} first ({pct(nai[nw], 'en')}): one low-season "
                   f"month is a small, volatile base ({num(N.at[f'{s}-01', nw] / 1e6, 'en', 2)} M)"
                   + (", and January 2022 was still depressed in several regions." if s == 2022 else ".") if rw != nw else
                   "Comparing single months gives the same winner here, but full years remain the safer basis.")
        trap_fr = (f"Comparer janvier {s} à janvier {e} placerait {nm(nw)} en tête ({pct(nai[nw], 'fr')}) : un mois de basse "
                   f"saison est une base petite et volatile ({num(N.at[f'{s}-01', nw] / 1e6, 'fr', 2)} M)"
                   + (", et janvier 2022 restait déprimé dans plusieurs régions." if s == 2022 else ".") if rw != nw else
                   "Comparer des mois isolés donne ici le même gagnant, mais l'année pleine reste la base la plus sûre.")
        ex_en = (f"1) The series is not seasonally adjusted and peaks in summer, so compare full calendar years (12 months each). "
                 f"2) Annual totals: {nm(rw)} {pct(rob[rw], 'en')}. 3) Trap: {trap_en} 4) Labels are NUTS 2 statistical regions "
                 f"(e.g. Midi-Pyrénées lies within today's Occitanie administrative region), not the 2016 administrative regions.")
        ex_fr = (f"1) La série n'est pas corrigée des variations saisonnières et culmine l'été : on compare des années civiles pleines. "
                 f"2) Totaux annuels : {nm(rw)} {pct(rob[rw], 'fr')}. 3) Piège : {trap_fr} 4) Les libellés sont des régions "
                 f"statistiques NUTS 2 (ex. Midi-Pyrénées, comprise dans l'actuelle région Occitanie), pas les régions administratives de 2016.")
        var = {"correct": V(ref_en, ex_en, ref_fr, ex_fr)}
        if rw != nw:
            var["WRONG_WINDOW"] = V(f"{nm(nw)} grew the most ({pct(nai[nw], 'en')}).",
                                    f"I compared the first month, January {s}, with January {e}.",
                                    f"La région qui a le plus progressé est {nm(nw)} ({pct(nai[nw], 'fr')}).",
                                    f"J'ai comparé le premier mois, janvier {s}, à janvier {e}.")
        adm = NUTS[rw][1]
        if adm != NUTS[rw][0]:
            var["NUTS_LABEL"] = V(ref_en.replace(nm(rw), adm, 1), ex_en.split(" 4)")[0] + f" {adm} is the current region.",
                                  ref_fr.replace(nm(rw), adm, 1), ex_fr.split(" 4)")[0] + f" {adm} est la région actuelle.")
        r2 = rank[1]
        var["ARITHMETIC"] = V(f"{nm(r2)} grew the most ({pct(rob[rw] + 0.5, 'en')} in annual nights).",
                              f"Annual totals summed for {s} and {e}.",
                              f"La région qui a le plus progressé est {nm(r2)} ({pct(rob[rw] + 0.5, 'fr')} en nuitées annuelles).",
                              f"Totaux annuels additionnés pour {s} et {e}.")
        add(type="series_analysis", subtype="seasonal_growth", difficulty=3, source=src("tour_occ_nin2m"),
            series_code="tour_occ_nin2m (TOTAL, I551-I553, NR)", data_status="final", prompt_en=p_en, prompt_fr=p_fr,
            ref_en=ref_en, ref_fr=ref_fr, expl_en=ex_en, expl_fr=ex_fr,
            check=f"winner_annual={rw}; winner_january={nw}; growth={rob[rw]:.2f}", variants=var)


# ---------------------------------------------------------------- S3: year-on-year ranking for one month
def s3():
    months = ["2026-09", "2026-06", "2026-03", "2025-12", "2025-09", "2026-08"]
    for m in months:
        for _ in range(200):
            cs = sorted(rng.choice(list(R.columns), 3, replace=False).tolist())
            yoy = {c: (R.at[m, c] / R.at[sh(m, -12), c] - 1) * 100 for c in cs}
            mom = {c: (R.at[m, c] / R.at[sh(m, -1), c] - 1) * 100 for c in cs}
            ry, rm = sorted(cs, key=yoy.get, reverse=True), sorted(cs, key=mom.get, reverse=True)
            v = sorted(yoy.values())
            if ry != rm and min(v[1] - v[0], v[2] - v[1]) > 0.3:
                break
        cells = [(c, t) for c in cs for t in (m, sh(m, -12))]
        p_en = (f"Rank {join([cshort(c, 'en') for c in cs], 'en')} by the year-on-year change of their retail trade volume "
                f"in {ym(m, 'en')} (Eurostat, seasonally and calendar adjusted index).")
        p_fr = (f"Classe {join([cshort(c, 'fr') for c in cs], 'fr')} selon l'évolution sur un an du volume de leurs ventes "
                f"au détail en {ym(m, 'fr')} (Eurostat, indice CVS-CJO).")
        ref_en = "Year-on-year: " + " > ".join(f"{cshort(c, 'en')} ({pct(yoy[c], 'en')})" for c in ry) + "."
        ref_fr = "Sur un an : " + " > ".join(f"{cshort(c, 'fr')} ({pct(yoy[c], 'fr')})" for c in ry) + "."
        st_en, st_fr = status_note(cells, "en"), status_note(cells, "fr")
        ex_en = (f"1) Year-on-year means {ym(m, 'en')} versus {ym(sh(m, -12), 'en')}, not versus the previous month. "
                 f"2) Compute value/value-12 - 1 for each country. 3) The month-on-month ranking would differ "
                 f"({' > '.join(cshort(c, 'en') for c in rm)}). {st_en}").strip()
        ex_fr = (f"1) « Sur un an » signifie {ym(m, 'fr')} comparé à {ym(sh(m, -12), 'fr')}, pas au mois précédent. "
                 f"2) Calcul valeur/valeur-12 - 1 pour chaque pays. 3) Le classement d'un mois sur l'autre serait différent "
                 f"({' > '.join(cshort(c, 'fr') for c in rm)}). {st_fr}").strip()
        var = {"correct": V(ref_en, ex_en, ref_fr, ex_fr),
               "WRONG_WINDOW": V(" > ".join(f"{cshort(c, 'en')} ({pct(mom[c], 'en')})" for c in rm),
                                 f"I compared {ym(m, 'en')} with {ym(sh(m, -1), 'en')}.",
                                 " > ".join(f"{cshort(c, 'fr')} ({pct(mom[c], 'fr')})" for c in rm),
                                 f"J'ai comparé {ym(m, 'fr')} à {ym(sh(m, -1), 'fr')}.")}
        if st_en:
            var["PROVISIONAL_AS_FINAL"] = V(ref_en, ex_en.split(" Data status")[0], ref_fr, ex_fr.split(" Statut")[0])
        add(type="series_analysis", subtype="yoy_ranking", difficulty=2, source=src("sts_trtu_m"),
            series_code="sts_trtu_m (VOL_SLS, G47, SCA, I21)", data_status="p/e flags" if st_en else "final",
            prompt_en=p_en, prompt_fr=p_fr, ref_en=ref_en, ref_fr=ref_fr, expl_en=ex_en, expl_fr=ex_fr,
            check="ranking=" + ">".join(ry), variants=var)


# ---------------------------------------------------------------- S4: percentage points vs percent
def s4():
    items = [("U", "FR", "2025-10", "2026-09"), ("U", "IT", "2025-10", "2026-09"), ("U", "ES", "2024-09", "2026-09"),
             ("U", "PT", "2025-01", "2026-09"), ("H", "FR", "2025-10", "2026-10"), ("H", "IT", "2025-10", "2026-10")]
    for kind, g, t1, t2 in items:
        S = U if kind == "U" else H
        a, b = S.at[t1, g], S.at[t2, g]
        d, rel = b - a, (b / a - 1) * 100
        lab_en = "unemployment rate (Eurostat une_rt_m, seasonally adjusted)" if kind == "U" else \
            "annual HICP inflation rate (Eurostat prc_hicp_minr)"
        lab_fr = "taux de chômage (Eurostat une_rt_m, CVS)" if kind == "U" else \
            "taux d'inflation annuel IPCH (Eurostat prc_hicp_minr)"
        p_en = f"By how much did the {lab_en} of {cname(g, 'en')} change between {ym(t1, 'en')} and {ym(t2, 'en')}?"
        p_fr = f"De combien a varié le {lab_fr} de {cname(g, 'fr')} entre {ym(t1, 'fr')} et {ym(t2, 'fr')} ?"
        ref_en = (f"{pts(d, 'en')} (from {pct(a, 'en', sign=False)} to {pct(b, 'en', sign=False)}); "
                  f"in relative terms the rate itself changed by {pct(rel, 'en')}.")
        ref_fr = (f"{pts(d, 'fr')} (de {pct(a, 'fr', sign=False)} à {pct(b, 'fr', sign=False)}) ; "
                  f"en relatif, le taux lui-même a varié de {pct(rel, 'fr')}.")
        ex_en = (f"1) Both values are rates (%), so their difference is in percentage points: {num(b, 'en')} - {num(a, 'en')} = "
                 f"{num(d, 'en')}. 2) A '%' change would be relative: {num(b, 'en')}/{num(a, 'en')} - 1 = {pct(rel, 'en')}. "
                 f"3) Writing '{pct(d, 'en')}' mixes the two and understates or overstates the move.")
        ex_fr = (f"1) Les deux valeurs sont des taux (%), leur différence s'exprime en points : {num(b, 'fr')} - {num(a, 'fr')} = "
                 f"{num(d, 'fr')}. 2) Une variation en « % » serait relative : {num(b, 'fr')}/{num(a, 'fr')} - 1 = {pct(rel, 'fr')}. "
                 f"3) Écrire « {pct(d, 'fr')} » confond les deux.")
        var = {"correct": V(ref_en, ex_en, ref_fr, ex_fr),
               "PCT_VS_POINTS": V(f"It changed by {pct(d, 'en')}.", f"{num(b, 'en')} - {num(a, 'en')} = {num(d, 'en')}%.",
                                  f"Il a varié de {pct(d, 'fr')}.", f"{num(b, 'fr')} - {num(a, 'fr')} = {num(d, 'fr')} %."),
               "FR_DECIMAL": {"fr": [f"{pts(b * 10 - a, 'fr')}.",
                                     f"J'ai lu « {num(b, 'fr')} » comme {num(b * 10, 'fr', 0)} : {num(b * 10, 'fr', 0)} - {num(a, 'fr')}."]}}
        add(type="series_analysis", subtype="points_vs_percent", difficulty=2,
            source=src("une_rt_m" if kind == "U" else "prc_hicp_minr"),
            series_code="une_rt_m (SA, TOTAL, T, PC_ACT)" if kind == "U" else "prc_hicp_minr (TOTAL, RCH_A)",
            data_status="final", prompt_en=p_en, prompt_fr=p_fr, ref_en=ref_en, ref_fr=ref_fr, expl_en=ex_en,
            expl_fr=ex_fr, check=f"diff_pp={d:.2f}; rel_pct={rel:.2f}", variants=var, fr_trap=True)


# ---------------------------------------------------------------- S5: seasonality, peak month
def s5():
    y = N.loc[N.index.str.startswith("2025")]
    for r in ["FRM0", "FRJ2", "FRK2", "FR10", "FRI1"]:
        s = y[r]
        pk, lo = s.idxmax(), s.idxmin()
        ratio = s.max() / s.min()
        nm = NUTS[r][0]
        p_en = (f"In 2025, in which month did the NUTS 2 region {nm} record the most tourist nights, and how many times larger "
                f"was that month than its weakest month? (Eurostat tour_occ_nin2m)")
        p_fr = (f"En 2025, quel mois la région NUTS 2 {nm} a-t-elle enregistré le plus de nuitées touristiques, et combien de fois "
                f"ce mois était-il plus élevé que le mois le plus faible ? (Eurostat tour_occ_nin2m)")
        ref_en = (f"{ym(pk, 'en')}: {num(s.max() / 1e6, 'en', 2)} M nights, {num(ratio, 'en')} times the weakest month "
                  f"({ym(lo, 'en')}, {num(s.min() / 1e6, 'en', 2)} M).")
        ref_fr = (f"{ym(pk, 'fr')} : {num(s.max() / 1e6, 'fr', 2)} M de nuitées, soit {num(ratio, 'fr')} fois le mois le plus "
                  f"faible ({ym(lo, 'fr')}, {num(s.min() / 1e6, 'fr', 2)} M).")
        ex_en = (f"1) Take the 12 monthly values of 2025 (raw, not seasonally adjusted: seasonality is what we measure). "
                 f"2) Max = {ym(pk, 'en')}, min = {ym(lo, 'en')}. 3) Ratio = max / min = {num(ratio, 'en', 2)}, "
                 f"not a difference. 4) {nm} is a NUTS 2 statistical region.")
        ex_fr = (f"1) On prend les 12 valeurs mensuelles de 2025 (brutes : c'est la saisonnalité qu'on mesure). "
                 f"2) Max = {ym(pk, 'fr')}, min = {ym(lo, 'fr')}. 3) Rapport = max / min = {num(ratio, 'fr', 2)}, pas une "
                 f"différence. 4) {nm} est une région statistique NUTS 2.")
        var = {"correct": V(ref_en, ex_en, ref_fr, ex_fr),
               "ARITHMETIC": V(f"{ym(pk, 'en')}, {num((s.max() - s.min()) / 1e6, 'en', 2)} times larger.",
                               "I subtracted the weakest month from the peak.",
                               f"{ym(pk, 'fr')}, {num((s.max() - s.min()) / 1e6, 'fr', 2)} fois plus.",
                               "J'ai soustrait le mois le plus faible du pic.")}
        if NUTS[r][1] != nm:
            var["NUTS_LABEL"] = V(ref_en, ex_en.split(" 4)")[0] + f" {nm} is one of France's 13 regions.",
                                  ref_fr, ex_fr.split(" 4)")[0] + f" {nm} est l'une des 13 régions de France.")
        add(type="series_analysis", subtype="peak_month", difficulty=1, source=src("tour_occ_nin2m"),
            series_code="tour_occ_nin2m (TOTAL, I551-I553, NR)", data_status="final", prompt_en=p_en, prompt_fr=p_fr,
            ref_en=ref_en, ref_fr=ref_fr, expl_en=ex_en, expl_fr=ex_fr, check=f"peak={pk}; ratio={ratio:.3f}", variants=var)


# ---------------------------------------------------------------- S6: largest monthly fall
def s6():
    for g in ["DE", "FR", "PT", "SE", "IE"]:
        s = R[g].dropna()
        mom = (s / s.shift(1) - 1) * 100
        win = mom[mom.index >= "2024-01"]
        t = win.idxmin()
        t_all = mom.idxmin()
        p_en = (f"Since January 2024, in which month did {cname(g, 'en')}'s retail trade volume (Eurostat, seasonally adjusted "
                f"index) fall the most compared with the previous month?")
        p_fr = (f"Depuis janvier 2024, quel mois le volume des ventes au détail de {cname(g, 'fr')} (Eurostat, indice CVS-CJO) "
                f"a-t-il le plus baissé par rapport au mois précédent ?")
        ref_en = f"{ym(t, 'en')}: {pct(win[t], 'en')} month on month ({num(s[sh(t, -1)], 'en')} -> {num(s[t], 'en')})."
        ref_fr = f"{ym(t, 'fr')} : {pct(win[t], 'fr')} sur un mois ({num(s[sh(t, -1)], 'fr')} -> {num(s[t], 'fr')})."
        st_en, st_fr = status_note([(g, t)], "en"), status_note([(g, t)], "fr")
        ex_en = (f"1) Compute the month-on-month change for every month from January 2024. 2) The minimum is {ym(t, 'en')} "
                 f"({pct(win[t], 'en')}). {st_en}").strip()
        ex_fr = (f"1) Calculer la variation mensuelle pour chaque mois depuis janvier 2024. 2) Le minimum est {ym(t, 'fr')} "
                 f"({pct(win[t], 'fr')}). {st_fr}").strip()
        var = {"correct": V(ref_en, ex_en, ref_fr, ex_fr)}
        if t_all != t:
            var["WRONG_WINDOW"] = V(f"{ym(t_all, 'en')} ({pct(mom[t_all], 'en')}).", "I scanned the whole series from 2022.",
                                    f"{ym(t_all, 'fr')} ({pct(mom[t_all], 'fr')}).", "J'ai parcouru toute la série depuis 2022.")
        if st_en:
            var["PROVISIONAL_AS_FINAL"] = V(ref_en, ex_en.split(" Data status")[0] + " The figure is final.",
                                            ref_fr, ex_fr.split(" Statut")[0] + " Le chiffre est définitif.")
        second = win.drop(t).idxmin()
        var["ARITHMETIC"] = V(f"{ym(second, 'en')} ({pct(win[second], 'en')}).", "Largest monthly fall since 2024.",
                              f"{ym(second, 'fr')} ({pct(win[second], 'fr')}).", "Plus forte baisse mensuelle depuis 2024.")
        add(type="series_analysis", subtype="largest_fall", difficulty=1, source=src("sts_trtu_m"),
            series_code="sts_trtu_m (VOL_SLS, G47, SCA, I21)", data_status="p/e flags" if st_en else "final",
            prompt_en=p_en, prompt_fr=p_fr, ref_en=ref_en, ref_fr=ref_fr, expl_en=ex_en, expl_fr=ex_fr,
            check=f"month={t}; mom={win[t]:.2f}", variants=var)


# ---------------------------------------------------------------- claim checks
def ins(idb):
    return INS[INS.idbank == idb].set_index("period").value


def claim(sub, verdict, cl_en, cl_fr, ref_en, ref_fr, ex_en, ex_fr, source, code, wrong, diff, extra=None, trap=False,
          status="final"):
    var = {"correct": V(f"{verdict}. {ref_en}", ex_en, f"{VFR[verdict]}. {ref_fr}", ex_fr)}
    var.update(wrong)
    if extra:
        var.update(extra)
    add(type="claim_check", subtype=sub, difficulty=diff, source=source, series_code=code, data_status=status,
        prompt_en=f'Is this claim accurate? Check it against the primary source and give a verdict. Claim: "{cl_en}"',
        prompt_fr=f"Cette affirmation est-elle exacte ? Vérifie-la à la source primaire et donne un verdict. Affirmation : « {cl_fr} »",
        ref_en=f"{verdict}. {ref_en}", ref_fr=f"{VFR[verdict]}. {ref_fr}", expl_en=ex_en, expl_fr=ex_fr,
        check=f"verdict={verdict}", variants=var, fr_trap=trap)


VFR = {"TRUE": "VRAI", "FALSE": "FAUX", "MISLEADING": "TROMPEUR", "OUTDATED": "OBSOLÈTE"}


def claims():
    old, cur = ins("001763852"), ins("011814630")
    yo = (old["2025-12"] / old["2024-12"] - 1) * 100
    yc = (cur["2026-10"] / cur["2025-10"] - 1) * 100
    mo = (old["2025-12"] / old["2025-11"] - 1) * 100
    src_i = f"INSEE BDM, series 001763852 (stopped) and 011814630 (current), extracted {EXTR}"
    stale = lambda en, fr: {"STALE_SOURCE": V(f"TRUE. {en}", "The INSEE CPI series 001763852 confirms it.",
                                              f"VRAI. {fr}", "La série IPC 001763852 de l'Insee le confirme.")}
    for cl_en, cl_fr, val in [
        (f"INSEE's consumer price index shows French prices up {num(yo, 'en')}% over the latest 12 months.",
         f"L'indice des prix de l'Insee montre une hausse des prix de {num(yo, 'fr')} % sur les 12 derniers mois.", yo),
        (f"INSEE's consumer price index rose {num(mo, 'en', 2)}% in the latest month.",
         f"L'indice des prix de l'Insee a augmenté de {num(mo, 'fr', 2)} % le mois dernier.", mo),
        (f"At {num(old['2025-12'], 'en', 2)}, France's latest consumer price index is the newest official level.",
         f"À {num(old['2025-12'], 'fr', 2)}, l'indice des prix français est le dernier niveau officiel publié.", old["2025-12"])]:
        claim("stale_series", "OUTDATED", cl_en, cl_fr,
              f"The figure ({num(val, 'en', 2)}) comes from series 001763852 (CPI base 2015, all items excluding tobacco), which "
              f"INSEE marks as stopped; its last point is December 2025. The current series 011814630 (CPI base 2025, all items) "
              f"gives {pct(yc, 'en')} year on year in October 2026.",
              f"Le chiffre ({num(val, 'fr', 2)}) vient de la série 001763852 (IPC base 2015, ensemble hors tabac), que l'Insee "
              f"marque comme arrêtée ; son dernier point est décembre 2025. La série en cours 011814630 (IPC base 2025, ensemble) "
              f"donne {pct(yc, 'fr')} sur un an en octobre 2026.",
              "1) Find the series code behind the figure. 2) Read its title: 'Stopped series', base 2015, excluding tobacco. "
              "3) Find the current series (base 2025) and recompute: Oct 2026 / Oct 2025 - 1. 4) Verdict OUTDATED, not FALSE: "
              "the number was right for its date and scope.",
              "1) Retrouver le code de la série derrière le chiffre. 2) Lire son titre : « série arrêtée », base 2015, hors tabac. "
              "3) Trouver la série en cours (base 2025) et recalculer : oct. 2026 / oct. 2025 - 1. 4) Verdict OBSOLÈTE, pas FAUX : "
              "le chiffre était juste à sa date et sur son champ.",
              src_i, "INSEE 001763852 / 011814630", stale(cl_en, cl_fr), 3)
    for g in ["FR", "ES"]:
        claim("stale_series", "OUTDATED",
              f"Eurostat's latest HICP figure puts annual inflation in {cname(g, 'en')} at {num(HO.at['2025-12', g], 'en')}%.",
              f"Selon le dernier chiffre IPCH d'Eurostat, l'inflation annuelle de {cname(g, 'fr')} est de {num(HO.at['2025-12', g], 'fr')} %.",
              f"{num(HO.at['2025-12', g], 'en')}% is December 2025 in prc_hicp_manr, a dataset frozen at 2025-12 (last update "
              f"{UPD['prc_hicp_manr']}). The current dataset prc_hicp_minr gives {num(H.at['2026-10', g], 'en')}% for October 2026.",
              f"{num(HO.at['2025-12', g], 'fr')} % correspond à décembre 2025 dans prc_hicp_manr, jeu figé à 2025-12 (dernière mise à "
              f"jour {UPD['prc_hicp_manr']}). Le jeu en cours prc_hicp_minr donne {num(H.at['2026-10', g], 'fr')} % pour octobre 2026.",
              "1) Check the dataset's last period and update date, not only the value. 2) Eurostat's catalogue lists the "
              "successor (ECOICOP ver.2, prc_hicp_minr). 3) Quote the latest month with its code.",
              "1) Vérifier la dernière période et la date de mise à jour du jeu, pas seulement la valeur. 2) Le catalogue d'Eurostat "
              "indique le successeur (ECOICOP v2, prc_hicp_minr). 3) Citer le dernier mois avec son code.",
              f"Eurostat prc_hicp_manr (stopped) and prc_hicp_minr (updated {UPD['prc_hicp_minr']}), extracted {EXTR}",
              "prc_hicp_manr / prc_hicp_minr",
              {"STALE_SOURCE": V("TRUE. Eurostat's HICP dataset confirms the figure.", "Read prc_hicp_manr, latest value.",
                                 "VRAI. Le jeu IPCH d'Eurostat confirme le chiffre.", "Lecture de prc_hicp_manr, dernière valeur.")}, 2)
    uo, uc = ins("001688526"), ins("001688527")
    claim("stale_series", "OUTDATED",
          f"According to INSEE, the unemployment rate stands at {num(uo.iloc[-1], 'en')}% in the latest quarter.",
          f"Selon l'Insee, le taux de chômage s'établit à {num(uo.iloc[-1], 'fr')} % au dernier trimestre.",
          f"{num(uo.iloc[-1], 'en')}% is {uo.index[-1]} in series 001688526 (metropolitan France), which INSEE marks as stopped. "
          f"The current series 001688527 (France excluding Mayotte) gives {num(uc.iloc[-1], 'en')}% in {uc.index[-1]}.",
          f"{num(uo.iloc[-1], 'fr')} % correspond au {uo.index[-1]} de la série 001688526 (France métropolitaine), marquée arrêtée. "
          f"La série en cours 001688527 (France hors Mayotte) donne {num(uc.iloc[-1], 'fr')} % au {uc.index[-1]}.",
          "1) Identify the series and its scope (metropolitan France vs France excluding Mayotte). 2) Its title says stopped. "
          "3) Quote the current series and quarter.",
          "1) Identifier la série et son champ (France métropolitaine ou hors Mayotte). 2) Son titre indique « arrêtée ». "
          "3) Citer la série en cours et le trimestre.",
          f"INSEE BDM 001688526 (stopped) / 001688527 (current), extracted {EXTR}", "INSEE 001688526 / 001688527",
          {"STALE_SOURCE": V("TRUE. INSEE's series confirms it.", "Series 001688526, last quarter.",
                             "VRAI. La série de l'Insee le confirme.", "Série 001688526, dernier trimestre.")}, 2)
    # HICP comparisons (TRUE / FALSE), current dataset
    pairs = [("IT", "ES", "2026-10"), ("DE", "FR", "2026-10"), ("BE", "NL", "2026-09"), ("ES", "PT", "2026-09"),
             ("FR", "EA20", "2026-10"), ("NL", "DE", "2026-10"), ("PT", "FR", "2026-10"), ("IT", "DE", "2026-09")]
    for a, b, t in pairs:
        va, vb = H.at[t, a], H.at[t, b]
        truth = "TRUE" if va > vb else "FALSE"
        claim("comparison", truth,
              f"In {ym(t, 'en')}, annual inflation (HICP) was higher in {cname(a, 'en')} than in {cname(b, 'en')}.",
              f"En {ym(t, 'fr')}, l'inflation annuelle (IPCH) était plus élevée en {cshort(a, 'fr')} qu'en {cshort(b, 'fr')}."
              .replace("qu'en zone euro", "que dans la zone euro").replace("en zone euro", "dans la zone euro").replace("en Pays-Bas", "aux Pays-Bas").replace("en Portugal", "au Portugal"),
              f"{cname(a, 'en')} {num(va, 'en')}% vs {cname(b, 'en')} {num(vb, 'en')}% (prc_hicp_minr, {t}).",
              f"{cshort(a, 'fr')} {num(va, 'fr')} % contre {cshort(b, 'fr')} {num(vb, 'fr')} % (prc_hicp_minr, {t}).",
              "1) Use the current HICP dataset (prc_hicp_minr, annual rate of change, all items). 2) Read both values for the "
              "same month. 3) Compare.",
              "1) Utiliser le jeu IPCH en cours (prc_hicp_minr, taux annuel, ensemble). 2) Lire les deux valeurs du même mois. "
              "3) Comparer.",
              src("prc_hicp_minr"), "prc_hicp_minr (TOTAL, RCH_A)",
              {"ARITHMETIC": V(f"{'FALSE' if truth == 'TRUE' else 'TRUE'}. {cname(a, 'en')} {num(vb, 'en')}% vs "
                               f"{cname(b, 'en')} {num(va, 'en')}%.", "Values read from the table.",
                               f"{VFR['FALSE' if truth == 'TRUE' else 'TRUE']}. {cshort(a, 'fr')} {num(vb, 'fr')} % contre "
                               f"{cshort(b, 'fr')} {num(va, 'fr')} %.", "Valeurs lues dans le tableau.")}, 1)
    # points vs percent
    for g, t1, t2 in [("FR", "2025-10", "2026-09"), ("IT", "2025-10", "2026-09"), ("BE", "2025-01", "2026-09")]:
        a, b = U.at[t1, g], U.at[t2, g]
        d = b - a
        claim("points_vs_percent", "MISLEADING",
              f"{cname(g, 'en')}'s unemployment rate rose by {num(d, 'en')}% between {ym(t1, 'en')} and {ym(t2, 'en')}."
              .replace("rose by -", "fell by "),
              f"Le taux de chômage de {cname(g, 'fr')} a augmenté de {num(d, 'fr')} % entre {ym(t1, 'fr')} et {ym(t2, 'fr')}."
              .replace("augmenté de -", "baissé de "),
              f"The rate moved from {num(a, 'en')}% to {num(b, 'en')}%: {pts(d, 'en')}, a relative change of "
              f"{pct((b / a - 1) * 100, 'en')}. The size is right but the unit is wrong.",
              f"Le taux passe de {num(a, 'fr')} % à {num(b, 'fr')} % : {pts(d, 'fr')}, soit {pct((b / a - 1) * 100, 'fr')} en "
              f"relatif. L'ampleur est juste, l'unité est fausse.",
              "1) Read both rates (une_rt_m, SA). 2) Difference of two rates = percentage points. 3) The claim's '%' would mean a "
              "relative change; verdict MISLEADING.",
              "1) Lire les deux taux (une_rt_m, CVS). 2) Différence de deux taux = points de pourcentage. 3) Le « % » de "
              "l'affirmation signifierait une variation relative ; verdict TROMPEUR.",
              src("une_rt_m"), "une_rt_m (SA, TOTAL, T, PC_ACT)",
              {"PCT_VS_POINTS": V(f"TRUE. The rate went from {num(a, 'en')}% to {num(b, 'en')}%.", "Difference matches.",
                                  f"VRAI. Le taux passe de {num(a, 'fr')} % à {num(b, 'fr')} %.", "La différence correspond.")},
              2, trap=True)
    # provisional / estimated
    for g, t in [("FR", "2026-09"), ("IE", "2026-08"), ("NL", "2026-07")]:
        v0, v1 = R.at[sh(t, -1), g], R.at[t, g]
        ch = (v1 / v0 - 1) * 100
        f = RS.at[t, g]
        claim("provisional", "MISLEADING",
              f"Eurostat confirms that {cname(g, 'en')}'s retail volume changed by {pct(ch, 'en')} in {ym(t, 'en')}, a final figure.",
              f"Eurostat confirme que le volume des ventes au détail de {cname(g, 'fr')} a varié de {pct(ch, 'fr')} en {ym(t, 'fr')}, "
              f"chiffre définitif.",
              f"The change is correctly computed ({num(v0, 'en')} -> {num(v1, 'en')}), but the {ym(t, 'en')} value carries the "
              f"flag '{f}' ({FLAG[f]}); it is not final and may be revised.",
              f"La variation est bien calculée ({num(v0, 'fr')} -> {num(v1, 'fr')}), mais la valeur de {ym(t, 'fr')} porte "
              f"l'indicateur '{f}' ({FLAG_FR[f]}) : elle n'est pas définitive.",
              "1) Recompute the change from the index. 2) Read the observation status in the JSON-stat 'status' field. "
              "3) A correct number presented as final when flagged is MISLEADING.",
              "1) Recalculer la variation à partir de l'indice. 2) Lire le statut de l'observation (champ « status » du JSON-stat). "
              "3) Un chiffre juste présenté comme définitif alors qu'il est signalé est TROMPEUR.",
              src("sts_trtu_m"), "sts_trtu_m (VOL_SLS, G47, SCA, I21)",
              {"PROVISIONAL_AS_FINAL": V(f"TRUE. The index went from {num(v0, 'en')} to {num(v1, 'en')}.", "Recomputed: matches.",
                                         f"VRAI. L'indice passe de {num(v0, 'fr')} à {num(v1, 'fr')}.", "Recalcul : conforme.")},
              2, status=f)
    # NUTS labels
    A = N.groupby(N.index.str[:4]).sum()
    for r in ["FRJ2", "FRI1"]:
        nm, adm = NUTS[r]
        v = A.at["2025", r] / 1e6
        claim("nuts_label", "MISLEADING",
              f"{nm}, one of France's administrative regions, recorded {num(v, 'en', 2)} million tourist nights in 2025.",
              f"{nm}, l'une des régions administratives françaises, a enregistré {num(v, 'fr', 2)} millions de nuitées en 2025.",
              f"The figure matches Eurostat ({num(v, 'en', 2)} M), but {nm} is a NUTS 2 statistical region; since 2016 it is "
              f"part of the administrative region {adm}.",
              f"Le chiffre correspond à Eurostat ({num(v, 'fr', 2)} M), mais {nm} est une région statistique NUTS 2 ; depuis "
              f"2016 elle fait partie de la région administrative {adm}.",
              "1) Sum the 12 months of 2025. 2) Check the geography: code " + r + " is a NUTS 2 unit, not a current region.",
              "1) Additionner les 12 mois de 2025. 2) Vérifier la géographie : le code " + r + " est une unité NUTS 2, pas une région actuelle.",
              src("tour_occ_nin2m"), "tour_occ_nin2m (TOTAL, I551-I553, NR)",
              {"NUTS_LABEL": V(f"TRUE. {nm} recorded {num(v, 'en', 2)} M nights.", "Sum of 2025 months matches.",
                               f"VRAI. {nm} a enregistré {num(v, 'fr', 2)} M de nuitées.", "La somme des mois 2025 correspond.")}, 2)
    # French formats: decimal comma, milliard vs billion, trimestre vs semestre
    tot = A.loc["2025"].sum() / 1e9
    claim("french_format", "TRUE",
          f"The eight NUTS 2 regions in this dataset recorded about {num(tot, 'en', 2)} billion tourist nights in 2025.",
          f"Les huit régions NUTS 2 de ce jeu ont enregistré environ {num(tot, 'fr', 2)} milliard de nuitées en 2025.",
          f"Sum of 2025 = {num(tot * 1000, 'en', 1)} million = {num(tot, 'en', 2)} billion.",
          f"Somme 2025 = {num(tot * 1000, 'fr', 1)} millions = {num(tot, 'fr', 2)} milliard.",
          "1) Sum 12 months x 8 regions. 2) Convert: 1 billion (EN) = 10^9 = 1 milliard (FR); the French 'billion' is 10^12.",
          "1) Somme 12 mois x 8 régions. 2) Conversion : 1 billion (anglais) = 10^9 = 1 milliard ; le « billion » français vaut 10^12.",
          src("tour_occ_nin2m"), "tour_occ_nin2m (TOTAL, I551-I553, NR)",
          {"FR_BILLION": {"fr": [f"VRAI. Environ {num(tot, 'fr', 2)} billion de nuitées.", "Somme convertie en billions."]},
           "ARITHMETIC": V(f"FALSE. The total is {num(tot * 10, 'en', 2)} billion.", "Sum of the regions.",
                           f"FAUX. Le total est de {num(tot * 10, 'fr', 2)} milliards.", "Somme des régions.")}, 2, trap=True)
    v = A.at["2025", "FRM0"] / 1e6
    claim("french_format", "TRUE",
          f"Corsica (NUTS 2 region FRM0) recorded {num(v, 'en', 3)} million tourist nights in 2025.",
          f"La Corse (région NUTS 2 FRM0) a enregistré {num(v, 'fr', 3)} millions de nuitées touristiques en 2025.",
          f"Sum of the 12 months of 2025 = {num(v * 1e6, 'en', 0)} nights.",
          f"Somme des 12 mois de 2025 = {num(v * 1e6, 'fr', 0)} nuitées.",
          f"1) Sum the 2025 months. 2) In French, the comma is the decimal separator: '{num(v, 'fr', 3)}' means {num(v, 'en', 3)}.",
          f"1) Additionner les mois de 2025. 2) En français la virgule est décimale : « {num(v, 'fr', 3)} » signifie {num(v, 'en', 3)} et non {num(v * 1000, 'fr', 0)}.",
          src("tour_occ_nin2m"), "tour_occ_nin2m (TOTAL, I551-I553, NR)",
          {"FR_DECIMAL": {"fr": [f"FAUX. La Corse n'a pas pu enregistrer {num(v * 1000, 'fr', 0)} millions de nuitées.",
                                 f"J'ai lu « {num(v, 'fr', 3)} » comme {num(v * 1000, 'fr', 0)}."]},
           "ARITHMETIC": V(f"FALSE. Corsica recorded {num(v * 0.9, 'en', 2)} million.", "Sum of months.",
                           f"FAUX. La Corse a enregistré {num(v * 0.9, 'fr', 2)} millions.", "Somme des mois.")}, 1, trap=True)
    q = "2026-Q2"
    claim("french_format", "TRUE",
          f"In the second quarter of 2026, France's ILO unemployment rate (excluding Mayotte) was {num(uc[q], 'en')}%.",
          f"Au deuxième trimestre 2026, le taux de chômage au sens du BIT (France hors Mayotte) était de {num(uc[q], 'fr')} %.",
          f"INSEE series 001688527 gives {num(uc[q], 'en')}% for {q}.",
          f"La série Insee 001688527 donne {num(uc[q], 'fr')} % pour {q}.",
          "1) Quarterly series 001688527, period 2026-Q2. 2) Quarter = trimestre (3 months); semester = semestre (6 months).",
          "1) Série trimestrielle 001688527, période 2026-T2. 2) Trimestre = 3 mois ; semestre = 6 mois : ne pas confondre.",
          f"INSEE BDM 001688527, extracted {EXTR}", "INSEE 001688527",
          {"FR_TERM": {"fr": [f"FAUX. Le chiffre de {num(uc[q], 'fr')} % porte sur le premier semestre, pas sur un trimestre.",
                              "J'ai lu « deuxième trimestre » comme le premier semestre."]},
           "STALE_SOURCE": V(f"FALSE. INSEE gives {num(uo['2026-Q1'], 'en')}%.", "Series 001688526.",
                             f"FAUX. L'Insee donne {num(uo['2026-Q1'], 'fr')} %.", "Série 001688526.")}, 2, trap=True)


# ---------------------------------------------------------------- texts: summarise and chunk
SUMMARIES = {
    "Eurostat": (
        "Eurostat is the European Commission's statistical office, a Directorate-General based in Luxembourg City. It supplies "
        "statistics to EU institutions and promotes harmonised statistical methods across member states, candidate countries "
        "and EFTA countries. With its national partners it forms the European Statistical System, a term in EU law since 2009.",
        "Eurostat est l'office statistique de la Commission européenne, une direction générale installée à Luxembourg. Il fournit "
        "des statistiques aux institutions de l'UE et harmonise les méthodes des États membres, des pays candidats et des pays de "
        "l'AELE. Avec les instituts nationaux, il forme le Système statistique européen, terme inscrit dans le droit de l'UE depuis 2009."),
    "Consumer price index": (
        "A consumer price index estimates the price level of the goods and services households buy, as a weighted average over a "
        "basket that is updated periodically. Prices are collected, often monthly, from sampled outlets and adjusted when an item "
        "is replaced by one of different quality. The index tracks inflation and allows comparisons across countries, although it "
        "is not a perfect measure of inflation or of the cost of living.",
        "Un indice des prix à la consommation estime le niveau des prix des biens et services achetés par les ménages, comme une "
        "moyenne pondérée sur un panier mis à jour régulièrement. Les prix sont relevés, souvent chaque mois, dans un échantillon de "
        "points de vente et corrigés quand un produit est remplacé par un produit de qualité différente. L'indice suit l'inflation et "
        "permet des comparaisons entre pays, sans être une mesure parfaite de l'inflation ni du coût de la vie."),
    "Seasonal adjustment": (
        "Seasonal adjustment removes the seasonal component of a time series so that its trend and cycle can be analysed on their "
        "own. Many economic series follow seasonal patterns, such as crop yields or spending before Christmas, so official "
        "statistics, unemployment rates in particular, are often published seasonally adjusted.",
        "La désaisonnalisation retire la composante saisonnière d'une série temporelle pour analyser seuls sa tendance et son cycle. "
        "Beaucoup de séries économiques suivent des rythmes saisonniers, comme les récoltes ou les dépenses avant Noël : les "
        "statistiques officielles, en particulier les taux de chômage, sont donc souvent publiées corrigées des variations saisonnières."),
    "Institut national de la statistique et des études économiques": (
        "INSEE, created in 1946 and based in Montrouge, collects, produces, analyses and disseminates information on the French "
        "economy and society. It produces in particular the national accounts (annual and quarterly), demographic indicators, the "
        "unemployment rate and the consumer price index. It is a directorate-general of the economy ministry, with an independence "
        "guaranteed by law since 2008, and it also manages several administrative registers.",
        "L'Insee, créé en 1946 et installé à Montrouge, collecte, produit, analyse et diffuse des informations sur l'économie et la "
        "société françaises. Il produit notamment la comptabilité nationale annuelle et trimestrielle, les indicateurs démographiques, "
        "le taux de chômage et l'indice des prix à la consommation. Direction générale du ministère de l'Économie, il dispose d'une "
        "indépendance garantie par la loi depuis 2008 et gère aussi plusieurs répertoires administratifs."),
    "Nomenclature des unités territoriales statistiques": (
        "NUTS is a territorial classification developed by the European Union to make statistical comparisons between countries "
        "easier. It covers EU member states and also some neighbouring countries.",
        "La NUTS est un découpage territorial conçu par l'Union européenne pour faciliter les comparaisons statistiques entre pays. "
        "Elle couvre les pays de l'UE ainsi que certains pays voisins."),
}
NON_CONTENT = {"See also", "References", "External links", "Further reading", "Notes et références", "Annexes", "Sources",
               "Compléments", "Voir aussi", "Liens externes"}
STOP = set("about after their there which these those would could other first since under where while years being "
           "dans pour avec plus sont leur leurs elle entre comme cette ainsi aussi selon après depuis être était "
           "national nationale statistics statistical statistique statistiques".split())


def sections(text):
    """Top-level blocks: lead + '== X ==' sections; '=== sub ===' stay inside their parent block."""
    parts = re.split(r"^==\s*([^=].*?)\s*==\s*$", text, flags=re.M)
    blocks = [("Lead", parts[0])] + [(parts[i], parts[i + 1]) for i in range(1, len(parts), 2)]
    return [(h, b) for h, b in blocks if h not in NON_CONTENT]


def texts():
    meta = pd.read_csv(PUB / "texts_meta.csv")
    for _, m in meta.iterrows():
        text = (PUB.parent / "raw" / m.raw_file).read_text(encoding="utf-8")
        blocks = sections(text)
        lead = blocks[0][1].strip()
        wc = [(h, len(b.split())) for h, b in blocks]
        title, lang_src = m.title, m.lang
        cite = f"Wikipedia ({lang_src}), '{title}', revision {m.revid} ({m.rev_timestamp[:10]}), CC BY-SA 4.0"
        base = dict(type="summarise_chunk", source=cite, series_code=f"oldid={m.revid}", data_status="final")
        # K1 chunk
        blk_en = "; ".join(f"{h} ({w} words)" for h, w in wc)
        blk_fr = " ; ".join(f"{'Introduction' if h == 'Lead' else h} ({w} mots)" for h, w in wc)
        add(**base, subtype="chunk", difficulty=2 if len(wc) > 6 else 1,
            prompt_en=f"Split the Wikipedia article '{title}' (revision {m.revid}) into logical blocks and give each block a short title.",
            prompt_fr=f"Découpe l'article Wikipédia « {title} » (révision {m.revid}) en blocs logiques et donne un titre court à chaque bloc.",
            ref_en=f"{len(wc)} content blocks: {blk_en}. Reference lists and links are left out.",
            ref_fr=f"{len(wc)} blocs de contenu : {blk_fr}. Les listes de références et de liens sont exclues.",
            expl_en="1) Use the author's own structure first: the lead plus each top-level section is one block; sub-sections stay "
                    "inside their parent. 2) Drop non-content blocks (See also, References, External links). 3) Check that every "
                    "sentence of the article belongs to exactly one block.",
            expl_fr="1) Partir de la structure de l'auteur : l'introduction plus chaque section de premier niveau forment un bloc ; "
                    "les sous-sections restent dans leur parent. 2) Écarter les blocs sans contenu (Voir aussi, Références, Liens). "
                    "3) Vérifier que chaque phrase appartient à un seul bloc.",
            check=f"n_blocks={len(wc)}",
            variants={"correct": V(f"{len(wc)} blocks: {blk_en}.", "Lead + top-level sections, references dropped.",
                                   f"{len(wc)} blocs : {blk_fr}.", "Introduction + sections, références exclues."),
                      "MISSED_BLOCK": V(f"{len(wc) - 1} blocks: " + "; ".join(h for h, _ in wc[:-1]) + ".", "Main sections listed.",
                                        f"{len(wc) - 1} blocs : " + " ; ".join(h for h, _ in wc[:-1]) + ".", "Sections principales.")})
        # K2 summary (hand-written reference, figures checked against the lead)
        s_en, s_fr = SUMMARIES[title]
        for s in (s_en, s_fr):
            for n in re.findall(r"\d{3,4}", s):
                assert n in lead, f"{n} not in lead of {title}"
            assert len(re.findall(r"[.!?](\s|$)", s)) <= 3, f"summary of {title} too long"
        hall = ("It employs about 4,000 people." if lang_src == "en" else "Il emploie environ 4 000 personnes.")
        var = {"correct": V(s_en, "Each sentence maps to one paragraph of the lead.", s_fr,
                            "Chaque phrase reprend un paragraphe de l'introduction."),
               "HALLUCINATED_DETAIL": V(s_en.split(". ")[0] + ". It employs about 4,000 people.", "Summary of the lead.",
                                        s_fr.split(". ")[0] + ". Il emploie environ 4 000 personnes.", "Résumé de l'introduction.")}
        trap = False
        if "trimestrielle" in s_fr:
            var["FR_TERM"] = {"fr": [s_fr.replace("trimestrielle", "semestrielle"), "Résumé de l'introduction."]}
            trap = True
        add(**base, subtype="summary", difficulty=2,
            prompt_en=f"Summarise the lead section of the Wikipedia article '{title}' (revision {m.revid}) in at most three sentences, in English.",
            prompt_fr=f"Résume l'introduction de l'article Wikipédia « {title} » (révision {m.revid}) en trois phrases au plus, en français.",
            ref_en=s_en, ref_fr=s_fr,
            expl_en="1) One idea per paragraph of the lead. 2) Keep every figure and date exactly as in the source; add nothing that is "
                    "not in it (the check script verifies every number). 3) No names of people.",
            expl_fr="1) Une idée par paragraphe de l'introduction. 2) Garder chaque chiffre et chaque date tels quels ; ne rien "
                    "ajouter (le script de contrôle vérifie chaque nombre). 3) Aucun nom de personne.",
            check="numbers_in_source=ok; sentences<=3", variants=var, fr_trap=trap)
        # K3 dates in lead
        yrs = sorted(set(re.findall(r"\b(1[89]\d\d|20\d\d)\b", lead)))
        ans = join(yrs, "en") if yrs else "none"
        add(**base, subtype="extract_dates", difficulty=1,
            prompt_en=f"List every year mentioned in the lead section of '{title}' (revision {m.revid}), in chronological order.",
            prompt_fr=f"Liste toutes les années citées dans l'introduction de « {title} » (révision {m.revid}), dans l'ordre chronologique.",
            ref_en=f"Years: {ans}." if yrs else "No year is mentioned in the lead.",
            ref_fr=f"Années : {join(yrs, 'fr')}." if yrs else "Aucune année n'est citée dans l'introduction.",
            expl_en="1) Scan the lead only (not the whole article). 2) Keep four-digit years; ignore other numbers. 3) Sort and deduplicate.",
            expl_fr="1) Lire l'introduction seulement. 2) Garder les années à quatre chiffres ; ignorer les autres nombres. 3) Trier, dédoublonner.",
            check="years=" + ",".join(yrs),
            variants={"correct": V(f"{ans}.", "Years found in the lead.", f"{join(yrs, 'fr') if yrs else 'aucune'}.", "Années de l'introduction."),
                      "MISSED_BLOCK": V(f"{', '.join(yrs[:-1]) or 'none'}.", "Years found.", f"{', '.join(yrs[:-1]) or 'aucune'}.", "Années trouvées.")
                      if yrs else None, "HALLUCINATED_DETAIL": None if yrs else
                      V("2009.", "Year in the article.", "2009.", "Année de l'article.")})
        # K4 locate a topic: a word frequent in exactly one block
        best = None
        for h, b in blocks[1:]:
            for w, c in pd.Series(re.findall(r"[A-Za-zÀ-ÿ]{7,}", b.lower())).value_counts().items():
                if w in STOP or c < 3:
                    continue
                if sum(w in bb.lower() for _, bb in blocks) == 1 and (best is None or c > best[2]):
                    best = (w, h, c)
        w, h, c = best
        other = next(hh for hh, _ in blocks[1:] if hh != h)
        add(**base, subtype="locate", difficulty=1,
            prompt_en=f"In the Wikipedia article '{title}' (revision {m.revid}), which block discusses '{w}'?",
            prompt_fr=f"Dans l'article Wikipédia « {title} » (révision {m.revid}), quel bloc traite de « {w} » ?",
            ref_en=f"The block '{h}' (the word appears {c} times there and in no other block).",
            ref_fr=f"Le bloc « {h} » (le mot y apparaît {c} fois et dans aucun autre bloc).",
            expl_en="1) Split into blocks as in the chunking task. 2) Search the term in each block. 3) Report the block and quote it briefly.",
            expl_fr="1) Découper en blocs comme pour la tâche de découpage. 2) Chercher le terme dans chaque bloc. 3) Donner le bloc et le citer brièvement.",
            check=f"block={h}",
            variants={"correct": V(f"'{h}'.", f"'{w}' appears there.", f"« {h} ».", f"« {w} » y apparaît."),
                      "HALLUCINATED_DETAIL": V(f"'{other}'.", "It is the most relevant block.", f"« {other} ».", "C'est le bloc le plus pertinent.")})
        # K5 longest block
        lw = max(wc[1:], key=lambda x: x[1])
        sec = sorted(wc[1:], key=lambda x: x[1])[-2]
        add(**base, subtype="longest_block", difficulty=1,
            prompt_en=f"Which section of '{title}' (revision {m.revid}) is the longest, in words, excluding the lead and reference lists?",
            prompt_fr=f"Quelle section de « {title} » (révision {m.revid}) est la plus longue, en mots, hors introduction et références ?",
            ref_en=f"'{lw[0]}' with {lw[1]} words (next: '{sec[0]}', {sec[1]} words).",
            ref_fr=f"« {lw[0]} » avec {lw[1]} mots (ensuite : « {sec[0]} », {sec[1]} mots).",
            expl_en="1) Count words per top-level section, sub-sections included. 2) Exclude lead and reference lists. 3) Compare.",
            expl_fr="1) Compter les mots par section de premier niveau, sous-sections comprises. 2) Exclure introduction et références. 3) Comparer.",
            check=f"longest={lw[0]}",
            variants={"correct": V(f"'{lw[0]}' ({lw[1]} words).", "Word counts per section.", f"« {lw[0]} » ({lw[1]} mots).", "Mots par section."),
                      "ARITHMETIC": V(f"'{sec[0]}'.", "Longest section.", f"« {sec[0]} ».", "Section la plus longue.")})


if __name__ == "__main__":
    s1(); s2(); s3(); s4(); s5(); s6(); claims(); texts()
    df = pd.DataFrame(TASKS)
    df.to_csv(PROC / "tasks_data.csv", index=False, encoding="utf-8")
    print(df.groupby(["type", "subtype"]).size().to_string())
    print("total", len(df))
