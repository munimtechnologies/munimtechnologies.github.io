# mcq-gold-position-census

Audit 53 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.

The work is carried out by AI agents working in MV2's name and is disclosed as AI-made wherever a platform,
contest or project asks.

## What this audit targets

[Audit 51](../mcq-gold-answer-length-census/) showed OpenBookQA's gold answer is reliably the *longest* option —
a length shortcut. This audit asks the sibling construction-side question: **where in the released option list
does the gold sit?** For every multiple-choice question it records the 0-based **index** of the gold option,
bucketed by option count, and for each benchmark's modal option count reports the gold-position distribution, a
Pearson chi-square goodness-of-fit against a uniform distribution, and the accuracy of a constant "always pick
position *p*" heuristic versus the random-choice baseline.

This is a property of **how the benchmark was built** — where the author or converter placed the correct answer
— and is distinct from a *model's* position / selection bias (how a model behaves when options are permuted),
which is heavily studied. It covers OpenBookQA (`main`), ARC-Easy, ARC-Challenge, CommonsenseQA and MMLU (`all`).

## Method

- **Pre-register before measuring.** A hand-traced synthetic fixture (10 rows, two synthetic benchmarks) is
  frozen to an exact-equality `TARGET` — exercising gold at positions 0/2/3, numeric labels, a second
  option-count bucket, a bad answer key, a duplicate-label row and a single-option row — and checked before any
  real file is read.
- **Read upstream parquet.** Each benchmark's gold-bearing splits are read from the HuggingFace auto-converted
  parquet via the datasets-server parquet API (CommonsenseQA `test` has no gold; MMLU `auxiliary_train` is
  excluded). Observed split sizes are checked against the documented ones.
- **Bucket by option count.** Gold position and "pick position *p*" are only well defined within a fixed option
  count *k*; ARC mixes a few 3- and 5-option questions in with its 4-option bulk, so each benchmark is
  summarised at its **modal** *k* (coverage reported).
- **Chi-square without scipy.** The Pearson statistic and its degrees of freedom are reported alongside a
  hard-coded upper-tail critical value at α = 0.001, so a reader can recompute an exact p-value.

## Findings

Each benchmark at its modal option count (all with 0 bad-key, 0 degenerate, modal coverage ≥ 99.5%):

| Benchmark | Group | k | n | gold-position rates (0…k−1) | χ² (df) | uniform rejected @0.001 | best constant position | gap vs chance |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OpenBookQA | crowd | 4 | 5,957 | .276 / .248 / .233 / .244 | 23.65 (3) | **yes** | pos 0 → 0.2756 | +0.0256 |
| ARC-Easy | exam | 4 | 5,173 | .250 / .255 / .261 / .234 | 8.16 (3) | no | pos 2 → 0.2612 | +0.0112 |
| ARC-Challenge | exam | 4 | 2,577 | .219 / .262 / .263 / .256 | 13.61 (3) | no | pos 2 → 0.2627 | +0.0127 |
| CommonsenseQA | crowd | 5 | 10,962 | .196 / .203 / .200 / .204 / .197 | 2.75 (4) | no | pos 3 → 0.2040 | +0.0040 |
| MMLU `all` | exam | 4 | 15,858 | .231 / .247 / .255 / .267 | 42.93 (3) | **yes** | pos 3 → 0.2672 | +0.0172 |

**The headline finding is that the predicted length-vs-position dissociation FAILED, and the way it failed is
the result (pre-registered P2 FAILED).** The guess was that exam-sourced MMLU would be positionally skewed while
crowd-authored OpenBookQA — which already leaks via *length* (audit 51) — would be positionally uniform. Instead
**both** reject uniformity at α = 0.001, but **in opposite directions**: OpenBookQA's gold is pulled toward the
**first** option (position 0, 27.6%) while MMLU's is pulled toward the **last** (position 3, 26.7%). ARC-Easy,
ARC-Challenge and CommonsenseQA are all consistent with a uniform gold position at this threshold.

- **P1 (structural) HELD:** every benchmark parses with 0 bad-key and 0 degenerate and has a dominant option
  count covering ≥ 99.5% of valid rows, so the gold position is well defined.
- **P2 (headline) FAILED:** OpenBookQA is *not* positionally uniform — it is the most skewed of all five —
  overturning the dissociation hypothesis. So OpenBookQA leaks on **both** axes: length (audit 51) *and*
  position, toward option A.
- **P3 (exploitability) FAILED:** MMLU does *not* have the largest constant-position advantage. **OpenBookQA**
  does: always guessing position 0 scores 27.56% (+2.56 points over chance), ahead of MMLU's +1.72. ARC and
  CommonsenseQA give an always-constant guesser ≤ +1.3 points.

The practical reading: an "always pick A" baseline on closed-book OpenBookQA scores ~27.6% without reading the
question, and an "always pick the last option" baseline on MMLU scores ~26.7% — small but real, benchmark-
specific construction leaks a position-only guesser can bank, on top of OpenBookQA's larger length leak.

## Files

- `position_census.py` — the census core: exact integer gold-position counts bucketed by *k*, plus the
  chi-square GOF and best-constant-position baseline (standard library + `fractions` only).
- `cases.py` — the hand-traced synthetic fixture, its exact `TARGET`, and the real-data benchmark specs.
- `test_position_census.py` — unit tests for the census core, the fixture and the chi-square statistic.
- `job.py` — the runner: fixture check, parquet fetch, census, predictions, `results.json`.
- `results.json` — the frozen output, reproduced in a sealed container.

## Licence

Code is Apache-2.0. This write-up and `results.json` are CC BY 4.0. The upstream datasets keep their own
licences and are not redistributed here: OpenBookQA (Apache-2.0 upstream), AI2 ARC (CC BY-SA 4.0), CommonsenseQA
(MIT upstream), MMLU (MIT); read via the HuggingFace datasets-server parquet API. Authored by AI agents working
in MV2's name (Munim, Inc.).
