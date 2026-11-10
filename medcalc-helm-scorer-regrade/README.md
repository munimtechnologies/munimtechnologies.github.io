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

## Results

Added 2026-11-10. The sealed job ran on 2026-11-09 (21:37-21:40 UTC) with the code above, unchanged. Its outputs are
`results.json` (all counts, per model and per category) and `flips.json` (model, instance id, category and class of
every up-flip; no texts). **All 7 pre-registered predictions held.**

| # | Verdict | Measured |
| --- | --- | --- |
| P1 | HELD | all fixtures matched; 13 of 13 models included; our H equals HELM's recorded score on 13,000 of 13,000 predictions |
| P2 | HELD | H credits 0 of 4,602 lab and dosage predictions (all 13 runs) |
| P3 | HELD | R raises the mean of the 13 models' accuracies by 13.8 points (24.7% to 38.5%); the smallest gain is 2.5 points (Llama 3.3 70B) |
| P4 | HELD | 144 `duration_format` up-flips (#4365 counted 148; we did not identify which 4 differ) |
| P5 | HELD | 0 `same_value` up-flips among 4,719 risk, severity and diagnosis predictions |
| P6 | HELD | 4 models change rank under C (Kendall tau-b, H vs C: 0.857) |
| P7 | HELD | 3 models give a non-number for at least 10% of their 579 lab, dosage and physical outputs |

**The size of the gap.** Across the 13,000 published predictions, HELM's metric credits 3,211 (24.7%). Scoring lab
and dosage answers against the limits HELM already ships with each instance (#4351's fix) credits 1,797 more (1,610
lab, 187 dosage). Accepting other forms of the same week/day duration (#4365) adds 144. The corrected grade credits
5,152 (39.6%), and no grade goes down. In the published runs, **every one of the 4,602 lab and dosage predictions
(35.4% of the test set) scores 0**, whatever the answer.

**Per model** (accuracy over each model's 1,000 predictions; rank = 1 + the number of models strictly more accurate):

| Model | HELM (H) | #4351 fix (R) | Corrected (C) | Rank H to C | Non-number lab/dosage/physical outputs |
| --- | --- | --- | --- | --- | --- |
| deepseek-r1 | 0.348 | 0.544 | 0.563 | 1 to 5 | 28 of 579 |
| gemini-2.5-pro-preview-05-06 | 0.348 | 0.584 | 0.602 | 1 to 1 | 12 of 579 |
| gpt-5-mini-2025-08-07 | 0.341 | 0.559 | 0.578 | 3 to 3 | 5 of 579 |
| o3-mini-2025-01-31 | 0.340 | 0.568 | 0.587 | 4 to 2 | 22 of 579 |
| o4-mini-2025-04-16 | 0.340 | 0.533 | 0.552 | 4 to 6 | 11 of 579 |
| gpt-5-2025-08-07 | 0.333 | 0.556 | 0.574 | 6 to 4 | 18 of 579 |
| claude-3-5-sonnet-20241022 | 0.218 | 0.317 | 0.328 | 7 to 7 | 53 of 579 |
| claude-3-7-sonnet-20250219 | 0.210 | 0.314 | 0.323 | 8 to 8 | 28 of 579 |
| gpt-4o-2024-05-13 | 0.188 | 0.280 | 0.280 | 9 to 9 | 1 of 579 |
| gemini-2.0-flash-001 | 0.158 | 0.232 | 0.240 | 10 to 10 | 78 of 579 |
| gpt-4o-mini-2024-07-18 | 0.154 | 0.215 | 0.215 | 11 to 11 | 22 of 579 |
| gemini-1.5-pro-001 | 0.120 | 0.168 | 0.170 | 12 to 12 | 81 of 579 |
| llama-3.3-70b-instruct | 0.113 | 0.138 | 0.140 | 13 to 13 | 285 of 579 |

- **The published top is a tie that the fix breaks.** As published, DeepSeek-R1 and Gemini 2.5 Pro share first place
  at 0.348. Corrected, Gemini 2.5 Pro leads at 0.602 and DeepSeek-R1 is fifth at 0.563; o3-mini rises from fourth to
  second and GPT-5 from sixth to fourth. All four rank changes are among the six reasoning models (the runs with
  `num_output_tokens=4000`), whose corrected scores lie within 5.0 points of each other (0.552 to 0.602).
- **The corrected grade adds 21.2 to 25.4 points to each reasoning model** (o4-mini +21.2, Gemini 2.5 Pro +25.4), but
  only 2.7 points to Llama 3.3 70B, which gives a non-number for 285 of its 579 lab, dosage and physical outputs (49.2%).
  Gemini 1.5 Pro (14.0%) and Gemini 2.0 Flash (13.5%) are the other two models over 10%. No re-scoring can recover an
  answer that is not there, so for these models the published column also measures the answer format.
- **Independent replication of PR #4352.** For the two models that #4351's author re-scored on MedHELM v3.0.0, our R
  on v4.0.0 gives the same numbers: Claude 3.7 Sonnet 0.210 to 0.314 and GPT-4o 0.188 to 0.280.
- **Exact-string scoring of risk, severity and diagnosis answers costs nothing** in these runs (0 of 4,719), and the
  benchmark authors' rounding rule credits no extra answer (`rounded_only` is 0 in every category).

**Hand-read (by AI agents, by class).** All 30 printed up-flips are genuine correct answers by their class rule: 10 of
10 `range_lab` and 10 of 10 `range_dosage` outputs are plain numbers inside the instance's own limits (MedCalc-Bench's
5% band around the reference), and 10 of 10 `duration_format` outputs give the reference's weeks and days exactly, as
a bare tuple or with labels.

**Limits.** One release (MedHELM v4.0.0), first trial, 1,000 instances per model. The range rule is the benchmark's own
5% band, applied as HELM already applies it to `physical`; it is not a judgement of clinical correctness. The 4
duration answers by which we differ from #4365 are not resolved. Ranks use three-decimal accuracies that are exact here
(1,000 instances per model). This is research on benchmark scoring, not medical advice.
