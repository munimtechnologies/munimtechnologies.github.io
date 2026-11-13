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

Folder: [helm-synthetic-reasoning-operators](../helm-synthetic-reasoning-operators/). No earlier HELM issue reported
this; MV2 reported it as issue [#4381](https://github.com/stanford-crfm/helm/issues/4381) on 2026-11-12.
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

## 11. Audit 100: HELM Classic's Dyck column checks only the last bracket

Folder: [helm-dyck-last-token](../helm-dyck-last-token/). MV2 reported it, with audit 101, as HELM issue
[#4382](https://github.com/stanford-crfm/helm/issues/4382) on 2026-11-13.
- HELM Classic scores Dyck (write the 1 to 3 closing brackets of a Dyck-3 prefix) with `exact_match_indicator`, which
  keeps only the text after the last space, its default indicator. For the gold `) ] }` only `}` is compared, while
  the HELM paper says Dyck reports strict exact match.
- Release v0.4.0: 69 runs, 78,500 records; every stored per-record score, run mean and all 69 published cells
  reproduced.
- **24,395 of the 40,778 published credits (59.8%) are wrong closing sequences.** The share grows with the number of
  closers: 42.3% on 1-closer golds, 57.8% on 2, 76.5% on 3. The wrong credits are extra closers in front of the right
  ones (8,689), only the last one or two closers (6,349), the right count with wrong inner brackets (2,022) and other
  wrong sequences (7,335). Only 20.9% of records are strictly right, against 51.9% credited.
- Every cell falls (largest YaLM, 0.633 to 0.033); 54 of 69 runs move 3 or more places; Kendall tau-b **0.589**
  (pre-registered P6, which expected at least 0.8, failed). The two leaders swap: code-davinci-002 (0.567) is first and
  Anthropic-LM v4-s3 (0.849 published, 0.526) second; Llama 30B falls from 11th to 46th. Post-hoc: in 56 of 69 runs
  more than half of the published score is wrong-sequence credit.
- The other direction is small: 34 right answers in two `stop=hash` runs (T5 11B, UL2) score 0 because the stored
  output keeps the `#` stop character glued to the last bracket.
- Pre-registered: 6 of 7 held. A hand-read of 32 wrong credits from 8 runs (by AI agents) agreed with every class.

## 12. Audit 101: HELM Classic's GSM8K column scores right answers 0

Folder: [helm-gsm-classic-indicator](../helm-gsm-classic-indicator/). Reported with audit 100 as HELM issue
[#4382](https://github.com/stanford-crfm/helm/issues/4382) (#4337 is about HELM Lite's other GSM8K metric).
- The same `exact_match_indicator` is the main metric of HELM Classic's GSM8K column. The gold ends
  `The answer is 72.`, so only `72.` is compared, literally: `The answer is $72.`, `1,000.` against `1000.`, or
  `72 apples.` score 0. We expected comparing the last token to be safe here (audit 100's recommendation said so); it
  is not.
- Release v0.4.0: 69 runs, 157,000 records; every stored per-record score, run mean and all 69 published cells
  reproduced.
- **2,949 answers whose stated answer is right score 0: 16.7% of the 17,694 published credits.** By class: the number
  written differently (1,131), words after it (822), no "the answer is" but a right last number (989, the noisiest).
  HELM's own `final_number_exact_match`, which the GSM8K run spec lists but these runs do not store, credits 2,772
  more answers than the published metric and none fewer.
- **The leader changes:** GPT-3.5 Turbo 0301 goes from 0.531 (3rd) to 0.775 (1st) and 0613 from 0.469 (6th) to 0.756
  (2nd); Palmyra X, first as published, goes from 0.633 to 0.639 (3rd). HELM's `final_number_exact_match` gives the
  same top three. 20 runs move 3 or more places (Kendall tau-b 0.927). Post hoc, counting only the 1,131 differently
  written numbers (8 of 8 read were right) gives the same top three in the same order.
- Hand-read (by AI agents) of 26 under-credits: 20 right, 3 wrong (2 repetition loops ending on the gold's number by
  chance, 1 fraction our grade misread), 3 doubtful. All 8 "over-credits" read were right answers our grade misread
  ("the answer is 300 - 240 = 60"), so our total is a slight underestimate.
- Pre-registered: 6 of 7 held; P7 (output continuing after the answer as the main cause) failed: 2 records.

## 13. Audit 108: HELM Finance's FinanceBench prompt keeps only the first evidence page

Folder: [helm-financebench-first-page](../helm-financebench-first-page/). No HELM issue reported this. Not a scorer
defect but a prompt one: it is the input, not the grade, that differs from the benchmark's design.
- HELM Finance v1.0.0's FinanceBench column (22 models, 140 test questions, GPT-4o judge) builds each prompt from the
  first cited evidence item's page only. The FinanceBench paper's Oracle setting gave all cited pages.
- All 22 runs included; every one of their 140 test prompts is exactly the first page plus the question; every judge
  label agrees with HELM's stored stat (3,080 labels) and all 22 published cells are reproduced.
- **32 of 140 test questions (22.9%) cite a page the prompt leaves out**, 21 of them metrics-generated (ratios built
  from two statements: 21 of the 47 metrics-generated test questions).
- On those 32, the models are judged correct on **10.4%** of answers (73 of 704) against **65.4%** (1,555 of 2,376) on
  the other 108; "failure to answer" is 39.2% against 6.7%, **5.8 times** as common; all 22 runs do worse there. Among
  metrics-generated questions only: 6.5% against 70.3%.
- The order holds (Kendall tau-b 0.965; no model moves 3 or more places; Claude 3 Opus first either way), but 20 of 22
  cells are 0.10 to 0.16 lower than on complete questions. A model that says the needed statement is not given scores
  the same as a wrong guess: Claude 3.5 Sonnet declines on 25 of the 32, GPT-3.5 Turbo (0125) on none, and both are
  judged correct on a similar few (4 and 6).
- Hand-read (by AI agents): 7 of 8 missing questions lack a figure the answer needs (net income, revenue, inventories
  or a cash-flow line); 6 of 8 "failure to answer" labels on them say so; 3 of 8 "correct" labels read are one question
  whose figure also appears on the given page, so 32 is an upper bound on truly unanswerable questions.
- Pre-registered: 7 of 8 held; P7 (a model moving 3 or more places) failed.

## 14. Audit 105: HELM Capabilities' MMLU-Pro column reads boxed answers as no answer

Folder: [helm-mmlu-pro-answer-extraction](../helm-mmlu-pro-answer-extraction/). Bears on open HELM PR #4323 (the
escaped `Answer:` regex), which gives no count; no issue reported the rest.
- HELM Capabilities v1.15.0 (the current leaderboard) scores MMLU-Pro and GPQA "COT correct" with one
  `extract_answer()`: the **first** match of `answer is X`, a dead `\[aA\]nswer:` regex, then two "correct answer is"
  fallbacks. `\boxed{C}`, `Answer: C` and `**The correct answer is** **C**` are read as no answer.
- 67 of 68 runs (one is missing from the public bucket), 67,000 records; every stored per-record score and all 67
  cells reproduced (59 runs by HELM main's extractor, 8 older ones by the version before PR #3445).
- Graded by the model's **last** explicit answer statement: **952 records gain, 133 lose** (net 819, 1.2% of
  records). Boxed right letters are most of the gains (619); 223 are answer phrases HELM's regexes miss (often bold
  markup); 110 are cases where HELM read another letter, from an earlier statement or from text such as "(insert
  answer here)".
- **Two models carry most of it:** Gemini 2.5 Flash-Lite 0.537 to 0.778 (rank 54 to 27 of 67; 237 boxed right
  answers) and Gemini 2.5 Flash preview 0.639 to 0.814 (rank 42 to 16; 175). 15 other models gain 0.01 or more, the
  top ten change by at most 0.001, and Kendall tau-b is 0.930. PR #4323's fix would recover 63 of the 952.
- Hand-read (by AI agents): 6 of 6 boxed and 6 of 6 other-letter up-flips genuine; 6 of 6 revised-answer down-flips
  genuine (HELM credits the answer the model later abandoned); 5 of 6 `down_fallback` cases are right answers our
  narrow rule misses, so the net gain is an underestimate.
- GPQA uses the same extractor; its outputs are encrypted in the public archive, so it was not checked.
- Pre-registered: 7 of 8 held; P8 (two other Gemini models gaining 0.02) failed: only one did.

## 15. Audit 107: HELM Finance's FinQA prompt and scorer spell programs differently

Folder: [helm-finqa-program-accuracy](../helm-finqa-program-accuracy/). No HELM issue reported this.
- HELM Finance v1.0.0's only FinQA column, Program Accuracy, uses FinQA's own `equal_program`, which maps arguments
  by their literal spelling. HELM's instructions spell the table operations `table-max` (the scorer accepts only
  `table_max`), omit the `none` argument, and never mention `const_100`.
- 22 runs, 22,000 records; every stored per-record score, run mean and all 22 cells reproduced; execution accuracy
  too.
- **539 records (2.45%) are right programs scored 0 for spelling**, 6.3% as many as the 8,600 published credits:
  `const_N` written as a number 260, hyphenated operation names 101, other number forms (`850` for `850.0`, `0.05` for
  `5.0%`) 86, combined 84, missing `none` 8. No record goes down. 625 records in all use the prompt's hyphenated names.
- Gemini 1.5 Pro stays first (0.587 to 0.654); Gemini 1.5 Flash moves 5th to 2nd; Kendall tau-b 0.939. Execution
  accuracy, stored but not shown, is 0.05 or more above program accuracy in 11 of 22 runs.
- Hand-read (by AI agents): 38 of 38 up-flips read are right programs.
- Pre-registered: 8 of 8 held (P8 exactly on its boundary).

## 16. Audit 109: HELM Finance's BANKING77 prompt numbers the labels, the scorer reads only their text

Folder: [helm-banking77-numbered-labels](../helm-banking77-numbered-labels/). No HELM issue reported this (#2909 shows
the numbered list and the RAFT paper's reason for it, but nobody there discusses how numbered answers are scored).
- HELM Finance v1.0.0's BANKING77 "EM" column (22 models, 1,000 test queries) reuses RAFT's instructions, which list
  the 77 intent labels as a **numbered** list. The numbers served the RAFT paper's first-token probability scoring;
  HELM generates the label and compares it with the label text by quasi-exact match, so the right label's number
  (`71`), or the number plus the right label (`71. verify_source_of_funds`), scores 0.
- All 22 runs, every stored score and all 22 cells reproduced.
- **398 of 22,000 answers (1.81%) name the right intent by its list number** and score 0: 148 bare numbers, 250
  number plus label, 0 spacing-only. That is 2.7% as many as the 14,479 answers HELM credits.
- **15 of 22 models never do it** (every GPT, Claude and Qwen run, Gemini 1.5, the larger Llama 3.1 and 3.2 models).
  For the smaller Llama 3 chat models it is a large part of the score: **Llama 3 Instruct 8B 0.327 to 0.497
  (+0.170)**, Llama 3.2 11B Vision 0.407 to 0.532, Llama 3.1 8B 0.466 to 0.529; **Llama 3 Instruct 70B moves 11th to
  7th**. Kendall tau-b 0.956; GPT-4o stays first.
- Hand-read (by AI agents): 11 of 11 misread answers read are right. 81 answers contain the gold label among other
  words and are not credited; 3 of the 8 read pair the gold label with a neighbouring label's number, so the lenient
  cells are conservative.
- HELM's banking77 run spec adds "Answer with only the label for the last query." to the RAFT instructions; the
  numbered answers occur despite it.
- Pre-registered: 8 of 8 held.

## 17. Audit 103: HELM Classic's WikiFact column mixes three decoding regimes

Folder: [helm-wikifact-best-of-five](../helm-wikifact-best-of-five/). No HELM issue reported this (#42 and PR #834
added the sort by log probability).
- HELM Classic v0.4.0 asks each model for 5 completions per WikiFact prompt at temperature 1.0 and publishes the
  quasi-exact match of the completion with the **highest log probability**. What that completion is depends on how
  each model's API answered.
- All 669 runs (67 models, 10 relations, 1,124,212 records) and 67 of 67 cells reproduced.
- **In ranked runs the published score is 20.08% against 14.48% single-draw accuracy (+5.60 points)**; median
  bonus (published minus single-draw) 0.054 for ranked models against 0.000 for the 25 unranked ones, all of which
  keep or improve their rank under single-draw accuracy.
- **48 of 67 models move 3 or more places** when ranked by single-draw accuracy (Kendall tau-b **0.758**, below the
  pre-registered 0.9): text-davinci-002 3rd to 20th, text-davinci-003 5th to 18th, TNLG v2 530B 14th to 33rd.
- *Post hoc,* three regimes: **28 models get a best-of-five pick** (bonus 0.002 to 0.121, median 0.065: OpenAI GPT-3
  and InstructGPT, AI21 J1 and J2, TNLG v2, and the Together-served OPT, BLOOM, GLM, GPT-J, GPT-NeoX, UL2, T5, T0pp,
  YaLM); **24 have every completion scoring alike** (Llama, Llama 2, Falcon, MPT, Mistral 7B, Pythia,
  RedPajama-INCITE, Vicuna, Alpaca, Cohere command-medium-beta; the two spot-checked `author` runs returned fewer than
  five completions per record); **4 are scored on one random draw of five** (GPT-3.5 Turbo 0301 and 0613, Palmyra X,
  Palmyra Instruct 30: log probability 0 everywhere, any-of-five 7.4 to 17.7 points higher). The remaining 11 return
  nearly identical completions.
- The prediction page shows the first completion, not the scored one: they differ on 25.8% of ranked records and
  their scores differ on 3.82% (pre-registered at least 5%: failed). Hand-read (by AI agents) of 16 such records:
  every one is classed correctly.
- Pre-registered: 6 of 8 held; P6 and P7 failed.

## 18. Desk checks: audits 114, 116 and 117 (code-certain, no published number re-computed)

These read HELM's code and test the mechanism on synthetic inputs; HELM's archive either redacts the data or holds no
runs for these scenarios, so their effect on published scores is not measured.
- **Audit 114, MedHELM MIMIC-IV Billing Code** ([helm-mimic-billing-icd-regex](../helm-mimic-billing-icd-regex/)):
  one pattern, `\b[A-Z]\d{1,3}(?:\.\d{1,4})?\.?\b`, reads both the gold list and the answer. It can never match a
  seven-character ICD-10-PCS procedure code (about 27% of the source set's distinct codes), it cuts `S72.001A` to
  `S72` (so a different fracture scores as an exact match), and it drops codes like `Z3A`. In four synthetic notes
  HELM's F1 is 1.0 where full-code F1 is 0.8, 0.0, 0.667 and 0.667.
- **Audit 116, KPI-EDGAR adjusted macro F1** ([helm-kpi-edgar-adjusted-f1](../helm-kpi-edgar-adjusted-f1/)): partial
  credit is applied once per tag across the whole test set. Per tag the score is 2p/(2+p-r) as coded and 2r/(2+r-p)
  with open PR #4350's swap, so **both orders have a floor of 2/3**: as coded, a tag with no wrong words scores at
  least 0.667 however little it finds; with the swap, repeating the sentence under every tag does. An unexpected
  lower-case tag raises `KeyError` and the run writes no scores. A check job on the test split is queued.
- **Audit 117, ConvFinQACalc** ([helm-convfinqa-five-tokens](../helm-convfinqa-five-tokens/)): the run spec never sets
  `max_tokens`, so answers are cut at the helper's default of **5 tokens**, while `float_equiv` needs the gold (to 5
  decimals) within 1e-6 and reads only the first number. For digit-split tokenizers (LLaMA 1, Llama 2) a gold such as
  `0.14136` cannot be written in 5 tokens; `yes`/`no` golds score 0 for every model. *Check job, 2026-11-13:* on
  ConvFinQA's 1,490 validation golds at the commit HELM pins, **a digit-splitting model can score at most 0.644**
  (959 golds fit in 5 such tokens even written in their shortest form; 527 numeric golds do not, and 4 are
  `yes`/`no`), while OpenAI's `cl100k_base` and `o200k_base` reach 1,484 of 1,490 in 5 tokens. So the cut falls by
  tokenizer, not skill. Rounding to 2 decimals caps any model at 0.681, a thousands separator loses all 355 golds of
  1,000 or more, and 214 of 252 percent-worded questions have a gold below 1 (most likely a fraction).
- **Where else the 5-token default applies (a census of HELM main, read 2026-11-13).** `get_generation_adapter_spec`
  defaults to `max_tokens=5`; `AdapterSpec` itself and the translation and summarization helpers default to 100. We
  read the run spec files for Classic, Lite, Capabilities, Safety, SEA-HELM, Long Context, CLEVA, Multilingual,
  Enterprise, LMKT, Finance, Arabic, Arabic Enterprise, SQL, MELT, MedHELM, Simple and Experimental. Every
  generation spec on a current leaderboard other than those below sets `max_tokens` (CLEVA's generic branch falls
  back to 20 tokens, but its published translation and math word problem runs store 201). Left on the default: in
  HELM Classic, BoolQ, IMDB, CivilComments and entity matching (yes/no or one-word answers), entity data imputation
  (a missing city or manufacturer) and bAbI (whose task 8 answers are comma lists such as `milk,apple`); in the
  enterprise set, ConvFinQACalc (audit 117) and two one-label classifiers; in MedHELM, `medbullets_freetext`, which
  asks for an answer and an explanation but is not among MedHELM v4.0.0's runs. So audit 117's scenario is the only case
  we found where the default can cut a numeric answer, and bAbI task 8 is the only list-valued one (not measured).
  Not read: BLUEX, ENEM, OAB, HealthQA-BR, the Portuguese and African-language files, CodeInsights, VLM, audio,
  Unitxt, HEIM, AIR-Bench, DecodingTrust and instruction following.

## 19. Recommendations for re-scoring HELM (so far)

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
15. Never score a multi-token answer with `exact_match_indicator` and its default space indicator: it compares only
    the last token. For Dyck, use exact match after collapsing whitespace (in HELM Classic this removes 24,395 wrong
    credits and adds 34 right ones once a glued stop character is stripped). *Corrected 2026-11-12:* an earlier
    version said to keep the indicator where the last token is the answer by design, as in GSM8K; audit 101 shows
    that even there it scores 2,949 right answers 0 (16.7% of the published credits).
16. Re-publish HELM Classic's GSM8K column with `final_number_exact_match`, the metric its run spec already lists and
    HELM Lite already uses: it credits 2,772 more answers, none fewer, and changes the column's leader.
17. Build FinanceBench prompts from the full pages of every cited evidence item, without duplicates, as the paper's
    Oracle setting did, and re-run the column: as published, 32 of its 140 questions are asked without a page they
    cite. Check other open-book scenarios for the same `evidence[0]` pattern.
18. In `GPQAChainOfThoughtMetric`, read `\boxed{X}` and take the **last** answer statement, not the first; merge
    PR #4323 too. On HELM Capabilities' MMLU-Pro this credits 952 records and removes 133, and moves Gemini 2.5
    Flash-Lite from 54th to 27th. Re-check GPQA, which uses the same extractor, with the decrypted outputs.
19. Make FinQA's prompt and scorer agree: spell the table operations `table_max` etc. in HELM's instructions, show
    the `none` argument and `const_N`, or normalise both programs' arguments before `equal_program`. This credits 539
    right programs in HELM Finance and lowers none. Consider showing execution accuracy beside program accuracy.
20. Where a generation prompt numbers its labels (BANKING77 in HELM Finance; the RAFT prompts it was copied from),
    either drop the numbers, which served only the RAFT paper's probability scoring, or map a leading list number to
    its label before scoring. In HELM Finance this credits 398 right answers and lowers none; it moves Llama 3
    Instruct 70B from 11th to 7th. HELM Classic's RAFT columns use the same lists and were not measured.
21. Score a k-sample generation column on one decoding regime for every model: report single-sample accuracy (the
    mean over the returned completions) or any-of-k, not the highest-log-probability completion, which is a
    best-of-five pick only for APIs that return log probabilities. Show the scored completion on the prediction page.
22. Read full ICD-10 codes, including ICD-10-PCS procedure codes and lettered extensions, in the MIMIC-IV Billing Code
    metric, or state that it scores diagnosis categories only (audit 114).
23. Set `max_tokens` explicitly in every generation run spec: ConvFinQACalc inherits the 5-token default while FinQA
    and KPI-EDGAR allow 100 (audit 117); on its validation golds the default caps a digit-splitting model at 0.644.

## Across audits 90-101, 103, 105 and 107-109: what a bug report should carry (added 2026-11-11, updated 2026-11-13)

- **The gate held everywhere it was applied.** In the thirteen audits that grade individual records (90-94, 96,
  99-101, 103, 105, 107, 109), our transcriptions reproduce **2,693,514** published per-instance records; audits 95, 97
  and 98 reproduce every run-level number or cell they include, and audit 108 matches all 3,080 judge labels to HELM's
  stored stats and all 22 cells.
- **Pre-registration record:** **103 of 126** predictions held (audit 98 counted as v2). Of the 23 failures, 3 were
  inclusion gaps in our own code (P1 of 93, 94 and 97), 5 were audit 98's predictions of drops that never happened,
  and 15 were effects we guessed wrong (most recently audit 103's P6, the order moved far more than predicted, and
  P7). Separately, audit 102's first run stopped before grading on a gap in our code (a 5,760-digit number); it is not
  counted until it is graded.
- **Severity in code is not effect on the archive.** Four of the eleven open HELM issues we tested (#4374, #4363,
  #4345, #4344) change no published number in the releases checked, and #4358 changes 20 predictions. The largest
  effects we found (audits 99 and 100: 49,376 wrong credits together; audit 101: 2,949 right answers scored 0) had no
  issue before MV2's own (#4381 for audit 99, #4382 for audits 100 and 101), and audit 103's (48 of 67 WikiFact
  models moving 3 or more places on a common footing) has none yet. Open PR #4323 fixes a real dead regex that recovers 63 MMLU-Pro records, while the first-match
  and boxed-answer rules beside it cost 889 more. A scorer bug report that states how many published grades it changes
  (for example "N of M records in release vX") lets maintainers triage, and HELM's per-instance archive makes that a
  one-run count.
- **One metric, two directions.** `exact_match_indicator` over-credits Dyck (59.8% of credits are wrong sequences)
  and under-credits GSM8K (2,949 right answers scored 0) in the same release. Checking a metric on one column says
  little about another column that uses it.
- **Format habits concentrate on a few models.** On the current MMLU-Pro column, 51 of 67 models are within 0.01 of
  their stated-answer score, while two Gemini 2.5 models lose 0.24 and 0.18. On BANKING77, 15 of 22 models never
  answer with a list number while Llama 3 Instruct 8B loses 17 points that way. An average over models hides this; a
  per-model count of "no answer extracted" shows it at once (324 for Gemini 2.5 Flash-Lite against 0 to 5 for each
  Claude 4 and GPT-5 model).
- **The prompt can contradict the scorer.** In FinQA, HELM's own instructions spell `table-max`, which its scorer
  rejects; 625 records follow the instructions. In BANKING77, the prompt numbers the labels and the scorer reads only
  their text. A test that runs each prompt's own examples, and its own list formats, through its scorer would catch
  both.
- **The API can decide the score.** In WikiFact the same metric is a best-of-five pick for models whose API returns
  log probabilities and a single random draw for those that return zeros; 48 of 67 models move 3 or more places on a
  common footing. A column that samples more than once should record which regime each model got.
- **A level can be wrong while the order is right.** In audit 108 a fifth of FinanceBench's questions are asked
  without a page they need, which lowers every model's score by about 0.10 to 0.16 but moves no model 3 places. A
  leaderboard user comparing models is barely affected; one reading the number as "how well a model answers from the
  filing" is.
- **A desk check, not an audit:** HELM issue #4379 (DecodingTrust OOD-knowledge accuracy always 0, filed 2026-11-10)
  concerns a metric whose suite is not among the 26 top-level folders of HELM's public results bucket
  (crfm-helm-public, listed 2026-11-11), so we know of no published HELM leaderboard number it changes. Audits 114,
  116 and 117 (section 18) are the same kind: the mechanism is certain from the code, its effect on published scores is
  unmeasured. For audit 117 a count on the real golds now bounds it: a model whose tokenizer splits digits cannot score
  above 0.644 there, whatever it knows.
