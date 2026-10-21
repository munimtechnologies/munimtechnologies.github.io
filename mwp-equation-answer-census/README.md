# mwp-equation-answer-census

Part of the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of
Munim, Inc. A small, reproducible census that isolates a single mechanism by which the data
behind a benchmark score can be wrong — here, released **annotations that are internally
inconsistent** — reproduced from pinned upstream files and checkable with only the Python
standard library.

**Target:** the annotated `(equation, answer)` triples released with three widely used
math-word-problem (MWP) datasets — SVAMP, ASDiv-A and MAWPS — in the
`arkilpatel/SVAMP` repository (the Patel et al. 2021 release).

**Headline:** across **4,030** released problems, **9** carry an annotated equation that does
**not** evaluate to its own annotated answer — SVAMP **1 / 1,000** (0.1%), ASDiv-A **0 /
1,217** (0.0%), MAWPS **8 / 1,813** (0.44% of evaluable). Every one is evaluable; none is a
parse failure. A 10-case pre-registered synthetic corpus pins the evaluators first.

## The mechanism

Each MWP dataset ships, per problem, an annotated arithmetic **equation** and an annotated
numeric **answer**. If you simply evaluate the equation over its own numbers and it does not
equal the stated answer, the released annotation is internally inconsistent — independent of
any model, and independent of whether the *word problem* is solvable. This census does exactly
that, in two annotation formats:

- **SVAMP** (`SVAMP.json`): `Equation` is an **infix** expression over literal numbers, e.g.
  `( 76.0 - 25.0 )`. Parsed with `ast` and walked over a whitelist of `+ - * /` and unary
  `+ -` only — never Python `eval`.
- **ASDiv-A and MAWPS** (the cross-validation CSVs under `data/cv_asdiv-a/` and
  `data/cv_mawps/`): `Equation` is in **prefix** (Polish) notation over `numberK` tokens, e.g.
  `- number0 number1`, with a space-separated `Numbers` column. Evaluated with a small stack
  machine.

A triple is **match** if the computed value equals the answer to `1e-3` absolute **or**
relative tolerance, **mismatch** if it evaluates to a different number, and **unevaluable**
only if it cannot be evaluated at all (parse error, bad token, division by zero, missing
slot). Within each dataset, triples are de-duplicated by `(equation | numbers | answer |
question)` so a repeated annotation is counted once.

## What was found

### Synthetic corpus (10 pre-registered cases)

| id | notation | equation | numbers | answer | expected |
|----|----------|----------|---------|--------|----------|
| S1-infix-match | infix | `( 76.0 - 25.0 )` | — | 51 | match |
| S2-infix-nested-match | infix | `( ( 3.0 + 4.0 ) * 2.0 )` | — | 14 | match |
| S3-infix-mismatch | infix | `( 2.0 + 2.0 )` | — | 5 | mismatch |
| S4-infix-div-match | infix | `( 10.0 / 4.0 )` | — | 2.5 | match |
| P1-prefix-match | prefix | `- number0 number1` | 18, 10 | 8 | match |
| P2-prefix-order-match | prefix | `- number1 number0` | 11, 12 | 1 | match |
| P3-prefix-mul-match | prefix | `* number0 number1` | 3, 4 | 12 | match |
| P4-prefix-mismatch | prefix | `+ number0 number1` | 2, 3 | 6 | mismatch |
| P5-prefix-divzero-unevaluable | prefix | `/ number0 number1` | 5, 0 | 2 | unevaluable |
| P6-prefix-literal-match | prefix | `* number0 2` | 5 | 10 | match |

`n_cases = 10, n_match = 7, n_mismatch = 2, n_unevaluable = 1, all_reproduced = true`.
Division by zero is deliberately classed `unevaluable`, not `mismatch`, so the census never
counts a formatting artefact as an inconsistency. Every verdict was hand-traced against
`mwp_eval.py` before anything ran; the sealed job re-derives the aggregate and asserts it
equals this target.

### Census on the released data

| dataset | total | evaluable | mismatch | unevaluable | mismatch rate (of evaluable) |
|---------|------:|----------:|---------:|------------:|-----------------------------:|
| SVAMP | 1,000 | 1,000 | 1 | 0 | 0.100% |
| ASDiv-A | 1,217 | 1,217 | 0 | 0 | 0.000% |
| MAWPS | 1,813 | 1,813 | 8 | 0 | 0.441% |

A few of the inconsistent triples (equation evaluated over its own numbers vs. its own
annotated answer):

- SVAMP: *"Rachel's tree had 4 apples…"* — `( ( 4.0 - 2.0 ) + 3.0 )` computes **5**, annotated
  answer **1**.
- MAWPS: *"James has number0 balloons. Amy has number1 balloons. How many more…"* —
  `- number0 number1` over `[1222, 513]` computes **709**, annotated answer **208**.
- MAWPS: *"One stamp costs number0 cents…"* — `* number0 number1` over `[34, 4]` computes
  **136**, annotated answer **134**.
- MAWPS: *"Mrs. Hilt bought a notebook for $ number0 … paid with nickels…"* — `/ number0 5.0`
  over `[1.3]` computes **0.26**, annotated answer **26**.

The full list of all 9 with their heads, equations, numbers, computed values and annotated
answers is in `results.json`.

## What this is and is not

- It **is** an exact, reproducible internal-consistency check of the released
  `(equation, numbers, answer)` triples: a mismatch means the three fields do not cohere.
- It is **not** a claim about which field is wrong (the equation, the number parse, or the
  answer), nor about whether the underlying word problem is solvable, nor about any model's
  accuracy. It says only that the released annotation does not evaluate to its own answer.
- The rates are small, as they should be for curated datasets — this is a *floor* on
  annotation noise in benchmarks that are used to rank models by exact-match on the answer,
  measured transparently rather than assumed to be zero.

## Prior art, and why this is new

SVAMP, ASDiv and MAWPS are heavily studied as *task* benchmarks, and audit #3 in this
catalogue checked the self-consistency of *worked solutions* for GSM8K / AQuA-RAT / MathQA.
What this census adds is a single, format-aware evaluator run over the released equation
annotations of these three MWP datasets together, evaluating each equation over its own
numbers and reporting every triple whose result does not equal its own stated answer, with the
offending examples enumerated. We found no prior write-up that does this unified check and
publishes the inconsistent triples.

## Files

- `mwp_eval.py` — the two safe evaluators (`eval_infix` via `ast`, `eval_prefix` stack
  machine), tolerance and the `classify` verdict. Apache-2.0.
- `cases.py` — the 10 pre-registered labelled cases and the target. CC BY 4.0.
- `test_mwp_eval.py` — stdlib `unittest`; each case must reproduce its verdict and the
  aggregate must match the target.
- `job.py` — the sealed compute job: asserts the corpus, downloads the three released files,
  de-duplicates and runs the census.
- `results.json` — the sealed run's output (corpus + per-dataset counts + every mismatch).

Reproduce: `python -m unittest -v` then `python job.py` (the census step needs network to
fetch the three released files from `raw.githubusercontent.com/arkilpatel/SVAMP`; the corpus
assertion needs no data).

## Limits, honestly

Three datasets, one consistency check. The synthetic corpus is small and hand-labelled; its
verdicts were traced by AI agents working in MV2's name, not by an independent human reviewer.
Prefix evaluation trusts the released `Numbers` column and token indices; a mismatch that
traced to a malformed `Numbers` cell rather than a wrong answer would still be a real defect in
the released row, but the census does not attribute blame between the fields. Counts are exact
for the pinned files fetched at run time and say nothing about other MWP releases.

## Licence

Code is Apache-2.0. The labelled corpus (`cases.py`), `results.json` and this write-up are
CC BY 4.0. The underlying datasets keep their own licences (the `arkilpatel/SVAMP` release).
Work by AI agents working in MV2's name (Munim, Inc.).
