# Data issues log

Issues met while building the gold set (extraction 2026-11-23). Each one became a task or a rubric rule.

| # | Source | Issue | Effect if missed | Handling |
|---|---|---|---|---|
| 1 | INSEE BDM 001763852 | CPI base 2015, all items **excluding tobacco**, marked *Stopped series*; last point 2025-12 (119.76) | Confirms a 0.7% inflation rate that is 10 months old and on another scope | Current series 011814630 used; claim tasks with verdict OUTDATED; rule R5 |
| 2 | INSEE BDM 001688526 | Unemployment, metropolitan France, stopped at 2026-Q1 | Quotes 7.9% instead of 8.2% (2026-Q3, France excl. Mayotte, 001688527) | Same |
| 3 | Eurostat `prc_hicp_manr` | Dataset frozen at 2025-12 (last update 2026-02-06); successor `prc_hicp_minr` | Quotes December 2025 as "latest" | Successor found in the Eurostat catalogue; claim tasks OUTDATED |
| 4 | Eurostat `sts_trtu_m` | Flags: `p` on every month since 2022 for AT, BE, DE, ES; FR `p` from 2024-09 and `e` for 2026-09; IE, NL, PL, SE `p` on recent months | Provisional values presented as final | Reference answers state the status; rule R4; PROVISIONAL_AS_FINAL code |
| 5 | Eurostat `tour_occ_nin2m` | `time` holds the **year** and months are in a separate `month` dimension (13 values incl. total). A naive flatten returns 4 "periods" | Monthly analysis impossible; totals double-counted if the annual total is kept | Parser rebuilds `YYYY-MM` and drops the total; 8 regions x 48 months = 384 values |
| 6 | Eurostat `tour_occ_nin2m` | Labels are NUTS 2 (2021) statistical regions: Midi-Pyrénées, Aquitaine, Rhône-Alpes, Nord-Pas-de-Calais | Confused with the 2016 administrative regions | Rule R6; NUTS_LABEL code; current region given in the reference |
| 7 | Eurostat labels (encoding) | Correct UTF-8 in the API. Our own Windows console printed "Midi-Pyr�n�es"; decoding UTF-8 as cp1252 gives "Midi-PyrÃ©nÃ©es". The FRL0 label uses a typographic apostrophe (U+2019) | Broken labels, failed joins on "Côte d'Azur" | Decode bytes as UTF-8 explicitly; join on codes, never on labels |
| 8 | Eurostat `une_rt_m` | No `EA20` aggregate returned (euro-area composition changed in 2026) | Missing benchmark | Countries only for unemployment tasks |
| 9 | Wikipedia | Articles change; leads may name people | Gold answer drifts; personal names in the gold set | Fixed revision ids (`oldid`); summaries without names; full texts kept out of the repository |

## Simulated-data notes

- The model and the reviewers are **simulated** (seed 42). Their error mix illustrates the method; it is not a
  measurement of any real model.
- The lower raw pass rate in French (54% vs 64%) is a **composition effect**: French items were rated harder more
  often (45% at difficulty 3 vs 24%). At equal difficulty the gap is within 2 points; standardised rates are equal
  (59.5% vs 59.1%). Not reported as a finding.
