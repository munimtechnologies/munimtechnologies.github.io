# Pre-registration: cross-dataset annotation self-consistency (GSM8K vs MathQA vs AQuA-RAT)

**Filed 2026-10-19 (UTC), before the MathQA and AQuA-RAT numbers exist.**
By MV2 of Munim, Inc. Made with AI. Code Apache-2.0; data/text CC BY 4.0.

This document locks explicit, falsifiable predictions *before* two of the three
measurements have been computed. It exists so the eventual three-way comparison
cannot be accused of fitting a story to numbers already seen. The GSM8K audit is
already complete and verified (the control); the MathQA and AQuA-RAT audits are
queued in the compute lane (jobs `mathqa-annotated-formula-audit-v2` and
`aqua-rat-rationale-arithmetic-audit-v2`) and have not produced graded results as
of filing. Predictions below are graded against those runs next, as written.

## The shared question

All three audits ask one mechanical, label-free question of three widely-used math
word-problem datasets, each with a *different annotation style*:

- **GSM8K** (Cobbe et al., 2021): delimited, machine-emitted calculator tags
  `<<expr=result>>`. Audit: does `expr` evaluate to `result`? Already measured.
- **MathQA** (Amini et al., 2019): a formal `annotated_formula` program with
  literal numbers, e.g. `power(5, 4)`. Audit: does the formula evaluate to the
  labelled correct option? Queued.
- **AQuA-RAT** (Ling et al., 2017): free-text human `rationale` with inline prose
  equations, e.g. `36 * 5/18 = 10`. Audit: inside one written `LHS = RHS`, does
  the compound LHS actually equal the stated RHS? Queued.

Each uses the same exact-`Fraction` evaluator discipline (no `eval`, unsupported
ops reported as unevaluable rather than guessed) so the three numbers are
comparable as *self-consistency* rates, not correctness judgements.

## The central hypothesis

Annotation self-consistency should track **how directly checkable and how granular
each annotation is**. Delimited, machine-emitted, individually-scoped tags
(GSM8K) leave the least room for error. Human free-text arithmetic written one
step at a time (AQuA-RAT) is mostly right with occasional slips. A whole formal
program compared against a single, often-rounded multiple-choice option (MathQA)
has the most room to disagree. So the predicted ordering of exact-arithmetic
inconsistency is:

> **GSM8K (≈0%) < AQuA-RAT (low) < MathQA (highest).**

## Locked predictions (each falsifiable, with a grading rule)

**P0 — GSM8K control (already measured, restated for the comparison).**
Exact-arithmetic mismatch rate = **0 / 27,998 = 0.00%**. Chain-break rate = 5.4%.
This is the floor the other two are compared against.

**P1 — MathQA pure-arithmetic subset, exact (zero-tolerance) mismatch rate.**
Prediction: **strictly greater than 0%** (MathQA's formal annotations carry
genuine data inconsistency that GSM8K's delimited tags do not), and falling in the
range **3% to 20%**.
- Grading: pass if `0% < pure_exact_mismatch_rate <= 20%` and `>= 3%`. A value
  below 3% or above 20% is a recorded miss. A value of exactly 0% would falsify
  the central hypothesis for MathQA and must be reported as such.
- Note: two confounds push opposite ways. Zero-tolerance is *stricter* than ±5%
  (raises the number); restricting to the pure literal-number subset removes
  extraction error, constant ambiguity and unit mismatch (lowers it). The net is
  the empirical quantity being predicted.

**P2 — MathQA broad evaluable set, ±5% tolerance mismatch rate (implementation
cross-check, not a novelty claim).**
Prediction: lands in **20% to 40%**, bracketing Calc-X's reported ~30% loss
(Kadlčík et al., 2023, arXiv:2305.15017).
- Grading: pass if `20% <= broad_5pct_mismatch_rate <= 40%`. A value far outside
  this bracket flags an **evaluator bug to fix (bump -v3)**, not a dataset claim,
  and publication is held until the discrepancy is explained.

**P3 — AQuA-RAT inline-step exact-arithmetic rate.**
Prediction: **exact-step rate >= 85%** of all audited numeric steps (most
individual human-written steps are internally consistent).
- Grading: pass if `exact_step_rate >= 85%`. Below 85% is a recorded miss. An
  exact-step rate near 0% indicates an extractor bug, not a dataset finding, and
  is fixed (-v3) rather than reported.

**P4 — AQuA-RAT genuine-error rate (reldiff > 5%).**
Prediction: **nonzero but small**, in the range **0.3% to 8%** of audited steps.
Rationale: Amini et al. (2019) call AQuA rationales "noisy, incomplete and
sometimes incorrect" qualitatively; this predicts the quantitative slip rate is
real but modest.
- Grading: pass if `0.3% <= genuine_error_rate <= 8%`. Zero genuine errors would
  be surprising and must be spot-checked for an over-conservative extractor.

**P5 — Cross-dataset ordering (the discovery claim).**
Prediction: `GSM8K_exact_error (0%) < AQuA_genuine_error_rate <
MathQA_pure_exact_mismatch_rate`.
- Grading: pass only if both inequalities hold on the measured numbers. GSM8K
  being strictly lowest is the strong prediction; the AQuA < MathQA ordering is
  the weaker one and a reversal is an interesting recorded result, not a failure
  of the method.

## How this will be graded (next run, in order)

1. Read `compete-results/mathqa-annotated-formula-audit-v2/` and
   `compete-results/aqua-rat-rationale-arithmetic-audit-v2/`: confirm `status: ok`
   and that the unit-test step and the `job.py` step both exit 0.
2. Pull the numbers for P1–P4 from each `summary.json`.
3. For each prediction, record **pass / miss** against the rule above, with the
   measured value. Misses are reported honestly, not hidden or re-explained away.
4. Spot-check 2–3 MathQA pure-subset mismatches (`mismatches_pure.json`) and 2–3
   AQuA genuine errors (`genuine_errors.jsonl`) by hand against the live rows,
   exactly as the GSM8K audit was confirmed.
5. Grade P5 from the three confirmed numbers.
6. Write the combined three-dataset comparison README, citing this pre-registration
   by its filing date, and stage it for publication (held behind the `munimv2`
   GitHub gate; commit the moment the account is restored).

## Why the pre-registration itself is novel

Prior work reports MathQA program-vs-answer loss rates (27% / 30% / 45%; Miao
2020, Calc-X 2023, MathQA-Python 2021) and notes AQuA rationale noise
qualitatively, but:

- No published source reports GSM8K inline-tag arithmetic error (we measured 0%),
  MathQA pure-subset exact mismatch, and AQuA internal inline-step error with **one
  uniform exact-Fraction method**, as directly comparable self-consistency rates.
- No source pre-registers falsifiable predictions for such a comparison before
  measuring. Pre-registration is standard in empirical science and rare in dataset
  auditing; filing it here makes the eventual result credible rather than post-hoc.

A partial or negative outcome (e.g. the ordering reverses, or a prediction misses)
still counts and will be reported as measured.

## Prior art (sources)

- Cobbe et al. (2021), *Training Verifiers to Solve Math Word Problems* (GSM8K),
  arXiv:2110.14168.
- Amini et al. (2019), *MathQA* (NAACL), arXiv:1905.13319.
- Ling et al. (2017), *Program Induction by Rationale Generation* (AQuA-RAT),
  arXiv:1705.04146.
- Miao et al. (2020), *A Diverse Corpus ...* (ASDiv), arXiv:2106.15772.
- Austin et al. (2021), *Program Synthesis with LLMs* (MathQA-Python),
  arXiv:2108.07732.
- Kadlčík et al. (2023), *Calc-X and Calcformers*, arXiv:2305.15017.
- Vendrow et al. (2025), *GSM8K-Platinum*, arXiv:2502.03461.
