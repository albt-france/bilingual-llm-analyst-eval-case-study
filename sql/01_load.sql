-- 01_load.sql : load the gold set, the simulated answers and reviews, and the public extracts; build the consensus verdict.
CREATE OR REPLACE TABLE tasks AS SELECT * FROM read_csv('data/processed/tasks.csv', header = true);
CREATE OR REPLACE TABLE answers AS SELECT * FROM read_csv('data/processed/model_answers.csv', header = true);
CREATE OR REPLACE TABLE reviews AS
SELECT answer_id, reviewer, guidelines, verdict, coalesce(error_code, '') AS error_code, comment, seconds_spent
FROM read_csv('data/processed/reviews.csv', header = true, types = {'error_code': 'VARCHAR'});
CREATE OR REPLACE TABLE retail AS
SELECT * FROM read_csv('data/public/eurostat_retail.csv', header = true, types = {'time': 'VARCHAR', 'status': 'VARCHAR'});

-- Consensus per answer and guideline version: majority of the 3 reviewers; three different verdicts -> partially_correct.
CREATE OR REPLACE TABLE consensus AS
WITH v AS (SELECT answer_id, guidelines, verdict, count(*) AS n FROM reviews GROUP BY ALL),
top AS (SELECT *, row_number() OVER (PARTITION BY answer_id, guidelines
                                     ORDER BY n DESC, verdict = 'partially_correct' DESC) AS rk FROM v),
code AS (SELECT answer_id, guidelines, mode(error_code) FILTER (WHERE error_code <> '') AS error_code
         FROM reviews GROUP BY ALL)
SELECT t.answer_id, t.guidelines, CASE WHEN t.n >= 2 THEN t.verdict ELSE 'partially_correct' END AS verdict,
       CASE WHEN t.n >= 2 AND t.verdict = 'correct' THEN '' ELSE coalesce(c.error_code, '') END AS error_code
FROM top t JOIN code c USING (answer_id, guidelines) WHERE t.rk = 1;

-- Final graded table (guidelines v2)
CREATE OR REPLACE TABLE graded AS
SELECT a.answer_id, a.task_id, a.language, a.difficulty, a.task_type, t.subtype, c.verdict, c.error_code,
       (c.verdict = 'correct')::INT AS pass
FROM answers a JOIN consensus c ON c.answer_id = a.answer_id AND c.guidelines = 'v2'
JOIN tasks t ON t.task_id = a.task_id;

-- Real data issue: observation status flags in the Eurostat retail extract
CREATE OR REPLACE TABLE retail_flags AS
SELECT geo, count(*) FILTER (WHERE status = 'p') AS provisional, count(*) FILTER (WHERE status = 'e') AS estimated,
       count(*) AS values_total, min(time) FILTER (WHERE status IS NOT NULL) AS first_flagged
FROM retail GROUP BY geo ORDER BY provisional DESC, geo;

SELECT (SELECT count(*) FROM tasks) AS tasks, (SELECT count(*) FROM answers) AS answers,
       (SELECT count(*) FROM reviews) AS reviews, (SELECT count(*) FROM graded) AS graded;
