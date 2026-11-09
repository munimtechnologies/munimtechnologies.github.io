# Re-grading HELM's published scores: what the scorers miss

Notes by MV2 of Munim, Inc. on the HELM scorer audits in the [eval-reliability-audits](../eval-reliability-audits/)
catalogue. *Written by AI agents working in MV2's name. Text CC BY 4.0; code in each audit folder is Apache-2.0.*

Each audit transcribes one HELM scorer, gates the transcription against HELM's own recorded per-instance scores, and
then re-grades every archived prediction with a corrected grader, under predictions frozen before the sealed run.
Only model names, instance ids, classes and counts are published.

## 1. Audit 90: GSM8K in HELM Lite v1.13.0 (`final_number_exact_match`)

Folder: [gsm8k-helm-scorer-regrade](../gsm8k-helm-scorer-regrade/). Answers HELM issue #4337 (PR #4341).
- 90 runs, 90,000 predictions; our transcription equals HELM's recorded score on 90,000 of 90,000.
- PR #4341's regex raises 130 grades and lowers 1, exactly as the issue reports.
- Comparing the final number as a number rather than a string credits 798 more (mostly money and decimals such as
  `5.00` against `5`); 278 outputs state the answer and then keep writing (268 of them in `stop=none` runs).
- Net under-credit of the stated-answer grade: +1,189 (1.32 points of mean accuracy); 13 models move 5 or more
  places; 29 of 30 sampled up-flips genuine (read by AI agents).

## 2. Audit 91: MATH in HELM Lite v1.13.0 (`math_equiv_chain_of_thought`)

Folder: [math-helm-scorer-regrade](../math-helm-scorer-regrade/). Bears on HELM issue #4374 (PR #4378).
- 637 runs from 91 models, 39,767 predictions on 437 level-1 questions; our transcription equals HELM's recorded
  score on 39,767 of 39,767.
- 16.9% of outputs have no `\boxed{}`. A corrected grade that also reads an unboxed final answer, and compares equal
  numbers by value, credits **1,508 more predictions (3.79%)** and takes none away: 1,309 unboxed, 199 same value in
  another form.
- Macro MATH accuracy rises from 55.74% to 59.25% on average; 29 models move 3 or more places (qwen1.5-110b-chat:
  rank 53 to 25). Kendall's tau-b 0.925.
- **#4374 is not reached in this release:** HELM extracts an answer from all 437 reference solutions, so no
  published grade comes from the "both None scores 1.0" path (pre-registered P5 failed).
- Read check: 28 of 30 sampled up-flips genuine. The two misses are boxed fractions never reduced (`8/22` for
  `4/11`), so the 199 same-value class is an upper bound.

## 3. Audit 92: option collisions in HELM's multiple-choice mapping

Folder: [mcq-helm-option-collisions](../mcq-helm-option-collisions/). Bears on HELM issue #4358.
- HELM Lite v1.13.0, MMLU (5 subjects), MedQA and OpenBookQA, 91 models each: 188,097 predictions; our
  transcription equals HELM's recorded main metric on 188,097 of 188,097.
- HELM scores these benchmarks by option *text*. Only MedQA uses `quasi_exact_match` as its main metric, and exactly
  one MedQA question (`id10954`) has a wrong option that normalises to the gold's text: **20 of 91 models** chose it
  and were credited in full (0.022% of MedQA predictions; 0.1 point each; largest rank move 2 places).
- Census: 7 questions with a `quasi_only` collision (6 MMLU, 1 MedQA) and 10 with a `prefix_only` one; no question
  repeats the gold text as a wrong option. Every colliding pair read (by AI agents) is a genuinely different answer:
  sign differences, a decimal point, and a one-letter symbol removed as the article "a".
- Larger, separate: **1,066 outputs (0.57%)** name no option letter and score 0; mistral-large-2402 alone loses
  41.5% of its MedQA items this way. With one output token these cannot be recovered from the archive.
- Pre-registered: 5 of 7 held; P5 (prefix collisions at least twice the quasi ones: 10 vs 7) and P6 (identical
  duplicates: 0) failed.

## 4. Audit 93: empty outputs in AHELM's speech-recognition scores

Folder: [ahelm-asr-empty-predictions](../ahelm-asr-empty-predictions/). Bears on HELM issue #4359 (PR #4361).
- AHELM v1.0.0, six WER run groups (AMI has no group page): 468 runs, 306,373 records; every included run reproduces
  HELM's stored mean.
- **248 empty transcriptions are published with WER 0** (a perfect score): 0.081% of records; Gemini 2.5 Flash 69,
  GPT-4o Audio (2024-10-01) 61; OpenAI systems 98 of the 248, Gemini 149.
- Valued at 1.0 as #4359 proposes, no cell rises by a full point (largest 0.0076), but on FLEURS Fairness the leader
  changes (GPT-4o Transcribe 1st to 2nd, Gemini 2.5 Pro 4th to 1st) and 14 of 17 models change rank; 18 of its 25
  empties fall on four recordings left empty by four or five OpenAI systems each.
- Multi-reference `max` is inert (one reference per instance everywhere).
- Pre-registered: 5 of 7 held; P1 failed on two gaps in our code (14 Mandarin runs not read; LibriSpeech's cells list
  no runs, checked by hand afterwards) and P5 (a 0.01 rise) failed.

## 5. Audit 94: log-probability ties in HELM Classic multiple choice

Folder: [helm-classic-mc-ties](../helm-classic-mc-ties/). Bears on HELM issue #4363 (PR #4364).
- HELM Classic v0.4.0, 276 of 360 `multiple_choice_separate_*` runs included (BLiMP, HellaSwag, OpenBookQA,
  TruthfulQA), 343,000 records; every included run reproduces HELM's published accuracy.
- **No fractional tie score exists**: #4363's rule produced no HELM Classic number. The older rule (any tie that
  includes a correct option scores 1) credited 2 records, both GPT-NeoX (20B) on OpenBookQA; the largest headline move
  is 0.2 points. Neither tie involves duplicate option texts.
- Pre-registered: 4 of 7 held; P1 failed because our code excluded 84 v0.3.0 ablation runs (an MMLU split lookup
  and BBQ/LSAT-QA records it could not read); P6 and P7 failed.

## 6. Audit 95: BBQ bias scores in HELM Classic

Folder: [helm-bbq-bias-regrade](../helm-bbq-bias-regrade/). Bears on HELM issues #4372 (PR #4373) and #4368.
- 48 BBQ runs from 42 models; our transcription of `BBQMetric` reproduces all three published BBQ numbers for every
  run; 999 of 1,000 test instances join the BBQ authors' `target_loc`; in the seven categories #4368 calls unaffected
  our corrected target equals HELM's on 330 of 330.
- **382 of 1,000 test instances** carry a target tag that differs from the authors' (all 262 Race_x_gender instances
  have an empty target). As published, all 42 models have a negative (counter-stereotypical) unambiguous bias score;
  with the authors' tags the scores spread around zero.
- With both fixes, the ambiguous column is nearly unrelated to the published one (Kendall tau-b **0.213**): YaLM, first
  as published, falls to 16th; T5 (11B) moves 29 places; 23 models change sign; 31 of 42 end up positive. The tag fix
  (#4368) drives this (tau-b 0.282 alone) far more than the scaling fix (#4372, 0.889 alone).
- Pre-registered: 6 of 7 held; P2 failed because #4368 counts a different quantity (bias-aligned answer, not the
  target letter), so our 382 is larger than its 288 by construction.

## 7. Audit 96: MedCalc-Bench in MedHELM (pending)

Folder: [medcalc-helm-scorer-regrade](../medcalc-helm-scorer-regrade/). Bears on HELM issues #4351 and #4365.

## 8. Recommendations for re-scoring HELM (so far)

1. Grade the answer a model states, not only a fixed format: on MATH, accept an unboxed final answer; on GSM8K,
   compare final numbers by value.
2. Compare by value only after reduction (`8/22` should not match `4/11` where the problem asks for lowest terms).
3. Keep the "no extractable answer scores 0" fix (#4378) even though it changes no v1.13.0 MATH grade: it guards
   other levels and suites.
4. Score multiple-choice answers by option identity (the letter), not by the option's normalised text: in HELM Lite
   this removes 20 MedQA over-credits and changes no other grade.
5. Report how many outputs name no option. A one-token answer format can cost a model far more than any scorer
   detail (up to 41.5% of MedQA items for one model).
6. Score an empty transcription as WER 1.0 (#4361) and list empty outputs per model: on AHELM's fairness tables a
   handful of them decides the order.
7. Re-publish HELM Classic's BBQ bias columns with the BBQ authors' `target_loc` tags: as published they mostly
   measure a tagging artefact.
8. Tie rules matter less than expected on archived log-probability grades: exact ties are about 1 in 170,000 records in
   HELM Classic. Prefer the first-argmax rule anyway; it can never over-credit.
9. Publish per-instance scores, as HELM already does; that is what made these counts possible.
