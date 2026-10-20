# math-equiv-hazards

A dependency-free, labeled and execution-checked set of cases where the **Hendrycks MATH
answer-equivalence check** (`strip_string` / `is_equiv`) gives a score that disagrees with
what the answer actually says.

The same function scores MATH in EleutherAI's lm-evaluation-harness (`hendrycks_math`) and
computes the MATH reward in verl, and it has been copied into many other evaluation and RL
codebases. It is pure standard library, so every case here can be reproduced exactly.

Pinned upstream sources:

| copy | commit | file |
|---|---|---|
| EleutherAI/lm-evaluation-harness | `d42a3e4` | `lm_eval/tasks/hendrycks_math/utils.py` |
| hendrycks/math (original) | `940d1bf` | `modeling/math_equivalence.py` |
| volcengine/verl | `d73e600` | `verl/utils/reward_score/math_reward.py` |

The three copies behave the same on every case here except one difference (group D).

## Findings

27 labeled cases, 14 of them hazards (`cases.json`). Each group has controls showing the
intended behaviour.

**A. Text after `\text{ ` is cut off, so hedged answers get credit (false positive).**
`remove_right_units` was written to drop units ("`\text{ ` only ever occurs ... when describing
units"). It keeps only what comes before the first `\text{ `. Any wording after it is thrown away:

| prediction | gold | scored |
|---|---|---|
| `2 \text{ or } 3` | `2` | **correct** |
| `x = 2 \text{ or } x = 3` | `2` | **correct** |
| `7 \text{ is a guess, the correct value is } 12` | `7` | **correct** |
| `2 \text{ or } 3` | `3` | wrong |
| `2 \text{ or } 3 \text{ or } 4` | `2` | wrong (3 pieces fail an `assert`; raw-string fallback) |
| `2 \text{ and } 3` | `2, 3` | wrong (a complete two-solution answer is cut to `2`) |

End to end, lm-evaluation-harness gives `exact_match = 1` to the response `So $x = 2 \text{ or }
x = 3$.` when the solution is `\boxed{2}`. verl's `compute_score` pays reward **1.0** for
`\boxed{2 \text{ or } 3}` when the ground truth is `2`.

**B. Whether `x =` is stripped depends on spacing (false negative).** The "remove `k = `" rule
checks that the left-hand side is at most 2 characters long, but it measures that *before*
spaces are removed. `x = 5` → `5`, but ` x = 5` (one leading space) → `x=5`. `xy=5` → `5`, but
`xy = 5` → `xy=5`. The harness takes the text between the first and last `$`, so
`The answer is $ x = 5$.` scores 0 and `The answer is $x = 5$.` scores 1.

**C. The decimal and slash rescues only work for positive values (false negative).** `1/2` →
`\frac{1}{2}` but `-1/2` → `\frac{-1}{2}`, while MATH golds are written `-\frac{1}{2}`.
`0.5` is rescued by an exact string test (`string == "0.5"`), so `-0.5` is not.

**D. In lm-evaluation-harness only, one `/` can switch off all normalization.** The
original's `_fix_a_slash_b` uses a bare `except:` and verl uses `except Exception`, but the
harness narrowed it to `except AssertionError`. When the string has exactly one `/` and a side
that is not an integer, `int()` raises `ValueError`. That error escapes to `is_equiv`, which then
compares the **raw** strings. So `\dfrac{3}{2}\text{m/s}` vs `\frac{3}{2}\text{m/s}` is wrong in
the harness and right in the original and in verl. The same pair without the `/` is right in all three.

**E. Deleting `\left`/`\right` as plain substrings merges arrows (false positive).** `\rightarrow`
and `\leftarrow` both normalize to `arrow`. This is rare in MATH answers; we include it for
completeness.

## Why this is new

* A 2026 category-level audit of RLVR verifiers ([arXiv:2609.01354](https://arxiv.org/abs/2609.01354))
  tested this normalizer (the "strip-string" verifier) and reported that it "judges everything
  and errs by rejecting". Its only false-positive probe was off-by-one answers, and it accepted
  0% of those. Group A is a false-positive class it did not cover. Groups B–E are exact
  mechanisms behind failures the audit reported only in aggregate, or did not report at all.
* Wrong *units* being credited is already known: OpenRLHF/OpenRLHF#1364 reports it for
  OpenRLHF's copy. It is included here as case A7 and credited. That report is about two
  different units; it does not cover hedges, self-corrections or the two-vs-three asymmetry.
* hendrycks/math#21 (percent sign handling) and lm-evaluation-harness issues #3116, #3477 and
  #3643 (boxed-answer extraction) are separate problems and are not repeated here.
* We found no report of the narrowed `except` in the harness (group D) or the spacing rule (group B).
  An Epoch AI port of MATH grading catches `ValueError` in its `fix_a_slash_b`, which avoids D.

## Limits

* We have not measured how often these cases appear in real model outputs or in MATH golds.
  This is a mechanism corpus, not a prevalence study.
* Group A is a grading error, not a reward hack in expectation. Only the *first* option
  is credited, so hedging earns the same expected reward as committing to that option. What
  goes wrong is that hedged and self-correcting answers are counted as correct and are never
  penalized.
* `semantically_correct` is a hand label meaning the prediction states the same single final
  answer as the gold. Some MATH problems also require a particular form, such as a common
  fraction.
* `math_equiv.py` reproduces the upstream behaviour faithfully but is not byte-identical.

## Reproduce

```
python -m unittest -v test_math_equiv_hazards.py
```

Standard library only.

## Upstream sources and licences

`math_equiv.py` is a behaviourally faithful transcription of the pure-Python functions in the
three pinned upstream copies above. Those functions remain under their own open-source
licences. Each project's own `LICENSE` file at the pinned commit is the authoritative text, and
carries the copyright notice that applies to the transcribed code:

* **EleutherAI/lm-evaluation-harness**, `LICENSE.md` at commit `d42a3e4` (copyright line:
  "Copyright (c) 2020 EleutherAI").
* **hendrycks/math**, `LICENSE` at commit `940d1bf` (copyright line: "Copyright (c) 2021 Dan
  Hendrycks").
* **volcengine/verl**, `LICENSE` at commit `d73e600` (Apache License 2.0, copyright Bytedance
  Ltd. and/or its affiliates).

Please keep these attributions with any copy of `math_equiv.py`.

## Licence of this work

MV2's additions in `math_equiv.py` (the `catch_all` switch, the comments, the tests) are
Apache-2.0, matching the repository `LICENSE`. The corpus (`cases.json`) and this write-up are
licensed CC BY 4.0.

*This research and write-up were made with AI, by MV2 of Munim, Inc. (mv2@munimtech.com).*
