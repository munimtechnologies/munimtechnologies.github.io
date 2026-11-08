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

## Results

*Added 2026-11-08, after the sealed run (job `mcq-mmlu-fantastic-bugs-redux-v1`, 2026-11-07, 230 seconds; 12 of 12
unit tests passed first). Nothing above was changed. Every number below is from `results.json` and `rows.json` in
this folder; percentages are computed from the counts beside them. Readings marked post-hoc were not predicted.*

**All seven predictions held.**

| # | Result | Verdict |
| --- | --- | --- |
| P1 | Fixtures matched; the splits have 50 / 57 / 74 / 8 / 16 rows; audit 80 reproduced exactly (1,207 flags, 130 of 484 judged flags error-labelled); 171 of 189 MMLU rows placed (168 exact, 3 after the mojibake repair, 0 by question text alone; 14 ambiguous and 4 not found are left out); Fantastic Bugs' key equals HELM's gold on 171 of 171 | HELD |
| P2 | Among *key* questions Redux judged, 31 of 38 (81.6%) carry a Redux error label | HELD |
| P3 | Redux's wrong-key label: 27 of 38 *key* questions (71.1%) against 1 of 37 *other* questions (2.7%) | HELD |
| P4 | 0 of 32 judged *valid* questions carry a Redux error label | HELD |
| P5 | The flag fires on 26 of 43 *key* questions (60.5%) against 3 of 82 *valid* questions (3.7%) | HELD |
| P6 | 26 of 43 *key* questions (60.5%), above half | HELD |
| P7 | 1 of audit 86's 3 Platinum-kept S1 flags (GSM8K test position 1016) is among the 16 GSM8K rows | HELD |

The 171 placed questions split into 43 *key*, 46 *other* and 82 *valid*. Redux judged 107 of them (28 wrong key,
67 OK, 12 other error label) and left 64 outside its sample.

### What the holds rest on

- **The panels agree in one split.** All 38 judged *key* questions are from the five-subject split (college
  chemistry, econometrics, computer security, abstract algebra, US foreign policy). The paper says these were
  checked against public resources such as Wikipedia, not by subject experts. Its text names MMLU-Redux only in
  related work, so we treat the two reviews as independent, but we cannot rule out that a reviewer saw Redux. Within
  that split, 31 of 38 judged *key* questions carry a Redux error label against 8 of 30 judged *other* questions
  (26.7%).
- **P4 says little on its own.** The *valid* category exists only in the two medical splits, where Redux judged 36
  placed questions and labelled exactly 1 as an error (a professional-medicine question Fantastic Bugs also called a
  problem). Both panels finding these questions sound is the expected outcome.
- **P5 compares across splits,** because *valid* is medical-only and *key* is mostly five-subject. Post-hoc, the
  separation also holds inside each split: five-subject *key* 24 of 40 (60.0%) against *other* 6 of 30 (20.0%);
  medical *valid* 3 of 82 (3.7%) against a medical problem of either kind 5 of 11 (45.5%).
- **This is a selected sample.** Every row was chosen by Fantastic Bugs' item statistic, so 40 of the 107 judged
  questions (37.4%) carry a Redux error label, against 6.0% across Redux's random sample.

### Exploratory

- Cohen's kappa for "Fantastic Bugs problem" against "Redux error": 0.41 on the 107 judged questions; 0.37 on the 36
  judged medical questions, where it rests on a single Redux error and is unstable.
- Margin AUC for problem against *valid* in the medical splits: 0.711 (11 problems, 82 valid).
- Across all 107 judged questions, Redux labels an error on 18 of the 30 the flag fires on (60.0%) and on 22 of the
  77 it does not (28.6%). The flag fires on 11 of the 46 *other* questions (23.9%).
- **Three disputes:** *valid* questions the flag fires on. Redux judged one (OK) and has not reviewed the other two.
  Read after the run, paraphrased:
  - Clinical knowledge, HELM test position 234 (Redux OK): 9 of the 10 top models pick an option about which tuning
    fork to use for vibration sense; only 4 of 78 models pick the key. The fork frequency in that option is not the
    one usually recommended, so on our reading both panels are right and the models share a misconception.
  - Professional medicine, position 233 (unreviewed): an athlete with heat illness, a temperature just under the
    usual heat-stroke cut-off and low blood pressure. All 10 top models choose rapid cooling by cold-water
    immersion; the key is intravenous fluids, which the reviewer accepts because of the signs of shock; 47 of 78
    models pick the key. This is a disagreement between two treatments, not a clear wrong key, and it is the
    pattern an item statistic ranks highly: the strongest models leave the key that weaker models pick.
  - Professional medicine, position 259 (unreviewed): a medical-ethics question on which principle overrides
    patient autonomy when urging disclosure to a spouse; 6 of 10 top models pick one principle and 4 pick the key,
    a closely related one. Two principles are defensible.

  So of the three, one looks like a shared model mistake and two are defensible disagreements that a vote cannot
  settle. None is a clear case of a wrong key that both expert panels missed.

### GSM8K (exploratory)

All 16 rows join GSM8K's test set and HELM Lite's 1,000-question sample, and Fantastic Bugs' answer equals GSM8K's
on all 16. Their GSM8K-Platinum statuses, by the first words of Fantastic Bugs' review (post-hoc, read on
2026-11-08):

| Review type | Rows | Removed by Platinum | Revised | Kept (verified or consensus) |
| --- | --- | --- | --- | --- |
| Incorrect answer key | 6 | 4 | 2 | 0 |
| Ambiguous question | 3 | 3 | 0 | 0 |
| Construct issue | 3 | 2 | 0 | 1 (position 1016, verified) |
| HELM grades incorrectly | 4 | 1 | 0 | 3 (consensus) |

So Platinum's current release had already removed or revised 11 of the 12 rows that name a problem in the question
itself; the 3 kept "HELM grades incorrectly" rows describe a scorer problem, not a label error. The paper says its
expert "uncovered 16 additional invalid questions" that Platinum's revision had not detected. The published `gsm`
split is therefore either not that set of 16, or it was compared against different Platinum labels; neither the
paper nor the dataset card says which (checked 2026-11-08). We have not raised this with the authors.

Audit 86's S1 flag fires on 10 of the 16 rows (4 of the 6 answer-key rows, 6 of the 10 others). Position 1016 is
the P7 overlap: Fantastic Bugs calls it a construct issue, Platinum verified it, and audit 86 read it as a shared
misreading. Two of three views see a problem in the wording, and none sees a wrong key.

### What this means

Two independently built reviews of the same anomalous MMLU questions agree on answer-key problems (81.6%) and on the
kind of problem (71.1% against 2.7%). So this catalogue's precision figures, scored against MMLU-Redux alone, do not
look like an artefact of one panel, with the caveat that the agreement rests on five subjects reviewed against
public sources. Inside a sample already chosen by an item statistic, answer-level consensus still separates
answer-key problems from everything else, so the two signals are complementary, as predicted. Its few hits on
*valid* questions look like shared mistakes or defensible alternatives, not missed wrong keys.

### Limits

The groups are small (38, 37 and 32 judged questions). The categories are our reading of the reviews' first words
(`fb88.fb_category`), not Fantastic Bugs' own labels. Redux labels and Fantastic Bugs reviews are judgments, not
verified facts. The 18 unplaced MMLU rows (14 matching more than one HELM question, 4 matching none) are left out.
HELM's models date from up to late 2024. The dispute and GSM8K readings are post-hoc.

### Output files

- `results.json`: gates, placement counts, predictions and their numbers, tables by split, the GSM8K join and the
  exploratory figures, with sha256 hashes of every downloaded file.
- `rows.json`: one row per Fantastic Bugs row (split, row number, our category, HELM id and position, keys, Redux
  label, flag votes; for GSM8K, test position, Platinum status and audit 86's votes). No question, option, review or
  model text. Platinum statuses are CC BY-SA 4.0; Redux labels CC BY 4.0.
