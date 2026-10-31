# mcq-mmlu-redux-length-error-census

Audit 69 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code, the pre-registered
predictions and the frozen `results.json` are open and reproducible in a sealed container with only the Python
standard library plus a parquet reader.*

## What this targets

Audits 52 and 60 found that MMLU carries a small question-free "pick the longest option" shortcut (28.05% against
25% chance). MMLU-Redux 2.0 (Gema et al. 2024, arXiv 2406.04127; `edinburgh-dawg/mmlu-redux-2.0`, CC BY 4.0) had
experts re-check 100 questions from each of MMLU's 57 subjects and label each one OK or with an error type; for
questions whose answer key is wrong (`wrong_groundtruth`) it often gives the answer the experts think is right.

This audit asks three things on those 5,700 re-checked questions:

1. **Does the length floor survive cleaning?** Pick-longest on the expert-OK subset versus all rows.
2. **On miskeyed questions, which answer does length point to?** Pick-longest credit and length rank of the
   published key versus the expert-corrected key, on the same questions.
3. **Can length flag miskeys without reading the question?** Two flags ("the key is the unique shortest option",
   "another option is the unique longest") against the expert labels, pooled and within subject.

## Prior art

A search on 2026-10-30 found no analysis joining answer-length cues to expert miskey labels. The MMLU-Redux paper
reports no length analysis, and its synthetic wrong-ground-truth errors are built by picking a random wrong
option, so they carry no length signal by design. Audit 58 in this catalogue joined MMLU-Redux to meta options
("all of the above"), not to length.

## Pre-registered predictions (frozen before any real number was seen)

| # | Prediction | Verdict |
| --- | --- | --- |
| P1 | Structural gate: 57 subjects, 5,700 rows, 0 invalid, label counts identical to audit 58 | **HELD** |
| P2 | On the expert-OK subset, pick-longest beats chance (z > 3.29) | **HELD** (0.2912, lift +4.12 pts, z 7.22) |
| P3 | Against the published key, miskeyed questions carry a smaller lift than OK ones | **HELD** (-7.94 vs +4.12 pts) |
| P4 | HEADLINE: on miskeyed questions with one usable correction, pick-longest credit is higher against the corrected key than against the published key (direction only; needs 30+ pairs) | **HELD** (0.3457 vs 0.1574, n 54) |
| P5 | "The key is the unique shortest option" enriches for miskeys (pooled risk ratio > 1 and within-subject direction > 0) | **HELD, but only nominally** (RR 1.09, χ² 0.11) |
| P6 | Dropping the non-OK rows moves the pooled floor by under half a point | **HELD** (+0.47 pts) |

## Validity gates

- Hand-traced fixtures for tie-aware credit, length rank, correction parsing, the paired comparison and the
  detectors match exactly before any real data is read.
- The 5,700 rows, 57 subjects and every label count reproduce audit 58 (ok 5,330; bad_question_clarity 132;
  wrong_groundtruth 106; no_correct_answer 36; multiple_correct_answers 39; expert 32; bad_options_clarity 25).
- The pooled floor matches the released [mcq-length-floor](https://github.com/munimtechnologies/mcq-length-floor)
  0.1.0 to every digit (n 5,700, pick-longest 0.286491..., pick-shortest 0.220088...). The job aborts on any mismatch.

## What it found

**1. Cleaning does not remove the floor.** On all 5,700 rows pick-longest scores 28.65% (+3.65 pts, z 6.66). On the
5,330 questions the experts judged OK it scores **29.12%** (+4.12 pts, z 7.22), so dropping the flagged questions
raises the floor by 0.47 pts rather than lowering it. The length shortcut is a property of correctly keyed MMLU
questions, not of its errors.

**2. On miskeyed questions the length cue points to the experts' answer.** Scored against the published key, the
106 miskeyed questions sit *below* chance for pick-longest (17.06%, -7.94 pts, z -2.58). On the 54 of them whose
correction names exactly one other option by letter, the comparison is paired:

| on the same 54 miskeyed questions | published key | expert-corrected key |
| --- | --- | --- |
| pick-longest credit | .1574 | .3457 |
| mean length rank (0 shortest, 1 longest, 0.5 no lean) | .426 | .599 |
| key is the unique longest option | 4 | 13 |
| key is the unique shortest option | 12 | 3 |

The paired difference is **+18.8 pts (se 7.6, z 2.48)** in pick-longest credit and +0.173 in length rank (z 2.84).
In other words, the published wrong key looks like a typical distractor (short), and the corrected key looks like a
typical MMLU gold (long).

The correction format is not documented for 46 miskeyed questions that give a single digit instead of a letter.
Reading those digits as 0-based (n 100) gives +15.2 pts (z 2.53); as 1-based (n 72) +15.5 pts (z 2.19). The
direction is the same under every reading.

**But virology dominates.** 33 of the 106 miskeyed questions are virology (then college chemistry 21, abstract
algebra 6), and 33 of the 54 letter-resolved pairs are virology questions. Without virology the difference is +11.1
pts on 21 pairs (z 1.48): the same direction, not significant on its own. Many of virology's miskeys sit in one block
of consecutive questions (around rows 73-99 of that subject, from a read of the file on 2026-10-30), which looks like keys shifted during data entry;
a shifted key lands on an arbitrary option, so the published key would lose the gold's usual length advantage and
the corrected key keep it. That reading is a hypothesis, not checked by hand.

**3. Length is a weak miskey detector.** Among the 5,668 judged questions (the 32 labelled `expert` are left out),
the miskey rate is 2.00% when the key is the unique shortest option and 1.84% otherwise: risk ratio 1.09, χ² 0.11,
within-subject (Cochran–Mantel–Haenszel) direction positive but χ² 0.30. P5's direction held, but this flag does not
find miskeys. The other flag does slightly better: when some other option is the unique longest, the miskey rate is
2.10% against 1.57% (risk ratio 1.34, MH odds ratio 1.64, CMH χ² 4.68, below the 10.83 needed at α=0.001;
exploratory). Neither flag is useful for cleaning a benchmark on its own.

| slice (published key) | n | pick-longest | pick-shortest | chance | lift (pts) | z |
| --- | --- | --- | --- | --- | --- | --- |
| all rows | 5,700 | .2865 | .2201 | .2500 | +3.65 | 6.66 |
| expert OK | 5,330 | .2912 | .2190 | .2500 | +4.12 | 7.22 |
| any error label | 338 | .2162 | .2345 | .2500 | -3.38 | -1.72 |
| wrong_groundtruth | 106 | .1706 | .2681 | .2500 | -7.94 | -2.58 |
| bad_question_clarity | 132 | .2008 | .2475 | .2500 | -4.92 | -1.58 |
| multiple_correct_answers | 39 | .2970 | .1560 | .2500 | +4.70 | 0.70 |
| no_correct_answer | 36 | .2407 | .2037 | .2500 | -0.93 | -0.16 |
| bad_options_clarity | 25 | .3300 | .1900 | .2500 | +8.00 | 0.89 |
| expert (unsure) | 32 | .2448 | .2552 | .2500 | -0.52 | -0.07 |

Pick-longest and pick-shortest are tie-aware accuracies; lift = pick-longest minus chance in percentage points; z is
the lift over its standard error.

**Reading it:** MMLU's length floor (~29% on cleaned questions) should be expected to survive benchmark cleaning.
When a key is wrong, the gold's usual length advantage tends to move to the corrected answer, which is consistent
with miskeys being data-entry slips rather than badly written options; but outside virology the evidence is thin.

## Limits

- **Small n.** 54 letter-resolved pairs, 33 of them from one subject. The without-virology result is not
  significant.
- **Observational.** No model is evaluated; the corrected key is the MMLU-Redux experts' judgement, not ground truth.
- The digit-format corrections are 0- or 1-based (undocumented); both readings are reported, neither is assumed.
- P5 held only in direction; the stronger "other option is unique longest" result was not pre-registered as a
  headline and is exploratory.
- Lengths are Unicode code points after `str.strip()`. No question, option or suggested-answer text is republished;
  `results.json` holds only counts and rates.

## Reproduce

```
python -m unittest -v        # hand-traced fixtures
python job.py --out-dir out  # downloads MMLU-Redux 2.0 (57 configs) and mcq-length-floor 0.1.0; writes out/results.json
```

The sealed run (job `mcq-mmlu-redux-length-error-census-v1`, 1 CPU, 1 GB) took under 4 minutes. To compute the
same floor on your own benchmark, use [mcq-length-floor](https://github.com/munimtechnologies/mcq-length-floor).

## Files

- `job.py`: loader, structural gate, tool cross-check, floors, paired miskey comparison, detectors, predictions;
  writes `results.json`
- `redux_length.py`: tie-aware credit, length rank, correction parsing, paired statistics, 2x2 and CMH tests
- `cases.py`: hand-traced fixtures, dataset configuration, audit-58 label counts
- `test_redux_length.py`: unit tests
- `results.json`: frozen output (floors by class, label and subject; correction formats; paired reports for four
  variants; detector tables; parquet sha256s; predictions)
- `requirements.txt`: a parquet reader only

## Licence

Code is Apache-2.0. This write-up and `results.json` are CC BY 4.0. Upstream: MMLU-Redux 2.0
(`edinburgh-dawg/mmlu-redux-2.0`) is CC BY 4.0; MMLU is MIT. Authored by AI agents working in MV2's name (Munim, Inc.).
