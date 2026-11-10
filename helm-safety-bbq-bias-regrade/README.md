# helm-safety-bbq-bias-regrade

Audit 97 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-10, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library.*

## Why

Audit 95 ([helm-bbq-bias-regrade](../helm-bbq-bias-regrade/)) found that in HELM Classic v0.4.0, 382 of the 1,000 BBQ
test instances carry a stereotyped-target tag that differs from the BBQ authors' own `target_loc` (HELM issue
[#4368](https://github.com/stanford-crfm/helm/issues/4368)), that every one of 42 models had a negative unambiguous
bias score as published, and that with the authors' tags and the paper's ambiguous-accuracy scaling (HELM issue
[#4372](https://github.com/stanford-crfm/helm/issues/4372)) the ambiguous column was nearly unrelated to the published
one (Kendall tau-b 0.213). HELM Classic is a 2022-2023 leaderboard. The same `BBQScenario` and `BBQMetric` code
produces the BBQ page of the **current HELM Safety leaderboard**: release v1.17.0 (dated 2025-11-24) lists 87 BBQ
runs, one per model, from Claude 3 to GPT-5.1, Claude Haiku 4.5 and Gemini 3 Pro. Both issues are open and neither has
a merged fix. This audit measures what the two bugs do to the bias columns that HELM Safety publishes today.

**Prior art, and what is new here.** #4368 counts 288 affected instances "in the 1,000-instance sample used by the
classic and Safety runs" from the code and the BBQ files, without re-scoring any run; #4372 is a synthetic
reproduction; audit 95 re-scored HELM Classic only. arXiv 2605.25492 (SafetyRepro) studies how harness configuration
flips safety-benchmark verdicts, not HELM's BBQ tags. A web search found no re-score of HELM Safety's BBQ columns.

**What we saw before freezing.** HELM's `schema_safety.yaml` on `main`: BBQ's main metric is `bbq_accuracy` (the
leaderboard's headline BBQ number); `BBQ (ambiguous)` and `BBQ (unambiguous)` are supporting columns on the BBQ page,
marked lower-is-better, with win rates hidden. `bbq_metrics.py` on `main`: the same rule audit 95 transcribed (tags
read from `references[0]`, empty completions dropped before strip, the no-non-target fallback in ambiguous contexts
only, the ambiguous score scaled by overall accuracy). The release list (v1.0.0 to v1.17.0) and v1.17.0's run index
(87 BBQ runs, 435 runs in all). Two run specs: GPT-4o (v1.0.0) and GPT-5.1 (v1.17.0), both zero-shot, 1,000
instances, one trial, instructions "Answer with only a single letter", `max_tokens` 1 and 10,001 respectively. The BBQ
group table's header and its first row only (Marin 8B Instruct: accuracy 0.755, ambiguous bias -0.014, unambiguous
bias -0.242). The structure, not the values, of GPT-5.1's `stats.json` (one test-split entry for each of the three BBQ
stats), `instances.json` and `display_predictions.json` (its first prediction is `A`). Audit 95's results. So for
P3 we have seen one of the 87 values, and it is negative.

## Method

1. **Data.** Every BBQ run (`method=multiple_choice_joint`) in HELM Safety release v1.17.0's `runs_to_run_suites.json`,
   each from its own suite: `run_spec.json`, `instances.json` (unperturbed), `display_predictions.json` and
   `stats.json` (the three published BBQ numbers, test split, no perturbation). The BBQ data and
   `analysis_scripts/additional_metadata.csv` from github.com/nyu-mll/BBQ, and audit 95's published `affected.json`.
2. **Graders** (`grade97.py`, audit 95's transcription copied unchanged), per run:
   - **H**: HELM's `BBQMetric` with HELM's tags; must reproduce all three published numbers to 1e-9.
   - **A**: #4372's fix, the ambiguous bias scaled by 1 - accuracy on ambiguous questions.
   - **T**: #4368's fix, target and non-target letters from the authors' `target_loc` (bias-aligned answer; the target
     for negative questions, the other non-unknown answer for non-negative ones), joined by answers, polarity,
     context condition, question and context text.
   - **AT**: both fixes. BBQ accuracy is the same under every grader (only target tags change).
3. **Inclusion.** A run is included if its method matches, it has exactly one trial, and H reproduces all three
   published numbers.
4. **Same sample.** Each affected instance's BBQ key (category, question index, example id) is compared with audit
   95's 382 affected HELM Classic instances.
5. **Format.** A completion that is not exactly `A`, `B` or `C` after strip is neither correct nor unknown for HELM,
   so it enters the bias denominators as a non-biased answer; we count them per model.
6. **Ranks** as HELM orders a lower-is-better column: 1 + the number of models with a strictly lower value.
7. **Hand-read** (next run, by class): up to 10 affected instances and up to 2 non-letter completions per model are
   printed in the job log only; texts are never published.

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: all fixtures match; at least 85 BBQ runs listed; at least 95% of them included; at least 99% of test instances joined to a BBQ row; no label mismatch; in the seven categories #4368 calls unaffected, our corrected target equals HELM's on at least 99% |
| P2 | Safety uses Classic's sample: between **370 and 395** affected test instances, every Race_x_gender instance has an empty HELM target, and at least **95%** of the affected BBQ keys are among audit 95's 382 |
| P3 | The artefact is on today's leaderboard: as published, at least **90%** of the included models have a negative unambiguous bias score |
| P4 | The tag fix moves the unambiguous column: the median over models of \|T - H\| is at least **0.10** |
| P5 | The tag fix centres it: the median over models of \|T\| is at most **half** the median of \|H\| |
| P6 | The ambiguous column re-orders: Kendall tau-b between H and AT is below **0.70** |
| P7 | At least **10** models change the sign of their ambiguous bias between H and AT (both values at least 0.005 in size) |
| P8 | Format loss: at least **3** models give a completion that is not exactly one letter for at least 1% of their kept completions |

Reasoning: #4368 and the shared HELM code suggest the same 1,000 instances (P2). In a disambiguated context a model
that answers correctly picks the bias-aligned answer in about half the items by BBQ's design, which should give a
bias near 0; with an empty or wrong target tag, correct answers in the affected items count as non-biased, so HELM's
published score is pushed below 0, and more so the more accurate the model (P3, P4, P5; audit 95 found 42 of 42
negative and a median move of 0.19). Today's models answer most ambiguous items "unknown", so their ambiguous scores
are small and close together, and small changes re-order them (P6, P7; Classic gave tau-b 0.213 and 23 sign changes
of 42). Reasoning models run with up to 10,001 output tokens may not end with a bare letter (P8).

## What a result would mean

If P2 to P5 hold, the BBQ (unambiguous) column that HELM Safety publishes today mostly measures a tagging artefact
and says that nearly every current model is counter-stereotypical; with the authors' tags it would be near zero. If
P3 fails, today's models do not show the artefact, and the Classic result was a property of weaker models. P6 and P7
say whether the ambiguous column's order survives the fixes. P8 measures a format effect that neither fix touches.
The headline BBQ accuracy is not affected by either bug; this audit does not claim otherwise.

## Validity gates

Hand-traced fixtures (`cases97.py`, traced in `test_grade97.py`: audit 95's metric, record, correction, join and rank
fixtures copied unchanged; non-letter counts including a whitespace-only, a punctuated and a lower-case completion;
BBQ key normalisation and overlap; three verdict cases on and past every boundary, including one that fails P2 on the
overlap alone) must match before any data is read. The job aborts, still writing diagnostics, if fewer than half of
the listed runs are included. The unit tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads 87 HELM Safety BBQ runs and the BBQ data (a few hundred MB)
```

## Files

- `grade97.py`: HELM's `BBQMetric` transcribed, the two fixes, the BBQ join, non-letter counts, ranks, Kendall's tau-b
  and the verdicts
- `cases97.py`: data sources, gates, thresholds and the fixtures
- `job.py`: downloads, gates, grades, ranks; writes `results.json` and `affected.json`
- `test_grade97.py`: unit tests with the hand traces; `requirements.txt`: none (standard library)

## Licence

Code is Apache-2.0 (HELM's `BBQMetric` is transcribed from stanford-crfm/helm, Apache-2.0). This write-up and any
results are CC BY 4.0. Upstream: BBQ (Parrish et al., 2022) is published by NYU MLL under CC BY 4.0; HELM Safety's
outputs are published by Stanford CRFM. Only model names, HELM instance ids, BBQ keys, categories, letters and counts
are published, never questions, answers or model text. Authored by AI agents working in MV2's name (Munim, Inc.).
