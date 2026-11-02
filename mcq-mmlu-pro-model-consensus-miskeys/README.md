# mcq-mmlu-pro-model-consensus-miskeys

Audit 77 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-02, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library plus a parquet
reader.*

## Why

Audit 76 ([mcq-mmlu-pro-inherited-miskey-models](../mcq-mmlu-pro-inherited-miskey-models/)) found that on 46
MMLU-Pro questions whose MMLU key MMLU-Redux 2.0's experts marked wrong, all 45 published models it read pick the
experts' answer more often than the key (1,041 picks vs 283 pooled). MMLU-Redux only checked 5,700 of MMLU's
questions, and none of MMLU-Pro's 5,222 questions from other sources. So this audit asks: used as a detector, does
agreement among the strongest published models find miskeyed questions where experts have looked, and what does it
flag where they have not?

**Prior art.** Using many models' answers to find mislabelled test items is not new: Northcutt et al. ("Pervasive
Label Errors in Test Sets", 2021) used confident learning, and Land & Bikel ("Auditing LLM Benchmarks with Item
Response Theory", arXiv 2605.30504, EMNLP 2026) fit an IRT indicator to 114 models on seven preference and
multiple-choice benchmarks; their released item list (`Writer/IRT-mislabeled-items`) covers RewardBench 1 and 2,
RM-Bench, JudgeBench, GPQA Diamond and multiple-choice MATH and GSM8K, not MMLU-Pro, though its JudgeBench appendix
names two MMLU-Pro ids (6643, 8762). Song & Park (arXiv 2608.30372) find MMLU answer-key errors from model probability
landscapes and validate against MMLU-Redux. A search on 2026-11-02 found no model-consensus flag over all of
MMLU-Pro, none built from TIGER-AI-Lab's published per-question predictions, and no MMLU-Pro check validated against
MMLU-Redux's independent expert labels. What is new here is that combination: a frozen, simple rule, applied to
public predictions, scored against experts the models never saw, with every flagged id published.

## Method

1. **Predictions.** Every archive audit 66 listed is read with the reader and join rule of audits 65, 66 and 76 (a
   record joins only if its `question_id`, stripped options and answer equal the HF row; an archive is included only
   if at least 95% of its records join and it covers at least 95% of the test set).
2. **Panel.** The 10 included models with the highest MMLU-Pro accuracy on their joined questions (ties broken by
   name). A panel model without a joined prediction on a question counts as missing.
3. **The flag (frozen).** A question is FLAGGED when at least 6 of the 10 panel models pick the same option other
   than the key, and more of them pick it than pick the key. That option is the *consensus*.
4. **Expert labels.** MMLU-Redux 2.0 is joined to MMLU test and then to MMLU-Pro with audit 75's rules (question text
   plus at least 3 of MMLU's 4 options, same subject preferred). A single match carries the Redux label; ids in an
   ambiguous match are set aside. The join must reproduce audit 75 exactly (5,690 Redux rows joined to MMLU, 2,758
   single and 71 ambiguous MMLU-Pro matches, and the same 55 miskey ids) or the job aborts.
5. **Groups.** Redux-miskeyed (`wrong_groundtruth`), Redux-OK, other Redux error labels, MMLU-derived questions Redux
   never reviewed, and the source families (`ori_mmlu`, `stemez` STEM website, `theoremQA`, `scibench`).

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: both fixtures match; MMLU-Pro has 12,032 valid rows with audit 63's source families; the Redux join reproduces audit 75 (5,690 / 2,758 / 71 and the same 55 miskey ids); at least 30 archives are included; the panel has 10 models |
| P2 | HEADLINE: the flag rate on Redux-miskeyed questions is at least 5 times the flag rate on Redux-OK questions |
| P3 | At least 40% of audit 76's 46 targets are flagged, and on at least 80% of the flagged ones the consensus is the experts' answer |
| P4 | At least 20% of flagged Redux-judged questions carry a Redux error label (any of the five) |
| P5 | The flag rate on MMLU-derived questions Redux never reviewed is higher than on Redux-OK questions |
| P6 | The flag rate on STEM-website (`stemez`) questions is higher than on MMLU-derived questions |

Reasoning: P2-P4 test the flag where experts have looked. Redux reports about 6% of the MMLU questions it checked as
erroneous, so P4's 20% asks for at least about three times that base rate among flagged questions. P5 follows if
unreviewed questions carry MMLU's usual error rate while Redux-OK ones were cleared. P6 follows from MMLU-Pro's paper,
which names flawed answer extraction from the STEM website as a source of wrong keys, but numeric STEM questions can
also draw shared calculation slips, so it is a real test.

## What a result would mean

If P2-P4 hold, a panel of published models agreeing on one non-key option is a usable, cheap pointer to MMLU-Pro
questions that deserve an expert look, and `candidates.json` lists every one by `question_id`, with its source, the
key and consensus letters and the vote counts. The list is model-flagged, not expert-checked: a flag can also mark a
misconception the strong models share, an ambiguous question or a question with two defensible answers. If P2 or P4
fails, model agreement mostly marks hard questions rather than wrong keys, and that is reported as it comes out.
Exploratory, not predicted: the flag counts per group for thresholds 4 to 10 of 10, flag rates by category, the
status of the 46 targets one by one, and the two MMLU-Pro ids Land & Bikel name.

## Validity gates

Two hand-traced fixtures (`cases77.py`, traced in `test_consensus77.py`: one for the panel, flags and verdicts, one
for the Redux join) must match exactly before any real data is read; the MMLU-Pro parse must reproduce audit 63's
counts and the Redux join must reproduce audit 75's; the job aborts otherwise. The unit tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads MMLU-Pro, MMLU, MMLU-Redux 2.0 and TIGER-AI-Lab's prediction archives
```

## Files

- `consensus77.py`: the Redux join (audit 75's rules), panel, flag, groups, predictions, threshold curve
- `cases77.py`: the frozen rule and thresholds, audit 76's targets, audit 75's miskey ids, archives, both fixtures
- `job.py`: loaders, gates, joins; writes `results.json` and `candidates.json`
- `test_consensus77.py`: unit tests; `requirements.txt`: a parquet reader only

## Licence

Code is Apache-2.0. This write-up and any results are CC BY 4.0. Upstream: MMLU-Pro and MMLU are MIT, MMLU-Redux 2.0
is CC BY 4.0, and TIGER-AI-Lab's published evaluation outputs keep their own licence. Only ids, letters, counts and
sha256s are published, never question, option or model text. Authored by AI agents working in MV2's name (Munim,
Inc.).

## Results

*Added 2026-11-02, after the sealed run (started 2026-11-02 06:30 UTC, 226 s; 20 unit tests, both fixtures, the
structural gate and the Redux-join gate passed). Everything above this heading is unchanged from the
pre-registration. Frozen outputs: `results.json` (aggregates, per-target and threshold curve) and `candidates.json`
(all 1,210 flagged ids).*

**Status: results in. P1, P2, P3 and P5 held; P4 and P6 FAILED. The 10-model consensus flag finds the questions
MMLU-Redux's experts call miskeyed at 5.7 times the rate of questions they cleared, and recovers 34 of audit 76's 46
inherited miskeys. But at the frozen threshold most flags are not expert-labelled errors: of 359 flagged questions
that Redux judged, 65 (18.1%) carry any Redux error label and 36 (10.0%) a wrong-key label. So the 1,210 flags are a
list to review, not a list of errors.**

| # | Result |
| --- | --- |
| P1 | **HELD.** Both fixtures match; MMLU-Pro parses to 12,032 rows (`ori_mmlu` 6,810, `stemez` 4,083, `theoremQA` 598, `scibench` 541); the Redux join reproduces audit 75 (5,690 joined, 10 unmatched, 0 label conflicts; 2,758 single and 71 ambiguous MMLU-Pro matches; the same 55 miskey ids); **45 of 48** archives included (the same three as audit 76 excluded); panel of 10; 46 of 46 targets still keyed as in audit 75 |
| P2 | **HELD.** Flag rate on Redux-miskeyed questions **36 of 55 (65.5%)** vs Redux-OK **294 of 2,553 (11.5%)**: **5.68 times** (threshold 5) |
| P3 | **HELD.** **34 of 46** targets flagged (73.9%; threshold 40%); the consensus is the experts' answer on **31 of 34** (91.2%; threshold 80%) |
| P4 | **FAILED.** **65 of 359** flagged Redux-judged questions (**18.1%**; threshold 20%) carry a Redux error label: 36 wrong key, 29 other errors (unclear question or options, several or no correct answers). The other 294 (81.9%) were cleared by Redux |
| P5 | **HELD, narrowly.** MMLU-derived questions Redux never reviewed: **501 of 3,928 (12.75%)** vs Redux-OK 11.52% |
| P6 | **FAILED, the other way.** STEM-website questions are flagged **half as often**: `stemez` **271 of 4,083 (6.64%)** vs MMLU-derived **874 of 6,810 (12.83%)**. `theoremQA` 40 of 598 (6.69%), `scibench` 25 of 541 (4.62%) |

**The panel** (accuracy on joined questions): Gemini 3.1 Pro 91.1%, `arx_0314` 83.0%, iAsk Pro 81.3%, `arx_3` 78.4%,
Claude 3.5 Sonnet (2024-10-22) 77.7%, `claude-3.5-sonnet` 76.4%, GPT-4o (2024-08-06) 74.8%, `sonnet-3.5` 0-shot 73.2%,
GPT-4o (2024-05-13) 72.5%, Gemini 1.5 Pro 002 70.3%. The 10 slots are not independent: three are Claude 3.5 Sonnet
runs, two GPT-4o versions and two `arx` runs.

**Threshold curve (exploratory, read after the run).** How many of the 10 panel models must agree:

| Agree | Flagged (of 12,032) | Redux-miskeyed (of 55) | Redux-OK (of 2,553) | Ratio | Error label among flagged Redux-judged | Unreviewed MMLU (of 3,928) |
| --- | --- | --- | --- | --- | --- | --- |
| 4 | 1,682 | 40 | 371 | 5.0× | 75 of 446 (16.8%) | 654 |
| 5 | 1,496 | 39 | 343 | 5.3× | 72 of 415 (17.3%) | 614 |
| **6 (frozen)** | **1,210** | **36** | **294** | **5.7×** | **65 of 359 (18.1%)** | **501** |
| 7 | 892 | 30 | 213 | 6.5× | 58 of 271 (21.4%) | 383 |
| 8 | 626 | 27 | 157 | 8.0× | 46 of 203 (22.7%) | 262 |
| 9 | 418 | 27 | 113 | 11.1× | 38 of 151 (25.2%) | 168 |
| 10 | 201 | 21 | 49 | 19.9× | 28 of 77 (36.4%) | 79 |

A stricter rule trades recall for precision: with all 10 agreeing, 21 of 55 Redux miskeys are caught and 36.4% of
flagged Redux-judged questions carry an error label. P4's 20% would have been met from 7 of 10 upward, but 6 was the
frozen rule, so P4 stays FAILED. The unreviewed-MMLU flag rate is above the Redux-OK rate at 6 of 7 thresholds (not
at 9: 4.28% vs 4.43%), so P5's margin is small and not robust. The `stemez` rate is below the MMLU-derived rate at
every threshold (from 10.73% vs 16.36% at 4 to 0.93% vs 2.33% at 10).

**The 46 inherited miskeys one by one.** Flagged with the experts' answer as consensus: 31. Flagged with a third
option as consensus (the panel still rejects the key): 3725, 3811 and 9814. Not flagged: 12. On four of those, **all
10 panel models pick MMLU-Pro's key over the experts' answer: 6639 (virology), 8972 (abstract algebra), 9677
(astronomy) and 9947 (conceptual physics)**; on 7791 (abstract algebra) 9 of 10 do and on 4341 (college chemistry) 6
of 10. Three of the four unanimous cases (8972, 9677, 9947) rest on the 0-based reading of Redux's digit corrections
that audit 75 adopted after the fact, so the re-check should cover that reading as well as the expert label. The panel
splits evenly or nearly on 4438 (5 vs 5), 4346 (5 experts' answer vs 4 key) and 3990 (3 vs 3). On 4607 and 7687 two
non-key options tie for the lead; on 5885 a third option leads with 4 votes to the experts' answer's 3 and the key's 0.

**By category (exploratory).** Flag rates are highest in law (207 of 1,101, 18.8%) and history (66 of 381, 17.3%) and
lowest in math (58 of 1,351, 4.3%) and biology (44 of 717, 6.1%). A post-hoc guess, not tested here: law and history
questions leave more room for a second defensible reading, which would fit P4's failure.

**Land & Bikel's two MMLU-Pro ids (exploratory).** Neither is flagged. On 6643 the panel's top non-key option has 4
votes and the key 2 (all 45 models: key 25, that option 10). On 8762 the top non-key option has 4 votes, the key 1 and
3 panel models give no valid answer (34 of 45 models give none). This audit neither confirms nor rules out their
reading.

**What it means.** Where experts have looked, agreement among the strongest published models is a strong pointer to a
wrong key (5.7 times the base rate, and 31 of 46 known inherited miskeys recovered with the experts' answer), but a
weak verdict: at 6 of 10, about four in five flagged expert-reviewed questions were cleared by Redux's experts. Those
are either questions where the models share a mistake or a defensible second reading, or errors Redux missed; this
audit cannot tell which. One candidate cause it cannot test is that MMLU-Pro added six options per MMLU question that
Redux, which reviewed MMLU's four, never saw; MMLU-Pro's own paper (Table 1) reports that its expert review removed
1,953 false-negative options from its MMLU part, so a correct added option that review missed would look exactly like
a flag on a Redux-OK question. The
STEM-website questions that MMLU-Pro's paper names as a source of wrong keys are flagged half as often, which fits
either cleaner keys there or wrong answers that scatter across numeric options rather than agree. `candidates.json`
is a review list: 1,210 ids at the frozen rule, 201 with all 10 panel models agreeing. It is model-flagged, not
expert-checked. Limits: the panel's 10 slots come from fewer distinct models; the archives are TIGER-AI-Lab's
(5-shot chain-of-thought, mostly 2024 models); Redux labels are expert judgments of MMLU's four-option form, not of
MMLU-Pro's ten.
