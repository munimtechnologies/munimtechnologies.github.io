# Audit 110: HELM Long Context v1.0.0, two inherited scorer risks checked (a negative desk check)

Status: **desk check, 2026-11-12.** Read by hand from HELM's public archive, not pre-registered and not re-run in a
sealed container. A negative result: neither risk changes a published number in this release.

Part of [eval-reliability-audits](../eval-reliability-audits/) by MV2 of Munim, Inc. Made with AI agents working in
MV2's name.

## What was checked

HELM's Long Context leaderboard (release `v1.0.0`, 11 models, 5 run groups, 55 runs; files under
`gs://crfm-helm-public/long-context/benchmark_output/`) has two columns whose scorers were known to be risky.

1. **InfiniteBench En.MC ("EM").** The main metric is strict `exact_match` against the option letter, while
   InfiniteBench's own scorer (`compute_scores.py`, `get_score_one_longbook_choice_eng`) reads a letter out of answers
   like `(B)`, `**C**` or `The answer is D`. HELM changed the prompt in PR #3790 (2025-08-05) to ask twice for "only a
   single letter" and "no period", but left the metric alone. Question: do format misses cost any model points?
2. **RULER HotpotQA ("RULER String Match").** HELM's `RulerQAMetric` copies RULER's `string_match_part`: a record
   scores 1 if any gold answer, lower-cased, appears **anywhere** inside the lower-cased response. NVIDIA/RULER issue
   [#112](https://github.com/NVIDIA/RULER/issues/112) (open, 2026-09-23) shows that the gold `no` then matches inside
   `not`, `know` or `cannot`, so a refusal can score 1. It gives no counts. Question: do any of HELM's published credits
   come from that?

## Method

- En.MC: for each of the 11 runs, `stats.json` (split `test`, no perturbation): `exact_match`, `quasi_exact_match`,
  `quasi_prefix_exact_match`, `num_output_tokens`. If strict matching cost points, quasi-exact match would be higher.
- RULER HotpotQA: for each of the 11 runs, `display_predictions.json` (100 records each): every record scored 1 whose
  response contains the letters `no` in any case, then a check of whether the gold could be `no`. A response that is a
  bare `No` and scores 1 proves the gold is `no` (the gold must be a substring of `no`); a credited response that does
  **not** contain `no` proves the gold is not `no`.
- Every run's credit count was compared with the published cell.

## Results

**InfiniteBench En.MC: no effect.** In all 11 runs `exact_match` = `quasi_exact_match` = `quasi_prefix_exact_match`
(range 0.72 to 0.97, 100 questions each). Models wrote 1 to 2 output tokens on average (three providers report 0
tokens). The PR #3790 prompt seems to have worked; strict EM costs no model a point in this release.

| Model | EM = QEM = QPEM | Mean output tokens |
| --- | --- | --- |
| GPT-4.1 (2025-04-14) | 0.97 | 1.0 |
| Amazon Nova Premier | 0.92 | 1.0 |
| Llama 4 Maverick (17Bx128E) Instruct FP8 | 0.89 | 2.0 |
| Gemini 2.0 Flash | 0.87 | 0.0 (not reported) |
| Palmyra X5 | 0.87 | 0.0 (not reported) |
| Llama 4 Scout (17Bx16E) Instruct | 0.85 | 2.0 |
| Gemini 2.0 Flash Lite | 0.85 | 0.0 (not reported) |
| Amazon Nova Lite | 0.82 | 1.0 |
| GPT-4.1 mini (2025-04-14) | 0.82 | 1.0 |
| Amazon Nova Pro | 0.79 | 1.11 |
| GPT-4.1 nano (2025-04-14) | 0.72 | 1.0 |

**RULER HotpotQA: no false credit from `no` inside a word.**

- All 11 cells are reproduced from the records: 571 of 1,100 records score 1 (GPT-4.1 70, GPT-4.1 mini 64, Nova
  Premier 57, Palmyra X5 57, Gemini 2.0 Flash 55, Llama 4 Maverick 55, Gemini 2.0 Flash Lite 53, Llama 4 Scout 47,
  GPT-4.1 nano 41, Nova Pro 37, Nova Lite 35; each equals the published value times 100).
- 27 of the 571 credited responses contain the letters `no`. **14** answer one of two yes/no questions (ids `118` and
  `355`) and begin with the word `No`; bare `No` answers to both are credited, so both golds are `no`, and these 14
  credits are right. **13** contain `no` inside a longer answer: 10 give the same dialect answer to id `316`, and 3 are
  ids `45`, `144` and `289`. For `45`, `144` and `289` a credited response without the letters `no` (or a response
  containing `no` that scored 0) proves the gold is not `no`. For `316` this is inferred, not proved: 10 models giving
  the same specific dialect is not what a yes/no question produces.
- So **0 of 571 published credits** come from the mechanism in RULER #112. HELM samples 100 of RULER's questions, and
  only 2 of them have the gold `no`; every response to those two that scored 0 contains no `no` at all (otherwise it
  would have scored 1), so no refusal such as `not stated` or `I cannot tell` was given there.

**Seen on the way (post hoc, two runs only):** the opposite failure exists. GPT-4.1 mini answered both yes/no
questions with a correct explanation that never uses the word `no` (it names where each band came from, or what kind
of plant each genus is) and scored 0 on both. GPT-4.1 nano answered `Yes` to both and also scored 0. Containment
scoring cannot credit a right yes/no answer that does not say the word. Not counted across the other 9 runs.

## Limits

- Read by hand from the archive through a web reader, one pass per file; not re-run in a container and not
  pre-registered. The cell reproduction (571 = the sum of the published cells) is the main check that the reading is
  complete.
- Only the `no` mechanism was checked. Other short golds that can match inside longer words (numbers inside years, for
  example) were not.
- RULER SQuAD has no yes/no golds (RULER #112) and was not read. InfiniteBench En.Sum and OpenAI MRCR were not
  audited; HELM's MRCR metric matches OpenAI's published `grade` function line for line.

## Prior art

- NVIDIA/RULER #112 reports the mechanism in RULER itself, with an upper bound (19 of RULER's 500 HotpotQA golds are
  `no`) but no measured counts. Nothing we found measures it on HELM's leaderboard.
- HELM PR #3790 changed the En.MC prompt; HELM's issues mention no En.MC scoring problem.

## Licence

Text and numbers: CC BY 4.0. Authored by AI agents working in MV2's name (Munim, Inc.).
