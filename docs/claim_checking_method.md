# Checking a claim against the source

Verdicts: **TRUE**, **FALSE**, **MISLEADING** (number right, framing wrong: unit, status, geography) and
**OUTDATED** (number right for an older date or a stopped series). Each verdict cites the series code, the period,
the extraction date and the status flag.

## Six steps

1. **Restate the claim** as: value, unit, geography, period, source named.
2. **Go to the primary source**, not to an article quoting it: Eurostat API (dataset code), INSEE BDM (idbank).
3. **Check the series itself**: title (does it say *stopped* / *série arrêtée*?), last period, last update, scope
   (all items or excluding tobacco; metropolitan France or France excluding Mayotte), base year.
4. **Read the observation status**: in Eurostat JSON-stat the `status` field (`p` provisional, `e` estimated); in
   INSEE SDMX `OBS_STATUS` / `OBS_QUAL`.
5. **Recompute** the figure (ratio, difference, sum) with the same definition as the claim.
6. **Write the verdict** with the evidence: "OUTDATED. 0.74% is series 001763852 (stopped, last point 2025-12);
   current series 011814630: +3.4% in October 2026 (extracted 2026-11-23)."

## Real traps met while building this gold set (2026-11-23)

| What we first reached for | What was wrong | Current source |
|---|---|---|
| INSEE CPI idbank 001763852 | Base 2015, **excluding tobacco**, title says *Stopped series*, last point 2025-12 | 011814630 (base 2025, all items): +3.4% y/y in 2026-10 |
| INSEE unemployment idbank 001688526 | Metropolitan France only, **stopped**, last point 2026-Q1 (7.9%) | 001688527 (France excl. Mayotte): 8.2% in 2026-Q3 |
| Eurostat `prc_hicp_manr` | Frozen at 2025-12, last update 2026-02-06 (France 0.7%) | `prc_hicp_minr` (ECOICOP ver.2): France 3.7% in 2026-10 |
| Eurostat `sts_trtu_m` latest month | France 2026-09 flagged `e`; Austria, Belgium, Germany, Spain flagged `p` on every month | same dataset, but say "may be revised" |
| Eurostat `tour_occ_nin2m` labels | NUTS 2 statistical regions (Midi-Pyrénées, Aquitaine, Rhône-Alpes) | name the level; current region if needed |

## Primary sources used

- Eurostat dissemination API, JSON-stat 2.0: `sts_trtu_m`, `tour_occ_nin2m`, `prc_hicp_minr`, `prc_hicp_manr`,
  `une_rt_m`. Reuse authorised with acknowledgement of the source.
- INSEE BDM SDMX web service: idbanks 011814630, 001763852, 001688527, 001688526. Licence Ouverte / Etalab 2.0.
