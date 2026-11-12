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

Folder: [helm-dyck-last-token](../helm-dyck-last-token/). No HELM issue reported this.
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

Folder: [helm-gsm-classic-indicator](../helm-gsm-classic-indicator/). No HELM issue reported this (#4337 is about
HELM Lite's other GSM8K metric).
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

## 14. Recommendations for re-scoring HELM (so far)

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

## Across audits 90-101 and 108: what a bug report should carry (added 2026-11-11, updated 2026-11-12)

- **The gate held everywhere it was applied.** In the nine audits that grade individual records (90-94, 96, 99-101),
  our transcriptions reproduce 1,458,302 published per-instance records; audits 95, 97 and 98 reproduce every
  run-level number or cell they include, and audit 108 matches all 3,080 judge labels to HELM's stored stats and all
  22 cells.
- **Pre-registration record:** 74 of 94 predictions held (audit 98 counted as v2). Of the 20 failures, 3 were
  inclusion gaps in our own code (P1 of 93, 94 and 97), 5 were audit 98's predictions of drops that never happened,
  and 12 were effects we guessed wrong.
- **Severity in code is not effect on the archive.** Four of the eleven open HELM issues we tested (#4374, #4363,
  #4345, #4344) change no published number in the releases checked, and #4358 changes 20 predictions. The two largest
  over-credits we found (audits 99 and 100: 49,376 wrong credits together) and audit 101's under-credit (2,949
  right answers scored 0) had no issue before MV2's own (#4381, for audit 99). A
  scorer bug report that states how many published grades it changes (for example "N of M records in release vX")
  lets maintainers triage, and HELM's per-instance archive makes that a one-run count.
- **One metric, two directions.** `exact_match_indicator` over-credits Dyck (59.8% of credits are wrong sequences)
  and under-credits GSM8K (2,949 right answers scored 0) in the same release. Checking a metric on one column says
  little about another column that uses it.
- **A level can be wrong while the order is right.** In audit 108 a fifth of FinanceBench's questions are asked
  without a page they need, which lowers every model's score by about 0.10 to 0.16 but moves no model 3 places. A
  leaderboard user comparing models is barely affected; one reading the number as "how well a model answers from the
  filing" is.
- **A desk check, not an audit:** HELM issue #4379 (DecodingTrust OOD-knowledge accuracy always 0, filed 2026-11-10)
  concerns a metric whose suite is not among the 26 top-level folders of HELM's public results bucket
  (crfm-helm-public, listed 2026-11-11), so we know of no published HELM leaderboard number it changes.
