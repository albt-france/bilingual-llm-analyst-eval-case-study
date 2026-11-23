# Writing a gold answer and its explanation

A gold (reference) answer is what a model should have said. It is used to grade answers and to teach the model
*why* it was wrong, so it has two parts:

1. **The answer**, in one or two sentences, with the number, its unit and its date.
2. **The explanation**, as short numbered steps a reader can redo: which data, which period, which formula, which
   trap, and the data status.

All reference answers in this repository are **computed** from the public files (`src/build_series_tasks.py`,
SQL in the notebook, brute-force solver for puzzles). None is read "by eye". Every task exists in English and
French; the French version is written for a French reader (decimal comma, `milliard`, `trimestre`), not
translated word for word.

## Checklist

| Step | Question to ask | Example |
|---|---|---|
| Period | Which months are compared, and why? | 3-month averages at each end, or full years for a seasonal series |
| Source | Which series code, updated when, extracted when? | `sts_trtu_m`, updated 2026-11-21, extracted 2026-11-23 |
| Status | Is any value provisional (`p`) or estimated (`e`)? Is the series stopped? | "values flagged p, may be revised" |
| Unit | %, percentage points, index points, millions, milliard? | "+0.5 percentage points" |
| Trap | What would a hasty answer say, and why is it wrong? | endpoint growth from one atypical month |
| Check | How can a reviewer verify it in under a minute? | the `check` column of the gold set |

## Five complete examples

### 1. "Which country grew the most?" (real data, the classic trap) - T001

**Task (EN).** Using Eurostat's monthly retail trade volume index (seasonally and calendar adjusted, 2021 = 100),
which of these countries grew the most between January 2024 and September 2026: Spain, Finland, Ireland and Poland?
Explain your choice of period.

**Reference (EN).** Spain grew the most: +5.6% (3-month averages). Ranking: Spain +5.6%; Poland +5.3%;
Ireland +4.7%; Finland +2.3%.

**Explanation (EN).**
1. Period: a single month is noisy, so compare the average of January-March 2024 with the average of
   July-September 2026.
2. Compute: Spain 105.3 -> 111.2, i.e. +5.6%.
3. Trap: endpoint-to-endpoint growth would put Poland first (+6.3%) because its January 2024 value (106.5) is
   below its 3-month average (107.9): one atypical month drives the ranking.
4. Data status: the values used for Spain, Ireland and Poland are flagged provisional (`p`), so the result may be revised.

**Référence (FR).** Le pays qui a le plus progressé est l'Espagne : +5,6 % (moyennes sur 3 mois). Classement :
Espagne +5,6 % ; Pologne +5,3 % ; Irlande +4,7 % ; Finlande +2,3 %. *(Explication : mêmes étapes, nombres au
format français.)*

### 2. The same question on a seasonal series (tourist nights) - T011

**Task.** Which of these NUTS 2 regions grew the most from 2023 to 2025: Île-de-France, Aquitaine, Rhône-Alpes and
Provence-Alpes-Côte d'Azur? Say which months you compare and why.

**Reference.** Île-de-France: +6.1% in annual nights (85.16 M in 2023 -> 90.37 M in 2025). Ranking: Île-de-France
+6.1%; Provence-Alpes-Côte d'Azur +4.0%; Aquitaine +2.4%; Rhône-Alpes +2.1%.

**Explanation.**
1. The series is **not** seasonally adjusted and peaks in summer, so compare full calendar years.
2. Annual totals give Île-de-France +6.1%.
3. Trap: January 2023 vs January 2025 would put Provence-Alpes-Côte d'Azur first (+2.8%): a low-season month is a
   small, volatile base. Starting from January 2022 is worse: that month was still depressed in several regions.
4. Labels are NUTS 2 statistical regions (Midi-Pyrénées lies within today's Occitanie), not the 2016 regions.

### 3. A claim that matches a number, but an outdated one - T071

**Claim.** "INSEE's consumer price index shows French prices up 0.7% over the latest 12 months."

**Reference.** **OUTDATED.** 0.74% comes from series 001763852 (CPI base 2015, all items excluding tobacco), which
INSEE marks as stopped; its last point is December 2025. The current series 011814630 (CPI base 2025, all items)
gives +3.4% year on year in October 2026.

**Explanation.** 1) Find the series behind the figure. 2) Read its title: "Stopped series", base 2015, excluding
tobacco. 3) Find the current series and recompute October 2026 / October 2025 - 1. 4) Verdict OUTDATED, not FALSE:
the number was right for its date and scope.

**Référence (FR).** OBSOLÈTE. Le chiffre vient d'une série arrêtée (IPC base 2015, hors tabac) ; la série en cours
011814630 donne +3,4 % sur un an en octobre 2026.

### 4. A logic puzzle - T053

**Task.** A courier visits 5 stops (Harbour, Market, Old Town, Station, Hillside) once each. Rules: (1) Hillside comes
before Market. (2) Market comes before Harbour. (3) Old Town comes immediately after Market. (4) Station is the first
stop. In what order are the stops visited?

**Reference.** Station > Hillside > Market > Old Town > Harbour.

**Explanation.** Start with the most restrictive rules and count what is left: 120 possible orders; rule 3 (Old Town
right after Market) -> 24; rule 4 (Station first) -> 6; rule 1 -> 3; rule 2 -> 1. Then check the remaining order
against every rule. The solver (`src/puzzle_solver.py`) proves there is exactly one solution.

**Référence (FR).** Gare > Colline > Marché > Vieille-Ville > Port.

### 5. Percentage points, not percent - T025

**Task.** By how much did France's unemployment rate (Eurostat `une_rt_m`, seasonally adjusted) change between
October 2025 and September 2026?

**Reference.** +0.5 percentage points (from 8.0% to 8.5%); in relative terms the rate itself rose by 6.2%.

**Référence (FR).** +0,5 point de pourcentage (de 8,0 % à 8,5 %) ; en relatif, le taux a augmenté de 6,2 %.

## Three graded corrections (model answer -> verdict -> what to write back)

All three answers come from the **simulated** model.

**A. T011, English - `incorrect`, WRONG_WINDOW.**
Model: "Provence-Alpes-Côte d'Azur grew the most (+2.8%). I compared January 2023 with January 2025."
Feedback: "The ranking rests on one low-season month. The series is not seasonally adjusted, so compare full years:
Île-de-France grew most (+6.1%, 85.16 M -> 90.37 M nights). Please state the months you compare and why."

**B. T053, French - `incorrect`, CONSTRAINT_IGNORED.**
Model: « Gare > Port > Colline > Marché > Vieille-Ville. Cet ordre respecte toutes les règles. »
Feedback: « La règle 2 (Marché avant Port) n'est pas respectée : Port est 2e, Marché 4e. Seul l'ordre Gare > Colline >
Marché > Vieille-Ville > Port respecte les quatre règles ; vérifier chaque règle avant de conclure. »
(The solver flags the broken rule automatically: `violated()` in `src/puzzle_solver.py`.)

**C. T094, French - `incorrect`, FR_DECIMAL.**
Model: « FAUX. La Corse n'a pas pu enregistrer 11 035 millions de nuitées. J'ai lu « 11,035 » comme 11 035. »
Feedback: « En français la virgule est décimale : 11,035 millions = 11 034 583 nuitées, ce qui correspond à la somme
des 12 mois de 2025 (Eurostat tour_occ_nin2m). Verdict attendu : VRAI. »
