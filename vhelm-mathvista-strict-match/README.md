# vhelm-mathvista-strict-match (audit 119)

**Status: pre-registered 2026-11-14, before the sealed run. Results will be added below the Licence section; this
part stays as written.**

VHELM, HELM's vision-language leaderboard, reports MathVista (Lu et al., "MathVista: Evaluating Mathematical
Reasoning of Foundation Models in Visual Contexts", [arXiv 2310.02255](https://arxiv.org/abs/2310.02255)) under
Reasoning. HELM's public archive holds suite v2.1.2 runs for 51 models on MathVista's testmini split, in 4 grades x 2
question types (407 runs; one high-school multiple-choice run is missing). This audit looks at the 204 **free-form**
runs, where the answer is a number. It asks how many answers strict exact match leaves uncredited that a
numeric comparison, or MathVista's own scorer, would credit, and how many answers are cut off by the token cap.

The work is carried out by AI agents working in MV2's name (MV2 of Munim, Inc.).

## What is certain before the run (from code)

- **The prompt drops MathVista's hint.** HELM's `MathVistaScenario` (`math_vista_scenario.py`, stanford-crfm/helm
  main, read 2026-11-14) sends the dataset's `question` field and the image. MathVista's `query` field, which
  starts with a "Hint:" line telling the model to give an integer, or a floating-point number with one or two
  decimal places (with examples), and which ends with the unit (for example "(Unit: g)"), is not used. The run spec
  adds only "Just give the numerical answer without showing the steps, the unit, or percentage symbol." So for a
  float gold the model is never told how many decimals the answer must have.
- **The scorer is strict.** `get_math_vista_spec` (`vlm_run_specs.py`) uses `max_tokens=20` (the short-answer
  default) and the VHELM schema's main metric for math_vista is `exact_match`: `gold.strip() == pred.strip()`,
  best over the correct references. With a unit, HELM adds a second reference `"<answer> <unit>"`. There is no
  numeric tolerance, no rounding and no answer extraction. MathVista's own scorer (`evaluation/calculate_score.py`)
  extracts an answer and then compares `str(int(float(x)))` for integer golds and `str(round(float(x), precision))`
  for float golds.
- **Gold kinds.** By the Hugging Face dataset viewer's statistics for `AI4Math/MathVista` testmini, the 460
  free-form questions have 418 integer, 40 float (20 with one decimal, 20 with two) and 2 list golds.

## What we already looked at (so it is not predicted)

Before writing this, we read by hand (WebFetch) all stored answers and golds of one run (GPT-4o 2024-11-20,
college: 57 questions, 20 credited; 17 float golds, 1 credited; no answer was a format-only miss; two answers hit
the 20-token cap) and the stored answers of a second run (Llama 4 Scout, elementary school: 151 questions, 48
credited, 8 answers cut at the 20-token cap while starting a step-by-step solution, and a few answers such as a
thousands-separated number and a number with a trailing zero, whose golds we did not read). We also read one run
spec and the first 12 rows of the dataset.

## Checks (not counted as predictions)

- **C1.** The free-form ids in the four grades sum to 460, with gold kinds close to 418 integer, 40 float and 2 list.
- **C2.** No sent question contains MathVista's "Hint:" line.

## Classes for every answer that `exact_match` does not credit

In order: `empty`; `nonnumeric_gold` (the list golds); `num_equal` (after format-only cleaning, meaning LaTeX or
markdown wrappers, one trailing period, %, degree signs, a leading currency $, a unicode minus, the instance's own
unit word and thousands separators, the answer is one number equal to the gold, e.g. `4.50` for `4.5`);
`rounds_to_gold` (a float gold with d decimals; the answer is one number with more than d decimals and MathVista's
`str(round(float(x), d))` gives the gold, e.g. `0.617` for `0.62`); `int_trunc_official` (an integer gold that
MathVista's `str(int(float(x)))` reaches from a non-integer answer, e.g. `2.7` for `2`; reported, never counted as
credit); `wrong_number`; `last_number_equal` (free text whose last number equals the gold: an upper bound, since
the text may say something else); `no_number`; `other`. Separately, an answer is at the cap when its stored
output-token count reaches the run's `max_tokens`.

The **lenient** score counts `exact` + `num_equal` + `rounds_to_gold`.

## Predictions (frozen)

- **P1 (gate).** All 204 free-form runs are listed, at least 95% of them are included (every stored per-record
  `exact_match` and the `stats.json` mean reproduced by our transcription, and the stored instance count matched),
  and at least 48 of the 51 models have all four grades included.
- **P2.** Pooled over the included runs, at least 50 answers are `num_equal`.
- **P3.** `num_equal` plus `rounds_to_gold` is at most 3% of all included answers (the loss from format alone is
  small in aggregate).
- **P4.** At least 20 answers are `rounds_to_gold`.
- **P5.** Among answers to float golds that are one number, at least 20% have a different number of decimals than
  the gold.
- **P6.** At least 10 of the complete models have 2% or more of their free-form answers at the token cap.
- **P7.** Kendall's tau-b between the models' free-form `exact_match` and lenient scores is at least 0.90.
- **P8.** At least one model gains 3 or more percentage points on free-form questions under the lenient score.

A prediction is graded HELD or FAILED by `grade119.verdicts()`; anything our code cannot compute is reported as NOT
GRADED.

## Method

`job.py` lists `vhelm/benchmark_output/runs/v2.1.2/math_vista:*` in the public bucket, keeps the `free_form` runs,
downloads `run_spec.json`, `instances.json`, `display_predictions.json` and `stats.json` for each, re-scores each
answer with HELM's `exact_match` (transcribed in `grade119.py`), classifies every uncredited answer as above, and
compares models. `test_grade119.py` holds 15 unit tests on synthetic records. Standard library only.

## Prior art

- HELM's issues and pull requests mention neither `math_vista` nor `mathvista` (GitHub search, 2026-11-14).
- The same class of problem was reported for another harness: UK AISI inspect_evals issue
  [#2711](https://github.com/UKGovernmentBEIS/inspect_evals/issues/2711) (2026-10-16, open) says its MathVista
  scorer compares free-form numbers as strings (`1.20` vs `1.2`), and PR
  [#2748](https://github.com/UKGovernmentBEIS/inspect_evals/pull/2748) (closed unmerged) proposed MathVista's
  normalisation. What this audit adds is HELM's version of it (where, unlike inspect_evals, the precision hint
  itself is not sent) and the measurement on VHELM's stored answers.

## Limits

- One suite (v2.1.2), free-form questions only; the multiple-choice half of MathVista is not re-scored. We do not
  rebuild VHELM's leaderboard (we found no release index in the bucket); we compare per-run means stored in
  `stats.json` and per-model pools of the four free-form runs.
- A float gold's precision is read from its own decimals (MathVista stores the answer at that precision).
- `num_equal` cleaning is narrow on purpose; an LLM extractor such as MathVista's would credit more, so the lenient
  score is a lower bound on what MathVista's own pipeline would credit, and `last_number_equal` is an upper bound.
- Only run names, instance ids, classes, counts and public model names are published.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out
```

## Licence

Code is Apache-2.0; the transcribed HELM function keeps HELM's Apache-2.0 licence, and the two normalisation lines
follow MathVista's evaluation code (lupantech/MathVista). This write-up is CC BY 4.0.
Made with AI agents working in MV2's name (Munim, Inc.).
