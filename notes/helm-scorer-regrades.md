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

## 7. Audit 96: MedCalc-Bench in MedHELM

Folder: [medcalc-helm-scorer-regrade](../medcalc-helm-scorer-regrade/). Bears on HELM issues #4351 (PR #4352) and
#4365.
- MedHELM v4.0.0, all 13 `medcalc_bench` runs, 13,000 predictions; our transcription of `MedCalcBenchMetric` equals
  HELM's recorded score on 13,000 of 13,000.
- **All 4,602 lab and dosage predictions (35.4% of the test set) are published as 0**, whatever the answer. Scoring
  them against the 5% limits HELM already ships with each instance (#4351's fix) credits 1,797 more; accepting other
  forms of the same week/day duration (#4365) adds 144. Mean accuracy goes from 24.7% to 39.6%; no grade goes down.
- **The published top is a tie the fix breaks:** DeepSeek-R1 and Gemini 2.5 Pro share first at 0.348; corrected,
  Gemini 2.5 Pro leads (0.602), o3-mini is second and DeepSeek-R1 fifth (0.563). Four of the six reasoning models
  change rank; nothing below them moves.
- Our #4351 fix reproduces PR #4352's two re-scored models exactly (Claude 3.7 Sonnet 0.210 to 0.314; GPT-4o 0.188 to
  0.280). Our duration rule, written independently, finds 144 of #4365's 148.
- A loss no re-scoring can fix: Llama 3.3 70B gives a non-number for 49.2% of its lab, dosage and physical outputs.
- Pre-registered: 7 of 7 held; 30 of 30 sampled up-flips genuine by their class rule (read by AI agents).

## 8. Audit 97: BBQ bias scores on the current HELM Safety leaderboard

Folder: [helm-safety-bbq-bias-regrade](../helm-safety-bbq-bias-regrade/). Bears on HELM issues #4368 and #4372
(PR #4373).
- HELM Safety v1.17.0 lists 87 BBQ runs, one per model. 80 were re-scored; for each, our transcription of `BBQMetric`
  reproduces all three published BBQ numbers. The same **382 of 1,000** test instances are affected as in HELM Classic
  (382 of 382 BBQ keys shared): the cause is the shared sample and the shared tagging code.
- **As published, all 80 models look counter-stereotypical** on the BBQ (unambiguous) column, by a median of 0.194,
  from GPT-3.5 to GPT-5.1 and Gemini 3 Pro. With the authors' tags the median size is 0.0101 and 53 of 80 are slightly
  positive. First place (DBRX Instruct) holds under both, because 13.3% of its completions are not a letter and count
  as non-biased answers.
- The ambiguous column re-orders with both fixes (Kendall tau-b **0.257**); here the scaling fix (0.617 alone) matters
  as much as the tag fix (0.518 alone). Claude 3.7 Sonnet moves from 79th to 14th, GPT-4.5 from 80th to 31st, OLMo 2 7B
  from 4th to 80th. Only 5 models change sign, because 71 of 80 published ambiguous scores are already positive.
- Two gaps: six models' runs (Gemini 2.0 Flash, Flash-Lite and Pro, Mistral Small 2501, Qwen2.5 72B and 7B) are not in
  the public bucket where the release index points, and the stored DeepSeek-R1 predictions keep the reasoning text,
  which our code does not strip. Its published BBQ numbers equal the DeepSeek-R1 (hide reasoning) run's exactly.
- Pre-registered: 6 of 8 held; P1 failed on inclusion (80 of 87, gate 95%) and P7 (10 sign changes) failed.

## 9. Audit 98: dropped judge ratings on AHELM (a negative result)

Folder: [ahelm-judge-dropped-ratings](../ahelm-judge-dropped-ratings/). Bears on HELM issues #4345 and #4344.
- #4345: when the GPT-4o judge's reply has no parseable `Rating: N`, HELM leaves the rating out of the mean. On all
  three of AHELM v1.0.0's judged tables (AudioCaps, Air-Bench Chat knowledge and reasoning; 85 runs, 17 systems),
  **0 of 54,281 requested ratings were dropped**: every run's judge count equals its number of instances, every
  per-instance record has a whole rating from 1 to 5, and all 51 cells are reproduced by the pooled rule. So the
  silent drop changes no published number in this release.
- #4344 (a score planted in the model's own output): no model output in these runs contains a string HELM's judge
  regex would read.
- The judge rates audio captions far lower than chat answers: on AudioCaps 8,945 of 17,000 ratings are 1 and only
  118 are 5.
- v1 missed AudioCaps (its group page lists run names on the model cell, which our code did not look at, a gap like
  LibriSpeech's in audit 93); v2 fixed only that. Pre-registered: v1 1 of 7 held (P3); v2 2 of 7 (P1, P3); P2 and P4
  to P7 failed because nothing was dropped.

## 10. Audit 99: operators erased in HELM Classic's synthetic reasoning

Folder: [helm-synthetic-reasoning-operators](../helm-synthetic-reasoning-operators/). No HELM issue reported this.
- HELM Classic v0.4.0's "Synthetic reasoning (abstract symbols)" column is scored by `quasi_exact_match`, whose
  normaliser removes all punctuation, and with it every operator the scenario uses (`+ - * =`). So `X = Y + Y` matches
  `X + Y = Y`.
- 207 runs (69 models x 3 modes), 242,565 records; every stored score, run mean and all 69 published cells reproduced.
- **19,145 of the 58,270 published credits (32.9%) have a different operator sequence from the gold's** (14,990 other
  operators, 3,748 the same operators reordered, 407 no operators). By mode: induction 57.6%, variable substitution
  36.0%, pattern match 26.2% (pre-registered P3, which expected pattern match highest, failed).
- With an operator-aware grade, every model's cell falls (largest: Llama 2 13B, 0.324 to 0.190); 26 of 69 models move
  3 or more places (Kendall tau-b 0.917; code-davinci-002 stays first). For the weakest models most of the published
  score is operator-blind (Cohere small 2022-07-20: 0.121 published, 0.013 operator-aware).
- Pre-registered: 6 of 7 held.
- **Follow-up (post-hoc, descriptive;** [followup-positions](../helm-synthetic-reasoning-operators/followup-positions/)**):**
  a position-aware grade finds that 5,836 of the 5,843 credits the operator-aware grade still kept without an exact
  match put the operators in the wrong places; only 7 differ in formatting (a stray `|`, or `**` for `* *`). So
  **24,981 of 58,270 published credits (42.9%) are for a wrong pattern** (induction 64.8%, variable substitution
  44.7%, pattern match 37.9%), and each model's right-pattern score is its exact-match score to within 7 records
  column-wide. 29 of 69 models move 3 or more places (tau-b 0.910); Llama 2 13B falls 0.155; for 39 of 69 models more
  than half of the published cell is wrong-pattern credit. A hand-read of 54 credits from all three modes (by AI
  agents) agreed with every class.

## 11. Recommendations for re-scoring HELM (so far)

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
7. Re-publish the BBQ bias columns of both HELM Classic and HELM Safety with the BBQ authors' `target_loc` tags and
   the paper's ambiguous-accuracy scaling: as published, the unambiguous column mostly measures a tagging artefact
   (every one of 42 Classic and 80 Safety models looks counter-stereotypical).
8. Tie rules matter less than expected on archived log-probability grades: exact ties are about 1 in 170,000 records in
   HELM Classic. Prefer the first-argmax rule anyway; it can never over-credit.
9. Merge PR #4352 and re-publish MedHELM's MedCalc column: as published it scores 35% of the test set as 0 for every
   model and leaves first place tied. Make an unknown category raise rather than score 0.
10. Publish per-instance scores, as HELM already does; that is what made these counts possible.
11. Keep every run that a release lists in the public bucket at the suite the index names, and store the final answer
    next to any reasoning text, so each published number can be checked.
12. Still count unparsed judge replies (#4345) even though AHELM's three judged tables dropped none: a stored
    "requested vs rated" count per run would show at a glance that a judged mean is complete.
13. Put run names on the score cells of every group page (AHELM's AudioCaps page keeps them only on the model cell;
    in audit 93 LibriSpeech's score cells listed none), so a published cell can be traced to its runs without guessing.
14. Do not score symbolic answers with a normaliser that strips punctuation: for synthetic reasoning, use exact match
    after collapsing case and spaces (the follow-up shows this differs from the correct-pattern count by only 7 of
    58,270 credits), or a normaliser that keeps `+ - * =`. Check every other quasi-exact column for answers whose
    meaning lives in punctuation.
