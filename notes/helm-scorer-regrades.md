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

## 3. Audit 92: option collisions in HELM's multiple-choice mapping (pending)

## 4. Audit 93: empty outputs in AHELM's speech-recognition scores (pending)

## 5. Recommendations for re-scoring HELM (so far)

1. Grade the answer a model states, not only a fixed format: on MATH, accept an unboxed final answer; on GSM8K,
   compare final numbers by value.
2. Compare by value only after reduction (`8/22` should not match `4/11` where the problem asks for lowest terms).
3. Keep the "no extractable answer scores 0" fix (#4378) even though it changes no v1.13.0 MATH grade: it guards
   other levels and suites.
4. Publish per-instance scores, as HELM already does; that is what made these counts possible.
