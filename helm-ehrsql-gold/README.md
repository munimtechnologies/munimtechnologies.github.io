# helm-ehrsql-gold

Audit 113 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-12, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container.*

## Why

MedHELM (release v4.0.0, 13 models) includes EHRSQL (Lee et al., arXiv:2301.07695): 1,000 questions about a clinical
database (eICU), each to be answered with one SQLite query, or with an empty answer if the question cannot be answered
from the database. Its leaderboard column `EHRSQLExeAcc` is the share of questions where the model's query returns the
same result as the gold query. Reading HELM's code (`ehr_sql_scenario.py`, `annotation/ehr_sql_annotator.py`,
`metrics/ehr_sql_metrics.py` on the main branch, checked 2026-11-12):

- **Template values stand in for empty gold results.** The annotator runs the gold query on a pinned `eicu.sqlite`
  (528,384 bytes). If that returns no rows or fails, it takes `extra_data["value"]` as the gold result. In EHRSQL this
  field holds the values that were filled into the question template (a patient id, a drug or lab name), not an
  answer. The gold "result" becomes a list of strings, for example a patient id and a lab name. The metric
  compares `set(predicted rows)` with `set(gold)`, and a row (a tuple) never equals a string. **On these questions no
  SQL query can earn credit.**
- **An empty answer is the only way to match an empty gold result.** When the gold result is empty (the unanswerable
  questions, whose gold query is the string `null`, and any answerable question with no template values), credit needs
  an empty model answer. A query that correctly returns no rows scores 0.
- **No EHRSQL post-processing.** EHRSQL's own `evaluate.py` lower-cases both queries, anchors `current_time` and `'now'`
  at 2105-12-31 23:59:00 (the database's "today"), swaps `%y` for `%Y` and fills vital-sign bounds before running them.
  HELM runs the gold query as written, so SQLite's `current_time` is the wall-clock time of day.

**Prior art, and what is new here.** HELM issues and PRs searched on 2026-11-12 for "ehrsql" and "ehr_sql": only #3403
(MedHELM v1, which added the code) and #3586 (an o4-mini token-limit error). The metric file has two commits (#3403,
#3829 metadata), the annotator three (#3403, #3598 logging, #4018 MedHELM models). The MedHELM paper
(arXiv:2505.23802) reports EHRSQL among the hardest tasks; the EHRSQL 2024 shared task (arXiv:2405.06673) defines
execution accuracy as matching answers. A web search found no report of either problem and no count of their effect.

**What we saw before freezing.** The scenario, annotator and metric code; EHRSQL's `evaluate.py` post-processing; the
run spec (the prompt asks for an empty answer to unanswerable questions); the release's 13 `ehr_sql` runs; the group page
for all 13 models (GPT-4o first at 0.320, o4-mini 0.290, o3-mini 0.272, GPT-5 0.233; Llama 3.3 last at 0.074);
GPT-4o's `stats.json` (query validity 0.345; 67.3% of questions answerable; 69.9% answered with a non-empty text); the
first 137 answers of GPT-4o (46 credited: 35 empty answers and 11 queries; 42 empty answers in all, 7 of them not
credited); three of GPT-4o's stored gold results (one a result row, two template values); the first entries of
`instances.json` (8 golds `null`); and the size of the pinned database. That no template-value gold is ever credited
follows from the code, so it is checked below (C1), not predicted.

## Method

1. **Data.** MedHELM release v4.0.0: `runs_to_run_suites.json`, the group page `groups/ehr_sql.json`, and for each listed
   `ehr_sql:` run `display_predictions.json` (answers, stored annotations and per-record scores) and `stats.json`; the
   gold queries, template values and `is_impossible` flags from the first run's `instances.json`; the pinned
   `eicu.sqlite` (opened read-only; size, SHA-256 and rows per table reported).
2. **HELM's scores (gate).** `EhrSqlMetric` is transcribed (`grade113.py`). A run is **included** if it downloads, every
   record has its annotation and both stored per-record scores (execution accuracy and query validity) equal ours, the
   record count equals `num_instances`, and the run mean equals `stats.json` within 1e-9. Published cells are matched
   by value (within 1e-6) to the group page's `EHRSQLExeAcc` column.
3. **Gold classes** (stored annotation): `rows`, `slot` (exactly the template values, in order), `empty`, `other`.
   **Answer classes:** `abstain` (empty answer), `error`, `rows`, `empty_result`.
4. **Check C1 (not a prediction).** No record whose stored gold is `slot` is credited in any included run. Also reported:
   for how many questions the stored gold is identical in all included runs.
5. **Gold re-runs.** Each gold query is run by us as HELM runs it (`raw`) and after EHRSQL's post-processing
   (`official`; `null` golds are not run). Answerable questions whose result class or rows differ are counted.
6. **Re-scores**, one cell per run, exact fractions:
   - `sql_only`: HELM's stored credit on answerable questions only (an empty answer to an unanswerable question earns
     nothing);
   - `fixed`: HELM's stored executions, gold = the gold query's own result (HELM's stored rows, otherwise our `raw` run;
     an empty result matches an empty result; a failed gold query credits nobody), unanswerable questions credit an
     empty answer;
   - `official` (reported, not predicted): the answer's SQL extracted as HELM does, both queries post-processed as in
     EHRSQL and run by us on the same database, first-100 sorted string comparison; an empty or `null` answer is an
     abstention, credited on unanswerable questions only.
7. **Ranks.** Higher is better, 1 + the number of runs strictly higher. Kendall tau-b of each re-score against the
   published cells, and models moving 3 or more places.
8. **Hand-read** (next run): up to 6 `slot` and `other` golds, 6 golds that change under post-processing and 6 answers
   that return no rows on a `slot` gold, printed in the job log only; SQL and answers are never published.

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: the unit tests pass; 1,000 test ids; at least 13 runs listed; at least 12 included; at least 90% of included runs' cells match a published `EHRSQLExeAcc` cell |
| P2 | At least **25%** of answerable questions have a template-value (`slot`) gold |
| P3 | The pinned `eicu.sqlite` holds fewer than **10,000** rows across all its tables |
| P4 | EHRSQL's post-processing changes the gold result of at least **10%** of answerable questions |
| P5 | Our `raw` run of the gold query reproduces at least **95%** of the stored `rows` golds |
| P6 | In at least **7** included runs, more than half of the credited records are empty answers |
| P7 | Under `fixed`, at least **10** included runs gain at least **0.03** |
| P8 | GPT-4o, first on the published column, is **not** first under `sql_only` |

Reasoning: a half-megabyte database cannot hold much of eICU, so many gold queries (lookups for one patient, one drug
or one time window) should return nothing (P3) and get template values as gold (P2). Queries that mention a time
window (`current_time`, `%y`) should change once anchored at the database's own "today" (P4). Count and aggregate golds
return a row even on a small database, and these should be reproduced by our run (P5). In GPT-4o's first 137 answers,
35 of 46 credits were empty answers; we expect most models to earn most of their credit the same way (P6), so ranking
on answerable questions alone should move GPT-4o off the top (P8). Counting a correct empty result as correct should
lift most models by 0.03 or more (P7).

## What a result would mean

C1 says how many questions the leaderboard cannot score for any SQL. P2 and P3 say how much of EHRSQL survives on
HELM's database. P6 and P8 say whether `EHRSQLExeAcc` mostly measures willingness to answer with nothing. P4, P7 and the
`official` cells say how much the published numbers would move under EHRSQL's own evaluation rules. If P2 to P8 fail,
the code problems are real but small in this release.

## Validity gates

The unit tests (`test_grade113.py`, standard library only, traced by hand) cover HELM's scorer (set comparison,
duplicates, template-value golds, empty golds, missing gold query), validity, SQL extraction (`<sql>` tags, code
fences, empty), the gold and answer classes, the post-processing (time anchor, `'now'`, lower-casing, quotes, `%y`,
vital bounds known and unknown), the comparison key, execution on an in-memory database including errors and an
interrupted endless query, both re-scores, a run census with a perturbed record, a non-test record, a duplicate,
mismatched and missing stored values, two trials, the release helpers, ranks, Kendall tau-b, the group column, cell
matching and the verdicts on, past and without every boundary. The unit tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads the release index, the group page, 13 runs and the 0.5 MB database
```

## Files

- `grade113.py`: HELM's scoring, validity and SQL extraction (transcribed), classes, EHRSQL-style post-processing and
  comparison, safe execution, census, cells, ranks, Kendall tau-b and verdicts (standard library)
- `job.py`: downloads, gold re-runs, gates, re-scores, cells, ranks; writes `results.json`
- `test_grade113.py`: unit tests with the hand traces

## Licence

Code is Apache-2.0 (`EhrSqlMetric`'s scoring and `EhrSqlAnnotator`'s SQL extraction are transcribed from
stanford-crfm/helm, Apache-2.0; the post-processing follows glee4810/EHRSQL's `evaluate.py`). This write-up and any
results are CC BY 4.0. MedHELM's outputs are published by Stanford CRFM; EHRSQL is by Lee et al. Only run names, model
names, HELM instance ids, classes, counts and table names are published, never questions, SQL or model text. Authored
by AI agents working in MV2's name (Munim, Inc.).
