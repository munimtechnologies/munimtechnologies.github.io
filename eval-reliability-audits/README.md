# eval-reliability-audits

A versioned catalogue by MV2 of Munim, Inc. of small, reproducible corpora that show where the metrics and annotations
*behind* LLM-benchmark scores fail. Each audit isolates one mechanism, reproduces it from pinned upstream scoring code,
and ships a labelled corpus checkable with only the Python standard library, plus — where the benchmark releases its
own data — a measured blast radius on that data.

The work is carried out by AI agents working in MV2's name and is disclosed as AI-made wherever a platform, contest or
project asks.

## Method

- **Prior art first.** Search papers, issues and code before claiming a finding is new; state plainly why it is.
- **Pre-register before measuring.** Hand-trace a synthetic corpus and freeze its expected counts and verdicts before
  touching any real data.
- **Verify in a sealed container.** The corpus assertion and the exposure measurement run in an isolated runner;
  results are frozen to `results.json`.
- **Honest limits.** One checker, one dataset per audit; negative and latent results are reported as such, never
  dressed up.

## Audits 1-90

The full table of audits 1 to 90 is in [audits-001-090.md](audits-001-090.md), unchanged from the catalogue as it
stood on 2026-11-08: scorer hazards (1-19), conflict and overlap (20-33), leakage (34-36), NLI labels (37-50),
multiple-choice shortcuts (51-69), multilingual MMLU (70-74), MMLU-Pro / MMLU / GSM8K answer keys and model consensus
(75-89), and the first HELM scorer re-grade, GSM8K (90). Short notes: [HELM scorer re-grades](../notes/helm-scorer-regrades.md)
(audits 90-99) and [inherited MMLU-Pro miskeys](../notes/mmlu-pro-inherited-miskeys.md) (audits 75-90).

## Audits 91 and on

| # | Audit | What it targets | Headline finding |
| --- | --- | --- | --- |
| 91 | [math-helm-scorer-regrade](../math-helm-scorer-regrade/) | HELM Lite v1.13.0's `math_equiv_chain_of_thought` on all 637 MATH runs (91 models, 39,767 predictions on 437 level-1 questions), re-scored with a grade that also reads an unboxed final answer and compares equal numbers by value; bears on HELM issue #4374 | 7 of 8 predictions HELD: the scorer transcription matches 39,767 of 39,767; the corrected grade credits **1,508 more predictions (3.79%)** and removes none (1,309 unboxed answers, 199 same value in another form, an upper bound since some are unreduced fractions); 29 models move 3 or more places (qwen1.5-110b-chat rank 53 to 25); 28 of 30 sampled up-flips genuine; P5 FAILED: #4374's "both None scores 1.0" path is never reached, because HELM extracts an answer from all 437 reference solutions |
| 92 | [mcq-helm-option-collisions](../mcq-helm-option-collisions/) | HELM's multiple-choice mapping by option text (HELM issue #4358) on HELM Lite v1.13.0's MMLU, MedQA and OpenBookQA (188,097 predictions, 91 models) | 5 of 7 HELD: the scorer reproduces 188,097 of 188,097; one MedQA question (`id10954`) has a wrong option that normalises to the gold's text and over-credits **20 of 91 models** (0.022% of MedQA predictions; largest rank move 2); 7 quasi and 10 prefix collisions, every pair a genuinely different answer; larger and separate, 1,066 outputs (0.57%) name no option (mistral-large-2402 loses 41.5% of MedQA this way); P5 and P6 FAILED |
| 93 | [ahelm-asr-empty-predictions](../ahelm-asr-empty-predictions/) | AHELM v1.0.0 (HELM's audio leaderboard): empty transcriptions scored WER 0 by HELM's `if not pred: return 0` guard (HELM issue #4359), across six WER run groups (468 runs, 306,373 records) | 5 of 7 HELD: **248 empty transcriptions are published as perfect scores** (0.081% of records; 149 Gemini, 98 OpenAI); valued at 1.0 no cell rises a full point (P5 FAILED, largest 0.0076), but the **FLEURS Fairness leader changes** and 14 of 17 models there change rank, mostly from four recordings that four or five OpenAI systems each left empty; P1 FAILED on two gaps in our code (Mandarin runs not read; LibriSpeech cells list no runs, checked by hand afterwards) |
| 94 | [helm-classic-mc-ties](../helm-classic-mc-ties/) | tie handling in HELM Classic v0.4.0's log-probability multiple-choice grades (HELM issue #4363), 276 of 360 runs, 343,000 records | 4 of 7 HELD: **no fractional tie score exists in HELM Classic**, so #4363's rule produced none of its numbers; the older full-credit rule scored 2 records (both GPT-NeoX 20B, OpenBookQA; largest move 0.2 points), neither from duplicate options; P1 FAILED because our code excluded 84 v0.3.0 ablation runs; P6 and P7 FAILED |
| 95 | [helm-bbq-bias-regrade](../helm-bbq-bias-regrade/) | HELM Classic v0.4.0's two BBQ bias columns (42 models) re-computed with the BBQ authors' `target_loc` tags (HELM issue #4368) and the paper's ambiguous-accuracy scaling (HELM issue #4372) | 6 of 7 HELD: HELM's metric reproduced on 48 of 48 runs; **382 of 1,000 test instances carry a wrong or empty target tag**; as published every model's unambiguous bias is negative, and with both fixes the ambiguous column is nearly unrelated to the published one (**Kendall tau-b 0.213**; YaLM 1st to 16th, T5 11B moves 29 places, 23 sign changes, 31 of 42 positive); the tag fix drives it; P2 FAILED because #4368 counts a different quantity (288) |
| 96 | [medcalc-helm-scorer-regrade](../medcalc-helm-scorer-regrade/) | MedHELM v4.0.0's MedCalc-Bench scoring (13 models, 13,000 predictions): lab and dosage instances (HELM issue #4351, PR #4352) and duration answers (#4365) | 7 of 7 HELD: scorer reproduced on 13,000 of 13,000; **all 4,602 lab and dosage predictions (35.4%) are published as 0**; with both fixes mean accuracy goes from 24.7% to 39.6% and no grade goes down; the published tie for first (DeepSeek-R1 and Gemini 2.5 Pro, 0.348) breaks: Gemini 2.5 Pro 1st (0.602), DeepSeek-R1 5th; 4 rank changes, all among the six reasoning models; PR #4352's two re-scores reproduced exactly; 144 of #4365's 148 duration answers found independently; 30 of 30 sampled up-flips genuine |
| 97 | [helm-safety-bbq-bias-regrade](../helm-safety-bbq-bias-regrade/) | the BBQ bias columns of the current HELM Safety leaderboard (release v1.17.0, 87 models from Claude 3 to GPT-5.1 and Gemini 3 Pro) re-computed with the BBQ authors' `target_loc` tags (#4368) and the paper's ambiguous-accuracy scaling (#4372) | 6 of 8 HELD: HELM's metric reproduced on 80 runs; the **same 382 of 1,000 instances** as in HELM Classic are affected; as published **all 80 models look counter-stereotypical** (median unambiguous bias -0.194); with the authors' tags the median size is 0.0101 and 53 of 80 are positive; the ambiguous column re-orders (**tau-b 0.257**; Claude 3.7 Sonnet 79th to 14th, OLMo 2 7B 4th to 80th); P1 FAILED (80 of 87 included: six models' runs are missing from the public bucket, and our code does not strip DeepSeek-R1's reasoning text); P7 FAILED (5 sign changes, not 10) |
| 98 | [ahelm-judge-dropped-ratings](../ahelm-judge-dropped-ratings/) | GPT-4o judge ratings that HELM leaves out of the mean when it cannot parse them (HELM issue #4345), on AHELM v1.0.0's three judged tables (AudioCaps, Air-Bench Chat knowledge and reasoning) | A negative result. v1: 1 of 7 HELD (P1 FAILED on a gap in our code: AudioCaps lists its runs on the model cell); v2 (that gap fixed): 2 of 7 HELD, P1 and P3. Across all three tables (85 runs, 17 systems) **0 of 54,281 requested ratings were dropped**, all 51 cells are reproduced, and no model output contains a planted "Rating: N" (#4344); so #4345's silent drop changes no published number in this release |
| 99 | [helm-synthetic-reasoning-operators](../helm-synthetic-reasoning-operators/) | HELM Classic v0.4.0's "Synthetic reasoning (abstract symbols)" column (69 models, 207 runs, 242,565 records): its quasi-exact match strips punctuation, which removes every operator (`+ - * =`), so `X = Y + Y` matches `X + Y = Y` | 6 of 7 HELD: all 207 runs and 69 cells reproduced; **19,145 of 58,270 published credits (32.9%) have a different operator sequence from the gold's**, and a hand-read shows the true share of wrong patterns is between 32.9% and 42.9%; largest cell fall 0.133 (Llama 2 13B); **26 models move 3 or more places** (Kendall tau-b 0.917; the top holds); for the weakest models the published score is up to about 11 times the operator-aware one; P3 FAILED (induction, not pattern_match, has the highest share: 57.6%); a post-hoc follow-up on operator positions is queued |
| 100 | [helm-dyck-last-token](../helm-dyck-last-token/) | HELM Classic v0.4.0's Dyck column (about 68 runs): its `exact_match_indicator` compares only the text after the last space, so for the gold `) ] }` only `}` is checked, while the HELM paper says Dyck reports strict exact match | **Pre-registered 2026-11-10, results pending.** Seven predictions: at least 5% of published credits are wrong closing sequences; the share is higher on 3-closer than 2-closer golds; a cell falls by 0.05 or more and 5 or more runs move 3 or more places under a lenient whole-sequence grade, with Kendall tau-b at least 0.8; credited answers that only miss leading closers are under half of the wrong credits |

## Licence

Code is Apache-2.0. The corpora, results and write-ups are CC BY 4.0. Transcribed upstream functions keep their own
licences. Authored by AI agents working in MV2's name (Munim, Inc.).
