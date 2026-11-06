# mcq-mmlu-pro-panel-strength

Audit 84 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-06, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library plus a parquet
reader.*

## Why

[Audit 83](../mcq-mmlu-helm-panel-strength/) cut Stanford CRFM's 78 HELM models into seven disjoint panels of 10 by
MMLU accuracy and scored each panel's consensus flag against MMLU-Redux 2.0's expert labels. Weaker panels flagged
more questions but found mostly the same wrong keys: at an equal review budget, precision fell from 27.6% (top 10) to
18.8% (ranks 61-70), still three times the base rate, and adding ranks 11-20 to the top 10 did not help.
[Audit 82](../mcq-mmlu-helm-discrimination-miskeys/) added a post-hoc lead: on the 88 MMLU questions that none of the
78 models answers with the key, 27 of 37 expert-judged ones carry an error label (73%).

Both results come from one harness (HELM) and a 4-option benchmark. This audit repeats the design, unchanged where
possible, on a second harness and a 10-option benchmark: TIGER-AI-Lab's 45 published MMLU-Pro archives (5-shot
chain of thought), whose ranks 1-10 are [audit 77](../mcq-mmlu-pro-model-consensus-miskeys/)'s panel. It also tests
audit 82's lead before looking: are MMLU-Pro questions that no archive answers with the key more often wrong than
those the top 10 unanimously reject?

**Prior art.** As in audit 83: Nahum et al. ("Are LLMs Better than Reported?", arXiv 2410.18889, EMNLP 2025) report
that error detection improves with LLM-ensemble size on other datasets; Land and Bikel (arXiv 2605.30504) weight 114
models by ability in an item-response model on seven benchmarks other than MMLU and MMLU-Pro. Kamoi et al.
("Evaluating LLMs at Detecting Errors in LLM Responses", arXiv 2404.03602, COLM 2024) compare 12 LLMs as detectors of
errors in model responses, a different task. Vendrow et al. (arXiv 2502.03461) review benchmark items that models get
wrong. We found no comparison of disjoint, equal-size panels of different accuracy as miskey detectors on MMLU-Pro,
and no count of how often MMLU-Pro questions that no published model answers with the key carry an expert error
label.

## Method

1. **Data and joins (audits 75-79, rebuilt).** MMLU-Pro test (12,032 questions), MMLU test and MMLU-Redux 2.0 via the
   Hugging Face parquet API; MMLU-Redux joined to MMLU-Pro's MMLU-derived questions by audit 75's rule (5,690 Redux
   rows join MMLU, 2,758 land on one MMLU-Pro question, 55 of them miskeys); TIGER-AI-Lab's 48 archives, of which
   about 45 pass the join (audits 66 and 77).
2. **Strata.** Included archives ranked by accuracy (ties by name); S1..S4 = ranks 1-10, 11-20, 21-30, 31-40. From
   audit 79's published accuracies the panel means are about 0.78, 0.60, 0.44 and 0.33 (chance is about 0.10); the
   job records the exact values. Ranks 41-45 are used only in the exploratory sliding windows.
3. **Per panel.** (a) Audit 77's flag (>= 6 of 10 on one non-key option, more than on the key): count, precision
   (share of flagged Redux-judged questions with an error label) and miskeys caught. (b) The margin (votes for the
   most-picked non-key option minus votes for the key, -10 to +10): AUC of Redux miskeys against Redux-OK questions.
   (c) **Equal budget**: each panel sends its K highest-margin questions to review, K = S1's flag count (1,210 if the
   gate holds), ties at the cut shared evenly (exact expected counts).
4. **A 20-archive panel.** Ranks 1-20 as one panel, scored by its margin (-20 to +20) at the same budget K.
5. **No-key flag.** A question is flagged when at least 2 included archives cover it and none of them picks its key
   (a missing or unreadable answer counts as not picking it). Comparator: S1's flag at 10 of 10.
6. **Base rate.** Error-labelled share of all Redux-judged questions (wrong key, OK or another error label; unsure
   and conflicting labels left out, as in audits 77-83).

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: all eight fixtures match; the MMLU-Pro parse, the Redux join and audit 77's panel, flag counts (1,210) and precision (65 of 359) are reproduced by S1; at least 40 archives are included |
| P2 | Weaker panels flag more: S4's frozen rule flags more questions than S1's |
| P3 | HEADLINE: equal-budget precision falls with panel strength: S1 > S2 > S4 |
| P4 | The margin's AUC (Redux miskeys vs OK) is higher for S1 than for S4 |
| P5 | The weakest panel still carries signal: S4's equal-budget precision is at least 2 times the base rate |
| P6 | Adding the next 10 archives does not help: ranks 1-20 as one panel are not more precise than S1 at the same budget |
| P7 | The no-key flag is more precise than S1's 10-of-10 flag, with at least 10 Redux-judged no-key questions (fewer counts as FAILED: undecidable) |

Reasoning: P2-P6 predict that audit 83 replicates. The setting differs: S4 answers about a third of the questions
correctly (audit 83's weakest stratum: about 0.64), though it sits about as far above chance (about 3.3 times chance
against 2.6 times), and with 10 options a weak panel's wrong answers can scatter over nine distractors, which works
against P2. TIGER's top ranks also hold repeated
archives of the same models (audit 79), which may make S1 less independent than HELM's top 10. P7 tests audit 82's
post-hoc lead on fresh data; with 45 archives and 10 options, few questions may qualify, so it may be undecidable.

## What a result would mean

If P3-P5 hold, the HELM result is not a quirk of one harness or of 4-option questions: weaker panels still find wrong
keys, at lower precision per question reviewed. If P2 fails while P3-P5 hold, a fixed vote threshold behaves
differently with 10 options, which is one more reason to rank by margin at a fixed budget. If P7 holds, "no published
model picks the key" is a cheap first filter that works on two benchmarks. Exploratory, not predicted: every
stratum's numbers and flags by source family (MMLU-derived, STEM website, TheoremQA, SciBench), sliding windows of 10
consecutive ranks (starting at ranks 1, 6, ..., 36), overlap with S1's flags and miskeys, AUC on any error label,
the share of all archives picking the key as a score, and the no-key flag by group and family.

## Validity gates

Eight hand-traced fixtures (`cases84.py`, traced in `test_panel84.py`: audit 77's panel/flag and Redux-join fixtures
and audit 83's margin, AUC, strata, budget and per-panel fixtures, copied; new: key counts with the no-key flag and
key-share score, and the verdicts) must match before any data is read. The MMLU-Pro parse must give 12,032 rows in
the four source families, the Redux join must reproduce audit 75, and at least 40 archives must be included, or the
job aborts. The unit tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads MMLU-Pro, MMLU, MMLU-Redux 2.0 and TIGER-AI-Lab's 48 archives
```

## Files

- `panel84.py`: audit 79's join, panel and flag functions and audit 83's margin, AUC, strata, budget and per-panel
  statistics (copied), key counts, the no-key flag, the key-share score and the verdicts
- `cases84.py`: the frozen rule, strata, gate, thresholds, data sources, archive list and the eight fixtures
- `job.py`: downloads, every panel's flags and margins, the no-key flag; writes `results.json` and
  `nokey_candidates.json`
- `test_panel84.py`: unit tests; `requirements.txt`: a parquet reader only

## Licence

Code is Apache-2.0. This write-up and any results are CC BY 4.0. Upstream: MMLU-Pro and MMLU are MIT; MMLU-Redux 2.0
is CC BY 4.0; TIGER-AI-Lab's published model outputs keep their own terms. Only question ids, letters, counts, AUCs
and public model names and accuracies are published, never question, option or model text. Authored by AI agents
working in MV2's name (Munim, Inc.).
