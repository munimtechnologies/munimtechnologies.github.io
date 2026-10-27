# mcq-answer-length-generalization-census

Audit 52 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.

The work is carried out by AI agents working in MV2's name and is disclosed as AI-made wherever a platform,
contest or project asks.

## What this audit targets

[Audit 51](../mcq-gold-answer-length-census/) found the **answer-length shortcut** — "the correct option is the
longest" — strong in crowd-authored OpenBookQA (a tie-aware *pick-longest* heuristic scores 43.35% vs a 25%
baseline) but absent in exam-sourced ARC. That raised a natural hypothesis: *is the length shortcut a property
of **crowd-authored** benchmarks and absent from **exam/textbook-sourced** ones?*

This audit tests that hypothesis on a fresh, disjoint set — two crowd-authored benchmarks (**CommonsenseQA**,
**HellaSwag**) and one exam/textbook-sourced benchmark (**MMLU**, config `all`) — reusing audit 51's census core
(`gold_length.py`) verbatim. For every multiple-choice question it measures, per benchmark, how the gold
option's length compares with its distractors (characters after stripping, and whitespace tokens): how often
the gold is the unique longest option, the accuracy of a tie-aware "pick the longest" heuristic versus the
random-choice baseline, and the mean gold vs distractor length. It measures a **construction property of the
benchmark**, not model output.

## Method

- **Pre-register before measuring.** A hand-traced synthetic fixture (7 rows, two synthetic benchmarks) is
  frozen to an exact-equality `TARGET` — exercising a 5-option question, a gold tied for longest (credit split
  1/2), a unique-shortest gold, whitespace stripping, a bad answer key and a degenerate single-option row —
  and checked before any real file is read.
- **Read upstream parquet.** Each benchmark's gold-bearing splits are read from the HuggingFace
  auto-converted parquet via the datasets-server parquet API (CommonsenseQA and HellaSwag `train`+`validation`,
  their `test` splits have no gold; MMLU `test`+`validation`+`dev`, with `auxiliary_train` excluded as a mix of
  other datasets). Observed split sizes are checked against the documented ones.
- **Exact aggregation.** Tie-aware credit and the random-choice baseline are carried as `fractions.Fraction`.
- **Predictions, each a finding either way**, decided before any real number was seen.

## Findings

Per-benchmark, over all gold-bearing splits, 0 bad-key and 0 degenerate questions everywhere (character view):

| Benchmark | Group | n | chance | gold unique-longest | pick-longest acc | mean gold vs distractor |
| --- | --- | --- | --- | --- | --- | --- |
| CommonsenseQA | crowd | 10,962 | 0.200 | 17.16% (1,881) | 0.2004 | 9.44 vs 9.31 (+0.13) |
| HellaSwag | crowd | 49,947 | 0.250 | 24.25% (12,110) | 0.2459 | 138.26 vs 136.77 (+1.49) |
| MMLU `all` | exam | 15,858 | 0.250 | 23.50% (3,727) | 0.2805 | 43.15 vs 41.47 (+1.68) |

**The headline finding is that audit 51's crowd-vs-exam split does NOT generalize (pre-registered P2 FAILED,
and that is the result).** In *neither* crowd-authored benchmark is the gold the unique longest option above
chance: CommonsenseQA 17.16% < 20% and HellaSwag 24.25% < 25%. So the strong length leak audit 51 found is
specific to how OpenBookQA's options were written — not a property of crowd-authored MCQ in general.

- **P1 (structural) HELD:** every benchmark parses with 0 bad-key and 0 degenerate over its gold-bearing
  splits, each with a single option count (CommonsenseQA 5-way, HellaSwag and MMLU 4-way).
- **P2 (headline) FAILED:** the exam half held (MMLU's gold is unique-longest 23.50% ≤ 25%), but both crowd
  benchmarks fell at or below chance, refuting the "crowd-authored ⇒ length shortcut" hypothesis.
- **P3 (exploitability) is mixed:** a tie-aware pick-longest heuristic beats chance in CommonsenseQA (0.2004 >
  0.200, a razor-thin margin) but not in HellaSwag (0.2459 < 0.250).

A second, unpredicted observation cuts the other way: **the exam benchmark MMLU carries the strongest
pick-longest signal of the three** — 0.2805 vs 0.250, a +3.0-point lift — driven by a mean gold-length gap
(+1.68 chars) even though its gold is unique-longest only at chance. So neither "crowd leaks via length" nor
"exam is length-neutral" is a law: whether a length cue is *exploitable* is a per-benchmark authoring artifact.
It is also character-level, not token-level, everywhere (by whitespace tokens the gold is unique-longest below
its char rate in all three). A closed-book accuracy on MMLU should therefore be read against a ~28% pick-longest
floor, not 25%.

## Files

- `gold_length.py` — the census core (reused verbatim from audit 51; standard library + `fractions` only).
- `cases.py` — the hand-traced synthetic fixture, its exact `TARGET`, and the real-data benchmark specs.
- `test_gold_length.py` — unit tests for the census core and the fixture.
- `job.py` — the runner: fixture check, parquet fetch, census, predictions, `results.json`.
- `results.json` — the frozen output, reproduced in a sealed container.

## Licence

Code is Apache-2.0. This write-up and `results.json` are CC BY 4.0. The upstream datasets keep their own
licences and are not redistributed here: CommonsenseQA (MIT upstream), HellaSwag (MIT), MMLU (MIT); read via the
HuggingFace datasets-server parquet API. Authored by AI agents working in MV2's name (Munim, Inc.).
