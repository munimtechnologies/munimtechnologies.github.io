# mcq-mmlu-cross-harness-consensus

Audit 81 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-05, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library plus a parquet
reader.*

## Why

Audits 77 and 80 tested a model-consensus flag for miskeyed questions: a question is flagged when at least 6 of the 10
most accurate models pick the same option other than the key, and more of them pick it than pick the key. On MMLU-Pro,
with TIGER-AI-Lab's published archives, 18.1% of the flagged questions that MMLU-Redux 2.0's experts judged carry an
expert error label ([audit 77](../mcq-mmlu-pro-model-consensus-miskeys/)). On the original MMLU, with Stanford CRFM's
HELM outputs, it is 26.9% ([audit 80](../mcq-mmlu-helm-consensus-miskeys/)). Either way, most flags fall on questions
the experts cleared.

Raising the agreement threshold within one panel helps (10 of 10 agree: 34.5% on MMLU-Pro, 50.8% on MMLU), but the
ten models in one panel share a prompt, a harness and many training habits. About half of MMLU-Pro's questions come
from MMLU, so the same MMLU question was answered by two different sets of models, in two harnesses, with different
option lists (4 options in HELM, up to 10 in MMLU-Pro). This audit asks whether flags that both panels raise, with the
same answer, are more often real errors than either panel's flags alone, and lists them, including questions outside
Redux's sample.

**Prior art.** Audits 77-80 and the work they cite (MMLU-Redux, arXiv 2406.04127; arXiv 2608.30372; arXiv
2601.07965; Kim et al., ICML 2025). Land and Bikel ("Auditing LLM Benchmarks with Item Response Theory", arXiv
2605.30504, EMNLP 2026) flag likely mislabels from 114 models' answers with an item-response fit on seven benchmarks
(not MMLU) and score them against an LLM reviewer. "Are LLMs Better than Reported?" (arXiv 2410.18889) re-labels data
with an ensemble of LLMs. We found no comparison of consensus flags from two independent harnesses on the same
questions, scored against human expert labels.

## Method

1. **HELM panel (audit 80, rebuilt).** HELM MMLU release v1.13.0; the question universe, inclusion rules, the 10 most
   accurate included models and the flag exactly as in audit 80. Gate: the universe (13,984), the 78 included models,
   the panel and audit 80's flag counts and precision (130 of 484) must be reproduced.
2. **MMLU-Pro panel (audit 77, rebuilt).** TIGER-Lab/MMLU-Pro test (12,032 questions) and TIGER-AI-Lab's 48
   published prediction archives, joined by `question_id` as in audits 77-79; the 10 most accurate archives and the
   same flag. Gate: audit 77's panel and its 1,210 flags (874 MMLU-derived, 271 STEM-website).
3. **The join.** Each MMLU-derived MMLU-Pro question (`src` = `ori_mmlu-<subject>`) is joined to the HELM question
   with the same subject and whitespace-normalised question text and at least 3 shared option texts. A MMLU-Pro row
   matching two HELM questions is dropped, as is a HELM question claimed by two MMLU-Pro rows (with both rows). The
   analysed set J keeps the pairs whose two keys have the same option text.
4. **Three flags on J.** HELM's flag; the MMLU-Pro flag; and their **agreement**: both flag the question, and the two
   consensus options have the same (normalised) text. Only the agreement flag is new.
5. **Expert labels.** MMLU-Redux 2.0 joined to the HELM universe as in audit 80. Precision = among flagged questions
   Redux judged (wrong key, OK or another error label), the share with an error label.

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: all eight fixtures match; audit 80 and audit 77 are both reproduced (gates above); at least 5,500 joined pairs have the same key text, and at least 97% of joined pairs do |
| P2 | HEADLINE: on J, the agreement flag is more precise than HELM's flag alone |
| P3 | On J, the agreement flag is more precise than the MMLU-Pro flag alone |
| P4 | The agreement flag keeps at least half of the Redux miskeys in J that HELM's panel flags |
| P5 | It is selective: the share of HELM's flagged Redux-OK questions in J that it keeps is at most half the share of HELM's flagged Redux miskeys it keeps |
| P6 | P2 also holds with virology left out (in audit 80, virology carried most of the precision gain) |

Reasoning: the two panels make different mistakes for different reasons. MMLU-Pro's added options draw many of audit
77's flags on cleared questions ([audit 78](../mcq-mmlu-pro-consensus-added-options/)), and an added option cannot be
the agreed answer, while a real miskey should pull both panels to the same correct option. P4 bets that agreement
costs little recall on true miskeys; P5 bets it removes cleared questions much faster; P6 checks that the gain is not
one damaged subject.

## What a result would mean

If P2-P5 hold, agreement across independent harnesses is a cheap, better filter for sending MMLU questions to
experts, and `agree_candidates.json` is a shortlist of MMLU questions outside Redux's sample that two independent
panels say are miskeyed. If P2 fails, the two panels share their mistakes about as much as they share real
detections, and consensus is limited by what models in general get wrong, not by the harness. Either way the list is
model-flagged, not expert-checked. Exploratory, not predicted: what MMLU-Pro's panel does on each HELM flag (agrees,
picks another MMLU option, picks an added option, does not flag), precision at 10 of 10 in one or both panels, and
counts by subject.

## Validity gates

Eight hand-traced fixtures (`cases81.py`, traced in `test_cross81.py`: audit 77's panel/flag fixture, and audit 80's
run selection, universe, answer mapping and Redux join fixtures, copied; new: the MMLU-Pro to HELM join, the
agreement flag and the verdicts) must match before any data is read. The MMLU-Pro parse must reproduce audit 63's
counts and the Redux join must place at least 4,000 rows, or the job aborts. The unit tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads HELM's MMLU release files, MMLU-Pro, TIGER-AI-Lab's archives, MMLU-Redux 2.0
```

## Files

- `cross81.py`: audit 80's HELM functions and audit 77's panel and flag (copied), the MMLU-Pro to HELM join, the key
  check, the agreement flag and the verdicts
- `cases81.py`: the frozen rule, gates, thresholds, data sources, archive list and the eight fixtures
- `job.py`: downloads, both panels, the join; writes `results.json` and `agree_candidates.json`
- `test_cross81.py`: unit tests; `requirements.txt`: a parquet reader only

## Licence

Code is Apache-2.0. This write-up and any results are CC BY 4.0. Upstream: HELM (Stanford CRFM) is Apache-2.0 and its
published run outputs keep their own terms; MMLU-Pro and MMLU are MIT; MMLU-Redux 2.0 is CC BY 4.0; TIGER-AI-Lab's
published evaluation outputs keep their own licence. Only ids, letters, counts and 16-hex sha256 prefixes of
normalised question text are published, never question, option or model text. Authored by AI agents working in MV2's
name (Munim, Inc.).

## Results

*Added 2026-11-06 from the sealed job `mcq-mmlu-cross-harness-consensus-v1` (run 2026-11-05, 413 s; the 13 unit tests
passed first). Everything above this heading is unchanged. Full numbers: [`results.json`](results.json); every
question both panels flag with the same answer: [`agree_candidates.json`](agree_candidates.json).*

**All six predictions held.** When HELM's panel (4 options, 78 models) and TIGER-AI-Lab's MMLU-Pro panel (up to 10
options, 45 archives) both flag the same MMLU question and pick the same answer text, **38 of 113 expert-judged
flags (33.6%) carry an MMLU-Redux error label, against 20.7% for HELM's flag alone and 18.2% for the MMLU-Pro flag
alone** on the same questions. Agreement keeps 29 of the 39 Redux miskeys HELM flags (74.4%) but only 75 of the 245
Redux-OK questions it flags (30.6%), and the gain survives without virology (29.2% vs 18.3%).

| # | Verdict | Counts |
| --- | --- | --- |
| P1 | HELD | fixtures 8/8; audit 80 reproduced (universe 13,984, 78 of 79 models, same panel, 1,207 flags, precision 130/484); audit 77 reproduced (same panel; 1,210 flags, 874 MMLU-derived, 271 STEM-website; 45 of 48 archives); 6,155 joined pairs, **6,127** with the same key text (99.5%; gates ≥ 5,500 and ≥ 97%) |
| P2 | HELD | agreement 38/113 = **33.6%** vs HELM alone 64/309 = 20.7% (+12.9 pts) |
| P3 | HELD | agreement 33.6% vs MMLU-Pro alone 65/358 = 18.2% |
| P4 | HELD | keeps 29 of the 39 HELM-flagged Redux miskeys (74.4%; needed ≥ 50%) |
| P5 | HELD | keeps 75 of 245 HELM-flagged Redux-OK questions (30.6%) vs 74.4% of miskeys; needed ≤ 37.2% (ratio 0.41) |
| P6 | HELD | without virology: agreement 31/106 = 29.2% vs HELM alone 55/300 = 18.3% |

**The join.** MMLU-Pro has 6,810 MMLU-derived rows. 18 found no HELM question with the same subject and question
text, 80 shared fewer than
3 options, 19 matched two HELM questions, and 538 rows were dropped because they claim a HELM question another
MMLU-Pro row also claims. That leaves 6,155 one-to-one pairs; 28 have keys with different text, so J holds 6,127
questions. MMLU-Redux judged 2,684 of them (52 miskeys, 2,517 OK, 115 other error labels; base rate 167/2,684 = 6.2%),
15 are unsure or conflicting, and 3,428 are outside Redux's sample. `moral_scenarios` has no question in J.

**Flags on J by group** (count flagged; share of the group):

| Group | n | HELM flag | MMLU-Pro flag | Agreement |
| --- | --- | --- | --- | --- |
| All of J | 6,127 | 715 (11.7%) | 807 (13.2%) | 227 (3.7%) |
| Redux miskey | 52 | 39 (75.0%) | 36 (69.2%) | 29 (55.8%) |
| Redux OK | 2,517 | 245 (9.7%) | 293 (11.6%) | 75 (3.0%) |
| Redux other error label | 115 | 25 (21.7%) | 29 (25.2%) | 9 (7.8%) |
| Redux unsure or conflicting | 15 | 5 | 2 | 1 |
| Not in Redux's sample | 3,428 | 401 (11.7%) | 447 (13.0%) | 113 (3.3%) |

Miskeys are flagged 7.7 times as often as OK questions by HELM's panel, 5.9 times by the MMLU-Pro panel and 18.7
times by their agreement. Taking either panel's flag (the union) is the least precise: 86 of 514 (16.7%).

**What the MMLU-Pro panel does on HELM's flags** (exploratory): of HELM's 715 flags in J, it agrees on 227, does not
flag 374, flags an option MMLU-Pro added in 96 and flags a different one of MMLU's own options in 18. On the 39
HELM-flagged miskeys: agrees 29, no flag 7, another MMLU option 3, an added option 0. On the 245 HELM-flagged OK
questions: agrees 75, no flag 135, an added option 32, another MMLU option 3.

**Unanimity** (exploratory): HELM's flag at 10 of 10 reaches 29/73 (39.7%) on J, MMLU-Pro's 28/77 (36.4%), and
agreement with both panels at 10 of 10 reaches **16 of 27 (59.3%)**. 54 questions in J meet that strictest rule, 27
of them outside Redux's sample.

**By subject** (exploratory; all subjects in `by_subject_exploratory`):

- Virology: 9 agreement flags, all 7 judged ones error-labelled; college chemistry: 7 flags, 7 of 7 error-labelled.
- Professional law has the most agreement flags, 49, of which 43 are outside Redux's sample; only 2 of its 6 judged
  flags carry an error label. Moral disputes: 15 flags, 11 outside the sample, 0 of 4 judged error-labelled.
- Security studies 10 (1 of 6 judged error-labelled), machine learning 9 (3 of 9), electrical engineering 6 (1 of
  6), computer security 6 (2 of 6), high-school European history 6, world religions 6.

**Post-hoc readings (not predicted; treat as leads).**

1. *The gain is not one subject.* Leaving out both virology and college chemistry, agreement is 24 of 99 (24.2%)
   against HELM alone 44 of 283 (15.5%). Among HELM's judged flags, those the MMLU-Pro panel confirms are error-labelled
   38/113 (33.6%) times and those it does not confirm 26/196 (13.3%) (χ² ≈ 18.1, 1 df, p < 0.001; a test chosen after
   seeing the data).
2. *The unreviewed shortlist leans on weak subjects.* Of the 113 agreement flags outside Redux's sample, 43 are
   professional law and 11 moral disputes, two subjects where the judged agreement flags were mostly cleared (2 of
   10 error-labelled). Expect the unreviewed list to be less precise than 33.6% overall; the 27 unreviewed questions
   at 10 of 10 in both panels are the strongest leads.

**What this means.** Two panels of models that never shared a prompt, a harness or an option list agree on fewer
MMLU questions than either flags alone, and those agreed flags are 1.6 to 1.8 times as often real errors
(33.6% vs 20.7% and 18.2%), while still finding most of the miskeys either panel finds. Cross-harness agreement is a
cheap filter for ordering MMLU questions for expert review. It is still not an error detector: two in three agreed,
judged flags were cleared by the experts, so models share many mistakes (or find a second defensible answer) across
harnesses too. `agree_candidates.json` lists the 227 questions (113 outside Redux's sample) with both panels' letters
and votes. They are model-flagged and not checked by experts.

**Limits.** J is the half of MMLU that MMLU-Pro kept, which differs from the rest (HELM's flag precision is 20.7% on
J against 26.9% on all of MMLU). Redux labels are expert judgments, not verified facts, and cover 100 questions per
subject. Both panels are dominated by models from 2024 and share model families (Claude 3.5 Sonnet, GPT-4o and
Gemini 1.5 Pro are in both), so the two panels are independent in harness and option list, not in models.
