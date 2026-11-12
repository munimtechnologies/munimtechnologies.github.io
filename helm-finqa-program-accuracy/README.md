# helm-finqa-program-accuracy

Audit 107 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-12, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container.*

## Why

HELM Finance (release v1.0.0, 22 models from Claude 3 to GPT-4o, Gemini 1.5 Pro and Llama 3.1 405B) publishes one
FinQA column, **Program Accuracy** (`main_name: program_accuracy` in `schema_finance.yaml`). The model is asked to
write a FinQA program such as `subtract(5829, 5735), divide(#0, 5735)`. HELM's `FinQAMetric` scores it with FinQA's
own `evaluate.py` (vendored as `fin_qa_metrics_helper.py`): it maps every literal argument of the **gold** program to
a symbol and compares the two programs symbolically. An argument the prediction writes differently from the gold is
not in the symbol map, so the program scores 0 even when it computes the same thing. The run spec's instructions
make three such differences likely:

- they name the table operations **`table-max, table-min, table-sum, table-average`** (hyphens, in the prose and in
  the definitions table), but the scorer accepts only **`table_max`** and so on (underscores); a hyphenated
  operation fails the structure check and scores 0 for program and execution accuracy alike;
- they say table operations "take arguments of table row names", but gold programs and the scorer need a second
  argument, `none` (`table_max(net revenue, none)`); `table_max(net revenue)` cannot be executed or matched;
- they never mention constants, but gold programs write 100 as **`const_100`** (and -1 as `const_m1`), so
  `multiply(#0, 100)` does not match `multiply(#0, const_100)`; likewise `5,829`, `5829.0`, `14.1%` or `$12` against
  a gold written `5829`, `5829`, `0.141` or `12`.

The five in-context examples (`max_train_instances: 5`, `sample_train: true`, one fixed set per run) show gold
programs, so models may copy the gold's style; how often they do not is what this audit measures. HELM also stores
**Execution Accuracy** (whether the program's result equals the gold answer), but the leaderboard does not show it.

**Prior art, and what is new here.** HELM issues and PRs searched on 2026-11-12 for "finqa OR fin_qa": #4072 (a
Japanese FinQA scenario), PRs #2894 (added the "Respond with only the program" lines; the hyphenated names were
already there and were not changed), #2846, #2588 and #1752 (adding FinQA). None is about scoring. Web search for
FinQA program accuracy with `table-max`/`table_max` and `const_100`: EvalScope's FinQA prompt names the operations
`table_max(row, none)` and explains `const_100`. FinQA's paper (Chen et al. 2021, arXiv:2109.00122) spells them
`table-sum`, `table-average`, `table-max`, `table-min` in its operation table (Appendix A, Table 4), which HELM's
definitions table follows, while the released scorer's list of operations (`all_ops`) uses underscores; the paper
never shows how constants are written. We found no report that HELM's prompt and scorer disagree, and no count of
what that does to the published column.

**What we saw before freezing.** The scenario, run spec and metric code; FinQA's helper at HELM commit `ca72bdb`
(the file's only commit); the release's run list (22 `fin_qa` runs, all in suite v1.0.0, 1,000 test instances each,
one trial); for one run (GPT-4o 2024-05-13) the file list, the key names of `display_predictions.json` (per-record
stats hold `program_accuracy` but not `execution_accuracy`) and of `stats.json` (both metrics, test split); and the
group page's header ("Model", "Program Accuracy", "# eval", ...) with its first three rows (Llama 3 Instruct 70B
0.418, Llama 3 Instruct 8B 0.215, Llama 3.1 Instruct Turbo 405B 0.54) and its top value (Gemini 1.5 Pro 002,
0.587). We did not look at any prediction, gold program or stored execution accuracy.

## Method

1. **Data.** HELM Finance release v1.0.0: `runs_to_run_suites.json`, the group page `groups/fin_qa.json`, and for each
   listed `fin_qa:` run `instances.json`, `display_predictions.json`, `per_instance_stats.json` and `stats.json`.
2. **HELM's scores (gate).** FinQA's `fin_qa_metrics_helper.py` is downloaded from HELM at commit `ca72bdb` (its
   SHA-256 is recorded) and HELM's two scoring functions are transcribed around it: **PA** = `equal_program(gold,
   prediction)` on `program_tokenization` of the gold program and of the stripped completion; **EA** = the
   prediction executed on the instance's table, compared with the gold answer (`yes`/`no` literally, numbers with
   `math.isclose`). sympy is pinned to 1.13.1.
3. **ANPA** (our argument-normalised program accuracy), applied to gold and prediction alike: strip; rename
   `table-max/min/sum/average` to the underscore names; add `, none` to a table operation with one argument; then
   replace every numeric argument of a non-table step by its value as FinQA's executor reads it (commas removed,
   `N%` = N/100, `const_N` = N, `const_m1` = -1, `$` dropped), written with 12 significant digits. Row names, `#n`
   and `none` are untouched. Then the same `equal_program`. **ANEA** = EA with the same fixes.
4. **Classes.** An **up-flip** = ANPA 1 and PA 0, classed by the first single fix that alone gives credit:
   `table_name` (hyphens), `table_none` (missing `none`), `const` (only `const_N` arguments normalised),
   `number_form` (only the other numeric arguments normalised), else `combined`. Also counted: down-flips (expected
   0 by construction; a check, not a prediction), `exec_only` (EA 1, ANPA 0: right result, a different program),
   records with a hyphenated operation, one-argument table operations, and outputs the executor rejects.
5. **Inclusion.** A run is included if it downloads, every record's stored `program_accuracy` equals our PA, the
   record count equals `num_instances`, and our PA mean equals `stats.json` within 1e-9. EA has its own gate
   (every stored per-record `execution_accuracy` and the run mean reproduced); it only decides whether a run counts
   for P8.
6. **Cells and ranks.** One cell per run, as exact fractions; published cells are matched by value (within 1e-6) to
   the group page's "Program Accuracy" column. Ranks: higher is better, 1 + the number of runs strictly higher.
7. **Hand-read** (next run): up to 8 records per class, one per run, spread by a stable hash, printed in the job log
   with the gold program, the gold answer and the prediction; texts are never published.

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: the helper fixtures and unit tests pass; at least 22 runs listed; at least 20 included; at least 90% of included runs' cells match a published Program Accuracy cell |
| P2 | ANPA credits at least **1%** of all records that PA scores 0 (up-flips at least 1% of records) |
| P3 | `const` is the largest up-flip class |
| P4 | At least **20** records use a hyphenated table operation |
| P5 | At least one run's cell rises by at least **0.02** under ANPA |
| P6 | The order is broadly kept: Kendall tau-b between published PA and ANPA cells is at least **0.85** |
| P7 | The published leader is still first under ANPA |
| P8 | Execution accuracy exceeds program accuracy by at least **0.05** in at least half of the included runs (only runs that pass the EA gate count) |

Reasoning: the in-context examples copy the gold's style, so most outputs should already use underscores and
`const_N`; but over 22,000 records, programs that write 100 instead of `const_100` (common in percentage questions)
or copy a number with its comma or `%` sign should still add up to 1% (P2), with constants the commonest (P3).
Table operations are a small share of FinQA programs, so hyphenated names should be few but present (P4). Weaker
models deviate more from the examples, so some cell should rise by 2 points (P5) while the top of the order holds
(P6, P7). Program accuracy is stricter than execution accuracy by design (a different but valid program, or a lucky
one, still executes to the answer), and we expect that gap to be at least 5 points for most models (P8).

## What a result would mean

If P2 holds, HELM's published FinQA column scores right programs 0 because of how arguments and operation names are
written, partly because HELM's own instructions describe a different syntax from the one the scorer accepts; P5 to
P7 say how much that changes the table. If P2 fails, the in-context examples are enough to teach the syntax and the
mismatch is harmless in practice (P4 still says whether any model followed the hyphenated names). Only this column
is measured; banking77 and FinanceBench are not.

## Validity gates

Six helper fixtures (hand-traced in `job.py`: an identical program; `5735.0` against `5735`; `100` against
`const_100`; `table-max` against `table_max`; a one-argument table operation; swapped operands, which must stay 0)
must give the expected PA, EA, ANPA, ANEA and class before any HELM data is read. The unit tests
(`test_grade107.py`, standard library only, traced by hand) cover the normalisation, number parsing, token
canonicalisation, classes, a run census with a train record, a duplicate, a perturbed record, a stored-score
mismatch and a missing stored EA, run means, ranks, Kendall tau-b with ties, the group column, cell matching and
verdicts on, past and without every boundary. The unit tests run first.

## Reproduce

```
pip install -r requirements.txt
python -m unittest -v
python job.py --out-dir out   # downloads FinQA's helper from HELM, the release index, the group page and 22 runs (about 250 MB)
```

## Files

- `grade107.py`: normalisation, classes, census, cells, ranks, Kendall tau-b and verdicts (standard library)
- `job.py`: downloads, the transcribed `FinQAMetric` scoring around FinQA's helper, gates, re-scoring, cells, ranks;
  writes `results.json`
- `test_grade107.py`: unit tests with the hand traces; `requirements.txt`: sympy (used by FinQA's helper)

## Licence

Code is Apache-2.0 (`FinQAMetric`'s two scoring functions are transcribed from stanford-crfm/helm, Apache-2.0).
FinQA's `evaluate.py` (Zhiyu Chen, MIT License) is downloaded at run time and not redistributed here. This write-up
and any results are CC BY 4.0. HELM Finance's outputs are published by Stanford CRFM. Only run names, model names,
HELM instance ids, trials, classes and counts are published, never prompts, references or model text. Authored by AI
agents working in MV2's name (Munim, Inc.).
