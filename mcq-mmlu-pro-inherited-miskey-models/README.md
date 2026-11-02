# mcq-mmlu-pro-inherited-miskey-models

Audit 76 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-02, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library plus a parquet
reader.*

## Why

Audit 75 ([mcq-mmlu-pro-redux-inheritance](../mcq-mmlu-pro-redux-inheritance/)) found that MMLU-Pro still uses MMLU's
original key on 52 of the 55 questions MMLU-Redux 2.0's experts marked "wrong ground truth" that MMLU-Pro holds. On 46
of the 52 the experts' answer is one of MMLU-Pro's ten options (24 from a letter or exact-text correction, 22 from a
digit correction read 0-based, the only reading audit 75 found coherent). That is a list of expert judgments, not a
verified one. This audit asks the models: TIGER-AI-Lab publishes per-question MMLU-Pro predictions for dozens of
models (audit 66 read 48 archives), so on these 46 questions, do the models choose the experts' answer or the
published key?

**Prior art.** The MMLU-Redux paper (Gema et al., arXiv 2406.04127) compares model accuracy on MMLU's original and
corrected labels, and reads models that match MMLU's original wrong labels as possible memorisation. A search on
2026-11-02 found no per-question count of model choices on MMLU-Redux's miskeys inside MMLU-Pro, where each question
has up to ten options, and no use of TIGER-AI-Lab's prediction archives for this.

## Method

1. **Targets.** The 46 questions are frozen in `cases76.py` from audit 75's `pro_flags.json`: MMLU-Pro
   `question_id`, `src`, the key letter and the experts' answer letter among MMLU-Pro's options. A target counts only
   if MMLU-Pro's current test data still has that `src` and key (otherwise it is listed and dropped).
2. **Predictions.** Every archive audit 66 listed is read with audit 65/66's reader and join rule: a record joins
   only if its `question_id`, stripped options and answer equal the HF row; an archive is included only if at least
   95% of its records join and it covers at least 95% of the test set.
3. **Classes.** Each prediction on a target is the KEY, the EXPERTS' answer, OTHER (another option) or NONE (missing
   or malformed). An OTHER pick also adds 1/(k−2), so OTHER picks can be compared with one average other distractor.
4. **Control.** Each model's accuracy (as MMLU-Pro scores it) on the MMLU-derived questions other than the 55 Redux
   miskeys.

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: the fixture matches; the frozen list has 46 targets (24 primary) and 55 miskey ids; MMLU-Pro has 12,032 valid rows with audit 63's source families; at least 44 of 46 targets still carry audit 75's key; at least 30 archives are included |
| P2 | HEADLINE: pooled over included models, the experts' answer is picked more often than the published key on the targets |
| P3 | In at least 75% of models with at least 40 joined targets, expert picks exceed key picks |
| P4 | Pooled, the experts' answer is picked at least 3 times as often as an average other distractor |
| P5 | Every such model's key-pick rate on the targets is below its accuracy on the control questions |
| P6 | On at least 60% of the target questions, pooled expert picks exceed pooled key picks |
| P7 | P2 holds on the 24 primary (letter or exact-text) targets alone |

## What a result would mean

If P2-P4 and P6 hold, the models, which never saw Redux's labels, side with the experts on most of these questions,
which supports correcting MMLU-Pro's keys there. A question where models still pick the key is a candidate either for
a disputed expert label or for memorisation of MMLU's key; this audit reports those questions but does not decide
between the two. P7 checks that the result does not rest on the 0-based digit reading. Exploratory, not predicted:
each model's score change if the 46 keys followed the experts, and key picks against an average other distractor.

## Validity gates

A hand-traced fixture (`cases76.py`, traced in `test_inherit_models.py`) must match exactly before any real data is
read, the frozen list must be internally consistent, and the MMLU-Pro parse must reproduce audit 63's counts; the job
aborts otherwise. The unit tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads MMLU-Pro (test) and TIGER-AI-Lab's prediction archives
```

## Files

- `inherit_models.py`: classes, tallies, control accuracy, predictions
- `cases76.py`: the frozen targets, the 55 miskey ids, archives, thresholds, the hand-traced fixture
- `job.py`: loaders, gates, joins; writes `results.json`
- `test_inherit_models.py`: unit tests; `requirements.txt`: a parquet reader only

## Licence

Code is Apache-2.0. This write-up and any results are CC BY 4.0. Upstream: MMLU-Pro is MIT, TIGER-AI-Lab's published
evaluation outputs keep their own licence, and MMLU-Redux 2.0 is CC BY 4.0. Only ids, letters, counts and sha256s are published, never
question, option or model text. Authored by AI agents working in MV2's name (Munim, Inc.).
