# mcq-mmlu-pro-redux-inheritance

Audit 75 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-01, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library plus a parquet
reader.*

## Why

MMLU-Redux 2.0 (Gema et al., "Are We Done with MMLU?", arXiv 2406.04127; `edinburgh-dawg/mmlu-redux-2.0`, CC BY 4.0)
had experts label 100 MMLU test questions in each of 57 subjects as fine or as one of five error types, and give the
right answer for miskeyed ones. MMLU-Pro (Wang et al. 2024, arXiv 2406.01574; `TIGER-Lab/MMLU-Pro`, MIT) took 6,810
of its 12,032 test questions from MMLU (`src` "ori_mmlu-...") and says it had them reviewed.

**Prior art.** The MMLU-Redux paper states that "errors from the original MMLU persist in the extended MMLU-Pro
benchmark", but it gives no count and no list. The MMLU-Pro paper describes an expert phase that verified "the
accuracy of each answer" and reports (its Table 1) 350 incorrect answers, 1,953 false-negative options and 385 bad
questions found among the MMLU-sourced items; it does not list which questions were fixed. MMLU-Pro's dataset card records key fixes a few question ids at a time
(for example ids 143 and 6392 in July 2024, 15 medical answers in April 2025), and its maintainers have said they will
not make large-scale content changes. A search on 2026-11-01 (web, arXiv, the MMLU-Pro Hugging Face discussions)
found no study that joins Redux's labels to MMLU-Pro. Audit 62
([mcq-mmlu-pro-added-distractor-census](../mcq-mmlu-pro-added-distractor-census/)) joined MMLU-Pro to MMLU and found
the key text unchanged on 6,743 of 6,810 MMLU-derived questions, with 44 whose key text differs. Audit 69
([mcq-mmlu-redux-length-error-census](../mcq-mmlu-redux-length-error-census/)) found 106 miskeyed rows in Redux 2.0.

So this audit asks: of the questions MMLU's experts flagged, how many are in MMLU-Pro, and did MMLU-Pro keep the
disputed key? It also lists them by MMLU-Pro `question_id`, so MMLU-Pro users can check or exclude them.

## Method

1. **Redux to MMLU.** Each Redux row is matched to MMLU test (`cais/mmlu` `all`) by subject, whitespace-normalised
   question and the four normalised options in order. MMLU supplies the published key.
2. **MMLU to MMLU-Pro.** Each matched question is looked up among MMLU-Pro's `ori_mmlu` rows by normalised question
   text. A candidate counts only if at least 3 of MMLU's 4 options are among its options, because generic stems repeat
   inside a subject. Same-subject candidates are preferred. One candidate is a match, several are *ambiguous* (still
   in MMLU-Pro, but no key status), none is *not in MMLU-Pro*.
3. **Key status.** MMLU-Pro's key text is *kept* (the same as MMLU's key), *moved* (another of MMLU's options) or
   *new* (neither).
4. **The experts' answer.** For miskeyed rows (`wrong_groundtruth`), Redux's `correct_answer` is read as in audit 69:
   letters or the exact text of one option. Single digits (0- or 1-based, not documented) are reported as two
   sensitivity variants and are not used in any prediction. The answer is then located among MMLU-Pro's options.
5. **Inclusion.** Flagged (any of the five error labels) versus expert-OK rows: how often each is in MMLU-Pro,
   pooled and stratified by subject (Cochran-Mantel-Haenszel). Rows labelled `expert` (unsure) are left out.

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: MMLU-Pro test has 12,032 rows, 6,810 from MMLU; MMLU test has 14,042; Redux 2.0 has 5,700 rows in 57 subjects with audit 58/69's label counts; at least 99% of Redux rows match MMLU test by subject, question and options |
| P2 | At least 30% of the 5,700 Redux rows are in MMLU-Pro |
| P3 | HEADLINE: of the Redux-miskeyed questions MMLU-Pro contains (one match), MMLU-Pro keeps MMLU's disputed key on at least 75% (vacuous below 10) |
| P4 | Flagged questions are in MMLU-Pro more often than expert-OK ones: pooled risk ratio above 1 and Mantel-Haenszel odds ratio by subject above 1 |
| P5 | On inherited miskeys whose expert answer resolves (letters or text), that answer is still one of MMLU-Pro's options on at least 80% (vacuous below 10) |
| P6 | Where MMLU-Pro moved the key to another of MMLU's options, Redux had flagged the question (any non-OK label) on at least 50% (vacuous below 5) |

Reasoning behind P4: MMLU-Pro excluded questions that more than four of eight small models answered correctly
(5,886 questions, per its paper). A miskeyed question looks hard to such a filter, because a model that answers
correctly is marked wrong. MMLU-Pro's expert review could work the other way, and its paper reports 350 incorrect
answers found, so P3 and P4 are real tests.

## What a result would mean

If P3 holds, MMLU-Pro carries most of the MMLU miskeys that Redux found in the questions it took, and the list in
`pro_flags.json` names them by `question_id`. If P4 holds, MMLU-Pro's difficulty filter enriched MMLU's errors. If P6
holds, the keys MMLU-Pro did change were mostly real fixes. Any failure is reported as it comes out.

## Validity gates

A hand-traced fixture (`cases75.py`, traced row by row in `test_redux_pro.py`) must match exactly before any real
data is read (the job aborts otherwise), and the unit tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads MMLU-Pro (test), MMLU (all, test) and MMLU-Redux 2.0 (57 configs)
```

## Files

- `redux_pro.py`: joins, key status, the experts' answer, inclusion statistics, fixture summary
- `cases75.py`: datasets, pinned numbers, thresholds, the hand-traced fixture
- `job.py`: loaders, fixture gate, predictions; writes `results.json` and `pro_flags.json`
- `test_redux_pro.py`: unit tests; `requirements.txt`: a parquet reader only

## Licence

Code is Apache-2.0. This write-up and any results are CC BY 4.0. Upstream: MMLU-Redux 2.0 is CC BY 4.0; MMLU and
MMLU-Pro are MIT. Only counts, labels, `question_id`s, answer letters and sha256s are published, never question or
option text. Authored by AI agents working in MV2's name (Munim, Inc.).

## Results

*Added 2026-11-02, after the sealed run (started 2026-11-01 19:17 UTC, 177 s; unit tests and the fixture gate
passed). Everything above this heading is unchanged from the pre-registration. Frozen output: `results.json` and
`pro_flags.json`.*

**Status: results in. All 6 predictions held. P4 held only as worded: the pooled difference is within noise and the
within-subject one is modest. P6 held exactly at its 50% threshold, on 6 questions.**

| # | Result |
| --- | --- |
| P1 | **HELD.** MMLU-Pro test 12,032 rows (6,810 `ori_mmlu`), MMLU test 14,042, Redux 2.0 5,700 rows in 57 subjects with audit 58/69's label counts (ok 5,330, bad_question_clarity 132, wrong_groundtruth 106, multiple_correct_answers 39, no_correct_answer 36, expert 32, bad_options_clarity 25). **5,690 of 5,700** Redux rows (99.82%) join MMLU test (10 no match, 0 ambiguous), and Redux's `answer` equals MMLU's key on all 5,690 |
| P2 | **HELD.** **2,829 of 5,700** Redux rows (49.6%) are in MMLU-Pro: 2,758 with one match and 71 ambiguous. 2,861 are not in MMLU-Pro, 45 of them because the stem exists but no candidate shares 3 of MMLU's options; 6 single matches are filed under another subject |
| P3 | **HELD.** MMLU-Pro holds **55** of the 106 Redux-miskeyed questions with one match (56 counting one ambiguous) and keeps MMLU's disputed key on **52 of 55 (94.5%)**. It moved the key to another of MMLU's options on 3 (ids 2817, 8122, 8780) and used a new key text on 0 |
| P4 | **HELD as worded, weakly.** Flagged rows are in MMLU-Pro 174 of 337 times (51.6%) vs expert-OK rows 2,640 of 5,321 (49.6%): pooled risk ratio **1.04** (χ² 0.52, df 1, not significant). Within subject the Mantel-Haenszel odds ratio is **1.29** (CMH χ² 4.28, 46 informative strata; p < 0.05, not < 0.001) |
| P5 | **HELD.** 26 inherited miskeys have a letter or exact-text correction that differs from the key; all 26 are kept, and the experts' answer is still one of MMLU-Pro's options on **24 of 26 (92.3%)**. The two where it is not are virology ids 6586 and 6642. MMLU-Pro's key equals the experts' answer on 0 of the 26 |
| P6 | **HELD at the threshold.** MMLU-Pro moved the key on 6 of the questions it holds with one match: 3 Redux-miskeyed and 3 expert-OK (3 of 6, 50%) |

**By label** (questions with one MMLU-Pro match; "in MMLU-Pro" also counts ambiguous matches):

| Redux label | Joined | In MMLU-Pro | Kept | Moved | New |
| --- | --- | --- | --- | --- | --- |
| ok | 5,321 | 2,640 | 2,561 | 3 | 7 |
| bad_question_clarity | 131 | 62 | 61 | 0 | 1 |
| wrong_groundtruth | 106 | 56 | 52 | 3 | 0 |
| multiple_correct_answers | 39 | 23 | 23 | 0 | 0 |
| no_correct_answer | 36 | 17 | 17 | 0 | 0 |
| expert (unsure) | 32 | 15 | 15 | 0 | 0 |
| bad_options_clarity | 25 | 16 | 15 | 0 | 0 |

Every flagged question MMLU-Pro holds with one match is listed in `pro_flags.json` (MMLU-Pro `question_id`,
category, `src`, Redux label, key status, MMLU-Pro's key letter and, where it resolves, the letter of the experts'
answer among MMLU-Pro's options). Of the 172 questions there with one of the five error labels, 168 keep MMLU's key.

**The 52 inherited miskeys** (MMLU-Pro `question_id`; Redux `wrong_groundtruth`; key unchanged from MMLU):

- chemistry (18, all `college_chemistry`): 3538, 3636, 3637, 3725, 3811, 3814, 3894, 3990, 4084, 4088, 4089, 4341,
  4346, 4437, 4438, 4511, 4607, 4609
- health (9): virology 6067, 6068, 6277, 6278, 6586, 6639, 6640, 6642; anatomy 6224
- physics (5): 9547, 9677, 9733, 9814, 9947
- math (4, all `abstract_algebra`): 7687, 7791, 8876, 8972
- computer science (4): 10365, 10458, 10533, 10666
- other (4): 5225, 5726, 5885, 5949
- psychology (2): 1989, 2454
- law 1418; biology 2933; history 4752; economics 7306; philosophy 10859; engineering 11579

One of them, 5225 (`global_facts`), carries a Redux correction that names the published key's own option, so it is
miskeyed by label but has no usable correction; two (8876, 10859) have no correction at all.

**The digit-format corrections are 0-based (post-hoc reading, not pre-registered).** 26 of the 55 miskeys give the
experts' answer as a bare digit. Read 1-based, at least 7 of those digits are 0 (no option) and 8 point at the
published key itself, which a "wrong ground truth" label rules out. Read 0-based, all 26 point at an option other than the
key. The three keys MMLU-Pro moved are all digit-format rows, and under the 0-based reading MMLU-Pro's new key is the
experts' answer on **3 of 3** (under 1-based, 0 of 3). MMLU-Pro's dataset card lists id 2817 among answers it
corrected on 2024-09-06; 8122 and 8780 (both math) are not named there, though its 2024-08-07 math and engineering
entry ends with "etc.". Read 0-based, the experts' answer is still an MMLU-Pro option on **46 of 49** kept miskeys
that resolve (93.9%), and MMLU-Pro's key equals it on 3 of 52 (the three moves).

**What it means.** Of the MMLU questions that MMLU-Redux's experts judged miskeyed, about half are in MMLU-Pro, and
MMLU-Pro still grades 52 of the 55 it holds against MMLU's original key. Where MMLU-Pro did change one of these keys,
it changed it to the experts' answer (3 of 3, reading Redux's digit answers 0-based). In almost every kept case the experts' answer is still one of the ten options,
so a fix would be a one-letter key change, not a new question. MMLU-Pro's difficulty filter did not remove flagged
questions: they made it in at about the expert-OK rate, slightly more often within subject. Limits: Redux checked 100
questions per subject (5,700 of MMLU's 14,042), so MMLU-Pro questions Redux never looked at can carry more inherited
errors; Redux's labels are one expert pass and this audit did not re-check any of them; and 52 questions are 0.43% of
MMLU-Pro's 12,032, so overall scores move little, while `college_chemistry`-sourced chemistry, virology and abstract
algebra carry the most. A model-side check (do models choose the experts' answer on these questions more often than
the key?) is the natural next test.
