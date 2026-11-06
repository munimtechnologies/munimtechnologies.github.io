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

## Results

*Added 2026-11-06 from the sealed job `mcq-mmlu-helm-discrimination-miskeys-v1` (run 2026-11-06, 471 s; the unit tests
passed first). Everything above this heading is unchanged. Full numbers: [`results.json`](results.json); the 1,207
questions with the most negative r: [`discrimination_candidates.json`](discrimination_candidates.json).*

**3 of 6 predictions held, and the headline failed.** Across HELM's 78 models, negative item discrimination does pick
out wrong keys (P2), but it is **slightly less precise than the top-10 consensus flag at the same budget (121 of 504
judged flags error-labelled, 24.0%, against 130 of 484, 26.9%) and slightly worse without a threshold (AUC 0.898
against 0.912)**. The questions both flags select are the most precise set (102 of 301, 33.9%). The weaker models add
more noise than signal to a miskey flag, which is what audit 83 measures directly.

| # | Verdict | Counts |
| --- | --- | --- |
| P1 | HELD | fixtures 8/8; audit 80 reproduced (13,984 questions, 78 of 79 models, same panel, 1,207 flags, precision 130/484) |
| P2 | HELD | r < 0 on 78 of 106 Redux miskeys (73.6%) vs 389 of 5,285 Redux-OK questions (7.4%), 10.0 times (needed 5) |
| P3 | FAILED | budget flag 121/504 = 24.0% vs consensus flag 130/484 = 26.9% |
| P4 | FAILED | AUC (miskeys vs OK) 0.898 for -r vs 0.912 for the consensus margin |
| P5 | HELD | both flags: 102/301 = 33.9%, above 24.0% and 26.9% |
| P6 | FAILED | without virology: budget 85/464 = 18.3% vs consensus 91/442 = 20.6% |

**r.** 13,330 questions have a defined r, 566 were answered with the key by every included model (r = +1) and 88 by
none (r = -1); no question had too few models. The budget cut (K = 1,207) falls at r = -0.0029, so the budget flag is
almost the same set as "r below zero" (1,224 questions, 122 of 511 judged error-labelled, 23.9%).

**Flags by MMLU-Redux group** (count flagged):

| Redux group | Questions | Consensus | Budget | r < 0 | Both | No model picks the key |
| --- | --- | --- | --- | --- | --- | --- |
| Wrong key (miskey) | 106 | 80 | 77 | 78 | 71 | 23 |
| OK | 5,285 | 354 | 383 | 389 | 199 | 10 |
| Other error label | 230 | 50 | 44 | 44 | 31 | 4 |
| Unsure or conflicting | 32 | 8 | 6 | 6 | 5 | 0 |
| Not in Redux's sample | 8,331 | 715 | 697 | 707 | 459 | 51 |
| All | 13,984 | 1,207 | 1,207 | 1,224 | 765 | 88 |

The two flags share 765 of their 1,207 questions. What each adds alone is weak: the consensus flag's 442 questions
outside the budget flag carry an error label 28 of 183 judged times (15.3%), and the budget flag's 442 outside the
consensus flag 19 of 203 (9.4%), against a base rate of 336 of 5,621 judged questions (6.0%).

**AUC** (exploratory beyond P4): miskeys vs OK 0.898 (-r) vs 0.912 (margin); any error label vs OK 0.7335 vs 0.7339,
a tie; miskeys vs OK without virology 0.874 vs 0.890.

**Precision at fixed budgets** (exploratory). The r ranking has ties only at r = -1, and all 88 of those fit in the
smallest budget, so its curve does not depend on a tie-break:

| Budget | Discrimination: error-labelled / judged | Miskeys |
| --- | --- | --- |
| 100 | 27 / 43 (62.8%) | 23 |
| 200 | 42 / 82 (51.2%) | 38 |
| 300 | 52 / 120 (43.3%) | 44 |
| 500 | 70 / 197 (35.5%) | 56 |
| 750 | 93 / 297 (31.3%) | 66 |
| 1,000 | 108 / 413 (26.2%) | 73 |
| 1,207 | 121 / 504 (24.0%) | 77 |
| 1,500 | 135 / 637 (21.2%) | 80 |
| 2,000 | 165 / 862 (19.1%) | 87 |

`results.json` also holds the consensus margin's curve, but the margin is an integer from -10 to +10 with large ties,
and the job broke them by question id, which runs alphabetically by subject (virology comes late). Those numbers
depend on that tie-break and should not be compared with the table above. The tie-fair figure at K = 1,207, with
ties at the cut shared evenly, is 27.6% (audit 83, panel S1).

**By subject** (exploratory; all 57 in `by_subject_exploratory`): virology budget 36 of 40 judged error-labelled vs
consensus 39 of 42; college chemistry 14 of 23 vs 13 of 22; logical fallacies 1 of 4 vs 6 of 7; formal logic 4 of 17
vs 2 of 11. Professional law takes 255 of the 1,207 budget flags (294 consensus flags), 238 of them outside Redux's
sample, with 4 of 17 judged ones error-labelled.

**Post-hoc readings (not predicted; treat as leads).**

1. *No model picks the key.* 88 questions were answered with the published key by none of the 78 models. Redux
   judged 37 of them and gave 27 an error label (73.0%; 95% Wilson interval about 57% to 85%), 23 of them wrong
   keys, against the 6.0% base rate and against 67 of 132 (50.8%) for audit 80's strictest consensus rule (all 10
   top models on one non-key option). Virology holds 21 of the 88 (all 12 judged ones error-labelled); without it,
   15 of 25 (60.0%). Professional law holds 16, 15 of them outside Redux's sample. These are the first 88 rows of
   `discrimination_candidates.json` (r = -1). Reviewing items no model gets right is an established cleaning step
   (for example the "platinum" benchmark revisions of Vendrow et al., arXiv 2502.03461); this is a count of how
   often it finds MMLU-Redux's errors, not a new method.
2. *Weak models add noise to the bulk.* Beyond the top of the ranking, budget-only flags are barely above the base
   rate (9.4% vs 6.0%), and audit 83 finds the same thing from the other side: a panel of weaker models flags more
   questions and is less precise per review.

**What this means.** For ranking MMLU questions for expert review, the agreement of the strongest models is a better
default than classical item discrimination over every model HELM ran, at the same review budget and without a
threshold. Discrimination is not useless: its very top (questions no model answers with the key) is the most precise
short list seen in this series, and requiring both signals gives about the same precision as requiring two
independent harnesses (33.9% here, 33.6% in audit 81). `discrimination_candidates.json` lists the 1,207 questions with
the most negative r, 697 outside Redux's sample. They are model-flagged and not checked by experts.

**Limits.** Redux labels are expert judgments, not verified facts, and cover 100 questions per subject. HELM's 78
models are mostly from 2023-2024 and many share families, so r is not a sample of independent test-takers. The
item-rest correlation is the simplest discrimination statistic; an item-response model (as in Land and Bikel) might
do better and was not tested. The differences in P3, P4 and P6 are 2 to 3 points of precision and 0.014 to 0.016 of
AUC, with no significance test pre-registered; the direction, not the size, is the result.
