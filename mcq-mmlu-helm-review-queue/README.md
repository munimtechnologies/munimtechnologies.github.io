# mcq-mmlu-helm-review-queue

Audit 85 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-06, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library plus a parquet
reader.*

## Why

MMLU-Redux 2.0's experts re-annotated a random sample of 100 questions in each of MMLU's 57 subjects and marked 106
of them as having a wrong answer key. About 8,300 of MMLU's test questions have never had that expert review. Audits
80-83 in this catalogue showed that HELM's model outputs rank questions for review far better than chance: audit 77's
consensus flag on the 10 most accurate models catches 80 of the 106 miskeys
([audit 80](../mcq-mmlu-helm-consensus-miskeys/)), and on the 88 questions none of HELM's 78 models answers with the
key, 27 of 37 expert-judged ones carry an error label ([audit 82](../mcq-mmlu-helm-discrimination-miskeys/),
post-hoc).

Those audits measured precision on questions experts had already judged. This audit asks the practical questions for
everything else: **how many wrong keys are probably left among the questions outside Redux's sample, and which should
an expert read first?** Before giving an estimate, it tests on held-out expert labels whether the estimate can be
trusted.

**Prior art.** Gema et al. ("Are We Done with MMLU?", arXiv 2406.04127, NAACL 2025) built MMLU-Redux, sampling 100
questions per subject at random, and estimate by stratified sampling that 6.49% of MMLU's questions contain an error
of any kind; they give no estimate for wrong keys alone and no list for the unreviewed questions. Paquin and Jain
(arXiv 2609.09372) fit item-response models to 1,000 models on all of MMLU's test items to study difficulty, not label
errors. Vendrow et al. (arXiv 2502.03461) and Land and Bikel (arXiv 2605.30504) review items that models get wrong on
other benchmarks. Audits 80-82 here published HELM-flagged MMLU questions outside Redux's sample as unranked or
single-signal lists. We found no held-out test of whether model-based tiers can estimate MMLU's remaining wrong keys,
and no calibrated, ranked review queue for the questions Redux did not sample.

## Method

1. **Data (audits 80-83, rebuilt).** HELM MMLU release v1.13.0 (13,984 questions after dropping duplicated or unkeyed
   ones; 78 of 79 models pass the inclusion rules) and MMLU-Redux 2.0 joined by subject, question and options.
   *Judged* = Redux labels wrong key, OK, or another error type; unsure or conflicting labels are left out.
   *Unreviewed* = questions with no joined Redux row.
2. **Tiers (frozen, exclusive, checked in this order).**
   - **T1**: none of the 78 included models answers with the key (at least 2 models cover the question).
   - **T2**: all 10 most accurate models pick the same non-key option (audit 80's panel).
   - **T3**: audit 77's flag on that panel (at least 6 of 10 on one non-key option, more than on the key).
   - **T0**: everything else.
3. **Held-out test.** The judged questions are split into two fixed halves by the parity of
   sha256("subject|HELM instance id"). For each half, wrong-key rates are computed on the *other* half and used to
   predict this half's wrong keys in two ways: by tier (each question gets its tier's rate) and by subject (each
   question gets its subject's rate, Redux's own stratified approach). Errors are measured per subject: the sum over
   subjects of |predicted wrong keys - actual wrong keys|, added over both halves.
4. **Intervals.** An estimate's variance adds each question's own spread, n r (1 - r), and the rate's sampling
   spread, n^2 r (1 - r) / (judged questions behind the rate); the 95% interval is the estimate +- 1.96 sd. The same
   formula is used for the held-out check and for the final estimate.
5. **Transport check.** Because Redux sampled at random, unreviewed questions should land in tiers 1-3 as often as
   reviewed questions of the same subject. Observed: unreviewed questions in tiers 1-3. Expected: the sum over
   subjects of (unreviewed questions) x (reviewed share in tiers 1-3), with the variance from both samples.
6. **The estimate and the queue.** With rates from all judged questions, the expected number of wrong keys (and of
   any error label) among the unreviewed questions, by tier and by subject, with intervals. `review_queue.json` lists
   every unreviewed question in tiers 1-3, ranked by tier, then the panel's margin (votes for its most-picked non-key
   option minus votes for the key), then fewer models picking the key, then subject and position, with its tier's
   expert-measured rates.

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: all eleven fixtures match; audit 80 is reproduced (13,984 questions, 78 models, same panel, 1,207 flags, precision 130 of 484) and so is audit 82's no-key count (88 questions: 23 miskeys, 10 OK, 4 other errors, 51 unreviewed) |
| P2 | HEADLINE: on held-out halves, tier rates predict each subject's wrong keys better than subject rates (smaller summed per-subject absolute error) |
| P3 | The tier estimate is calibrated: in both halves, the actual number of wrong keys lies within the estimate's 95% interval |
| P4 | Redux's sample carries over: the number of unreviewed questions in tiers 1-3 lies within 1.96 sd of its subject-matched expectation |
| P5 | Wrong-key rates among judged questions fall from tier to tier: T1 > T2 > T3 > T0 |

Reasoning: wrong keys cluster in a few subjects (virology holds 33 of the 106), which favours the subject baseline
there, but in most subjects a half holds only 0-2 wrong keys, so a subject rate from 50 questions is mostly noise,
while the tiers use each question's own votes. Against P2: tier rates are pooled over subjects, so they will
under-predict virology, where 39 of 42 judged flags carry an error label (audit 80). P3 can fail if tier precision
differs by subject more than the rate's sampling spread allows. P4 should hold if the joins are right. P5 follows
from audits 80 and 82 but is scored on the exclusive tiers for the first time.

## What a result would mean

If P2-P4 hold, the tier estimate of wrong keys outside Redux's sample is the best available number, with an interval
that held up on held-out expert labels, and the queue is a ranked worklist for whoever re-reviews MMLU next. If P2
fails, subject rates estimate *how many* wrong keys are left better than model votes do, and the queue is still a
way to find *which* ones. If P3 fails, the interval is too narrow and will be reported as such. Exploratory, not
predicted: the same held-out test for any error label, per-subject estimates by both methods, the tier table with
Wilson intervals, and the queue's size by tier.

## Validity gates

Eleven hand-traced fixtures (`cases85.py`, traced in `test_queue85.py`: audit 77's panel/flag and audit 80's run
selection, universe, answer mapping and Redux-join fixtures, copied; new: key pickers and tiers, the queue order, the
held-out rates and predictions, the estimate with its interval, the transport check and the verdicts) must match
before any data is read. The Redux join must place at least 4,000 rows or the job aborts. The unit tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads HELM's MMLU release files and MMLU-Redux 2.0
```

## Files

- `queue85.py`: audit 80's HELM, Redux, panel and flag functions (copied from audit 83), key pickers, tiers, folds,
  rates, estimates with intervals, the held-out test, the transport check, Wilson intervals, queue rows and verdicts
- `cases85.py`: the frozen rule, gates, data sources and the eleven fixtures
- `job.py`: downloads, tiers, the held-out test and the estimate; writes `results.json` and `review_queue.json`
- `test_queue85.py`: unit tests; `requirements.txt`: a parquet reader only

## Licence

Code is Apache-2.0. This write-up and any results are CC BY 4.0. Upstream: HELM (Stanford CRFM) is Apache-2.0 and its
published run outputs keep their own terms; MMLU is MIT; MMLU-Redux 2.0 is CC BY 4.0. Only ids, letters, votes,
counts, rates and 16-hex sha256 prefixes of normalised question text are published, never question, option or model
text. Authored by AI agents working in MV2's name (Munim, Inc.).
