# Error taxonomy

13 codes, each with a default verdict (see [rubric.md](rubric.md)). Counts are the consensus codes on the 240
**simulated** answers (guidelines v2).

| Code | Family | Default verdict | Definition | How to fix |
|---|---|---|---|---|
| WRONG_WINDOW | Reasoning | incorrect | Wrong comparison period: growth from one atypical month, month-on-month instead of year-on-year, window wider than asked. | 3-month averages, full years or same month a year earlier; say why. |
| PCT_VS_POINTS | Units | partially_correct | Change between two rates written in % instead of percentage points. | Difference of rates = points; ratio = %. |
| CONSTRAINT_IGNORED | Logic | incorrect | Puzzle answer that breaks one stated rule. | Check the order against every rule. |
| UNJUSTIFIED_STEP | Explanation | partially_correct | Right answer, reasoning skipped. | Show the elimination. |
| STALE_SOURCE | Sources | incorrect | Claim confirmed with a stopped series or frozen dataset. | Read series status and last period; cite the current series. |
| PROVISIONAL_AS_FINAL | Data status | partially_correct | Value flagged `p`/`e` presented as final. | State that it may be revised. |
| NUTS_LABEL | Geography | partially_correct | NUTS 2 statistical region confused with a current region. | Name the NUTS level; give the current region if needed. |
| ARITHMETIC | Calculation | incorrect | Wrong calculation or wrong value read. | Recompute; show the formula. |
| HALLUCINATED_DETAIL | Faithfulness | incorrect | Fact, figure or location not in the source. | Every figure must be traceable. |
| MISSED_BLOCK | Completeness | partially_correct | A block, year or item of the source missing. | Every sentence belongs to one block. |
| FR_DECIMAL | French-specific | incorrect | Decimal comma read as thousands separator. | See below. |
| FR_BILLION | French-specific | incorrect | `billion` used in French for 10^9. | See below. |
| FR_TERM | French-specific | incorrect | trimestre/semestre, avant-dernier/dernier confused. | See below. |

Most frequent in the simulated sample: CONSTRAINT_IGNORED (25), PROVISIONAL_AS_FINAL (13), ARITHMETIC (11),
WRONG_WINDOW (10), PCT_VS_POINTS (8), STALE_SOURCE (7).

## French-specific pitfalls

These errors cannot happen in the English version of the same task. In the simulated sample they are 9 of the 55
failed French answers (16%).

| Pitfall | English | French | Typical slip |
|---|---|---|---|
| Decimal separator | 11.035 million | 11,035 millions | read as 11 035 millions |
| Thousands separator | 11,034,583 | 11 034 583 (space) | "11,034,583" pasted into a French text reads as 11.03 |
| 10^9 | billion | milliard | « 0,31 billion » (= 10^12 in French) |
| 10^12 | trillion | billion | the reverse slip |
| Quarter / half-year | quarter, Q2 | trimestre, T2 | « deuxième trimestre » read as « semestre » |
| Second-to-last | second-to-last | avant-dernier | read as « dernier » in a puzzle rule |
| Percentage points | percentage points | points (de pourcentage) | « +0,5 % » for a change of rate |
| Percent sign | 3.4% | 3,4 % (space before %) | form only, not an error |
| Seasonal adjustment | SA, seasonally and calendar adjusted | CVS-CJO | CVS confused with "brut" |
| Regions | NUTS 2 region | région NUTS 2 vs région administrative | « Midi-Pyrénées, région française » |
| Ordinals | first, 1st | premier, 1er | 1ère/1er agreement: form only |

*Rows marked "form only" are style, not errors: they do not change the verdict.*
