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
