-- 02_accuracy.sql : pass rate (consensus verdict = correct, guidelines v2) by task type, language and difficulty.
CREATE OR REPLACE TABLE accuracy_by_type AS
SELECT task_type, count(*) AS answers, round(100 * avg(pass), 1) AS pass_pct,
       round(100 * avg((verdict = 'partially_correct')::INT), 1) AS partial_pct,
       round(100 * avg((verdict = 'incorrect')::INT), 1) AS incorrect_pct
FROM graded GROUP BY task_type ORDER BY pass_pct;

CREATE OR REPLACE TABLE accuracy_by_subtype AS
SELECT task_type, subtype, count(*) AS answers, round(100 * avg(pass), 1) AS pass_pct
FROM graded GROUP BY ALL ORDER BY task_type, pass_pct;

CREATE OR REPLACE TABLE accuracy_by_difficulty AS
SELECT difficulty, language, count(*) AS answers, round(100 * avg(pass), 1) AS pass_pct
FROM graded GROUP BY ALL ORDER BY difficulty, language;

SELECT * FROM accuracy_by_type;
