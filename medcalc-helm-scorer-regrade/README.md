# medcalc-helm-scorer-regrade

Audit 96 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-09, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library.*

## Why

MedHELM's MedCalc-Bench column ("MedCalc Accuracy") is computed by HELM's `MedCalcBenchMetric`. Its `check_in_range`
range-checks only the categories `date`, `dosage conversion` and `physical`. MedCalc-Bench's own categories are
`lab` and `dosage`, so for those the metric raises a `ValueError` inside its own `try` block and scores the
instance 0 whatever the model answered. HELM issue [#4351](https://github.com/stanford-crfm/helm/issues/4351) (open,
2026-09-04) reports this. It re-scored two v3.0.0 runs (accuracy +10.4 and +9.2 points) and asks whether the
leaderboard column was produced this way. Issue [#4365](https://github.com/stanford-crfm/helm/issues/4365) (open,
2026-10-12) reports that week/day durations are accepted only in one quoted plural form, and counts 148 of 247
duration answers in MedHELM v4.0.0's 13 runs that the benchmark's reference evaluator would accept and HELM scores 0.
Risk, severity and diagnosis answers are compared as exact strings, so `9.0` does not match `9`.

**Prior art, and what is new here.** #4351 gives the mechanism and two v3.0.0 runs; #4365 checks durations only, in
all 13 v4.0.0 runs, and does not recompute rankings. The MedCalc-Bench paper (arXiv 2406.12036) defines the
range-check rule for lab, physical and dosage calculators. arXiv 2603.02222 audits MedCalc-Bench's ground truth, not
HELM's scorer. We found no re-score of all 13 published MedHELM v4.0.0 runs with both fixes, and no comparison of the
leaderboard ranks before and after.

**What we saw before freezing.** HELM's `medcalc_bench_metrics.py` on `main` (transcribed in `grade96.py`); issues
#4351 and #4365; MedHELM v4.0.0's `runs_to_run_suites.json` (13 `medcalc_bench` runs: 6 reasoning models with
`num_output_tokens=4000` in the run name and 7 without), one run spec (claude-3-5-sonnet-20241022: generation, `max_tokens`
10, temperature 0, prompt "Answer only the requested quantity without units"), the group table's column names, the
structure of that run's `instances.json` (`extra_data` with `category`, `lower_limit`, `upper_limit`) and, through a
summarising web reader asked for structure only, of its `display_predictions.json`: outputs are sometimes prose that
stops at the token limit, sometimes have trailing newlines, and include forms such as `12.0`, dates and `(0, 6)`. We
saw no scores. Because #4365's re-scoring with the current code matched all 13,000 archived scores, we expect P2 to
hold; it is a check that the published column carries #4351's gap, not a test.

## Method

1. **Data.** Every MedHELM release v4.0.0 `medcalc_bench` run (one per model): `instances.json` (reference =
   the first reference, as HELM uses; `extra_data` category and limits) and `display_predictions.json` (output and
   HELM's recorded `medcalc_bench_accuracy`), first trial only.
2. **Graders** (`grade96.py`), applied to every prediction:
   - **H**, HELM's score: `MedCalcBenchMetric` transcribed, gated against HELM's recorded score.
   - **R**, #4351's fix: H, plus lab and dosage outputs credited when `float(output)` lies within the limits
     (exactly as HELM already checks `physical`).
   - **C**, the corrected grade: R, plus (`duration_format`) a whole-output (weeks, days) tuple in another form, such
     as `(18, 1)`, `(18 weeks, 1 day)` or `('18 weeks', '1 day')` (both parts labelled or neither, matching quotes),
     credited when its total days lie within the limits; plus (`same_value`) a risk, severity or diagnosis output
     that is a plain number equal in value to a numeric reference (`9.0` for `9`). C only adds credit.
   - Exploratory, not in C: `rounded_only`, the benchmark authors' integer rule (round(output) equals an integer
     reference although the values differ), and outputs in lab, dosage and physical that are not a plain number.
3. **Accuracy and rank.** A model's accuracy is its mean over instances, as HELM's metric. Rank = 1 + the number of
   models strictly more accurate.
4. **Hand-read.** Up to 10 up-flips per class (chosen by a hash of model and instance id) are printed with output,
   reference and limits, and read in the next run: is each credit a genuine correct answer by the class rule? Texts
   are printed only in the job log, never published.

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: all fixtures match; at least 12 of 13 models included (a run has at most 1% of predictions without a reference, at least 95% of the median run's count, HELM's metric on every item, and our H equal to it on at least 99%); H equals HELM on at least 99.9% of all included predictions |
| P2 | #4351 is in the published column: H credits **no** lab or dosage prediction in any included run |
| P3 | It is large: R raises the mean of the models' accuracies by at least **5.0 points**, and every model's by at least 2.0 points |
| P4 | Our independent duration rule replicates #4365: between **120 and 175** `duration_format` up-flips (#4365 counted 148) |
| P5 | The exact-string rule costs little: `same_value` up-flips are under **1%** of all risk, severity and diagnosis predictions |
| P6 | Ranks move: at least **3** of the models have a different rank under C than under H |
| P7 | Format loss: at least **3** models have at least 10% of their lab, dosage and physical outputs that are not a plain number |

Reasoning: #4351's two runs gained 9-10 points, and lab plus dosage are about 35% of the test set, so even weak
models should gain 2 points (P3). Our duration rule is written independently of #4365's parser but accepts the same
two families (numeric tuples and labelled durations), so it should land near 148 (P4). The prompt asks for a bare
quantity, so decimals for integer scores should be rare (P5). Gains differ by model, and MedHELM's MedCalc scores
are close together, so several ranks should change (P6). The seven runs without a token setting presumably allow
10 output tokens like the one we read, and a model that starts to explain itself is cut off (P7).

## What a result would mean

If P2 and P3 hold, MedHELM's published MedCalc column under-states every model by a sizeable amount, and the results
give the corrected accuracy and rank for each of the 13 models. If P3 fails, the gap is real but smaller than #4351's
two runs suggest. P4 tests whether #4365's count is robust to a second, independent parser. P6 says whether the fix
changes the leaderboard's order, not only its level. P7 measures a loss that no re-scoring can repair: an output cut
off at 10 tokens has no answer to grade.

## Validity gates

Hand-traced fixtures (`cases96.py`, traced in `test_grade96.py`: thirteen HELM scores covering every category branch,
#4351's lab and dosage zeros, #4365's duration form, the unanchored duration match, one-digit dates and inclusive
limits; seventeen grades covering every up-flip class and its near misses; five rounding cases; seven duration
parses; run selection; ranks; Kendall's tau-b; four verdict cases on and past every boundary) must match before any
data is read. The job aborts, still writing diagnostics, if fewer than 12 models are included or our transcription
agrees with HELM's recorded score on under 99.9% of included predictions. The unit tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads MedHELM v4.0.0's 13 MedCalc-Bench runs (about 40 MB)
```

## Files

- `grade96.py`: HELM's `MedCalcBenchMetric` transcribed, the corrections, run selection, ranks, Kendall's tau-b and
  the verdicts
- `cases96.py`: data source, gates, thresholds and the fixtures
- `job.py`: downloads, gates, grades, ranks; writes `results.json` and `flips.json`
- `test_grade96.py`: unit tests with the hand traces; `requirements.txt`: none (standard library)

## Licence

Code is Apache-2.0 (HELM's `MedCalcBenchMetric` is transcribed from stanford-crfm/helm, Apache-2.0). This write-up and
any results are CC BY 4.0. Upstream: MedCalc-Bench is published by NCBI (ncbi-nlp/MedCalc-Bench); MedHELM's outputs
are published by Stanford CRFM. Only model names, HELM instance ids, categories, classes and counts are published,
never patient notes, questions, references or model text. This is research on benchmark scoring, not medical advice.
Authored by AI agents working in MV2's name (Munim, Inc.).
