# Grading rubric

Three verdicts, graded **headline first, explanation second**.

| Verdict | Definition | Counts as |
|---|---|---|
| `correct` | Final answer matches the reference **and** the explanation shows the steps (period, formula, source and status). Wording may differ. | Pass |
| `partially_correct` | Headline right, but something a reader needs is wrong or missing: unit (% vs points), data status, geography label, skipped justification, missing block. | Fail (minor) |
| `incorrect` | Headline wrong, or right for a reason that would fail on another case: wrong period, broken rule, stale source, invented fact, misread French number. | Fail (major) |

## Decision rules (guidelines v2)

| Rule | Text |
|---|---|
| R1 Headline first | Grade the final answer against the reference first, then the explanation. A right answer with no usable explanation is at best `partially_correct`. |
| R2 Period | For "who grew the most", growth measured from a single month when the question spans a period is `incorrect` if it changes the ranking, `partially_correct` if not. |
| R3 Units | A change between two rates is in percentage points. % with the right figures: `partially_correct`; if the conclusion depends on it: `incorrect`. |
| R4 Data status | A right number flagged provisional (`p`) or estimated (`e`) but presented as final: `partially_correct`. |
| R5 Source currency | Check the series is not stopped and the dataset not frozen. Confirming a claim with a stopped series: `incorrect`. |
| R6 Geography | NUTS 2 statistical regions are not the 2016 administrative regions. Wrong label, right number: `partially_correct`. |
| R7 French formats | Read numbers in the convention of the text (11,035 = 11.035 in French; `billion` = 10^12; trimestre = quarter). Changing the answer: `incorrect`. |
| R8 Puzzles | Check the order against every rule. One broken rule: `incorrect`. Right order, no justification: `partially_correct`. |

## Why v2 (SIMULATED reviewers)

Guidelines v1 had only the three definitions. In the first round, the three simulated reviewers agreed on 77% of
answers (mean Cohen's kappa 0.59), and only on 34% of the grey-zone answers (units, status, labels, missing
justification). Two checks were often skipped: series status (stopped series confirmed as TRUE) and French
formats. Rules R2-R8 were written for exactly those cases. Second round: 92% agreement, kappa 0.87, grey-zone
agreement 87%, median time per review down about 15%.

*Kappa within the grey-zone subset is not meaningful after v2: almost every verdict there is `partially_correct`,
so chance agreement is close to 1 (prevalence effect). Observed agreement is reported instead.*

## Feedback template

> **Verdict:** partially_correct (R3). **What is right:** the values 8.0% and 8.5%. **What to fix:** a change between
> two rates is +0.5 percentage points; "+0.5%" would mean a relative change. **Reference:** +0.5 pp (+6.2% relative).
