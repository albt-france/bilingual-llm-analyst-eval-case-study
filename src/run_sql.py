"""Run sql/01..05 in DuckDB and export the result tables to data/processed/.
Run from the repository root:  python src/run_sql.py
"""
import glob
import os

import duckdb

OUT = os.path.join("data", "processed")
EXPORT = ["graded", "consensus", "retail_flags", "accuracy_by_type", "accuracy_by_subtype", "accuracy_by_difficulty",
          "error_codes", "error_code_totals", "french_specific", "language_gap_raw", "language_gap_strata",
          "language_gap_standardised", "agreement", "confusion_r1_r3", "time_per_review"]

con = duckdb.connect()
for path in sorted(glob.glob(os.path.join("sql", "*.sql"))):
    sql = open(path, encoding="utf-8").read()
    stmts = [s for s in sql.split(";\n") if s.strip() and not all(
        l.strip().startswith("--") or not l.strip() for l in s.splitlines())]
    last = None
    for s in stmts:
        last = con.execute(s)
    print(f"== {os.path.basename(path)}")
    print(last.df().head(14).to_string(index=False))
for t in EXPORT:
    con.execute(f"SELECT * FROM {t}").df().to_csv(os.path.join(OUT, f"{t}.csv"), index=False)
print(f"exported {len(EXPORT)} tables to {OUT}")
