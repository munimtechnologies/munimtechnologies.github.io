# medqa-openbookqa-fantastic-bugs-consensus

Audit 89 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-08, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library plus a parquet
reader.*

## Why

[Audit 88](../mcq-mmlu-fantastic-bugs-redux/) set Fantastic Bugs' published expert reviews (Truong et al., "Fantastic
Bugs and Where to Find Them in AI Benchmarks", NeurIPS 2025 Datasets and Benchmarks, arXiv 2511.16842;
`stair-lab/fantastic-bugs`, MIT) beside MMLU-Redux and audit 77's consensus flag (at least 6 of the 10 most accurate
models pick the same non-key option, more than pick the key). The flag fired on 60.5% of the questions whose review
names the key and on 3.7% of the questions reviewers called valid. But that comparison crossed splits: the *valid*
reviews come only from two medical MMLU subjects, and the answer-key reviews almost all from five other subjects.

Two more Fantastic Bugs splits hold both kinds of review inside one benchmark and one selection: **MedQA** (49 rows,
reviewed by two licensed medical professionals) and **OpenBookQA** (50 rows). Both benchmarks are in HELM Lite, whose
per-question outputs are public. This audit asks, within each benchmark, whether answer-level consensus separates the
items reviewers judged invalid from the ones they judged valid, among items that an item statistic had already
picked out as anomalous.

**Prior art.** Truong et al. rank items with item statistics over right/wrong matrices and report expert precision
for their top items; which wrong option models choose is not used. Stutz et al. (cited in the Gemini medical report,
arXiv 2404.18416) had clinicians relabel MedQA questions; a JMIR study traced MedQA model errors to benchmark
integrity problems; arXiv 2607.08065 audits cross-model agreement on GPQA and warns that shared errors are common;
arXiv 2608.03038 checks a statistics exam's keys against model consensus. We found no test of an answer-level
consensus flag against published expert reviews of MedQA or OpenBookQA items (search on 2026-11-08).

**What we saw before freezing.** To define the categories we read the first words of every review in the two splits
(MedQA: 26 begin "Valid", 23 "Invalid"; OpenBookQA: 48 "Correct", 2 "Incorrect", each followed by an answer) and
checked that every answer key has four options with one tagged correct. We had not joined any row to HELM or looked
at any model answer. The thresholds below were set knowing audit 88's MMLU medical figures (flag on 3 of 82 valid
questions and on 5 of 11 problem questions).

## Method

1. **HELM Lite.** Release v1.13.0: per benchmark (`med_qa`; `commonsense:dataset=openbookqa`,
   `multiple_choice_joint`), one run per model (newest suite). The question universe comes from the oldest suite's
   `instances.json` (test split, one gold), and each run's `display_predictions.json` is mapped to it through its own
   suite's instances. A model is included when it answers at least 99% of the universe, its predicted letter agrees
   with HELM's mapped output on at least 99% of answers, and our correct count is within 0.5% of HELM's own
   exact_match. The panel is the 10 most accurate included models of that benchmark; the flag is audit 77's rule,
   unchanged.
2. **Categories (frozen, `fb89.fb_category`).** MedQA: first word "valid" -> *valid*, "invalid" -> *invalid*.
   OpenBookQA: "correct" -> *valid*, "incorrect" -> *invalid*. Anything else -> *unclear* (left out). For an
   OpenBookQA "incorrect" review we also find the option the reviewer names (`fb89.suggested_option`).
3. **Placement.** As in audit 88: normalised question and options, then Mac Roman repair, then question text alone
   if it matches exactly one universe question. A second row on a placed question is dropped. Fantastic Bugs' tagged
   key must equal HELM's gold.
4. **Per item:** the flag, the consensus option, the top-10 votes and margin (most-picked non-key option's votes
   minus the key's), whether all 10 agree, and whether no included model picks the key.

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: fixtures match; the splits have 49 and 50 rows; at least 50 included models in each benchmark; at least 45 rows placed in each split; Fantastic Bugs' key equals HELM's gold on at least 95% of placed rows in each |
| P2 | HEADLINE (MedQA): the flag fires on a larger share of *invalid* items than of *valid* items |
| P3 | MedQA: the margin separates *invalid* from *valid* items with AUC at least 0.60 |
| P4 | MedQA: the flag fires on at most a quarter of *valid* items |
| P5 | OpenBookQA: the flag fires on at most a quarter of *valid* items |
| P6 | MedQA: the flag fires on at least a third of *invalid* items |

A comparison with a group under 5 items (10 for P4 and P5) is reported as undecidable and counts as not held.

Reasoning: in audit 88 the flag rarely fired on questions medical reviewers accepted and often on questions they
faulted, so P2-P4 should hold. Against them: every item here was chosen because strong models answer it worse than
weak ones, so strong models already disagree with the key more often than usual, and on a hard valid MedQA vignette
they may share one wrong answer; and "invalid" in MedQA covers missing information and ambiguity as well as wrong
keys, which the flag catches less often (audit 86 caught 14 of 84 flawed GSM8K questions). P6 is the least certain.
P5 can fail because OpenBookQA questions are short and commonsense-heavy, so a shared misreading by strong models is
plausible even when the key is right.

## What a result would mean

If P2 and P3 hold, answer-level consensus adds information inside one benchmark's anomalous sample, confirming audit
88's cross-split reading without its confound. If they fail, audit 88's separation may have come from comparing
different subjects and review styles. P4 and P5 measure how often the flag would send an expert a sound item from
such a list; P6, how much of what experts fault it finds. Exploratory, not predicted: unanimous flags and no-key
items by category, the mean number of top-10 votes for the key by category, each benchmark's flag rate over its whole
universe, and, for the two OpenBookQA "incorrect" rows, whether the consensus option is the one the reviewer names.

## Validity gates

Hand-traced fixtures (`cases89.py`, traced in the docstring of `test_fb89.py`: the categories, the suggested option,
answer-key parsing, placement, HELM instance parsing, prediction mapping, run selection by prefix and the verdicts,
including undecidable cases) must match before any data is read. At least 20 rows per split must be placed, or the
job writes its diagnostics and stops. The unit tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads HELM Lite v1.13.0 med_qa and openbookqa run files and Fantastic Bugs'
                              # med_qa and openbookqa viewer splits
```

## Files

- `base89.py`: functions copied unchanged from audit 88 (`base88.py`, `fb88.py`)
- `fb89.py`: the review categories, the suggested option and the verdicts
- `cases89.py`: the frozen settings, gates, data sources and fixtures
- `job.py`: downloads, model inclusion, the panel and flag per benchmark, placement and the comparison; writes
  `results.json` and `rows.json`
- `test_fb89.py`: unit tests; `requirements.txt`: a parquet reader only

## Licence

Code is Apache-2.0. This write-up and any results are CC BY 4.0. Upstream: HELM (Stanford CRFM) is Apache-2.0 and its
published run outputs keep their own terms; Fantastic Bugs' data is MIT; MedQA is MIT; OpenBookQA is Apache-2.0. Only
split names, row numbers, ids, positions, letters, our categories, votes and counts are published, never question,
option, review or model text. Authored by AI agents working in MV2's name (Munim, Inc.).
