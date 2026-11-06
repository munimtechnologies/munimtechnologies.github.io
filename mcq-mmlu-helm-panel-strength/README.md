# mcq-mmlu-helm-panel-strength

Audit 83 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-06, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library plus a parquet
reader.*

## Why

Audits 77-82 flag a multiple-choice question as possibly miskeyed when at least 6 of the 10 most accurate models pick
the same option other than the key. On MMLU with Stanford CRFM's HELM outputs, 26.9% of the flags that MMLU-Redux
2.0's experts judged carry an expert error label ([audit 80](../mcq-mmlu-helm-consensus-miskeys/)). Anyone who wants
to audit a new benchmark this way has to choose a panel, and the strongest models are often the most expensive. So:
**how strong does the panel have to be?** Does a panel of mid-ranked models find wrong keys almost as well as the top
10, or does the signal disappear as the panel gets weaker?

This audit keeps everything fixed except panel strength. HELM's 78 included models are ranked by MMLU accuracy and cut
into seven disjoint panels of 10: S1 = ranks 1-10 (audit 80's panel), S2 = ranks 11-20, ..., S7 = ranks 61-70. From
audit 80's published accuracies, panel means run from about 0.85 (S1) to about 0.65 (S7); the job records the exact
values. Each panel uses the same rule, and all are scored against the same expert labels.

**Prior art.** Nahum et al. ("Are LLMs Better than Reported? Detecting Label Errors and Mitigating Their Effect on
Model Performance", arXiv 2410.18889, EMNLP 2025) vary the *size* of an LLM ensemble on four TRUE datasets and
SummEval, and report that error detection improves as the ensemble grows; they do not compare equal-size panels of
different strength. Land and Bikel (arXiv 2605.30504) weight 114 models by ability in an item-response model on seven
benchmarks other than MMLU. Song and Park ("Auditing MCQA Benchmarks through Probability Landscapes", arXiv
2608.30372, EMNLP 2026) flag items from one model's probability landscape and check them against MMLU-Redux. Audit 82
(pending) tests item discrimination across all 78 models. We found no controlled comparison of disjoint, equal-size
model panels of different accuracy as miskey detectors, scored against expert labels.

## Method

1. **HELM, the universe and the labels (audit 80, rebuilt).** HELM MMLU release v1.13.0; question universe, inclusion
   rules (78 of 79 models) and the MMLU-Redux 2.0 join exactly as in audit 80. Gate: the universe (13,984), the 78
   models, S1 = audit 80's panel, its flag counts (1,207) and precision (130 of 484) must be reproduced.
2. **Strata.** Included models ranked by accuracy (ties by name); S1..S7 = ranks 1-10 ... 61-70. Ranks 71-78 are
   left out of the strata (used only in the exploratory sliding windows).
3. **Per panel.** (a) Audit 77's flag (>= 6 of 10 on one non-key option, more than on the key): count, precision
   (share of flagged Redux-judged questions with an error label) and miskeys caught. (b) The margin (votes for the
   most-picked non-key option minus votes for the key, -10 to +10): AUC of Redux miskeys against Redux-OK questions
   (Mann-Whitney, ties count one half). (c) **Equal budget**: each panel sends its K highest-margin questions to
   review, K = S1's flag count (1,207 if the gate holds). Margins are integers with many ties, so ties at the cut are
   shared evenly: the expected counts under a random tie-break, computed exactly.
4. **A 20-model panel.** Ranks 1-20 as one panel, scored by its margin (-20 to +20) at the same budget K (its own
   frozen-rule count at >= 12 of 20 is exploratory).
5. **Base rate.** Error-labelled share of all Redux-judged questions in the universe (wrong key, OK or another error
   label; unsure and conflicting labels left out, as in audits 77-82).

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: all ten fixtures match and audit 80 is reproduced by S1 (gate above) |
| P2 | Weaker panels flag more: S7's frozen rule flags more questions than S1's |
| P3 | HEADLINE: the margin's AUC (Redux miskeys vs OK) falls with panel strength: S1 > S4 > S7 |
| P4 | Equal-budget precision falls with panel strength: S1 > S4 > S7 |
| P5 | The weakest panel still carries signal: S7's equal-budget precision is at least 2 times the base rate |
| P6 | Adding the next 10 models helps: ranks 1-20 as one panel are more precise than S1 at the same budget |

Reasoning: a weaker model is wrong more often, and its wrong answers are more likely to be its own mistakes than a
response to a bad key, so weaker panels should flag more questions (P2) and separate miskeys from sound questions less
well (P3, P4). But a truly wrong key misleads every panel, so even S7 should beat the base rate (P5). Nahum et al.
find that larger ensembles detect errors better, so a 20-model panel should beat 10 (P6), although the added models
are weaker. P3 and P4 need strict order at three points, so noise alone can break them.

## What a result would mean

If P3 and P4 hold and P5 holds, model consensus degrades gracefully: a cheaper panel finds fewer wrong keys per review
but still finds them, and the curve says how much each accuracy point buys. If P5 fails, only frontier-level panels
are worth using. If P6 holds, it is better to add weaker models to the top 10 than to rely on the top 10 alone.
Exploratory, not predicted: every stratum's numbers, sliding windows of 10 consecutive ranks (starting at ranks 1, 5,
..., 69) against their mean accuracy, how many of S1's flags each weaker panel shares and which miskeys only weaker
panels catch, and AUC on any error label.

## Validity gates

Ten hand-traced fixtures (`cases83.py`, traced in `test_panel83.py`: audit 77's panel/flag fixture, audit 80's run
selection, universe, answer mapping and Redux join fixtures and audit 82's margin and AUC fixtures, copied; new: the
strata, the budget counts with shared ties, one panel's statistics and the verdicts) must match before any data is
read. The Redux join must place at least 4,000 rows and at least 70 models must be included, or the job aborts. The
unit tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads HELM's MMLU release files and MMLU-Redux 2.0
```

## Files

- `panel83.py`: audit 80's HELM, Redux, panel and flag functions and audit 82's margin and AUC (copied from audit
  82), the strata, budget counts, per-panel statistics and verdicts
- `cases83.py`: the frozen rule, strata, gate, threshold, data sources and the ten fixtures
- `job.py`: downloads, every panel's flags and margins; writes `results.json`
- `test_panel83.py`: unit tests; `requirements.txt`: a parquet reader only

## Licence

Code is Apache-2.0. This write-up and any results are CC BY 4.0. Upstream: HELM (Stanford CRFM) is Apache-2.0 and its
published run outputs keep their own terms; MMLU is MIT; MMLU-Redux 2.0 is CC BY 4.0. Only model names and accuracies
(public HELM leaderboard facts), counts, AUCs and hashes are published, never question, option or model text.
Authored by AI agents working in MV2's name (Munim, Inc.).
