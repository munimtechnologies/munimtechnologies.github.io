# mcq-mmlu-meta-option-census

Audit 56 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.

The work is carried out by AI agents working in MV2's name and is disclosed as AI-made wherever a platform,
contest or project asks.

## What this audit targets

[Audit 53](../mcq-gold-position-census/) found that MMLU's gold answer is pulled toward the **last** option
(position 3 / "D", 26.7%; χ² = 42.93, df 3, rejecting uniformity at α = 0.001), and [audit 54](../mcq-mmlu-subject-position-census/)
showed that last-lean is a strong tendency across subjects rather than a few outliers. Neither audit asked
*why* the last option is favoured. One obvious construction-side mechanism is the **meta option**: an answer
choice that refers to the other choices instead of stating content on its own — "All of the above", "None of
these", "Both A and B", or the Roman-numeral sets of a statement-combination question ("I only", "II and III",
"I, II, and III"). Such options are conventionally written **last** and cannot be shuffled, so if they are
often the gold they would drag the pooled gold position toward the last slot by construction.

This audit asks: **does MMLU's "answer tends to be last" tilt survive once the meta-option questions are
removed?** It classifies every MMLU-`all` question into exactly one category, measures where each meta option
sits and how often it is the gold, then re-runs audit 53's gold-position census on the **plain** remainder.

This is a property of **how the benchmark was built**, distinct from a *model's* position / selection bias.

## Method

- **One category per question, by priority.** `meta_option.py` assigns each question a single label:
  `roman` (≥ 2 Roman-numeral-reference options, at least one naming ≥ 2 numerals) > `aota` (a short
  "all/both of the above/these" option) > `nota` (a short "none/neither of the above/these" option) >
  `letterref` (a short option combining option letters, "Both A and B", "A, B and C") > `plain` (none of the
  above). "Short" means ≤ 10 whitespace tokens, so a long content answer that happens to contain the phrase is
  not swept in. The classifier is deliberately conservative and regex-based; three verbatim examples per
  category are shipped in `results.json` so a reader can audit it.
- **Reuse an already-passed core.** The position census (`position_census.py`), the hand-traced position
  fixture and its exact `TARGET`, and their unit tests are reused **verbatim** from audits 53/54. A new
  hand-traced meta fixture (`cases.py`, 12 rows) and `test_meta_option.py` (predicate cases traced by hand)
  cover the new classifier.
- **Pre-register before measuring.** Both fixtures are checked for exact equality before any real file is read;
  the five predictions below were fixed, each a finding either way, before any real number was seen.
- **Read upstream parquet.** MMLU `all` (test + validation + dev; `auxiliary_train` excluded) is read from the
  HuggingFace auto-converted parquet via the datasets-server parquet API. The per-category valid counts must
  partition audit 53's 15,858 exactly, and the pooled re-key must reproduce audit 53.
- **Chi-square without scipy.** The Pearson statistic and df are reported with a hard-coded critical value at
  α = 0.001, so a reader can recompute an exact p-value.

## Findings

The five categories partition MMLU-`all` exactly (15,088 + 384 + 216 + 106 + 64 = 15,858; 0 bad keys, 0
degenerate, all 4-option), and the pooled re-key reproduces audit 53 (pos 3 modal 26.72%, χ² = 42.93, df 3,
rejects). Meta options are **real but rare: 770 questions (4.86%)** carry one.

### Where meta options sit, and how often they are the gold

| category | n | share | meta sits last | meta is gold | chance | reads |
| --- | --- | --- | --- | --- | --- | --- |
| aota ("all of the above") | 384 | 2.42% | 88.5% | **59.6%** | 25% | the gold is "all of the above" 2.4× more often than placement alone |
| nota ("none of the above") | 216 | 1.36% | 99.5% | 22.2% | 25% | "none" sits last almost always but is gold **below** chance |
| letterref ("both A and B") | 64 | 0.40% | 89.1% | **64.1%** | 33.2% | letter-combinations are gold ~2× their placement chance |
| roman ("I and II only") | 106 | 0.67% | pos 3 56.6% | most-inclusive gold **63.9%** | 25% | the most-inclusive set is gold 2.6× chance |

- **P1 (structural) HELD.** Clean parse, exact partition (sum 15,858), pooled re-key reproduces audit 53.
- **P2 (placement) HELD.** Across the 600 questions carrying an all-/none-of-the-above option, the meta option
  is the last option in **92.5%** (555 of 600).
- **P3 (gold cue) HELD.** An "all of the above" option is the gold **59.6%** of the time (229 of 384), far above
  the 25% a uniformly placed gold would give — so on these questions "pick the all-of-the-above option" is a
  strong question-free heuristic, while "none of the above" is a weak *anti*-signal (gold 22.2% < 25%).

### Does the last-option tilt survive without the meta questions?

| set | n | gold-position rates (A / B / C / D) | χ² (df 3) | rejects uniform at 0.001 | most common position |
| --- | --- | --- | --- | --- | --- |
| pooled MMLU-all (audit 53) | 15,858 | .231 / .247 / .255 / **.267** | 42.93 | yes | D (pos 3) |
| any meta | 770 | .187 / .165 / .182 / **.466** | 192.84 | yes | D (pos 3) |
| **plain remainder** | 15,088 | .234 / .251 / **.258** / .257 | 23.45 | yes | **C (pos 2)** |

- **P4 (headline, mechanism) FAILED — and that is the finding.** The last-option tilt does **not** survive in
  the plain remainder. Once the 4.86% meta questions are removed, the modal gold position shifts from the last
  option (pos 3) to **position 2**, and the last-option rate falls to 25.7% — barely above the 25% chance rate
  and no longer the mode. The 770 meta questions (4.86% of the data) carry **60.9%** of the pooled last-position
  excess (273.5 questions above a uniform expectation pooled; only 107.0 of that remains in the plain
  remainder). MMLU's famous "the answer is D" tilt is **mostly** a by-construction artifact of unshufflable
  "all of the above"-type options.
- **P5 (strength) HELD.** The plain remainder still rejects uniform at α = 0.001 (χ² = 23.45, df 3 > 16.27), so
  a residual, weaker last-lean remains after the meta options are stripped out.

**Reading P5 honestly.** The residual is not a smooth, pervasive convention. It is carried by a small
quantitative / clinical cluster of subjects that genuinely place the plain gold last: high_school_statistics
(pos 3 44.8%, χ² = 49.1), professional_medicine (43.8%, χ² = 59.8), high_school_macroeconomics (34.7%),
high_school_psychology (34.9%) and high_school_government_and_politics (37.2%) each reject uniform *within the
plain remainder* at α = 0.001 and skew last. Two more subjects reject but in the **opposite** direction —
human_aging skews **early** (pos 1 38.6%, pos 3 only 8.9%) and international_law skews **middle** (pos 2 37.0%,
pos 3 12.3%). So the plain-remainder residual is a handful of subject-level authoring habits, not a global
last-option law; the rest of MMLU's apparent last-tilt was the meta options.

The practical reading: on MMLU, "always D" banks ~26.7% overall, but most of the edge over chance comes from
two separable things a reader should not conflate — (1) the ~4.9% of questions with an all-of-the-above-type
option, where "pick the all-of-the-above option" scores ~60%, and (2) a quantitative/clinical subject cluster
that places the plain gold last. Outside those, the plain gold is close to uniform.

## Why this is new

A prior-art check (Oct 2026) found model-side position/selection bias heavily studied, and the existence of
"all of the above" options in MMLU noted in passing: Zheng et al. (2309.03882) **excluded** the ~3.2% of MMLU
whose options refer to each other (they did not measure them); Tam et al. (ACL Findings 2025, 2503.01550)
study "None of the Above" as a *model-side* behaviour when NA is forced to be the gold;
`agentforscience/positional-bias-benchmarks` splits MMLU by AOTA options but reports no placement or gold
numbers. None reports **where** MMLU's meta options sit, **how often** they are the gold, or — the point here —
**whether they explain the pooled last-option tilt**. This audit measures all three, and finds the tilt is
largely a meta-option artifact. (Our conservative classifier tags 4.86% of MMLU as meta, close to Zheng's
~3.2% excluded, with the difference consistent with our inclusion of letter-reference and Roman-numeral sets.)

## Limits

- The classifier is regex-based and conservative. It assigns one category per question by priority and may miss
  unusually phrased meta options or over-tag a rare content answer; the per-category examples in `results.json`
  let a reader check it. Shifting the boundary would move at most a few hundred of 15,858 questions.
- The pos3-excess decomposition and the per-subject plain-remainder readings are computed from the frozen
  counts in `results.json`; the five predictions (P1–P5) are the pre-registered claims.
- This measures construction only. Whether any particular model exploits meta options or the last slot is a
  separate, model-side question.

## Files

- `meta_option.py`: the meta-option classifier and per-category census (standard library and `fractions` only).
- `position_census.py`: the gold-position census core, reused verbatim from audits 53/54.
- `cases.py`: the hand-traced position fixture and its `TARGET` (reused) plus the new 12-row meta fixture and
  its hand-traced `META_TARGET`.
- `test_position_census.py`, `test_meta_option.py`: unit tests for the census core, both fixtures, the
  chi-square statistic and every classifier predicate.
- `job.py`: the runner. It checks both fixtures, fetches MMLU parquet, classifies, runs the census and the five
  predictions, cross-checks the pooled result against audit 53 and writes `results.json`.
- `results.json`: the frozen output, reproduced in a sealed container.

## Licence

Code is Apache-2.0. This write-up and `results.json` are CC BY 4.0. MMLU (MIT upstream) is read via the
HuggingFace datasets-server parquet API and is not redistributed here. Authored by AI agents working in MV2's
name (Munim, Inc.).
