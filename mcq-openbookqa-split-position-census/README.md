# mcq-openbookqa-split-position-census

Audit 55 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.

The work is carried out by AI agents working in MV2's name and is disclosed as AI-made wherever a platform,
contest or project asks.

## What this audit targets

[Audit 53](../mcq-gold-position-census/) found that OpenBookQA's gold position, pooled over all of `main`
(5,957 questions), is skewed toward the **first** option (position 0 / "A", 27.6%; χ² = 23.65, df 3, rejecting
uniformity at α = 0.001). That pooled number mixes the large train split (4,957) with the two 500-question
evaluation splits. People report OpenBookQA **test** accuracy, so this audit asks the follow-up: **is the
"answer tends to be A" skew present in the reported test split, or is it a train-only construction artifact?**

For every OpenBookQA `main` question it records the 0-based **index** of the gold option within the released
option list, keyed by **split**. Per split it reports the gold-position distribution, a Pearson chi-square
goodness-of-fit against a uniform distribution, and a best-constant-position baseline; it then reproduces
audit 53's pooled OpenBookQA numbers as a cross-check.

This is a property of **how the benchmark was built** — where the correct answer was placed — and is distinct
from a *model's* position / selection bias, which is heavily studied.

## Method

- **Reuse an already-passed core.** The census core (`position_census.py`), the hand-traced synthetic fixture
  and its exact-equality `TARGET` (`cases.py`) and the unit tests are reused **verbatim** from audits 53/54. Only
  a new by-split OpenBookQA loader and three fresh predictions differ.
- **Pre-register before measuring.** The fixture is checked for exact equality before any real file is read; the
  three real-data predictions below were fixed, each a finding either way, before any real number was seen.
- **Read upstream parquet.** OpenBookQA `main` (train + validation + test) is read from the HuggingFace
  auto-converted parquet via the datasets-server parquet API. Observed split sizes are checked against the
  documented ones (4,957 / 500 / 500), and the per-split valid counts must partition audit 53's 5,957 exactly.
- **Chi-square without scipy.** The Pearson statistic and its degrees of freedom are reported per split with a
  hard-coded critical value at α = 0.001, so a reader can recompute an exact p-value.

## Findings

Every split parses cleanly (0 bad keys, 0 degenerate rows, all 4-option), the splits are exactly 4,957 / 500 /
500, they partition audit 53's 5,957, and the pooled re-key reproduces audit 53 exactly.

| Split | n | gold-position rates (A / B / C / D) | χ² (df 3) | rejects uniform at 0.001 | most common position |
| --- | --- | --- | --- | --- | --- |
| train | 4,957 | **.278** / .245 / .231 / .246 | 23.42 | yes | A (pos 0) |
| validation | 500 | .252 / **.276** / .220 / .252 | 3.17 | no | B (pos 1) |
| test | 500 | **.276** / .252 / .264 / .208 | 5.28 | no | A (pos 0) |
| pooled (audit 53) | 5,957 | **.276** / .248 / .233 / .244 | 23.65 | yes | A (pos 0) |

- **P1 (structural) HELD.** Clean parse, exact partition (sum 5,957), and the pooled re-key reproduces audit 53
  (position 0 at 27.56%, χ² = 23.65 df 3, uniform rejected).
- **P2 (headline) HELD.** The "A" lean is present in the reported **test** split: its gold sits at the first
  option 27.6% of the time (138 of 500), above the 25% chance rate, and A is its most common gold position. A
  question-free "always A" guess scores **27.6% on OpenBookQA test**, the same edge as on train (27.8%).
- **P3 (consistency) FAILED.** The first option is **not** the most common gold position in every split: in
  **validation** the gold sits at A only 25.2% of the time (exactly chance) and B is modal (27.6%). So the
  direction of the lean is not stable across the two small evaluation splits.

**Reading these honestly.** Only train rejects uniformity on its own. That does **not** mean the evaluation
splits are uniform: at n = 500 a skew as large as train's is almost undetectable. Train's χ² per question is
23.42 / 4,957 ≈ 0.0047, so the same skew in 500 questions gives an expected noncentrality of only ≈ 2.4 —
far below the 16.27 needed to reject at 0.001 (or the 7.81 needed at 0.05). The test split's observed χ² of
5.28 is what that skew would typically produce (df + λ ≈ 5.4).

A post-hoc check (not pre-registered and not part of `results.json`, computed by hand from its per-split
counts): a 3 × 4 chi-square test of homogeneity across the three splits gives χ² ≈ 8.4 with df 6, below the
12.59 critical value at α = 0.05. So there is **no evidence that the splits differ** in where they put the gold.
The data are consistent with one shared, mild "A" lean, which the test split shows at full strength (27.6%) and
validation does not (25.2%), within sampling noise.

The practical reading: when reporting closed-book OpenBookQA test accuracy, the position-only floor is about
27.6% ("always A"), not 25%. Together with audit 51's length shortcut (pick-longest ≈ 43% over all of `main`),
these are the floors to beat before claiming that a model read the question.

## Why this is new

Audit 53 reported OpenBookQA pooled across splits. A prior-art check found model-side position and selection
bias heavily studied, and OpenBookQA described qualitatively as answer-balanced, but no per-split gold-position
census of OpenBookQA, and no statement of whether its construction-side "A" lean reaches the reported test split.
This audit gives the per-split counts, says plainly that the 500-question evaluation splits cannot confirm or
rule out the lean on their own, and finds no evidence that the splits differ.

## Limits

- The two evaluation splits have low power (see above); a non-rejection there is not proof of uniformity.
- The homogeneity figure is a hand calculation from the published counts, not a pre-registered prediction.
  `results.json` holds every count needed to recompute it.
- This measures construction only. Whether any particular model exploits the lean is a separate question.

## Files

- `position_census.py`: the census core (reused verbatim from audits 53/54). Exact integer gold-position
  counts bucketed by option count *k*, plus the chi-square GOF and best-constant-position baseline (standard
  library and `fractions` only).
- `cases.py`: the hand-traced synthetic fixture (reused), its exact `TARGET`, and the OpenBookQA-by-split spec.
- `test_position_census.py`: unit tests for the census core, the fixture and the chi-square statistic.
- `job.py`: the runner. It checks the fixture, fetches OpenBookQA parquet by split, runs the census and the
  predictions, cross-checks the pooled result against audit 53 and writes `results.json`.
- `results.json`: the frozen output, reproduced in a sealed container.

## Licence

Code is Apache-2.0. This write-up and `results.json` are CC BY 4.0. OpenBookQA (Apache-2.0 upstream) is read via
the HuggingFace datasets-server parquet API and is not redistributed here. Authored by AI agents working in
MV2's name (Munim, Inc.).
