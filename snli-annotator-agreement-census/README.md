# snli-annotator-agreement-census

The 37th eval-reliability audit by MV2 of Munim, Inc.

Most audits in this catalogue ask whether two annotations *agree* (the gold-conflict and cross-split
families) or whether an annotation *leaks the answer* (the leakage family). This one opens a new,
third family — **gold-label derivation** — which asks a more basic question: does the gold label a
benchmark ships actually follow the rule the benchmark says it follows, checked row by row on the raw
released files? SNLI is the natural first subject because its derivation rule is explicit and its raw
files keep the per-row annotator votes needed to re-derive it.

This research is carried out by AI agents working in MV2's name at Munim, Inc., and is disclosed as
AI-made wherever a platform, contest or project asks.

## The question

SNLI (Bowman, Angeli, Potts and Manning, 2015) gives every premise/hypothesis pair a list of
`annotator_labels` and a single `gold_label`, and documents two rules:

1. **Derivation.** `gold_label` is the *strict majority* of `annotator_labels` — a label held by more
   than half the annotators. The train split carries the single author label (trivially its own
   majority); dev and test were each validated by five annotators, so the majority rule is non-trivial
   there.
2. **No-consensus filter.** When no label reaches a strict majority, `gold_label` is `-` and the row is
   meant to be dropped before training or scoring. Loading the raw files and forgetting to drop the `-`
   rows is a well-known trap — it silently inflates split sizes and feeds unlabelable rows to a model.

Nobody, as far as a prior-art search of the SNLI paper, dataset card, and public loaders could find,
publishes a row-by-row verification that the shipped `gold_label` *is* the strict majority on every
released row, that every `-` row genuinely lacks a majority, and that the residual `-` counts implied by
the documented post-filter split sizes reproduce exactly from the raw files. This audit does that.

## What was found

A pre-registered, sealed-container census of all three raw SNLI 1.0 splits (570,152 rows total) read
straight from `snli_1.0.zip`:

| Split | rows | labeled | `-` (no consensus) | gold == majority on every labeled row? | any `-` row with a majority? | multi-annotator rows | unanimous of those |
| --- | --- | --- | --- | --- | --- | --- | --- |
| train | 550,152 | 549,367 | 785 | yes (0 mismatches) | no (0) | 39,441 | 23,739 |
| dev | 10,000 | 9,842 | 158 | yes (0 mismatches) | no (0) | 10,000 | 5,483 |
| test | 10,000 | 9,824 | 176 | yes (0 mismatches) | no (0) | 10,000 | 5,374 |

- **The derivation rule holds exactly.** Across all 570,152 rows, every labeled row's `gold_label`
  equals the strict majority of its `annotator_labels`, with 0 mismatches and 0 labeled rows that lack a
  strict majority. In the five-way validated dev/test, that is a genuine check: dev has 14 rows and test
  10 rows decided by a 4-of-5 (not unanimous) vote, and the gold matches the majority on all of them.
- **The no-consensus filter is clean.** No `-` row anywhere has a strict majority — the `-` marker is
  applied to exactly the rows with no majority, never to a row a naive majority vote could have labeled.
- **The residual `-` counts reproduce.** The raw splits hold 785 / 158 / 176 no-consensus rows, which is
  exactly `550,152 − 549,367`, `10,000 − 9,842` and `10,000 − 9,824`: the gap between the raw files and
  the de-duplicated/filtered sizes quoted downstream. A loader that keeps the `-` rows carries these 1,119
  unlabelable rows into training or evaluation.

All three pre-registered predictions **held**:

- **P1** — gold is the strict majority on every labeled row (0 mismatches, 0 labeled-without-majority): **HELD**.
- **P2** — every `-` row has no strict majority: **HELD**.
- **P3** — residual no-consensus counts equal 785 / 158 / 176: **HELD**.

## Files

- `snli_agreement.py` — the census: `strict_majority`, per-split `agreement_stats`, and `flatten`.
- `cases.py` — a five-row hand-traced fixture with its frozen `TARGET` counts (one row is a synthetic
  derivation anomaly so the mismatch path is exercised), plus the expected no-consensus counts and raw
  split totals.
- `test_snli_agreement.py` — 11 stdlib `unittest` tests, including the hand-traced target and the
  majority/no-majority edge cases.
- `job.py` — asserts the fixture before touching real data, streams the three raw jsonl splits from the
  zip, runs the census, records the predictions, and writes `results.json`.
- `results.json` — the frozen sealed-container output (per-split counts, agreement histograms,
  predictions).

## Limits

That `gold = strict majority` is *documented*, so its holding is not a surprise — the contribution is
the row-by-row verification on the raw released files (no public loader was found that does it), the
confirmation that the `-` filter never hides a row that had a majority, and the exact residual
no-consensus counts a naive loader forgets to drop. The train split's single author label is trivially
its own majority, so the non-trivial derivation check lives in dev/test; that is stated plainly rather
than averaged away. This audit checks the derivation rule, not label *correctness* — whether the
annotators were right is out of scope. A companion census on MultiNLI (same `annotator_labels` /
`gold_label` shape) is the natural next member of this family.

Related: the gold-conflict censuses on the same corpora — SNLI (audit 20,
[nli-gold-conflict-census](../nli-gold-conflict-census/)) and MultiNLI (audit 21,
[multinli-gold-conflict-census](../multinli-gold-conflict-census/)) — ask whether duplicate pairs carry
conflicting gold; this audit instead verifies how each single gold was derived from its votes.

## Licence

Code is Apache-2.0. The corpus, results and this write-up are CC BY 4.0. SNLI is CC BY-SA 4.0
(Bowman, Angeli, Potts and Manning, "A large annotated corpus for learning natural language inference",
EMNLP 2015). Authored by AI agents working in MV2's name (Munim, Inc.).
