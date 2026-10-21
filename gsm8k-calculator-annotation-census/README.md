# gsm8k-calculator-annotation-census

The 19th [eval-reliability audit](../eval-reliability-audits/). GSM8K annotates
each arithmetic step in a solution with an inline `<<expr=result>>` calculator
tag, and ends every solution with a `#### answer` line. Two self-consistency
questions follow from that format, and both are checked here against the full
released dataset (train + test, 8,792 solutions).

## The mechanism

Each `<<expr=result>>` tag asserts that `expr` evaluates to `result`. The census
re-evaluates every `expr` with an exact, AST-whitelisted arithmetic engine
(`+ - * /` over `Fraction`, so division is exact), then compares:

- **match** — the expression equals the stated result exactly;
- **rounded** — it equals the result only after rounding to the decimal places
  shown (e.g. `2/3 = 0.67`); counted separately, **not** as an error;
- **mismatch** — neither;
- **unparseable_expr / unparseable_result** — a side falls outside the
  arithmetic whitelist (integer `//` floor division, a bare fraction like `3/4`
  written as the result, etc.), counted rather than crashed on.

Separately, **final-answer consistency** asks whether the `#### answer` equals
the *last* `<<...>>` annotation's result. A mismatch is reported but is **not**
an error in GSM8K: the last tagged computation is often not the final step
(e.g. a percentage or a leftover-subtraction done in prose), so this count
measures how unsafe the common shortcut "read the answer off the last tag" is.

## What was found

### Annotation self-consistency

Across all 27,998 calculator annotations in train + test, **every single one
computes correctly**: 27,995 exact matches, 0 rounded, **0 mismatches**, and
only 3 unparseable (2 expressions, 1 result). GSM8K's step annotations are
arithmetically sound end to end.

| split | match | mismatch | rounded | unparseable_expr | unparseable_result |
|-------|------:|---------:|--------:|-----------------:|-------------------:|
| train | 23,714 | 0 | 0 | 2 | 0 |
| test  | 4,281  | 0 | 0 | 0 | 1 |

The three unparseable annotations are not arithmetic errors but notation the
whitelist refuses: `560//10` stated as `56` and `180//3` stated as `60` (both
train, integer floor-division, which do equal their results), and `3/4` written
as its own "result" string (test).

### Final-answer consistency

Of the 8,679 solutions that have both at least one annotation and a `#### answer`,
**470 (5.4%)** have a `#### answer` that differs from their last annotation's
result. Spot-checking confirms these are legitimate: the last tag is a sub-step,
not the conclusion. Examples (last-tag → the real answer is computed in prose
afterward):

- `16-4 = 12` → final answer is a *percentage* of the class in hip-hop dance;
- `300/5 = 60` → grams per serving, then multiplied for the calorie budget;
- `20-5 = 15` → Brian's remaining games, before Bobby's count is derived.

The lesson for anyone parsing GSM8K programmatically: the `#### answer` line is
authoritative; the last `<<...>>` tag is **not** a reliable proxy for it.

## Files

- `calc_eval.py` — the exact AST-whitelisted evaluator and the annotation /
  solution classifiers.
- `cases.py` — the pre-registered synthetic corpus (8 annotation cases + 3
  solution fixtures) and its frozen `TARGET` counts.
- `test_calc_eval.py` — unit tests asserting each case's label; run green in the
  sealed container before the census ran.
- `job.py` — the census driver over the released jsonl.
- `results.json` — frozen totals, per-split counts, and real examples.

## Limits

One dataset (GSM8K only). Rounding is reported separately and never as an error.
Thousands-separator commas are stripped before evaluation. Integer floor-division
(`//`) is intentionally outside the arithmetic whitelist, so the handful of `//`
tags are counted as unparseable rather than silently matched. Final-answer
"mismatch" is a format caveat, not a correctness defect in GSM8K.

## Licence

Code is Apache-2.0. The corpus, results and write-up are CC BY 4.0. Made by AI
agents working in MV2's name (Munim, Inc.).
