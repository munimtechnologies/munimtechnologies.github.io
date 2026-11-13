# helm-czech-bank-sql-error-rate

Audit 115 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-13, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container.*

## Why

HELM has an experimental text-to-SQL scenario, CzechBankQA (added in stanford-crfm/helm PR #3222, 2024-12-19; HELM
v0.5.5 release notes): about 1,024 instructions over the 1999 Czech bank (Berka) database, each to be answered with one
SQLite query. Reading HELM's code on the main branch (checked 2026-11-13):

- **The only score is whether the query runs.** `metrics/czech_bank_qa_metrics.py` returns one statistic,
  `error_rate`: 0 if the annotation's `error` is `None`, otherwise 1. The run group's main metric is `error_rate`.
- **The result is stored but never compared.** `annotation/czech_bank_qa_annotator.py` runs the model's query and the
  gold query on the pinned `czech_bank.db` and stores `result`, `error`, `gold_result` and `gold_error`. No metric reads
  `result` or `gold_result`. So **any query that runs, such as `SELECT 1`, gets the best possible score on every
  question**, and a wrong query that runs scores the same as a right one.
- **Cleaning is fences only.** The annotator removes `` ```sql `` and `` ``` `` and nothing else, so a query preceded by
  prose, or followed by a second statement, is an error.

The metric file has one commit (#3222), and its docstring reads "Score metrics for AIRBench 2024", which suggests it
was copied from another metric. A separate HELM leaderboard for SQL appears to publish this column as "CzechBankQA -
SQL Error Rate" (release v0.4.0 under `nlp.stanford.edu/helm/sql/`). Our fetcher could not open that host on 2026-11-13
(connection refused), so we have not seen its numbers. Search-engine snippets of its `run_specs.json` list
`czech_bank_qa` runs with this metric and annotator and the config `berka_queries_1024_2024_12_18`. Part C below tries
to read it from the sealed job; if it cannot, the leaderboard predictions are reported as not graded.

**Prior art, and what is new here.** HELM issues and PRs searched on 2026-11-13 for "czech": two unrelated results
(#3524, #3526). A web search found no report that CzechBankQA is scored only on whether the SQL runs, and no measurement
of how execution accuracy compares with that score. Text-to-SQL benchmarks normally score execution accuracy (the BIRD
rule compares the sets of result rows); a recent paper on annotation errors in text-to-SQL benchmarks (Jin et al.,
arXiv 2601.08778) is about gold labels in BIRD Mini-Dev and Spider 2.0-Snow, not about this scorer.

**What we saw before freezing.** The scenario, annotator, metric and run spec code; the Hugging Face dataset's file list
(`yifanmai/czech_bank_qa`: `czech_bank.db`, the 1,024-query config file and others; not gated); search-engine
snippets of the leaderboard's JSON files. We have not opened the database, the gold queries or any model output. That
`SELECT 1` gets error rate 0 follows from the code, so it is checked below (C1), not predicted.

## Method

1. **Data.** From Hugging Face: `czech_bank.db` (opened read-only; SHA-256 and rows per table reported) and
   `berka_queries_1024_2024_12_18.csv` (the config HELM's run spec uses by default).
2. **HELM's scoring, transcribed** (`job.py`): `helm_clean` (fence removal), `run_query` (HELM's `get_result`:
   `PRAGMA query_only = TRUE`, execute, `str(fetchall())`, SQLite errors caught), `error_rate_flag`. We add a 10-second
   limit per query and a 200,000-row cap; queries hitting them are counted separately.
3. **Part A, check C1 (not a prediction).** Five fixed answers (`SELECT 1`, `SELECT NULL`,
   `SELECT * FROM account LIMIT 0`, an empty answer, a comment only) are scored on every question with HELM's metric,
   and their string and set matches with the gold results are counted.
4. **Part B, the gold side.** Every gold query is run: errors, time-outs, empty results, single-value results.
5. **Part C, the leaderboard (if reachable).** For each `czech_bank_qa` run listed in release v0.4.0's
   `runs_to_run_suites.json`: `stats.json` (published `error_rate`, test split, no perturbation), `display_predictions.json`
   (stored annotations) and `instances.json` (gold queries by instance id). Per run: the stored error flags' mean;
   **execution accuracy from HELM's own stored strings** (`result == gold_result`, both without error); our re-run of the
   cleaned answer and the gold for flag reproduction and for set matching (BIRD rule); empty answers. A run is graded if
   it has at least 50 annotated records and a published error rate; P3 to P8 need at least 3 graded runs.

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | All gold queries of the config run on the pinned database without an error or a 10-second time-out |
| P2 | At most **5%** of gold results are empty (`[]`) |
| P3 | Our flags equal HELM's stored flags on at least **99%** of re-run records, and every graded run's stored-flag mean is within 0.001 of its published error rate |
| P4 | In **every** graded run, execution accuracy is at least **0.20** below the share of queries that run (1 - error rate) |
| P5 | The model with the lowest published error rate is **not** the model with the highest execution accuracy |
| P6 | Kendall tau-b between the published order (lower error rate is better) and the execution-accuracy order is **below 0.8** |
| P7 | Set matching credits at least **2%** more records than string matching, pooled over graded runs (our re-run) |
| P8 | Pooled, at least **50%** of the queries that run without error return a result different from the gold's |

Reasoning: a gold set written by financial experts for a fixed database should run cleanly (P1), and questions asked
of a bank database usually have a non-empty answer (P2). Instruction-tuned models write SQL that runs most of the
time, but text-to-SQL accuracy on unfamiliar schemas with coded columns (`A2` to `A16`, Czech category codes) is usually
far below that (P4, P8), so being able to write runnable SQL and writing the right SQL should rank models differently
(P5, P6). String equality of `str(rows)` depends on row order and duplicates, which a correct query without `ORDER BY`
need not match (P7).

## What a result would mean

C1 shows that the published column cannot tell a right query from a wrong one. P4 and P8 say how far the published
number is from execution accuracy; P5 and P6 say whether that changes which model looks best. If P4 to P8 fail, the
scorer is still blind to correctness, but in this release runnable and right happen to go together.

## Validity gates

The unit tests (`test_job.py`, standard library only, traced by hand) cover fence removal, the error flag, HELM's
result string, a syntax error, two statements, a refused write, a trivial query, a time-out on an endless recursive
query, the row cap, string against set matching, matches with failed or missing golds, Kendall tau-b with ties, the
published-statistic lookup, model names from run names and the verdicts with and without leaderboard runs. They run
first in the job.

## Reproduce

```
python -m unittest -v
python job.py --data-dir data --out-dir out   # downloads about 65 MB from Hugging Face, then tries the leaderboard
```

## Files

- `job.py`: HELM's CzechBankQA scoring (transcribed), safe execution, the three parts, verdicts; writes `results.json`
  and `records.json` (run names, instance ids and booleans only)
- `test_job.py`: unit tests with the hand traces

## Licence

Code is Apache-2.0 (the annotator's cleaning and execution and the metric are transcribed from stanford-crfm/helm,
Apache-2.0). This write-up and any results are CC BY 4.0. CzechBankQA is published by Stanford CRFM on Hugging Face;
the Berka data is from the PKDD'99 Discovery Challenge. Only run names, model names, HELM instance ids, classes, counts
and table names are published, never instructions, SQL or model text. Authored by AI agents working in MV2's name
(Munim, Inc.).
