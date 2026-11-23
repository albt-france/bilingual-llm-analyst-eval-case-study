-- 05_reviewer_agreement.sql : pairwise agreement and Cohen's kappa, guidelines v1 vs v2.
-- kappa = (p_o - p_e) / (1 - p_e); p_o = observed agreement, p_e = chance agreement from each reviewer's own verdict mix.
CREATE OR REPLACE TABLE pairs AS
SELECT a.guidelines, a.reviewer AS r_a, b.reviewer AS r_b, a.answer_id, a.verdict AS v_a, b.verdict AS v_b,
       g.error_code IN ('PROVISIONAL_AS_FINAL', 'PCT_VS_POINTS', 'NUTS_LABEL', 'UNJUSTIFIED_STEP', 'MISSED_BLOCK') AS grey_zone
FROM reviews a
JOIN reviews b ON a.answer_id = b.answer_id AND a.guidelines = b.guidelines AND a.reviewer < b.reviewer
JOIN graded g ON g.answer_id = a.answer_id;

CREATE OR REPLACE TABLE agreement AS
WITH base AS (
  SELECT guidelines, r_a, r_b, 'all answers' AS scope, v_a, v_b FROM pairs
  UNION ALL
  SELECT guidelines, r_a, r_b, 'grey-zone answers', v_a, v_b FROM pairs WHERE grey_zone),
po AS (SELECT guidelines, r_a, r_b, scope, count(*) AS n, avg((v_a = v_b)::INT) AS p_o FROM base GROUP BY ALL),
marg AS (
  SELECT guidelines, r_a, r_b, scope, cat, avg((v_a = cat)::INT) AS pa, avg((v_b = cat)::INT) AS pb
  FROM base, (VALUES ('correct'), ('partially_correct'), ('incorrect')) c(cat) GROUP BY ALL),
pe AS (SELECT guidelines, r_a, r_b, scope, sum(pa * pb) AS p_e FROM marg GROUP BY ALL)
SELECT po.scope, po.guidelines, po.r_a || '-' || po.r_b AS pair, po.n, round(po.p_o, 3) AS observed_agreement,
       round(pe.p_e, 3) AS chance_agreement, round((po.p_o - pe.p_e) / (1 - pe.p_e), 3) AS cohen_kappa
FROM po JOIN pe USING (guidelines, r_a, r_b, scope) ORDER BY scope, pair, guidelines;

CREATE OR REPLACE TABLE confusion_r1_r3 AS
SELECT guidelines, v_a AS r1_verdict,
       count(*) FILTER (WHERE v_b = 'correct') AS r3_correct,
       count(*) FILTER (WHERE v_b = 'partially_correct') AS r3_partially_correct,
       count(*) FILTER (WHERE v_b = 'incorrect') AS r3_incorrect
FROM pairs WHERE r_a = 'R1' AND r_b = 'R3' GROUP BY ALL
ORDER BY guidelines, list_position(['correct', 'partially_correct', 'incorrect'], any_value(v_a));

CREATE OR REPLACE TABLE time_per_review AS
SELECT r.guidelines, a.task_type, count(*) AS reviews, median(r.seconds_spent) AS median_s,
       quantile_cont(r.seconds_spent, 0.9) AS p90_s
FROM reviews r JOIN answers a USING (answer_id) GROUP BY ALL ORDER BY r.guidelines, a.task_type;

SELECT scope, guidelines, round(avg(cohen_kappa), 3) AS mean_kappa FROM agreement GROUP BY ALL ORDER BY ALL;
