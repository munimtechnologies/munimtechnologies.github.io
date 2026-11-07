# mcq-mmlu-subject-adjusted-tiers

Audit 87 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-07, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library plus a parquet
reader.*

## Why

[Audit 85](../mcq-mmlu-helm-review-queue/) sorted MMLU's 13,984 HELM questions into four tiers from model votes and
asked whether the tiers could estimate the wrong answer keys left outside MMLU-Redux 2.0's expert sample. The tiers
rank questions well (wrong-key rates 62.2%, 33.3%, 6.9% and 0.49% from T1 to T0), but its headline prediction
failed: on two fixed held-out halves of the expert labels, Redux's own subject rates predicted each subject's wrong
keys better than tier rates pooled over subjects (summed per-subject error 91.3 against 115.5). The two methods'
estimates for the 8,331 unreviewed questions differ by about 58 wrong keys (92.5 against 150.8), and a subject whose
sample held no wrong key gets an estimate of exactly 0 from the subject rates.

This audit tests the obvious repair, chosen after seeing audit 85's result: **keep the tiers, but scale them by how
damaged each subject's keys turned out to be.** It is scored on the same held-out halves audit 85 used, so the test
is weaker than one on fresh labels; it is still frozen before the adjusted model's numbers have been computed.

**Prior art.** Scaling a model's expected counts by observed over expected in each stratum is indirect
standardisation, the standardised ratio of epidemiology; adding a prior to both counts is ordinary shrinkage. In
label-error work, Northcutt et al. ("Pervasive Label Errors in Test Sets", arXiv 2103.14749) flag candidates with
confident learning and estimate test-set error rates from human-validated candidates; Gema et al. (arXiv 2406.04127)
estimate MMLU's error rate from a random sample of 100 questions per subject; prediction-powered inference
(Angelopoulos et al., 2023) combines model predictions with a small labelled sample to give valid intervals for
population quantities. We found no estimate of MMLU's remaining wrong keys that combines model-vote tiers with
Redux's stratified sample and is checked on held-out expert labels.

## Method

1. **Data and gates.** Audit 85 rebuilt exactly: HELM MMLU release v1.13.0 (13,984 questions, 78 included models),
   MMLU-Redux 2.0 joined by subject, question and options, audit 77's flag on the 10 most accurate models, audit 85's
   tiers (T1 no model picks the key; T2 the top 10 unanimous on one non-key option; T3 the top-10 flag; T0 the rest)
   and its folds (parity of sha256("subject|HELM instance id")). *Judged* = Redux labels wrong key, OK or another
   error type.
2. **The adjusted model (frozen).** Fitted on a set of judged training questions: tier rates r_t pooled over
   subjects (as audit 85), and for each subject s a factor k_s = (O_s + 1) / (E_s + 1), where O_s is the subject's
   wrong keys among the training questions and E_s the sum of their tier rates. A question's probability of a wrong
   key is min(1, r_t x k_s). With no wrong key in a subject's sample the factor shrinks the tier rates instead of
   setting them to 0; with more wrong keys than the tiers expect (virology) it raises them.
3. **Held-out test.** For each half, fit on the other half's judged questions and predict this half's. Error =
   the sum over subjects of |predicted - actual wrong keys|, added over both halves, compared with audit 85's subject
   and tier rates on the same halves.
4. **Bootstrap interval.** 1,000 replicates (seed 87 + half; 89 for the final estimate): resample the training
   questions with replacement within each subject (same count per subject), refit, then draw each target question as
   a wrong key with its probability; the 95% predictive interval is the 25th and 975th of the sorted totals. This
   covers both the uncertainty of the fitted rates and the chance in which questions turn out wrong.
5. **The estimate and the queue.** Fit on all judged questions; estimate the wrong keys among the 8,331 unreviewed
   questions, with the bootstrap interval; re-rank audit 85's 716-row queue by the adjusted probability
   (`review_queue_adjusted.json`).

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: all fixtures match; audits 80 and 82 reproduce as in audit 85, and audit 85 reproduces (tiers 88 / 239 / 882 / 12,775; queue 716; held-out errors 115.49 and 91.30; estimates 150.80 and 92.55) |
| P2 | HEADLINE: the adjusted model's summed per-subject error on the held-out halves is smaller than the subject rates' (91.30) |
| P3 | Calibration: in both halves, the actual number of wrong keys lies inside the adjusted model's bootstrap 95% interval built on the other half |
| P4 | The adjusted estimate for the 8,331 unreviewed questions lies strictly between audit 85's subject-rate (92.5) and tier-rate (150.8) estimates |
| P5 | P2 also holds for any error label (wrong key or another Redux error type) |

Reasoning: per subject, the adjusted total is the subject's own observed-over-expected ratio applied to the held-out
half's tier mix, so it should beat the subject rate wherever the two halves of a subject differ in how many T1 and T2
questions they hold, which is where most wrong keys are. Against P2: k_s rests on about 50 questions per subject and
on 0 to 2 wrong keys in most subjects, so it is noisy, and the prior of 1 pulls small subjects back toward the pooled
tier rates that lost in audit 85. P3 can fail because the bootstrap treats questions within a subject as
exchangeable. P4 should hold if the factors shrink the large unreviewed subjects (professional law, moral scenarios,
miscellaneous) and raise virology; it fails if, for example, the cap at 1 or the prior moves the total outside that
range. Other error types are less tied to model votes than wrong keys (audit 85: tier precision for any error label
is lower), so P5 is less certain than P2.

## What a result would mean

If P2 and P3 hold, the adjusted estimate is the best-supported count of MMLU's remaining wrong keys in this series,
with an interval that held on held-out expert labels, and the re-ranked queue is the one to use. If P2 fails,
model-vote tiers add nothing to Redux's subject rates for counting, and the subject-rate figure from audit 85 stands.
If P3 fails, the interval is too narrow and will be reported as such. Exploratory, not predicted: priors of 1/2, 2
and 5; per-subject estimates by all three methods and the factors; the same test for any error label as a point
estimate; how many wrong keys the adjusted model expects in the queue and in its top 50, 100 and 200 rows.

## Validity gates

Hand-traced fixtures (`cases87.py`, traced in the docstring of `test_est87.py`: the training rates, the subject
factors, the cap at 1, the held-out errors of all three methods, the bootstrap's two degenerate cases and its
percentile indices, and the verdicts) must match before any data is read. The Redux join must place at least 4,000
rows or the job aborts. Audits 80, 82 and 85 must reproduce (P1). The unit tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads HELM's MMLU release files and MMLU-Redux 2.0
```

## Files

- `base87.py`: audit 85's functions, copied unchanged from `queue85.py` (HELM, Redux, panel, flag, tiers, folds,
  rates, estimates, the held-out test and the queue order)
- `est87.py`: the subject factors, adjusted predictions, the adjusted held-out test, the bootstrap and the verdicts
- `cases87.py`: the frozen settings, gates, data sources and fixtures
- `job.py`: downloads, gates, the held-out test, the estimate and the re-ranked queue; writes `results.json` and
  `review_queue_adjusted.json`
- `test_est87.py`: unit tests; `requirements.txt`: a parquet reader only

## Licence

Code is Apache-2.0. This write-up and any results are CC BY 4.0. Upstream: HELM (Stanford CRFM) is Apache-2.0 and its
published run outputs keep their own terms; MMLU is MIT; MMLU-Redux 2.0 is CC BY 4.0. Only ids, letters, counts,
rates and probabilities are published, never question, option or model text. Authored by AI agents working in MV2's
name (Munim, Inc.).
