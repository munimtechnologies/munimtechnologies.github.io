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
