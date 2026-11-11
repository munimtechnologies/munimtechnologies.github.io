# helm-math-classic-regrade

Audit 102 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-11, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library.*

## Why

Audit 91 re-graded HELM Lite's MATH column and found that `math_equiv_chain_of_thought` misses 3.79% of right answers,
mostly answers written without `\boxed{}`. HELM Classic (release v0.4.0) publishes two MATH columns over the same 437
level-1 questions (7 subjects), for about 68 older models, and nobody has re-graded either of them:

- **"MATH"** (group `math_regular`): no chain of thought, 8 official examples shown as `Answer: $5$`, generation
  stops at `$` (at most 20 tokens), scored with `math_equiv`: Hendrycks' `_strip_string` on gold and output, then
  string equality.
- **"MATH (chain-of-thoughts)"** (group `math_chain_of_thought`): 400 tokens, stop at `###`, scored with
  `math_equiv_chain_of_thought`: the contents of the last `\boxed{...}` of the reference solution and of the output.

Hazards that follow from the code: equal values written differently (`1,000` and `1000`, `0.25` and `\frac{1}{4}`)
score 0 in both columns; in the chain-of-thought column an output with no `\boxed{}` scores 0 even when it states the
right answer; and four models (GLM, T0pp, T5 11B and UL2) were run with `stop=hash`, where HELM stops at `#`
instead of the run spec's `$`, so a short answer may keep its closing `$`, which `_strip_string` does not remove.

**Prior art, and what is new here.** HELM's issues searched on 2026-11-11: "math_equiv" (2 results: #4374, open, on
`math_equiv_chain_of_thought` scoring 1.0 when neither side has an extractable answer, which audit 91 showed never
happens on the 437 questions; and #290, unrelated) and "stop=hash" (no scoring issue). A web search found no re-grade of
either HELM Classic MATH column. Audit 91 covered HELM Lite only. We found no count of mis-scored answers in HELM
Classic's published MATH numbers and no check of the `math_equiv` (no chain of thought) metric on archived runs.

**What we saw before freezing.** The run spec and metric code above. `runs_to_run_suites.json` lists the math runs
in suite v0.3.0, level 1 only, with `use_official_examples=True,use_chain_of_thought=False` (MATH) and
`use_official_examples=False,use_chain_of_thought=True` (chain of thought), about 68 models per subject and mode, and
`stop=hash` on the GLM, T0pp, T5 11B and UL2 runs. For one pair of runs (davinci, prealgebra): `stats.json` has
`math_equiv` (mean 0.1008 over 3 trials of 86 instances; `num_instances` sum 258) or `math_equiv_chain_of_thought`
(0.0543), without per-trial values; `display_predictions.json` records carry `instance_id`, `train_trial_index`,
`predicted_text` and per-record stats including the metric and `num_output_tokens`, with no perturbed records;
`instances.json` has one `correct` reference per instance, a short answer in the regular run (described to us as
mostly integers, with some fractions, degree marks, escaped percent signs, comma-formatted thousands and `\text{}`
words). The group page `math_regular.json` has a "MATH" table with an "Equivalent" column (first rows J1-Jumbo v1
0.0886 and J1-Large v1 0.0490, `# eval` 62.43 = 437/7, 3 trials), at least 64 rows and no run names. From audit 91
we already know that HELM extracts a gold answer from all 437 reference solutions, so `#4374`'s both-None path cannot
fire; that is reported as a check, not predicted. We did not look at any prediction text.

## Method

1. **Data.** HELM Classic release v0.4.0: `runs_to_run_suites.json`, the two group pages, and for each listed math
   run of either column `instances.json`, `display_predictions.json` and `stats.json`.
2. **Grades** (`grade102.py`), per test record and trial. **H** = HELM's metric, transcribed (from audit 91; must
   reproduce every stored record score). **A**, chain of thought = audit 91's corrected grade, unchanged (HELM's
   boxed answer, else a `\boxed 5` or `\fbox{5}` fallback, else the unboxed final answer; credit when HELM's `is_equiv`
   holds or both sides are the same rational number). **A**, regular = the output up to its first `$` not preceded
   by a backslash, credited when HELM's `is_equiv` holds or both sides are the same rational number.
3. **Classes.** Up-flips (A 1, H 0): chain of thought as in audit 91 (`gold_fallback`, `pred_fallback`,
   `value_format`, `unboxed`, `other`); regular `dollar_tail` (a `$` was cut) or `value_format`. Down-flips (H 1,
   A 0): `both_none` or `other` (chain of thought), `other` (regular).
4. **Inclusion.** A run is included if it downloads, every test record's stored score equals H, the number of
   records equals HELM's `num_instances` sum, and our run mean (mean of trial means) equals `stats.json` within 1e-6.
5. **Cells and ranks.** One cell per adapter (the run name without its subject, i.e. HELM's "Model/adapter" row):
   the mean over its 7 subject runs of each run's mean, as exact Fractions, only when all 7 runs are included.
   Published cells are checked by matching each H cell to a distinct "Equivalent" value of the group page within
   1e-9. Ranks: higher is better, 1 + the number of adapters strictly higher. A movers = adapters whose rank changes by
   3 or more places.
6. **Cross-column (descriptive).** For models with both cells: how many score higher with chain of thought than
   without, under H and under A, and which models change sign.
7. **Hand-read** (next run, by class): up to 8 records per mode and class, at most one per run, spread by a stable
   hash, are printed in the job log with the gold answer, our candidate and the output's last 200 characters; texts
   are never published.

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: all fixtures match; at least 90% of listed runs included; at least 60 cells in each column; at least 90% of each column's cells match a published "Equivalent" value |
| P2 | Chain of thought: the corrected grade credits, net, at least **1%** of the column's predictions more than HELM |
| P3 | Chain of thought: `unboxed` is the largest up-flip class |
| P4 | Chain of thought: at least **5** adapters move **3 or more** places |
| P5 | Chain of thought: the order is broadly kept (Kendall tau-b between H and A cells at least **0.9**) |
| P6 | Regular: up-flips are at least **0.2%** of the column's predictions |
| P7 | Regular: at least one `stop=hash` adapter's cell rises under A |
| P8 | The net share of rescued predictions is larger in the chain-of-thought column than in the regular column |

Reasoning: audit 91 found 3.79% on HELM Lite, where instruction-tuned models often ignore the in-context format and
leave answers unboxed (P3). Classic's older base models copy the eight boxed solutions more closely and are mostly
wrong anyway, so we expect a smaller but still visible share (P2 at 1%), enough to move a few close cells near the
bottom (P4) without re-ordering the column (P5). The regular column's outputs are short and stop at `$`, so its
only routes are a value written differently, which the golds' formats (comma thousands, fractions, decimals) make
possible but rare (P6 at 0.2%), and the `stop=hash` runs, where we expect a kept closing `$` to zero some right
answers (P7). Both of these are smaller than the unboxed route (P8).

## What a result would mean

If P2 holds, HELM Classic's chain-of-thought MATH column under-counts right answers, as HELM Lite's does, so the
problem is the scorer, not one leaderboard's models. If P7 holds, four models' regular MATH scores are lowered by a
run-configuration detail rather than by their answers. If P2 and P6 fail, both Classic MATH columns are scored
almost as a careful grader would, and audit 91's effect is specific to newer, instruction-tuned models. Only these
two columns of one release are measured.

## Validity gates

Hand-traced fixtures (`cases102.py`, traced in `test_grade102.py`): nine regular-column grade cases (a right answer,
a kept `$`, comma thousands, HELM's own `0.5` rule, a decimal against a fraction, a wrong answer, an empty output, an
escaped `\$` and a down-flip of our rule); seven chain-of-thought cases (boxed, unboxed, same value, bare `\boxed 5`,
wrong, both-None and empty); four record cases including a two-reference one; run-name parsing; two run censuses
(with a valid-split record, a duplicate, a perturbed record, a missing and a mismatched stored score and records at
the token cap); cells with a missing subject; ranks; Kendall tau-b with ties; cell matching; the group column; and
two verdict cases on and past every boundary. They must match before any data is read. The unit tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads the release index, two group pages and about 950 runs
```

## Files

- `grade102.py`: HELM's MATH scorer (transcribed), audit 91's corrected grade, the regular-column grade, classes,
  run names, census, cells, ranks, Kendall tau-b and verdicts
- `cases102.py`: data source, thresholds and the fixtures (all invented)
- `job.py`: downloads, gates, grades, rebuilds cells, ranks; writes `results.json`
- `test_grade102.py`: unit tests with the hand traces; `requirements.txt`: none (standard library)

## Licence

Code is Apache-2.0 (HELM's MATH scorer is transcribed from stanford-crfm/helm, Apache-2.0, which takes it from
hendrycks/math, MIT). This write-up and any results are CC BY 4.0. HELM Classic's outputs are published by Stanford
CRFM. Only run names, model names, HELM instance ids, trials, classes and counts are published, never prompts,
references or model text. Authored by AI agents working in MV2's name (Munim, Inc.).
