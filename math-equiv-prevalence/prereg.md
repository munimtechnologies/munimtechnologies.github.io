# Pre-registration: how often do the math-equiv hazards touch the real MATH gold answers?

Written 2026-10-20 (UTC), before any count below was computed. Research by MV2 of Munim, Inc.,
made with AI agents working in his name.

## Question

`math-equiv-hazards` (published at
github.com/munimtechnologies/munimtechnologies.github.io/tree/main/math-equiv-hazards) shows
five mechanisms by which the Hendrycks MATH answer-equivalence check (`strip_string` /
`is_equiv`, as used by lm-evaluation-harness `hendrycks_math` and verl's MATH reward) misscores
answers. It says plainly that it is a mechanism corpus, not a prevalence study. This study
measures how many of the **12,500 real MATH gold answers** are exposed to each mechanism.
It still measures exposure, not how often models actually trigger the hazards.

## Data

All 12,500 MATH problems, as redistributed (MIT) in openai/prm800k `prm800k/math_splits/`
`train.jsonl` (12,000) + `test.jsonl` (500), de-duplicated by `unique_id`. Gold = the
lm-evaluation-harness extraction `remove_boxed(last_boxed_only_string(solution))`; a problem
whose gold cannot be extracted is counted and excluded. The checker is the published
`math_equiv.py` (pinned upstream commits in its header); the job records whether its local
copy is byte-identical to the published one.

Disclosure: before writing this, the agent saw the `answer` field of the first 20 records of
`test.jsonl` (none contains `\text{ ` with a space). Nothing else was looked at.

## Measures (L = lm-evaluation-harness variant, C = original/verl catch-all variant)

- M0 control: `is_equiv(g, g)` for every gold g, both variants.
- M1 normalization disabled: `strip_string(g)` raises, so `is_equiv` falls back to raw string
  equality for every prediction scored against g. Counted per variant, with exception type.
  `M1_L - M1_C` = golds hit only by the narrowed `except` (group D).
- M2 unit-stripping trigger (group A): g contains `\text{ ` after the `\\`->`\` collapse.
  M2a: exactly one occurrence (the text after it is discarded). M2b: the discarded tail
  contains the whole word `or` or `and` (non-unit content discarded). M2c: two or more
  occurrences (assert fails -> M1). Every M2 gold is listed with its tail.
- M3 leading space (group B): `is_equiv(" " + g, g)` is False.
- M4 trailing space control: `is_equiv(g + " ", g)` is False (only expected for M1 golds).
- M5 `\frac`->`\dfrac` control: for golds containing `\frac`, `is_equiv` of the `\dfrac`
  rewrite is False (only expected for M1 golds).
- M6 slash form (group C): for golds matching `^-?\\[dt]?frac\{\d+\}\{\d+\}$`, the rewrite
  `[-]a/b` is accepted? Reported separately for positive and negative golds.

Secondary breakdown (same measures, not separately predicted): the 5,000 problems of the
original MATH test split (`unique_id` starting `test/`), which is what `hendrycks_math`
evaluates. Exploratory, labelled as such: how often prm800k's own `answer` field is not
`is_equiv` to the harness-extracted gold.

## Predictions (graded HIT/MISS in the write-up; every number is reported either way)

- P1: M2 <= 3% of extractable golds.
- P2: M2b >= 1 (at least one gold where an incomplete answer would be credited).
- P3: M1_L <= 1% of golds, and M1_L >= M1_C.
- P4: M6 acceptance >= 99% for positive integer-fraction golds and exactly 0% for negative
  ones, with at least 50 negative integer-fraction golds.
- P5: M3 between 0.1% and 3% of golds.
- P6: M0 is True for 100% of golds in both variants.

## Limits stated in advance

Exposure is not prevalence of misscoring: a gold exposed to a hazard only costs a model
points if the model writes its answer in the triggering form. Hand labels (unit vs non-unit
tails) are by AI agents, not independent humans. MATH is MIT-licensed; only `unique_id`s
and short gold strings are republished.
