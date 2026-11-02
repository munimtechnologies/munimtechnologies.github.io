# mcq-mmlu-pro-consensus-added-options

Audit 78 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-02, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library plus a parquet
reader.*

## Why

Audit 77 ([mcq-mmlu-pro-model-consensus-miskeys](../mcq-mmlu-pro-model-consensus-miskeys/)) flagged 1,210 MMLU-Pro
questions where at least 6 of the 10 most accurate published models agree on one option other than the key. Where
MMLU-Redux 2.0's experts had looked, the flag found their miskeys at 5.7 times the base rate, but 294 of the 359
flagged questions they reviewed were ones they had cleared. MMLU-Redux reviewed MMLU's four options. MMLU-Pro kept
those four and added up to six more per question, written by GPT-4-Turbo; its own expert review then removed 1,953
added options from the MMLU part that were also correct (the paper's Table 1). If some such options remain, a strong
model would pick one, and the experts' "OK" would not cover it.

So this audit asks: when the panel agrees against the key, is the option it agrees on one of MMLU's original four, or
one that MMLU-Pro added?

**Prior art.** MMLU-Pro's paper (arXiv 2406.01574) reports the construction-time counts. Land & Bikel ("Auditing LLM
Benchmarks with Item Response Theory", arXiv 2605.30504) trace two JudgeBench items that come from MMLU-Pro to its
option augmentation, including id 6643, where an added option H gives a second defensible answer. MMLU-Pro+ (arXiv
2409.02257) adds second correct options on purpose. A search on 2026-11-02 found no count, over the released
MMLU-Pro, of how often model consensus against the key lands on an added option, and no list of such questions.

## Method

1. **Audit 77, re-run.** The same archives, join rule, panel (the 10 most accurate included models) and flag (at
   least 6 of 10 pick the same non-key option, and more of them than pick the key). The panel and the flag counts must
   reproduce audit 77 (1,210 flagged; 36 Redux-miskeyed, 294 Redux-OK, 29 other errors, 501 unreviewed MMLU-derived,
   874 MMLU-derived, 271 STEM-website).
2. **Map to MMLU.** Every MMLU test row is joined to MMLU-Pro with audit 75's rule (same normalised question, at least
   3 of MMLU's 4 options among MMLU-Pro's, same subject preferred, one match only). An MMLU-Pro id reached by MMLU rows
   with two different option sets is dropped.
3. **Origins.** On a mapped question, an MMLU-Pro option is ORIGINAL if its whitespace-normalised text equals one of
   MMLU's four choices and ADDED otherwise. Only *intact* questions, which keep all four MMLU choices, are classified,
   so an edited original option cannot be miscounted as added.
4. **Counts.** For flagged intact questions, the origin of the consensus option, by MMLU-Redux group and category.
   The baseline is the panel's non-key picks on *unflagged* intact MMLU-derived questions: how often a strong model's
   wrong answer lands on an added option when the panel does not agree.

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: all four fixtures match; MMLU-Pro has 12,032 valid rows; the Redux join reproduces audit 75; at least 6,000 of the 6,810 MMLU-derived questions map to one MMLU row and at least 85% of those are intact; audit 77's panel and flag counts are reproduced exactly; at least 30 archives are included |
| P2 | Control: on at least 80% of flagged Redux-miskeyed intact questions the consensus option is ORIGINAL (the experts' answer is one of MMLU's four) |
| P3 | On at least 50% of flagged Redux-OK intact questions the consensus option is ADDED |
| P4 | HEADLINE: the ADDED share among consensus options on flagged Redux-OK questions is higher than the ADDED share among the panel's non-key picks on unflagged MMLU-derived questions |
| P5 | Among flagged MMLU-derived questions, the ADDED share is higher in law than in all other categories together |

Reasoning: P2 checks the instrument, since a consensus that matches the experts' answer must be an original option.
P3 and P4 test the explanation for audit 77's failed P4: if flags on expert-cleared questions mostly mark added
options that are also correct, the consensus should land on added options, and more often than strong models' wrong
answers do in general (P4's baseline guards against added options simply being more tempting). If they mostly mark
shared mistakes on MMLU's own distractors, P3 and P4 fail. P5 follows audit 62, where law was the one category whose
added options changed the length cue most. About two in three non-key options are added, so P3's 50% is below the
rate a uniform pick would give, but strong models' wrong answers are not uniform; P4 is the comparison that matters.

## What a result would mean

If P3 and P4 hold, a large part of the MMLU-Pro questions where strong models agree against an expert-cleared key are
questions where an option MMLU-Pro added draws them, the pattern Land & Bikel describe for id 6643, and
`added_candidates.json` lists them by id for expert review. If P4 fails, the flags on cleared questions are not
explained by added options, and model agreement there mostly marks hard questions or shared mistakes. Either way the
list is model-flagged, not expert-checked. Exploratory, not predicted: the same counts for the other Redux groups and
for unreviewed questions, by category, for thresholds 4 to 10 of 10, and the status of ids 6643 and 8762.

## Validity gates

Four hand-traced fixtures (`cases78.py`, traced in `test_added78.py`: audit 77's panel/flag and Redux-join fixtures,
plus new ones for the MMLU map, the option origins and the verdicts) must match before any real data is read; the
MMLU-Pro parse must reproduce audit 63's counts and the Redux join audit 75's; the job aborts otherwise. The unit
tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads MMLU-Pro, MMLU, MMLU-Redux 2.0 and TIGER-AI-Lab's prediction archives
```

## Files

- `added78.py`: audit 77's join, panel and flag (copied unchanged), plus the MMLU map, option origins and verdicts
- `cases78.py`: the frozen rule, thresholds, audit 77's panel and counts, archives, the four fixtures
- `job.py`: loaders, gates, joins; writes `results.json` and `added_candidates.json`
- `test_added78.py`: unit tests; `requirements.txt`: a parquet reader only

## Licence

Code is Apache-2.0. This write-up and any results are CC BY 4.0. Upstream: MMLU-Pro and MMLU are MIT, MMLU-Redux 2.0
is CC BY 4.0, and TIGER-AI-Lab's published evaluation outputs keep their own licence. Only ids, letters, counts and
sha256s are published, never question, option or model text. Authored by AI agents working in MV2's name (Munim,
Inc.).

## Results

*Added 2026-11-02, after the sealed run (started 2026-11-02 12:16 UTC, 204 s; 8 unit tests, all four fixtures, the
structural gate, the Redux-join gate and the audit-77 reproduction passed). Everything above this heading is
unchanged from the pre-registration. Frozen outputs: `results.json` (aggregates, by group, by category, threshold
curve) and `added_candidates.json` (455 ids).*

**Status: results in. P1, P2, P3 and P4 held; P5 FAILED. When the 10-model panel agrees against a key that
MMLU-Redux's experts cleared, the option it agrees on is one MMLU-Pro added in 185 of 290 cases (63.8%), more often
than the panel's wrong answers land on added options elsewhere (56.7%). Where the experts say the key is wrong, the
consensus is one of MMLU's own four options in 36 of 36 cases. So added options explain part, not all, of audit 77's
flags on cleared questions: 105 of the 290 (36.2%) point at one of MMLU's own distractors.**

| # | Result |
| --- | --- |
| P1 | **HELD.** All four fixtures match; MMLU-Pro parses to 12,032 rows; the Redux join reproduces audit 75 (5,690 joined, 2,758 single and 71 ambiguous MMLU-Pro matches, 0 label conflicts, 55 miskey ids); **6,171** of 6,810 MMLU-derived questions map to one MMLU row and **5,818 (94.3%)** of those are intact; audit 77's panel and all seven flag counts (1,210 / 36 / 294 / 29 / 501 / 874 / 271) reproduced exactly; **45** archives included |
| P2 | **HELD.** Flagged Redux-miskeyed intact questions: consensus ORIGINAL on **36 of 36 (100%)**; threshold 80% |
| P3 | **HELD.** Flagged Redux-OK intact questions: consensus ADDED on **185 of 290 (63.8%)**; threshold 50% |
| P4 | **HELD.** 63.8% (185 of 290) vs the panel's non-key picks on unflagged intact MMLU-derived questions: **3,378 of 5,959 (56.7%)** added. Margin 7.1 points |
| P5 | **FAILED.** Flagged law questions: **69 of 139 (49.6%)** added, below all other categories together, **386 of 624 (61.9%)** |

**By MMLU-Redux group (flagged intact questions; the last column is the baseline for that group).**

| Group | Intact / all | Flagged intact | Consensus ADDED | Unflagged non-key picks ADDED |
| --- | --- | --- | --- | --- |
| Redux: wrong key | 52 / 55 | 36 | **0 (0%)** | 17 of 60 (28.3%) |
| Redux: OK | 2,442 / 2,553 | 290 | **185 (63.8%)** | 1,339 of 2,385 (56.1%) |
| Redux: other error | 107 / 117 | 28 | 15 (53.6%) | 88 of 169 (52.1%) |
| Redux: unsure or conflicting | 15 / 15 | 2 | 1 (50%) | 13 of 25 (52.0%) |
| Never reviewed by Redux | 3,202 / 3,928 | 407 | **254 (62.4%)** | 1,921 of 3,320 (57.9%) |
| All MMLU-derived | 5,818 / 6,810 | 763 | **455 (59.6%)** | 3,378 of 5,959 (56.7%) |

(The 142 MMLU-derived questions with an ambiguous Redux match are not intact by construction and are left out.)

**How to read the margin (exploratory, read after the run).** On the 5,818 intact questions, 31,146 of the 48,617
non-key options (64.1%) are ones MMLU-Pro added, about 5.35 added and 3.0 original per question, as expected from
MMLU's three distractors. The panel's scattered wrong answers favour MMLU's own distractors (56.7% added, below
64.1%), while its consensus on expert-cleared questions lands on added options at about the rate their number alone
would give (63.8%). So P4 holds, but the evidence is that added options draw consensus as often as their share, not
far more. No significance test was pre-registered; picks within a question are not independent, so the 7.1-point
margin should not be read as a precise effect size.

**Threshold curve (exploratory).** Consensus origin (original, added) on flagged intact questions, by how many of the
10 panel models must agree:

| Agree | Redux wrong key | Redux OK | ADDED share, Redux OK | Never reviewed | ADDED share, never reviewed |
| --- | --- | --- | --- | --- | --- |
| 4 | 39, 0 | 138, 227 | 62.2% | 199, 320 | 61.7% |
| 5 | 38, 0 | 126, 211 | 62.6% | 185, 303 | 62.1% |
| **6 (frozen)** | **36, 0** | **105, 185** | **63.8%** | **153, 254** | **62.4%** |
| 7 | 30, 0 | 64, 146 | 69.5% | 119, 190 | 61.5% |
| 8 | 27, 0 | 47, 110 | 70.1% | 80, 134 | 62.6% |
| 9 | 27, 0 | 33, 80 | 70.8% | 57, 86 | 60.1% |
| 10 | 21, 0 | 19, 30 | 61.2% | 34, 34 | 50.0% |

The control holds at every threshold: the consensus on Redux-miskeyed questions is never an added option. On
Redux-OK questions the added share stays between 61% and 71%, with no steady trend.

**By category (exploratory, flagged intact MMLU-derived questions, all Redux groups).** Added share is highest in
psychology (46 of 60, 76.7%), physics (30 of 40, 75.0%), business (15 of 20, 75.0%) and economics (40 of 55, 72.7%),
and lowest in engineering (4 of 13, 30.8%), chemistry (7 of 22, 31.8%), computer science (12 of 34, 35.3%) and
philosophy (28 of 66, 42.4%). Law, the category with the most flags (139), splits evenly (70 original, 69 added).
Audit 62's length-cue change in law did not carry over to where model consensus lands, so P5 fails.

**Land & Bikel's two ids (exploratory).** On 6643 (virology, not flagged: 4 panel models pick the top non-key option,
2 the key, 1 none), the option the panel leans to is one MMLU-Pro added, which agrees with their reading. 8762
(SciBench calculus) is not MMLU-derived, so it has no origin here.

**What it means.** Audit 77 left open why about four in five of its flags on expert-reviewed questions were on
questions the experts had cleared. One part of the answer is now counted: on 185 of those 290 questions, the strong
models agree on an option that MMLU-Pro added and MMLU-Redux's experts never saw, slightly more often than their
wrong answers land on added options elsewhere. These are the questions where a second defensible answer among the
added options is most plausible. The other 105 point at one of MMLU's own three distractors, which the experts did
see and still cleared; those look more like shared model mistakes or expert misses, and added options cannot explain
them. `added_candidates.json` lists all 455 MMLU-derived questions (185 Redux-OK, 254 never reviewed, 15 other error,
1 unsure) whose panel consensus is an added option, with key and consensus letters, vote counts and the number of
added options. It is model-flagged, not expert-checked: each may hold a second correct answer, a shared model mistake,
or a wrong key. Limits: origin is decided by exact normalised text, so a question where MMLU-Pro reworded any of
MMLU's four options is excluded as not intact (5,818 of 6,171 mapped questions kept); the panel's 10 slots come from fewer distinct models; the archives are TIGER-AI-Lab's 5-shot chain-of-thought
runs, mostly of 2024 models.
