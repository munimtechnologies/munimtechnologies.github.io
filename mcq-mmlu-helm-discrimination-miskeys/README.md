# mcq-mmlu-helm-discrimination-miskeys

Audit 82 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-06, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library plus a parquet
reader.*

## Why

Audits 77-81 flag a multiple-choice question as possibly miskeyed when at least 6 of the 10 most accurate models pick
the same option other than the key. On MMLU with Stanford CRFM's HELM outputs, 26.9% of its flags that MMLU-Redux
2.0's experts judged carry an expert error label ([audit 80](../mcq-mmlu-helm-consensus-miskeys/)); confirming a flag
with a second, independent harness raises that to 33.6% ([audit 81](../mcq-mmlu-cross-harness-consensus/)).

The consensus flag listens to 10 models and ignores the other 68 HELM evaluated. Test theory has an older signal that
uses all of them: **item discrimination**. If stronger test-takers pick an item's key *less* often than weaker ones,
the key is suspect. This audit computes the classical item-rest correlation for every MMLU question across HELM's 78
included models and asks, before looking, whether it finds MMLU-Redux's expert-labelled errors better than the
consensus flag does, both at the same number of flags and without any threshold.

**Prior art.** Land and Bikel ("Auditing LLM Benchmarks with Item Response Theory", arXiv 2605.30504, EMNLP 2026)
flag likely mislabels from where a four-parameter item-response model says stronger models grow less correct, on 114
models and seven benchmarks (not MMLU), scored against an LLM reviewer. Hofmann et al. ("Fluid Language Model
Benchmarking", arXiv 2509.11106, COLM 2025) fit a two-parameter model to 102 Open LLM Leaderboard models, note that
low-discrimination items are often mislabeled, and count MMLU-Redux mislabels in the items their method selects; they
report no precision or recall for discrimination as a detector and no comparison with model agreement. Jiang et al.
("AI Evaluation Should Require Standardized Item-Level Data Releases", arXiv 2604.03244) compute item-rest correlations
on 567 MMLU items from 66 models and point to near-zero or negative items as needing scrutiny, without checking them
against expert labels. Chen et al. (β³-IRT, arXiv 1903.04016) link negative discrimination to wrong labels for
classifiers. We found no pre-registered, head-to-head test of discrimination against model consensus as an MMLU miskey
detector, scored against MMLU-Redux's 5,700 expert labels.

## Method

1. **HELM and the consensus flag (audit 80, rebuilt).** HELM MMLU release v1.13.0; the question universe, the
   inclusion rules (78 of 79 models), the 10 most accurate included models and audit 77's flag exactly as in audit
   80. Gate: the universe (13,984), the 78 models, the panel, the flag counts (1,207) and precision (130 of 484) must
   be reproduced.
2. **Item-rest correlation r.** For each question and each included model with a prediction for it: x = 1 if the
   model picked the key (a missing or invalid answer counts as 0), and y = the model's accuracy on its other covered
   questions. r = Pearson(x, y). If every model picked the key, r = +1; if none did, r = -1 (the strongest possible
   sign); with fewer than 2 models, r = 0.
3. **Two discrimination flags.** *Budget*: the K questions with the most negative r (ties by question id), where K is
   the consensus flag's count (1,207 if the gate holds), so both flags send the same number of questions to review.
   *Negative*: every question with r < 0.
4. **Threshold-free comparison.** AUC (Mann-Whitney, ties count one half) of Redux miskeys against Redux-OK questions,
   for the score -r and for the consensus panel's margin (votes for its most-picked non-key option minus votes for
   the key, -10 to +10).
5. **Expert labels.** MMLU-Redux 2.0 joined to the HELM universe as in audit 80. Precision = among flagged questions
   Redux judged (wrong key, OK or another error label), the share with an error label.

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: all eight fixtures match and audit 80 is reproduced (gate above) |
| P2 | Negative discrimination finds miskeys: the share of Redux miskeys with r < 0 is at least 5 times the share of Redux-OK questions with r < 0 |
| P3 | HEADLINE: at equal budget K, the discrimination flag is more precise than the consensus flag |
| P4 | Without a threshold, -r separates Redux miskeys from Redux-OK questions better than the consensus margin (higher AUC) |
| P5 | Questions both flags select (consensus and budget) are more precise than either flag alone |
| P6 | P3 also holds with virology left out |

Reasoning: a miskeyed question should show the gradient across the whole ability range (strong models avoid the
key, weak ones hit it by chance), while a question the strongest models share a misconception about can still draw
a top-10 consensus. Land and Bikel report that an ability-based signal works on other benchmarks. Against that, weak
models answer near chance, which adds noise to r, and audit 80's flag already reaches 75.5% recall.

## What a result would mean

If P3 and P4 hold, the classical test-theory statistic, which needs no choice of panel size or vote threshold, is the
better default for ranking MMLU questions for expert review, and `discrimination_candidates.json` is that ranked list.
If they fail, the strongest models' agreement carries most of the signal and the weaker models mostly add noise. P5
tells whether the two signals catch different errors. Exploratory, not predicted: precision of both rankings at fixed
budgets from 100 to 2,000, AUC on any error label and without virology, precision of each flag's questions the other
misses, and counts by subject.

## Validity gates

Eight hand-traced fixtures (`cases82.py`, traced in `test_disc82.py`: audit 77's panel/flag fixture and audit 80's
run selection, universe, answer mapping and Redux join fixtures, copied; new: the item-rest correlation with its
conventions and rank flags, the margin and AUC, and the verdicts) must match before any data is read. The Redux join
must place at least 4,000 rows or the job aborts. The unit tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads HELM's MMLU release files and MMLU-Redux 2.0
```

## Files

- `disc82.py`: audit 80's HELM, Redux, panel and flag functions (copied from audit 81), the item-rest correlation,
  rank flags, margin, AUC and verdicts
- `cases82.py`: the frozen rule, gate, threshold, data sources and the eight fixtures
- `job.py`: downloads, the consensus flag, r for every question; writes `results.json` and
  `discrimination_candidates.json`
- `test_disc82.py`: unit tests; `requirements.txt`: a parquet reader only

## Licence

Code is Apache-2.0. This write-up and any results are CC BY 4.0. Upstream: HELM (Stanford CRFM) is Apache-2.0 and its
published run outputs keep their own terms; MMLU is MIT; MMLU-Redux 2.0 is CC BY 4.0. Only ids, letters, counts,
correlations and 16-hex sha256 prefixes of normalised question text are published, never question, option or model
text. Authored by AI agents working in MV2's name (Munim, Inc.).
