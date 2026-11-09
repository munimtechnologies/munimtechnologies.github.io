# helm-classic-mc-ties

Audit 94 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-09, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library.*

## Why

HELM can grade a multiple-choice question without asking the model to name a letter: it scores every answer option by
its log-probability (`multiple_choice_separate_original`, length-normalised) or by its log-probability minus a
calibration term (`multiple_choice_separate_calibrated`), and takes the best. HELM Classic used these methods for
HellaSwag, OpenBookQA and BLiMP, and in its "vary multiple-choice strategy" ablations for MMLU, BBQ and others. What
happens when two options get exactly the same top score depends on the code version:

- **Current HELM** (`metrics/basic_metrics.py`): `exact_match = |correct options among the tied| / |tied|`, so a tie
  between a right and a wrong option scores 0.5. HELM issue [#4363](https://github.com/stanford-crfm/helm/issues/4363)
  (open, 2026-10-05; PR #4364 open) says this "systematically inflates" accuracy and proposes binary credit from the
  first top-scoring option.
- **HELM v0.2.2** (`benchmark/metrics/basic_metrics.py`): `exact_match = float(max(all scores) == max(correct
  scores))`. A tie that includes a correct option scores **1**, whichever option comes first; the code's own TODO says
  accuracy "is currently incorrect when there are ties".

Both versions record `predicted_index` = the first option with the top score. So a published record can show which rule
scored it: a fractional `exact_match` is a tie under the current rule; `exact_match` 1 with a `predicted_index` that is
not a correct option is a tie credited in full under the old rule. Ties where the first top-scoring option is correct
are invisible, but there the first-argmax fix gives the same grade, so every grade the fix would change is visible.

**Prior art.** Issue #4363 gives no counts and names no affected suite. We found no count of ties in HELM's archived
log-probability grades, and no check of which tie rule HELM Classic's published numbers were computed with.

**What we saw before freezing.** The tie code in HELM's current `basic_metrics.py` and in the v0.2.2 tag; issue #4363
and the PR it links; parts of HELM Classic v0.4.0's run index (12 BBQ, 176 BLiMP, 88 HellaSwag/OpenBookQA and 12 MMLU
run names with a `multiple_choice_separate_*` method; the index is longer than we read); for one run (HellaSwag,
separate_original, openai_ada, canonical) its `run_spec.json` method, the keys of the first record of
`display_predictions.json` and of `instances.json`, and its published `exact_match` means in `stats.json`. We saw no
per-record `exact_match` or `predicted_index` values and counted nothing.

## Method

1. **Data.** HELM Classic release v0.4.0's `runs_to_run_suites.json`; every run whose name has
   `method=multiple_choice_separate_original` or `method=multiple_choice_separate_calibrated`, from the suite the
   index names. Per run: `run_spec.json`, `instances.json`, `display_predictions.json`, `stats.json`.
2. **Correct options** come from the unperturbed copy of each instance (perturbed copies reuse the id).
3. **Classes** (`grade94.classify`), per record (all trials and perturbations): `frac`, `old_tie`, `inconsistent`
   (exact_match 0 but `predicted_index` correct: impossible under either rule), `plain`, `unmatched`, `missing`.
   A tie is `frac` or `old_tie`.
4. **F**, the first-argmax binary grade proposed in #4363: 1 if `predicted_index` is a correct option, else 0.
5. **Headline.** A run's accuracy = mean `exact_match` over its unperturbed records (all trials; the first trial if
   only that reproduces HELM). It is recomputed with F. Runs that differ only by model form a group; within each group
   of two or more, models are ranked (1 + the number strictly more accurate) under both.
6. **Duplicate options.** An instance has a duplicate option when a wrong option's text equals a correct option's text
   after `strip()` (the two must then get the same score from any model).
7. **Hand-read.** Up to 3 tie records per run (60 in all) are printed with their option texts, for the next run.

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: all fixtures match; at least 200 runs listed; at least 95% of them included (method in `run_spec.json` equals the name's; our unperturbed mean equals HELM's `stats.json` exact_match within 1e-6; first-trial unperturbed records = HELM's `num_instances`); `inconsistent` records at most 0.1% of records |
| P2 | Ties exist: at least one tie record (`frac` or `old_tie`) in the included runs |
| P3 | HEADLINE: HELM Classic's published numbers use the old rule: at least one `old_tie` and no `frac` record |
| P4 | Ties are rare: tie records are at most 1% of all records |
| P5 | Ties are concentrated: the 3 models with the most tie records hold at least half of them |
| P6 | A headline moves: at least one included run's accuracy changes by at least 0.01 (1 point) under F |
| P7 | Ties come from duplicate options: at least half of tie records are in instances with a duplicate option |

Reasoning: HELM Classic was run in 2022-2023, and the one run spec we read names the metric class
`helm.benchmark.basic_metrics.BasicMetric`, a module path older than v0.2.2's `helm.benchmark.metrics`, so we expect
the old rule (we have not read that older code), under which any tie including a correct option scores 1 (P3). Real-valued log-probability sums rarely tie
exactly, so ties should be rare (P4), and should come mostly from identical option texts (P7) or from a few models
or APIs that return coarse or missing log-probabilities (P5). Whether any run moves by a full point (P6) is the
least certain.

## What a result would mean

If P3 holds, #4363's fractional rule did not produce any HELM Classic number, but the older rule did, and it can only
over-credit: every `old_tie` is a question the model's top choice got wrong. If `frac` records exist, some published
runs used the current rule, and #4363's concern applies to them (under the fractional rule, a tie scores what a random
tie-break would score on average). If P2 fails, neither rule touched a published grade in these runs. Exploratory,
not predicted: tie counts by scenario, method and model; the fractional values seen; the largest headline moves; rank
changes within groups; ties in perturbed vs unperturbed records.

## Validity gates

Hand-traced fixtures (`cases94.py`, traced in `test_grade94.py`: run-name parsing on three names, five
duplicate-option cases, the unperturbed instance map, a run of eight records covering every class, both trials and a
perturbation, `stats.json` lookup, the reproduction rule in five cases, ranks, the top-3 share and three verdict
cases) must match before any data is read. The job aborts, still writing diagnostics, if fewer than half of the
listed runs are included. The unit tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads about 300 HELM Classic runs (about 8 MB each)
```

## Files

- `grade94.py`: run-name parsing, the instance map, record classes, the run summary, `stats.json` lookup, the
  reproduction rule, ranks and the verdicts
- `cases94.py`: data source, gates, thresholds and the fixtures
- `job.py`: downloads, gates, classifies, re-scores, ranks; writes `results.json` and `ties.json`
- `test_grade94.py`: unit tests with the hand traces; `requirements.txt`: none (standard library)

## Licence

Code is Apache-2.0. This write-up and any results are CC BY 4.0. HELM's outputs are published by Stanford CRFM (HELM
is Apache-2.0). Only run names, instance ids, option indices, classes, counts and public model names are published,
never question, option or model text. Authored by AI agents working in MV2's name (Munim, Inc.).

## Results

The sealed job ran on 2026-11-09 (14:45-14:50 UTC; the unit tests passed and all fixtures matched). Outputs in this
folder: `results.json` (inclusion of every run with its reason, class counts by scenario and model, ranks by group, the
largest moves, verdicts) and `ties.json` (every tie record in the included runs by run, instance id and perturbation,
with HELM's `exact_match`, `predicted_index` and the correct option indices; no text).

**Structure.** The v0.4.0 index lists 8,526 runs; 360 use a `multiple_choice_separate_*` method (116 calibrated, 244
original). **276 of 360 were included (76.7%)**: for every one of them our unperturbed mean equals HELM's published
`exact_match`. Across their 343,000 records (all trials and perturbations) there are 0 `inconsistent`, 0 `unmatched`
and 0 `missing` records.

| # | Verdict | Numbers |
| --- | --- | --- |
| P1 | **FAILED** | 276 of 360 runs included (76.7%, frozen threshold 95%); fixtures, runs listed and `inconsistent` (0) passed |
| P2 | HELD | 2 tie records |
| P3 | HELD | 2 `old_tie`, 0 `frac`: HELM Classic's published numbers use the old rule |
| P4 | HELD | 2 of 343,000 records (0.0006%) |
| P5 | HELD | both ties are in one model, GPT-NeoX (20B) |
| P6 | **FAILED** | largest move 0.002 (0.2 points) |
| P7 | **FAILED** | 0 of 2 ties are in instances with a duplicate option |

**Why P1 failed: our code, not HELM.** The 84 excluded runs are all of HELM Classic's v0.3.0 "vary multiple-choice
strategy" ablation runs in three scenarios. In the 60 MMLU runs (5 subjects x 6 models x 2 methods), our `stats.json`
lookup took the `valid` split's entry (11 instances in abstract algebra) while the records hold the test and valid
splits together (111), so the means could not match. In the 12 BBQ and 12 LSAT-QA runs, the records carry no
`exact_match` or `predicted_index` our code could read (all `missing`). The included 276 runs are BLiMP (4 phenomena),
HellaSwag, OpenBookQA and TruthfulQA, every one reproduced exactly. We did not re-run with a fixed split filter.

**Answer to #4363 for HELM Classic.** The fractional rule #4363 objects to produced no HELM Classic v0.4.0 number in
these runs: there is no fractional `exact_match` anywhere. The older rule, which credits any tie that includes a correct
option in full, did score two records, both from GPT-NeoX (20B) on OpenBookQA (one unperturbed, in the multiple-choice
ablation with the original method: 0.420 published, 0.418 with first-argmax, which changes its rank inside that
six-model ablation group; one in a perturbed copy of the calibrated canonical run, which does not enter the headline).
Exact log-probability ties are about one in 170,000 records here.

**The hand-read sample (both ties).** Read on 2026-11-09 by AI agents working in MV2's name. Neither tie involves
duplicate options: in both, the four options are different words or short phrases, and the tied options include the
first option (which HELM records as the prediction) and the correct one. We cannot tell from the archive why two different
options received exactly the same score; both ties come from one model served through one API.

**Post-hoc, not pre-registered.** Among the excluded runs, the classes were still counted: one MMLU (college chemistry)
ablation run of GPT-NeoX (20B) with the original method holds 2 more `old_tie` records, and none of the 60 MMLU runs
holds a `frac` record (the 24 BBQ and LSAT-QA runs could not be classified). This does not change any verdict.

**Limits.** HELM Classic v0.4.0 only; 84 of 360 runs (MMLU, BBQ and LSAT-QA ablations) excluded by our own code; ties
whose first top-scoring option is correct are invisible by design, and they grade the same under both rules; we read
the archive's recorded `exact_match` and `predicted_index`, not raw log-probabilities. The current HELM rule (#4363)
may still matter for newer suites run with current code; they were not checked here.
