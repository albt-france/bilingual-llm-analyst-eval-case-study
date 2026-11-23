-- 04_language_gap.sql : is the model worse in French? Raw gap, then stratified by item difficulty.
CREATE OR REPLACE TABLE language_gap_raw AS
SELECT language, count(*) AS answers, round(100 * avg(pass), 1) AS pass_pct,
       round(100 * avg((difficulty = 3)::INT), 1) AS pct_hard_items
FROM graded GROUP BY language ORDER BY language;

CREATE OR REPLACE TABLE language_gap_strata AS
SELECT difficulty,
       count(*) FILTER (WHERE language = 'en') AS n_en, count(*) FILTER (WHERE language = 'fr') AS n_fr,
       round(100 * avg(pass) FILTER (WHERE language = 'en'), 1) AS pass_en,
       round(100 * avg(pass) FILTER (WHERE language = 'fr'), 1) AS pass_fr,
       round(100 * (avg(pass) FILTER (WHERE language = 'fr') - avg(pass) FILTER (WHERE language = 'en')), 1) AS gap_fr_minus_en
FROM graded GROUP BY difficulty ORDER BY difficulty;

-- Direct standardisation: apply each language's pass rate per difficulty to the pooled difficulty mix.
CREATE OR REPLACE TABLE language_gap_standardised AS
WITH mix AS (SELECT difficulty, count(*) / sum(count(*)) OVER () AS w FROM graded GROUP BY difficulty),
r AS (SELECT language, difficulty, avg(pass) AS p FROM graded GROUP BY ALL)
SELECT r.language, round(100 * sum(r.p * mix.w), 1) AS standardised_pass_pct
FROM r JOIN mix USING (difficulty) GROUP BY r.language ORDER BY r.language;

SELECT 'raw' AS view, language, pass_pct FROM language_gap_raw
UNION ALL SELECT 'standardised', language, standardised_pass_pct FROM language_gap_standardised;
