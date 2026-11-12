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

## Results

*Added 2026-11-12. The sealed job `helm-finqa-program-accuracy-v1` ran once, on 2026-11-12 from 15:25 to 15:29 UTC,
and exited 0. Full numbers: [results.json](results.json). Graded and hand-read by AI agents working in MV2's name; no
human has checked these counts.*

**8 of 8 predictions held** (P8 exactly on its boundary). The plan above is unchanged.

| # | Verdict | What was measured |
| --- | --- | --- |
| P1 | HELD | all six helper fixtures and the unit tests passed (helper SHA-256 `b07e4522...486a`); 22 runs listed, 22 included; every stored per-record score and run mean reproduced; 22 of 22 cells match the published column; all 22 runs also pass the execution-accuracy gate |
| P2 | HELD | **539 of 22,000 records (2.45%)** are scored 0 by HELM and 1 once arguments and operation names are normalised; that is 6.3% as many as the 8,600 credits HELM publishes. No record goes down |
| P3 | HELD | up-flips by class: `const` 260, `table_name` 101, `number_form` 86, `combined` 84, `table_none` 8 |
| P4 | HELD | **625 records** use a hyphenated table operation, as HELM's own instructions spell it; the scorer's structure check rejects that spelling |
| P5 | HELD | largest rise: Gemini 1.5 Pro 002, **0.587 to 0.654 (+0.067)**; Gemini 1.5 Flash 001 +0.064, Llama 3.1 405B +0.044; 19 of 22 cells rise by 0.01 or more |
| P6 | HELD | Kendall tau-b 0.939; one model moves 3 or more places: **Gemini 1.5 Flash 001, 5th to 2nd** (0.535 to 0.599) |
| P7 | HELD | Gemini 1.5 Pro 002 stays first |
| P8 | HELD | execution accuracy exceeds program accuracy by 0.05 or more in **11 of 22 runs**, exactly half (largest: Gemini 1.5 Flash and GPT-4o 2024-05-13, +0.102) |

**Totals.** Program accuracy 8,600 of 22,000 (39.1%); argument-normalised 9,139 (41.5%); execution accuracy 9,867
(44.9%); execution accuracy with the same fixes 10,009 (45.5%). 846 records execute to the right answer with a
program that still differs from the gold after normalisation. Also counted: 190 one-argument table operations, and
5,841 outputs (26.6%) that FinQA's executor rejects.

**Hand-read** (by AI agents; up to 8 records per class, one per run, gold program, answer and prediction printed in
the job log):

- All **38 up-flips read are right programs**: `const` 8 of 8 (`multiply(#0, 100)` for `multiply(#0, const_100)`,
  `divide(455, 7)` for `divide(455, const_7)`), `table_name` 8 of 8 (identical to the gold but for `table-max`),
  `table_none` 6 of 6 (identical but for the missing `, none`), `number_form` 8 of 8 (`divide(850, 650)` for
  `divide(850.0, 650.0)`, the same question in five of them; `multiply(375, 0.05)` for `multiply(375, 5.0%)`),
  `combined` 8 of 8 (`divide(2.0, 5.0)` for `divide(const_2, const_5)`; two rearrange `(a - 100)/100 - (b - 100)/100`
  as `(a - b)/100`, which FinQA's symbolic comparison accepts once 100 is mapped).
- `exec_only`, 8 read (not counted as right programs): 1 is the same computation written differently
  (`divide(a, b), subtract(#0, 1)` for `(a - b)/b`; the `1` is not in the gold's symbol map), 2 precompute an
  intermediate number, 3 use other numbers that reach the same answer, 1 uses `table_average` for an add-and-halve,
  and 1 adds extra steps.

**What it means.** HELM Finance's FinQA column scores a right program 0 when it spells an argument or operation
differently from the gold: 539 such records, 6.3% as many as the column credits, and every cell but one rises when
they count. 101 of them, and the 625 hyphenated records in all, come from following HELM's own instructions, which
spell the table operations `table-max` while the scorer accepts only `table_max`. The fix is small: spell the
operations with underscores in the prompt, mention `none` and `const_N`, or normalise arguments before comparing.
The order mostly holds; Gemini 1.5 Flash moves from 5th to 2nd. Separately, execution accuracy, which HELM stores but
does not show, is 0.05 to 0.10 higher than program accuracy for half the models.

**Limits.** One release, one column. ANPA fixes only spelling: other right programs that HELM scores 0 (the
`exec_only` read shows a few) are not in the 539. The hand-read covers 38 of 539 up-flips. Counts are by AI agents and have not been
checked by a human.
