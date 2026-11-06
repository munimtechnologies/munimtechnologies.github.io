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

## Results

*Added 2026-11-06 from the sealed job `mcq-mmlu-helm-panel-strength-v1` (run 2026-11-06, 286 s; the unit tests passed
first). Everything above this heading is unchanged. Full numbers, including every panel's model list:
[`results.json`](results.json).*

**5 of 6 predictions held.** Weaker panels find wrong keys less precisely, but the signal fades slowly. The panel
ranked 61-70 (mean MMLU accuracy 0.641, against 0.855 for the top 10) flags twice as many questions, still catches 73
of the 106 expert-confirmed miskeys (the top 10 catch 80), and at the same review budget is **18.8% precise against
27.6%**, about 3 times the 6.0% base rate. The headline AUC order held, but only weakly at its first step. **P6
failed**: adding the next 10 models to the top 10 did not help.

| # | Verdict | Counts |
| --- | --- | --- |
| P1 | HELD | fixtures 10/10; audit 80 reproduced by S1 (13,984 questions, 78 of 79 models, 1,207 flags, precision 130/484) |
| P2 | HELD | S7 flags 2,405 questions vs S1's 1,207 |
| P3 | HELD (weak first step) | AUC S1 0.912 > S4 0.903 > S7 0.871; S1 vs S4 differ by under one AUC point |
| P4 | HELD | equal-budget precision S1 27.6% > S4 22.8% > S7 18.8% |
| P5 | HELD | S7 equal-budget precision 18.8% = 3.1 times the base rate (336 of 5,621 judged, 6.0%; needed 2 times) |
| P6 | FAILED | ranks 1-20 at the same budget: 26.3% vs S1 27.6% |

**Every panel** (equal budget K = 1,207, ties at the cut shared evenly, so budget counts are expected values):

| Panel | Ranks | Mean accuracy | Flags (6 of 10 rule) | Judged flags error-labelled | Miskeys flagged (of 106) | AUC miskey vs OK | Equal-budget precision | Expected miskeys at K |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S1 | 1-10 | 0.855 | 1,207 | 130/484 (26.9%) | 80 | 0.912 | 27.6% | 85.3 |
| S2 | 11-20 | 0.815 | 1,343 | 125/511 (24.5%) | 75 | 0.908 | 25.9% | 77.8 |
| S3 | 21-30 | 0.786 | 1,627 | 122/653 (18.7%) | 73 | 0.901 | 23.3% | 71.3 |
| S4 | 31-40 | 0.765 | 1,721 | 126/681 (18.5%) | 74 | 0.903 | 22.8% | 73.9 |
| S5 | 41-50 | 0.726 | 1,888 | 120/734 (16.3%) | 65 | 0.886 | 21.8% | 61.6 |
| S6 | 51-60 | 0.685 | 1,875 | 113/669 (16.9%) | 66 | 0.904 | 21.9% | 62.8 |
| S7 | 61-70 | 0.641 | 2,405 | 128/920 (13.9%) | 73 | 0.871 | 18.8% | 55.2 |
| Top 20 | 1-20 | 0.835 | 1,081 (12 of 20 rule) | 111/412 (26.9%) | 72 | 0.912 | 26.3% | 82.3 |

Read down the columns: the number of miskeys each panel's rule catches barely moves (65 to 80), while the number of
flags doubles, so the frozen rule's precision halves (26.9% to 13.9%). Ranking by margin at a fixed budget softens the
fall (27.6% to 18.8%): the weakest panel keeps about two thirds of the top panel's precision per question reviewed.
The AUC hardly changes from S1 to S6 (0.886 to 0.912, not in strict order) and drops at S7.

**Sliding windows** of 10 consecutive ranks (exploratory):

| Ranks | Mean accuracy | Flags | AUC | Equal-budget precision |
| --- | --- | --- | --- | --- |
| 1-10 | 0.8550 | 1,207 | 0.912 | 27.6% |
| 5-14 | 0.8363 | 1,319 | 0.913 | 26.4% |
| 9-18 | 0.8210 | 1,394 | 0.908 | 25.1% |
| 13-22 | 0.8105 | 1,376 | 0.905 | 25.1% |
| 17-26 | 0.7990 | 1,351 | 0.902 | 24.7% |
| 21-30 | 0.7864 | 1,627 | 0.901 | 23.3% |
| 25-34 | 0.7770 | 1,791 | 0.896 | 22.2% |
| 29-38 | 0.7693 | 1,777 | 0.893 | 23.3% |
| 33-42 | 0.7580 | 1,701 | 0.901 | 23.3% |
| 37-46 | 0.7438 | 1,778 | 0.901 | 22.5% |
| 41-50 | 0.7263 | 1,888 | 0.886 | 21.8% |
| 45-54 | 0.7086 | 2,022 | 0.891 | 20.8% |
| 49-58 | 0.6913 | 2,117 | 0.896 | 21.1% |
| 53-62 | 0.6782 | 2,032 | 0.896 | 20.1% |
| 57-66 | 0.6642 | 2,158 | 0.885 | 19.5% |
| 61-70 | 0.6414 | 2,405 | 0.871 | 18.8% |
| 65-74 | 0.6000 | 2,297 | 0.868 | 19.5% |
| 69-78 | 0.5235 | 2,174 | 0.844 | 17.1% |

Equal-budget precision falls with mean accuracy, with small reversals. Even the weakest ten models HELM evaluated
(mean accuracy 0.52) reach 17.1%, 2.9 times the base rate.

**Overlap with the top 10** (exploratory):

| Panel | Flags | Shared with S1 | S1's 80 miskeys also flagged | S1's miskeys missed | Miskeys only this panel flags |
| --- | --- | --- | --- | --- | --- |
| S2 | 1,343 | 902 | 72 | 8 | 3 |
| S3 | 1,627 | 886 | 70 | 10 | 3 |
| S4 | 1,721 | 854 | 67 | 13 | 7 |
| S5 | 1,888 | 822 | 58 | 22 | 7 |
| S6 | 1,875 | 689 | 58 | 22 | 8 |
| S7 | 2,405 | 698 | 62 | 18 | 11 |

S7 shares only 698 of its 2,405 flags with S1, yet flags 62 of S1's 80 miskeys and 11 that S1 misses: weaker panels
find mostly the same wrong keys, buried among more of their own mistakes.

**AUC on any error label vs OK** (exploratory) is flat: 0.734, 0.743, 0.727, 0.734, 0.723, 0.730 and 0.702 for S1 to
S7. Model panels separate wrong keys from sound questions well (AUC 0.87-0.91), but Redux's other error types
(unclear questions or options, several or no correct answers) much less well, and panel strength barely changes that.

**What this means.** For a team that cannot afford a frontier panel, model consensus still works as a review queue: a
panel in the 0.6-0.7 accuracy range (S7 holds five 6-8B open models such as Llama 3 8B, Gemma 7B and Qwen1.5 7B,
alongside GPT-3.5 Turbo, Command R and others) finds most of the same wrong keys, at roughly two thirds
of the precision per question reviewed, provided it ranks by margin at a fixed budget rather than using a fixed vote
threshold (whose flag count grows as the panel weakens). Adding weaker models to a strong panel did not help here,
unlike the ensemble-size gains Nahum et al. report on other datasets; strength, not size, carried the signal. Audit 82
points the same way from another angle: item discrimination over all 78 models (24.0% at the same budget) sits between
S2 and S3.

**Limits.** One benchmark (MMLU), one harness (HELM) and one set of expert labels (MMLU-Redux 2.0, judgments on 100
questions per subject). Strata differ in more than accuracy: the top ranks hold larger and more recent models,
and families repeat within a stratum. The AUC differences between S1 and S4 and among S2 to S6 are under one
point with no significance test pre-registered. Panels flag questions; they do not prove a key wrong.
