# math-equiv-prevalence

How often do the [`math-equiv-hazards`](https://github.com/munimtechnologies/munimtechnologies.github.io/tree/main/math-equiv-hazards)
mechanisms touch the **real MATH gold answers**?

`math-equiv-hazards` is a mechanism corpus: it shows *that* the Hendrycks MATH
answer-equivalence check (`strip_string` / `is_equiv`, as used by lm-evaluation-harness
`hendrycks_math` and verl's MATH reward) can misscore answers, and *how* each failure is
triggered. It does not say how common the triggers are. This study measures the **exposure** of
all 12,500 MATH gold answers to each mechanism — how many golds are written in a form that the
check mishandles. It is pre-registered: every prediction and method below was fixed in
[`prereg.md`](prereg.md) before any number was computed.

Exposure is **not** prevalence of misscoring. A gold exposed to a hazard only costs a model
points if the model writes its answer in the triggering form; this study does not run any model.

## Data

All 12,500 MATH problems, as redistributed (MIT) in `openai/prm800k`
(`prm800k/math_splits/train.jsonl`, 12,000 + `test.jsonl`, 500), de-duplicated by `unique_id`
(12,499 unique golds; 0 golds failed extraction). Gold = the lm-evaluation-harness extraction
`remove_boxed(last_boxed_only_string(solution))`. The checker is the published
[`math_equiv.py`](math_equiv.py); the job records that its local copy is **byte-identical** to
the published one (`sha256 94c4256a…`), so these counts are produced by exactly the code the
hazard corpus documents.

## Results (L = lm-evaluation-harness variant, C = original / verl catch-all variant)

All six pre-registered predictions **HIT**. Every number is reported either way.

| Measure | What it counts | Full set (12,499 golds) | Test split (5,000) |
|---|---|---|---|
| **M0** control | `is_equiv(g, g)` true | 12,499 / 12,499 (L and C) | 5,000 / 5,000 |
| **M1** normalization disabled | `strip_string(g)` raises → raw-string fallback | L = 2 (0.016%), C = 0 | L = 0, C = 0 |
| **M2** unit-strip trigger (group A) | gold contains one `\text{ ` (tail discarded) | 101 (0.808%) | 44 |
| **M2b** hedge risk | …and the discarded tail contains the word `or`/`and` | **6** | 3 |
| **M3** leading-space flip (group B) | `is_equiv(" "+g, g)` is false | L = 34 (0.272%), C = 32 | L = 15, C = 15 |
| **M4** trailing-space control | `is_equiv(g+" ", g)` is false | L = 2, C = 0 | 0 |
| **M5** `\frac`→`\dfrac` control | rewrite not accepted (of 1,964 `\frac` golds) | 0 | 0 |
| **M6** slash-form (group C) | integer-fraction golds accepting `a/b` | pos 1,389/1,389; neg 0/122 | pos 557/557; neg 0/58 |

**The six hedge golds (M2b).** For each, everything from the first `\text{ ` onward is dropped
before comparison, so only the part before it is matched — a partial or hedged answer can be
credited:

```
7, -2, \text{ and } -5     ->  kept: "7, -2, "
-12 \text{ or } -30        ->  kept: "-12 "
12\text{ and }13           ->  kept: "12"
-2 \text{ or } -12         ->  kept: "-2 "
2, 3, \text{ and } 4       ->  kept: "2, 3, "
19 \text{ and }43          ->  kept: "19 "
```

Three of these (`7, -2, \text{ and } -5`, `12\text{ and }13`, `19 \text{ and }43`) are in the
500-problem test split that `hendrycks_math` scores.

**M1 (normalization disabled).** Two golds raise inside `strip_string` in the harness variant
and fall back to raw string comparison: `12^{1/7}` and `\begin{pmatrix} 0 \\ 1/11 \end{pmatrix}`
(both `ValueError` from the narrowed `except` in `_fix_a_slash_b`, group D). Neither is in the
test split. M4 flags exactly these two and no others, as expected.

**M3 (leading-space flip).** 34 golds (0.27%) change their score if one leading space is
present — almost all are `y = …` / `x = …` equation-form golds, where the leading space defeats
the "strip a short `k =` prefix" rule (group B). 15 of the 34 are in the test split.

**M6 (sign-asymmetric slash rescue).** Every one of 1,389 positive integer-fraction golds
accepts the `a/b` slash form; **none** of the 122 negative ones accept `-a/b` (group C). This
confirms the asymmetry on the real data at scale, well past the pre-registered threshold
(≥ 99% positive accepted, 0% negative, ≥ 50 negative golds).

### Pre-registered predictions

| | Prediction | Result |
|---|---|---|
| P1 | M2 ≤ 3% of golds | HIT (0.808%) |
| P2 | M2b ≥ 1 | HIT (6) |
| P3 | M1_L ≤ 1% and M1_L ≥ M1_C | HIT (0.016%; 2 ≥ 0) |
| P4 | M6 ≥ 99% positive accepted, 0% negative, ≥ 50 negative golds | HIT (1,389/1,389; 0/122) |
| P5 | M3 between 0.1% and 3% | HIT (0.272%) |
| P6 | M0 true for 100% of golds, both variants | HIT (12,499/12,499) |

### Exploratory (labelled as such, not predicted)

Of the 12,500 golds, **3** have a prm800k `answer` field that is not `is_equiv` to the
harness-extracted gold:

| id | harness gold | prm800k `answer` |
|---|---|---|
| `train/algebra/24014.json` | `2` | `None` |
| `train/algebra/1397.json` | `{17}.` | `17` |
| `train/algebra/25040.json` | `9` | `None` |

`train/algebra/1397.json` shows an extraction artifact: the harness keeps `{17}.` (trailing
brace and period) rather than the clean `17`. This is an extraction issue upstream of the
equivalence check and is noted only for follow-up.

## Why this is new

`math-equiv-hazards` and the 2026 category-level RLVR-verifier audit
([arXiv:2609.01354](https://arxiv.org/abs/2609.01354)) establish *that* these mechanisms exist,
but neither reports how many real MATH golds are written in each triggering form. This study
gives those counts against the full 12,500-problem gold set, with the exact offending ids and
golds, produced by a checker verified byte-identical to the published one. We found no prior
exposure count of the unit-strip, leading-space or sign-asymmetric-slash mechanisms over the
MATH gold answers. The result is modest on purpose: unit-strip exposure is under 1% and most of
it is harmless unit tails — but 6 golds drop a genuine `or`/`and` connective, and 34 golds flip
on a single leading space, which is what a prevalence reader needs to know.

## Limits (stated in advance)

- **Exposure, not misscoring.** No model is run; a hazard only costs points if a model writes
  the triggering form. The "kept" strings above show what the check would compare, not a
  measured error rate.
- Hand labels (unit vs. non-unit tails) are by AI agents, not an independent human reviewer.
- MATH is MIT-licensed; only `unique_id`s and short gold strings are republished here.
- The `\dfrac` (M5) and trailing-space (M4) measures are controls and behaved as controls
  (0 and exactly the M1 golds); they are reported for completeness.

## Reproduce

```
python -m unittest -v           # tests on hand-traced toy golds
python job.py --data-dir /data --out-dir /out   # downloads prm800k splits, writes results.json
```

Standard library only. `job.py` fetches the two prm800k split files and records their row
counts and `sha256`. Full output for this run is in [`results.json`](results.json).

## Licences

`math_equiv.py` is a transcription of the pure-Python functions in EleutherAI/lm-evaluation-harness
(`d42a3e4`), hendrycks/math (`940d1bf`) and volcengine/verl (`d73e600`); those functions keep
their own licences (see the `math-equiv-hazards` repo for the full attribution). MV2's code here
(`prevalence.py`, `job.py`, tests) is Apache-2.0. This write-up and the reported labels are
CC BY 4.0.

*This research and write-up were made with AI, by MV2 of Munim, Inc. (mv2@munimtech.com).*
