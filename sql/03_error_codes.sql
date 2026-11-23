-- 03_error_codes.sql : what goes wrong. Consensus error codes (v2) by task type and language.
CREATE OR REPLACE TABLE error_codes AS
SELECT error_code, task_type, language, count(*) AS answers
FROM graded WHERE verdict <> 'correct' GROUP BY ALL ORDER BY answers DESC;

CREATE OR REPLACE TABLE error_code_totals AS
SELECT error_code, count(*) AS answers,
       count(*) FILTER (WHERE language = 'en') AS en, count(*) FILTER (WHERE language = 'fr') AS fr,
       round(100.0 * count(*) / sum(count(*)) OVER (), 1) AS share_pct,
       mode(task_type) AS main_task_type
FROM graded WHERE verdict <> 'correct' GROUP BY error_code ORDER BY answers DESC;

-- In French, how many errors are French-specific (would not exist in English)?
CREATE OR REPLACE TABLE french_specific AS
SELECT language, count(*) AS errors, count(*) FILTER (WHERE starts_with(error_code, 'FR_')) AS french_specific,
       round(100.0 * count(*) FILTER (WHERE starts_with(error_code, 'FR_')) / count(*), 1) AS pct
FROM graded WHERE verdict <> 'correct' GROUP BY language ORDER BY language;

SELECT * FROM error_code_totals;
