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

## Results

*Added 2026-11-10 after the sealed run (job `helm-safety-bbq-bias-regrade-v1`, 2026-11-10 05:10-05:15 UTC; unit tests
passed first; every fixture matched). Everything above this heading is unchanged. Graded by AI agents working in
MV2's name. Files: [results.json](results.json) (per model and per run: published, H, A, T and AT values, ranks,
non-letter counts, exclusions) and [affected.json](affected.json) (the 382 affected instances: ids, BBQ keys,
categories, HELM's and the corrected letters).*

**Verdict: 6 of 8 predictions held. P1 failed (80 of 87 runs included, 92.0%, below the 95% gate) and P7 failed (5
sign changes, not 10).**

| # | Measured | Verdict |
| --- | --- | --- |
| P1 | fixtures all match; 87 BBQ runs listed (all `multiple_choice_joint`); **80 of 87 included (92.0%)**; 999 of 1,000 test instances joined (1 has an NA `target_loc` in the authors' file); 0 label mismatches; unaffected categories agree on 330 of 330 | **FAILED** (inclusion only) |
| P2 | **382** affected test instances; all 262 Race_x_gender instances have an empty HELM target; 382 of 382 affected BBQ keys (100%) are audit 95's HELM Classic keys, and so are the 382 HELM instance ids | HELD |
| P3 | as published, **80 of 80** included models (100%) have a negative unambiguous bias score (from -0.346 to -0.119) | HELD |
| P4 | median over models of \|T - H\| on the unambiguous column = **0.202** | HELD |
| P5 | median \|T\| = **0.0101**, median \|H\| = 0.194 (ratio 0.052) | HELD |
| P6 | Kendall tau-b between the published ambiguous column (H) and AT = **0.257** | HELD |
| P7 | **5** models change the sign of their ambiguous bias between H and AT | **FAILED** |
| P8 | **5** models give a non-letter completion for at least 1% of kept completions | HELD |

### Why P1 failed: seven runs could not be re-scored

- **Six models' per-instance files are not where the release index points.** HELM Safety v1.17.0's
  `runs_to_run_suites.json` places all five runs of Gemini 2.0 Flash, Gemini 2.0 Flash-Lite (preview 02-05), Gemini 2.0
  Pro (exp 02-05), Mistral Small (2501), Qwen2.5 Instruct Turbo 72B and Qwen2.5 Instruct Turbo 7B in suite v1.1.0. The
  public bucket's v1.1.0 folder holds 30 runs for six other models (DeepSeek-R1, DeepSeek-R1 hide-reasoning, DeepSeek-V3,
  o1, o1-mini, o3-mini) and none for these six, so every download returned HTTP 404. *Checked by hand after the run, not
  pre-registered:* their BBQ folders are also absent from suites v1.0.0 and v1.2.0 to v1.6.0 (v1.7.0 to v1.17.0 were not
  searched), while the published BBQ table still shows values for them (for example Qwen2.5 72B: accuracy 0.954,
  unambiguous bias -0.206). Their published numbers cannot be checked against per-instance outputs.
- **DeepSeek-R1 was not reproduced, a limit of our code.** Its `display_predictions.json` holds the raw output with the
  reasoning block (`<think>...`), so all 1,000 completions are non-letters to our transcription, which does not strip
  reasoning; HELM's published numbers clearly come from the final answers. *Observed after the run:* the published
  DeepSeek-R1 BBQ numbers (accuracy 0.966, ambiguous 0.01545, unambiguous -0.19277) equal those of the separate
  DeepSeek-R1 (hide reasoning) run to every stored digit; we did not check why. Including DeepSeek-R1 would give 81 of
  87 (93.1%), still below the gate, so the frozen verdict stands either way. Neither gap affects the other 80 runs,
  where HELM's three published numbers were reproduced to 1e-9.

### The unambiguous column: an artefact on today's leaderboard

- As published, every one of the 80 models looks counter-stereotypical in disambiguated contexts, by a median of
  0.194. With the BBQ authors' tags the column centres on zero: median \|T\| 0.0101; **53 of 80 models become
  positive** and 43 change sign (exploratory). The order changes too: Kendall tau-b between H and T is 0.508, and the
  largest rank move is 73 places (OLMoE 1B-7B Instruct, 78th to 5th).
- The same 382 instances are affected as in HELM Classic, so the cause is the shared 1,000-instance sample and the
  shared tagging code, not anything specific to either leaderboard.
- **First place is a format effect.** DBRX Instruct is first (most counter-stereotypical) under both H and T. 133 of
  its 1,000 completions (13.3%) are not a letter at all (the two we read are a control character and an invalid byte),
  and HELM counts each as a non-biased answer.

### The ambiguous column: re-ordered by both fixes

- Kendall tau-b between the published ambiguous column and AT is **0.257**; the scaling fix alone gives 0.617 and the
  tag fix alone 0.518 (exploratory). Unlike HELM Classic, where the tag fix drove almost all of the change, both fixes
  matter here.
- The scaling fix moves several of the most accurate recent models a long way. HELM multiplies the ambiguous bias by 1 minus *overall*
  accuracy, so a model's mistakes on disambiguated questions inflate its ambiguous score. Claude 3.7 Sonnet goes from
  79th to 14th (0.079 to 0.0081), GPT-4.5 (preview) from 80th to 31st, and Claude Haiku 4.5 from 78th to 17th. The tag
  fix moves weaker models the other way: OLMo 2 7B Instruct goes from 4th to 80th and GPT-3.5 Turbo (0613) from 7th to
  72nd.
- **Why P7 failed.** As published, 71 of 80 ambiguous scores are already positive, and 76 are with both fixes, so only
  5 change sign (OLMo 2 7B, DeepSeek LLM 67B Chat, Marin 8B, GPT-3.5 Turbo 0613 and 1106). In HELM Classic 23 of 42
  did. Under the corrected tags, the remaining errors of today's models on ambiguous questions lean bias-aligned (76
  of 80 positive). The prediction assumed more negative published scores than the leaderboard holds.

### Format loss (P8)

Five models give a non-letter for at least 1% of their kept completions: DBRX Instruct 133 of 1,000; Marin 8B
Instruct 56 of 1,000; Qwen3-Next 80B A3B Thinking 49 of 996; Granite 4.0 Micro with Guardian and Granite 4.0 H Small
with Guardian 29 of 1,000 each. Neither fix touches these; under HELM's rule each one is a wrong answer and a
non-biased one.

### Hand-read (by class, read by AI agents; texts are not published)

- **Affected instances (10 printed, the first 10 by instance id):** all 10 have an empty HELM target (7 Race_x_gender,
  2 Race_ethnicity, 1 Race_x_SES). In all 10 the authors' tag picks a named person, never the "unknown" option. In 6
  of 10, HELM's non-target letter is the very answer the authors mark as bias-aligned.
- **Non-letter completions (30 printed, at most 2 per model):** 4 refusals from the two Guardian-wrapped Granite models;
  6 first words of a sentence cut off by `max_tokens` 1 (Mistral, Mixtral, Marin); 6 single wrong characters (`Q`,
  `D`, `I`, `L`) and 3 lower-case letters (`b`, `c`); 2 control or invalid bytes (DBRX); 2 unrelated words (OLMoE);
  5 longer answers from reasoning-capable models (Gemini 3 Pro writes a sentence; DeepSeek-R1 hide-reasoning and
  R1-0528 give a letter followed by more text, or a lone quote mark); and DeepSeek-R1's 2 raw reasoning blocks
  (above). 5 of the 30 contain an answer letter (the 3 lower-case letters and 2 capital letters followed by more text)
  that HELM's exact-match rule does not read.

### What this means

- HELM Safety's BBQ (unambiguous) column, as published today, says that all 80 re-scored models, from GPT-3.5 to GPT-5.1
  and Gemini 3 Pro, are counter-stereotypical by about 0.2. That is the tagging bug in #4368, measured on the current
  leaderboard: with the authors' tags the column sits near zero and most models are slightly positive.
- The ambiguous column's order is mostly set by the two bugs: tau-b 0.257 with both fixed. Re-publishing the BBQ page
  with #4368's `target_loc` fix and #4372's scaling fix (PR #4373) would change both bias columns. The headline BBQ
  accuracy does not change.
- Smaller, separate: six models' runs in the release are not in the public bucket where the index points, and the
  stored DeepSeek-R1 predictions keep the reasoning text.

**Limits.** One release (v1.17.0), one sample of 1,000 instances per model, one trial. The authors' `target_loc` is
taken as ground truth; one test instance has no usable `target_loc` (NA in the authors' file). Ranks follow HELM's lower-is-better order, in
which a negative bias ranks above zero; another order (for example by absolute value) would rank differently. The
hand-read covers only the printed sample and was done by AI agents. Seven of 87 runs are not re-scored.
