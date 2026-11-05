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
