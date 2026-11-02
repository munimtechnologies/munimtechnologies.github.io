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
