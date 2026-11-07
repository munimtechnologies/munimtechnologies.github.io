# mcq-mmlu-fantastic-bugs-redux

Audit 88 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-07, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library plus a parquet
reader.*

## Why

Audits 77-87 scored a model-consensus flag for wrong answer keys (at least 6 of HELM's 10 most accurate models pick
the same non-key option, more than pick the key) against one expert panel: MMLU-Redux 2.0's labels on a random 100
questions per MMLU subject (and, in [audit 86](../gsm8k-helm-consensus-platinum/), GSM8K-Platinum on GSM8K). One
panel can be wrong too. **Fantastic Bugs** (Truong et al., "Fantastic Bugs and Where to Find Them in AI Benchmarks",
NeurIPS 2025 Datasets and Benchmarks, arXiv 2511.16842) gives a second, independent one: they ranked items by an item
statistic (tetrachoric correlation) on HELM right/wrong matrices, sent about the top 50 per benchmark to reviewers
(two licensed medical professionals for clinical knowledge and professional medicine; a math-assessment psychologist
for high-school math; public sources for a 5-subject set) and published the reviewed rows with a free-text review
(`stair-lab/fantastic-bugs`, MIT): 50 clinical-knowledge, 57 professional-medicine, 74 five-subject and 8 math rows
of MMLU, and 16 GSM8K rows (the paper reports 16 GSM8K problems beyond the 88 that GSM8K-Platinum marks).

This audit puts three opinions side by side on the same questions: Fantastic Bugs' review, MMLU-Redux's label, and
the consensus flag. It asks whether the two expert panels agree, and whether answer-level consensus (which wrong
option strong models pick) separates the reviewers' answer-key problems from the items they judged valid, inside a
sample that was chosen by a different signal.

**Prior art.** Truong et al. compare their GSM8K flags with GSM8K-Platinum and mention MMLU-Redux only in related
work; their detector uses right/wrong matrices, so which wrong option a model picks is discarded (checked in the
paper's HTML on 2026-11-07). Gema et al. (arXiv 2406.04127) built MMLU-Redux; we found no comparison of Redux's labels
with a second expert review of the same MMLU questions, and no test of answer-level consensus against Fantastic Bugs'
reviews. Our own earlier statement that nobody had scored HELM's GSM8K outputs against Platinum was wrong and is
corrected in audit 86's Results.

**What we saw before freezing.** We read the published review fields to define the categories below, so we knew the
category tallies (for example, most clinical and professional-medicine rows are reviewed as valid, and most
five-subject rows name the answer key). We had not joined any row to HELM, Redux or a flag, and we did not look up
which GSM8K questions the 16 rows are.

## Method

1. **Data and gates.** Audit 80 rebuilt exactly: HELM MMLU release v1.13.0 (13,984 questions, 78 included models),
   MMLU-Redux 2.0 joined by subject, question and options, audit 77's flag on the 10 most accurate models (must
   reproduce 1,207 flags and precision 130 / 484). Fantastic Bugs' viewer splits are read through the HF parquet
   API (never the 40 GB `raw/` folder).
2. **Categories (frozen, `fb88.fb_category`).** *valid*: the review's first word is "valid" (clinical knowledge and
   professional medicine only; the other splits publish only problem rows). *key*: the review points at the answer
   key (first word "key" or "bad key" in the five-subject and math splits; "incorrect" first or the word "key" in the
   two medical splits; "Incorrect Answer Key" in GSM8K). *other*: any other problem (ambiguous, construct, "all of the
   above", formatting, missing information, grading).
3. **Placement.** Each MMLU row is placed in the HELM universe by normalised question and options (any subject);
   failing that, after repairing Mac Roman mojibake; failing that, by question text alone if exactly one universe
   question has it. A second row on an already placed question is dropped. Fantastic Bugs' tagged key must equal
   HELM's gold.
4. **Three opinions per question.** Redux group (wrong key, OK, other error, unsure, unreviewed), the top-10
   consensus flag and its margin, and the no-key flag (no included model picks the key). *Judged* = Redux wrong
   key, OK or another error label; *Redux error* = any of the five error labels.
5. **GSM8K.** The 16 rows are joined to GSM8K's test set by question text, labelled with GSM8K-Platinum's status, and
   looked up in audit 86's published `candidates.json` (the S1 = top-10 consensus flag). HELM Lite's GSM8K universe
   is read from one model's `instances.json`.

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: fixtures match; the five Fantastic Bugs splits have 50 / 57 / 74 / 8 / 16 rows; audit 80 reproduces; at least 170 of the 189 MMLU rows are placed; Fantastic Bugs' key equals HELM's gold on at least 95% of placed questions |
| P2 | HEADLINE: among *key* questions that Redux judged, at least half carry a Redux error label (the two panels agree on answer-key problems) |
| P3 | Redux's wrong-key share is higher among *key* questions than among *other* questions (the panels agree on the kind of problem) |
| P4 | Among *valid* questions that Redux judged (at least 10), at most a quarter carry a Redux error label |
| P5 | The top-10 consensus flag fires on a larger share of *key* questions than of *valid* questions |
| P6 | The flag fires on at least half of the *key* questions |
| P7 | At least one of audit 86's S1-flagged GSM8K questions that Platinum kept is among Fantastic Bugs' 16 published GSM8K problems |

A comparison with a group under 5 questions (10 for P4) is reported as undecidable and counts as not held.

Reasoning: both panels read the same keys, and a wrong key is the most checkable kind of problem, so P2 and P3
should hold; against them, Redux's annotators and Fantastic Bugs' reviewers worked to different guidelines, and the
five-subject reviews were checked against public sources rather than by subject experts. P4 can fail because every
row was chosen for looking anomalous: strong models answer these questions worse than weak ones, which is also what a
subtle wrong key looks like. P5 and P6 follow from audits 77-85, where flagged questions were wrong keys far above the
base rate; against them, Fantastic Bugs selected on right/wrong patterns, and on a valid question that strong models
miss they may also agree on one wrong option. Audit 86's three kept S1 flags looked like misreadings that strong
models share; such questions are exactly what an item statistic ranks highest, and a reviewer might call them
ambiguous, so P7 is a coin flip.

## What a result would mean

If P2-P4 hold, two independent expert reviews agree on MMLU's answer-key problems, which strengthens every
precision figure in this catalogue that rests on Redux alone. If P2 fails, at least one panel misses many wrong keys,
and precision figures scored against a single panel should be read as lower bounds or upper bounds depending on
which one. If P5 and P6 hold, answer-level consensus adds information inside a sample already chosen by an item
statistic, so the two signals are complementary; if they fail, consensus flags mostly re-find what the item statistic
already found. Exploratory, not predicted: Cohen's kappa of "Fantastic Bugs problem" against "Redux error" (all
judged questions and the two medical splits), the margin AUC for problem against valid in the medical splits, the
questions Fantastic Bugs judged valid but the flag fires on, with Redux's view of them, and the GSM8K rows' Platinum
statuses and S1 votes.

## Validity gates

Hand-traced fixtures (`cases88.py`, traced in the docstring of `test_fb88.py`: the categories, the mojibake repair,
answer-key parsing, placement by each method, Redux groups, kappa and the verdicts, including the undecidable
cases) must match before any data is read. The Redux join must place at least 4,000 rows, and at least 100 Fantastic
Bugs rows must be placed, or the job aborts. The unit tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads HELM's MMLU release files, MMLU-Redux 2.0, Fantastic Bugs' viewer splits,
                              # GSM8K, GSM8K-Platinum and audit 86's candidates.json
```

## Files

- `base88.py`: functions copied unchanged from audits 80-87 (`base87.py`) and audit 86 (`gsm86.py`)
- `fb88.py`: the review categories, mojibake repair, answer-key parsing, placement, Redux groups, kappa and verdicts
- `cases88.py`: the frozen settings, gates, data sources and fixtures
- `job.py`: downloads, gates, placement, the three-way comparison and the GSM8K join; writes `results.json` and
  `rows.json`
- `test_fb88.py`: unit tests; `requirements.txt`: a parquet reader only

## Licence

Code is Apache-2.0. This write-up and any results are CC BY 4.0. Upstream: HELM (Stanford CRFM) is Apache-2.0 and its
published run outputs keep their own terms; MMLU is MIT; MMLU-Redux 2.0 is CC BY 4.0; Fantastic Bugs' data is MIT;
GSM8K is MIT; GSM8K-Platinum is CC BY-SA 4.0. Only split names, row numbers, ids, positions, letters, our categories,
labels and counts are published, never question, option, review or model text. Authored by AI agents working in
MV2's name (Munim, Inc.).
