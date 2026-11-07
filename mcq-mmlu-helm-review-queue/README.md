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

## Results

*Added on 2026-11-07 after the sealed job `mcq-mmlu-helm-review-queue-v1` ran on 2026-11-06 (unit tests passed, then
98 s of analysis). Nothing above was changed. Every number below is in [`results.json`](results.json); the queue is
[`review_queue.json`](review_queue.json). Percentages are shares of Redux-judged questions unless stated otherwise.*

**Four of five predictions held. The headline (P2) failed: per subject, Redux's own subject rates predicted held-out
wrong keys better than the model-vote tiers did.**

| # | Prediction | Verdict | Numbers |
| --- | --- | --- | --- |
| P1 | Structural and reproduction | HELD | 11 of 11 fixtures; 13,984 questions, 78 models, same panel, 1,207 flags, 130 of 484; no-key 88 (23 / 10 / 4 / 51) |
| P2 | HEADLINE: tiers beat subject rates per subject | **FAILED** | summed per-subject absolute error 115.5 (tiers) vs 91.3 (subjects); half 0: 61.2 vs 48.0; half 1: 54.3 vs 43.3 |
| P3 | Tier estimate calibrated in both halves | HELD | half 0: 57 actual, 53.9 expected (95%: 35.8 to 72.0); half 1: 49 actual, 51.8 expected (35.0 to 68.6) |
| P4 | Redux's sample carries over | HELD | 716 unreviewed questions in tiers 1-3, expected 679.5 (sd 68.7, z = 0.53) |
| P5 | Rates fall T1 > T2 > T3 > T0 | HELD | 62.2% > 33.3% > 6.9% > 0.49% |

### The tiers, with 95% Wilson intervals

| Tier | Questions | Judged | Wrong key | Any error label | Unreviewed |
| --- | --- | --- | --- | --- | --- |
| T1 no model picks the key | 88 | 37 | 23 (62.2%; 46.1 to 75.9%) | 27 (73.0%; 57.0 to 84.6%) | 51 |
| T2 top 10 unanimous | 239 | 102 | 34 (33.3%; 24.9 to 42.9%) | 45 (44.1%; 34.9 to 53.8%) | 136 |
| T3 top-10 flag | 882 | 346 | 24 (6.9%; 4.7 to 10.1%) | 59 (17.1%; 13.5 to 21.4%) | 529 |
| T0 the rest | 12,775 | 5,136 | 25 (0.49%; 0.33 to 0.72%) | 205 (4.0%; 3.5 to 4.6%) | 7,615 |

Tiers 1-3 hold 81 of the 106 wrong keys (76.4%) in 485 of the 5,621 judged questions (8.6%).

### What the held-out test says

Both methods got each half's *total* about right: tiers predicted 53.9 and 51.8 wrong keys, subject rates 56.3 and
46.8, against 57 and 49. They differ in *where* the wrong keys are. Tier rates are pooled over subjects, so they
over-predict in subjects where strong models share mistakes and under-predict in virology, and that costs more than
the noise in a subject rate from about 50 questions. The same held for any error label (exploratory): totals inside
the tier interval in both halves (178 vs 164.5 and 158 vs 170.9), but summed per-subject error 301.2 for tiers
against 195.5 for subject rates.

### How many wrong keys are left outside Redux's sample

Among the 8,331 HELM MMLU questions with no Redux label:

| Estimate | Wrong keys (95% interval) | Share of unreviewed | Any error label (95% interval) |
| --- | --- | --- | --- |
| By subject rates (favoured by P2) | 92.5 (44.0 to 141.1) | 1.11% | 577.2 (443.8 to 710.6) |
| By tier rates | 150.8 (118.2 to 183.4) | 1.81% | 491.4 (428.9 to 553.8) |

Adding the 106 wrong keys Redux found gives an estimate of about 199 (150 to 247) wrong keys in HELM's 13,984 MMLU
questions by subject rates (1.42%), or 257 (224 to 289) by tier rates (1.84%). These are estimates, not counts. The
subject figure is lower than Redux's sampled rate (106 of 5,621, 1.89%) because the subjects with the most unreviewed
questions (professional law 1,436, moral scenarios 796, miscellaneous 683) had few or no wrong keys in their sample,
while virology, with 33 of its 100 sampled questions miskeyed, has only 66 unreviewed. For any error label, the
subject-rate figure for all of MMLU is 336 + 577.2 = 913 of 13,984 (6.53%), close to Redux's own stratified estimate
of 6.49%, a consistency check on the join (post-hoc).

Limits of both intervals: a subject with no wrong key in its Redux sample gets an estimate of 0 with no spread, so the
subject-rate interval is too narrow wherever the true rate is small but not zero (moral scenarios alone has 796
unreviewed questions). The tier interval held in both halves (P3) but carries the per-subject bias P2 found.

Where the two estimates disagree most (exploratory, per subject, tier vs subject): professional law 45.7 vs 29.3,
virology 8.9 vs 21.8, moral scenarios 9.9 vs 0, moral disputes 7.6 vs 2.5, miscellaneous 6.3 vs 0, high school
psychology 5.6 vs 0, conceptual physics 1.0 vs 5.6, high school mathematics 3.6 vs 0.

### An outside check on one subject (post-hoc)

Vendrow et al.'s PlatinumBench (arXiv 2502.03461; dataset `madrylab/platinum-bench`, config `mmlu_math`, CC BY-SA
4.0) re-reviewed all 270 MMLU high-school-mathematics test questions: every question any of their models answered
wrongly was inspected by hand, a wrong answer was relabelled and a flawed question removed. Their paper reports no
relabelled keys and 2 removed questions (the current dataset marks 3 as rejected). For this subject's 170 unreviewed
questions (4 in T2, 22 in T3), the tier method expected 3.6 wrong keys and the subject method 0. The independent
review found none, which sides with the subject rates, as P2 did; under a Poisson reading, 0 or fewer at a mean of
3.56 has a probability of about 3%. This was seen after the job ran, is one subject, and was not joined question by
question; it is a reading, not a test.

### The review queue

`review_queue.json` lists the 716 unreviewed questions in tiers 1-3 (51 T1, 136 T2, 529 T3; 8.6% of the unreviewed
questions), ranked as pre-registered, each with its tier's measured rates. It is model-flagged, not expert-checked:
a row may be a wrong key, a second defensible answer or a mistake strong models share. Professional law fills 276 of
the 716 rows (15 / 48 / 213), and P2 and the outside check both suggest that tier rates overstate wrong keys in
subjects like it. A reading of the results (not a tested rule): start with T1 and T2 (187 rows; 57 of the 139
judged questions in these tiers were miskeyed, 41.0%), then T3 rows in subjects whose Redux sample already showed
wrong keys, such as virology (23 rows in tiers 1-3).
