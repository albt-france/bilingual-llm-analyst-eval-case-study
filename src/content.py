"""Rubric and error taxonomy, shared by the workbook builder (the docs/ pages explain them in prose)."""

VERDICTS = [
    ("correct", "Final answer matches the reference AND the explanation shows the steps that lead to it (period, "
                "formula, source and its status). Wording may differ.", "Pass"),
    ("partially_correct", "The headline answer is right but something a reader needs is wrong or missing: unit "
                          "(% vs points), data status (provisional shown as final), geography label, a skipped "
                          "justification, a missing block.", "Fail (minor)"),
    ("incorrect", "The headline answer is wrong, or it is right for a wrong reason that would fail on another case "
                  "(wrong period, broken rule, stale source, invented fact, misread French number).", "Fail (major)"),
]

RULES_V2 = [
    ("R1 Headline first", "Grade the final answer against the reference first, then the explanation. A right answer with "
                          "no usable explanation is at best partially_correct."),
    ("R2 Period", "For 'who grew the most', growth measured from a single month when the question spans a period is "
                  "incorrect if it changes the ranking, partially_correct if it does not."),
    ("R3 Units", "A change between two rates must be in percentage points. Using % with the right figures is "
                 "partially_correct; if the conclusion depends on it (e.g. a comparison), incorrect."),
    ("R4 Data status", "A right number flagged provisional (p) or estimated (e) but presented as final is "
                       "partially_correct. Always read the observation status."),
    ("R5 Source currency", "Before confirming a figure, check the series is not stopped and the dataset not frozen. "
                           "Confirming a claim with a stopped series is incorrect, even if the number matches it."),
    ("R6 Geography", "NUTS 2 statistical regions are not the 2016 administrative regions. Wrong label with the right "
                     "number: partially_correct."),
    ("R7 French formats", "Read numbers in the convention of the text: 11,035 in French is 11.035. 'billion' in French "
                          "is 10^12. trimestre = quarter, semestre = half-year. Any of these changing the answer: incorrect."),
    ("R8 Puzzles", "Check the proposed order against every rule. One broken rule: incorrect. Right order with no "
                   "justification: partially_correct."),
]

V1_TO_V2 = ("Guidelines v1 had only the three verdict definitions. v2 added rules R2-R8 after the first round showed "
            "most disagreement on grey-zone cases (units, data status, labels, missing justification) and on two "
            "checks reviewers skipped (series status, French formats).")

TAXONOMY = [
    # code, family, severity, definition, example EN, example FR, how to fix
    ("WRONG_WINDOW", "Reasoning", "incorrect", "Wrong comparison period: growth from one atypical month, month-on-month "
     "instead of year-on-year, or a window wider than asked.",
     "'Poland grew most: +6.3% from January 2024 to September 2026' (one low month drives it).",
     "« La Pologne a le plus progressé : +6,3 % de janvier 2024 à septembre 2026 » (un seul mois bas).",
     "Compare 3-month averages, full years or the same month a year earlier; say why."),
    ("PCT_VS_POINTS", "Units", "partially_correct", "Change between two rates written in % instead of percentage points.",
     "'Unemployment rose by 0.5%' (8.0% -> 8.5% is +0.5 points, +6.3% relative).",
     "« Le chômage a augmenté de 0,5 % » (8,0 % -> 8,5 % = +0,5 point).", "Difference of rates = points; ratio = %."),
    ("CONSTRAINT_IGNORED", "Logic", "incorrect", "Puzzle answer that breaks one stated rule.",
     "Order that places Station second when rule 4 says Station is first.",
     "Ordre qui place Gare en deuxième alors que la règle 4 l'impose en premier.", "Check the order against every rule."),
    ("UNJUSTIFIED_STEP", "Explanation", "partially_correct", "Right answer, but the explanation skips the reasoning.",
     "'The order follows directly from the rules.'", "« L'ordre découle directement des règles. »",
     "Show the elimination: which rule removes which options."),
    ("STALE_SOURCE", "Sources", "incorrect", "Claim confirmed with a stopped series or a frozen dataset.",
     "'TRUE, INSEE CPI series 001763852 confirms it' (series stopped at 2025-12).",
     "« VRAI, la série 001763852 le confirme » (série arrêtée en 2025-12).",
     "Read the series title/status and last period; cite the current series."),
    ("PROVISIONAL_AS_FINAL", "Data status", "partially_correct", "Flagged value (p, e) presented as final.",
     "'These are final official figures' for a value flagged 'e'.", "« Chiffres définitifs » pour une valeur « e ».",
     "Read the status field; state that the value may be revised."),
    ("NUTS_LABEL", "Geography", "partially_correct", "NUTS 2 statistical region confused with a current region.",
     "'Midi-Pyrénées, one of France's 13 regions'.", "« Midi-Pyrénées, l'une des 13 régions ».",
     "Name the NUTS level; give the current region if needed (Occitanie)."),
    ("ARITHMETIC", "Calculation", "incorrect", "Wrong calculation or value read from the wrong row/column.",
     "Peak/trough 'ratio' computed as a difference.", "« Rapport » calculé comme une différence.",
     "Recompute from the source values; show the formula."),
    ("HALLUCINATED_DETAIL", "Faithfulness", "incorrect", "Adds a fact, figure or location not in the source.",
     "'It employs about 4,000 people' (not in the text).", "« Il emploie environ 4 000 personnes » (absent du texte).",
     "Every figure in a summary must be traceable to the source."),
    ("MISSED_BLOCK", "Completeness", "partially_correct", "A block, year or item of the source is missing.",
     "Chunking that drops the last content section.", "Découpage qui oublie la dernière section.",
     "Check every sentence belongs to one block."),
    ("FR_DECIMAL", "French-specific", "incorrect", "French decimal comma read as a thousands separator.",
     "-", "« 11,035 millions » lu comme 11 035 millions.", "In French, the comma is the decimal separator."),
    ("FR_BILLION", "French-specific", "incorrect", "'billion' used in French for 10^9.",
     "-", "« 0,31 billion de nuitées » au lieu de « 0,31 milliard ».", "10^9 = milliard; billion (FR) = 10^12."),
    ("FR_TERM", "French-specific", "incorrect", "French term confused: trimestre/semestre, avant-dernier/dernier.",
     "-", "« deuxième trimestre » lu comme premier semestre.", "trimestre = 3 months; semestre = 6; avant-dernier = second-to-last."),
]
