# multinli-annotator-agreement-census

The 38th eval-reliability audit by MV2 of Munim, Inc., and the second member of the **gold-label
derivation** family started by audit 37 (SNLI).

The derivation family asks a basic question that benchmark papers state but rarely verify on their
own released files: does the gold label actually follow the rule the dataset says it follows, checked
row by row? Audit 37 did this for SNLI. MultiNLI (Williams, Nangia and Bowman, 2018) is the natural
second subject — it ships the identical `annotator_labels` list + single `gold_label` shape, so the
census logic is reused verbatim — but its construction differs from SNLI's in a way worth measuring,
and the raw files hold a surprise about the familiar dev sizes.

This research is carried out by AI agents working in MV2's name at Munim, Inc., and is disclosed as
AI-made wherever a platform, contest or project asks.

## The question

MultiNLI documents the same two rules as SNLI:

1. **Derivation.** `gold_label` is the *strict majority* of `annotator_labels` — a label held by more
   than half the annotators.
2. **No-consensus filter.** When no label reaches a strict majority, `gold_label` is `-` and the row is
   meant to be dropped before training or scoring.

But MultiNLI validated **only its dev and test sets** (four extra annotators each); the training split
is unvalidated and carries the single author label. SNLI, by contrast, ships a *validated subset inside
its train file*. So the two corpora should behave differently row-by-row, and nobody — as far as a
prior-art search of the MultiNLI paper, dataset card and public loaders could find — publishes a
row-by-row verification that the shipped `gold_label` *is* the strict majority on every released row,
that every `-` row genuinely lacks a majority, and the exact per-split no-consensus counts.

## What was found

A pre-registered, sealed-container census of all three raw MultiNLI 1.0 splits read straight from
`multinli_1.0.zip` (the test splits ship unlabelled for the Kaggle evaluations and are not in the file):

| Split | raw rows | labeled | `-` (no consensus) | gold == majority on every labeled row? | any `-` row with a majority? | annotators/row | unanimous |
| --- | --- | --- | --- | --- | --- | --- | --- |
| train | 392,702 | 392,702 | 0 | yes (0 mismatches) | — (no `-` rows) | 1 (single author) | — |
| dev_matched | 10,000 | 9,815 | 185 | yes (0 mismatches) | no (0) | 5 | 5,759 |
| dev_mismatched | 10,000 | 9,832 | 168 | yes (0 mismatches) | no (0) | 5 | 5,984 |

- **The derivation rule holds exactly.** Across all 412,702 raw rows, every labeled row's `gold_label`
  equals the strict majority of its `annotator_labels`, with 0 mismatches and 0 labeled rows that lack a
  strict majority. In the five-way validated dev sets that is a genuine check (the gold matches the
  majority even where the five votes are 3-2 or 4-1, not unanimous); in train the single author label is
  trivially its own majority.
- **Train is purely single-annotator and single-label.** The agreement histogram is `{1: 392702}` with
  0 `-` rows — MultiNLI train carries no validated subset at all. This is the clean contrast with SNLI,
  whose train file holds a validated subset (SNLI train histogram `{1: 510711, 4: 2466, 5: 36975}` with
  785 `-` rows, audit 37). If you want validated, multi-annotator NLI training signal, SNLI has it and
  MultiNLI does not.
- **The familiar dev sizes are post-filter counts, not raw line counts.** Each raw dev file ships
  **10,000 rows**, not the widely quoted 9,815 (matched) and 9,832 (mismatched). The difference is
  exactly the 185 and 168 no-consensus `-` rows: `10,000 − 185 = 9,815` and `10,000 − 168 = 9,832`. The
  numbers everyone cites are the labeled counts after the `-` filter. A loader that reads the raw jsonl
  and forgets to drop `-` carries 353 unlabelable rows into dev evaluation and reports a dev set 353
  rows larger than the paper's.
- **The no-consensus filter is clean.** No `-` row in either dev file has a strict majority — the marker
  is applied to exactly the 2-2-1 / 3-1-1 style splits with no majority, never to a row a naive vote
  could have labeled.

All three pre-registered predictions **held**:

- **P1** — gold is the strict majority on every labeled row of every split (0 mismatches, 0
  labeled-without-majority): **HELD**.
- **P2** — every `-` row has no strict majority: **HELD**.
- **P3** — train is unvalidated single-label (`{1: 392702}`, 0 `-`) while both dev splits are fully
  5-way validated: **HELD**.

## Files

- `nli_agreement.py` — the NLI-dataset-neutral census: `strict_majority`, per-split `agreement_stats`,
  and `flatten`. Byte-identical to audit 37's module (renamed), reused verbatim.
- `cases.py` — a five-row hand-traced fixture with its frozen `TARGET` counts (one row is a synthetic
  derivation anomaly so the mismatch path is exercised), plus the expected train histogram and raw split
  totals.
- `test_nli_agreement.py` — 11 stdlib `unittest` tests, including the hand-traced target and the
  majority / no-majority edge cases.
- `job.py` — asserts the fixture before touching real data, streams the three raw jsonl splits from the
  zip, runs the census, records the predictions, and writes `results.json`.
- `results.json` — the frozen sealed-container output (per-split counts, agreement histograms,
  predictions).

## Limits

That `gold = strict majority` is *documented*, so its holding is not a surprise — the contribution is
the row-by-row verification on the raw released files (no public loader was found that does it), the
confirmation that the `-` filter never hides a row that had a majority, the structural contrast with
SNLI's train, and the first published per-split no-consensus counts (185 / 168) that show the familiar
dev sizes are post-filter figures. The `rows_as_expected` flag in `results.json` is `false` precisely
*because* the pre-registered expected dev totals were the widely quoted labeled counts (9,815 / 9,832)
and the raw files hold 10,000 each — that mismatch is the finding, reported honestly rather than tuned
away. The train split's single author label is trivially its own majority, so the non-trivial
derivation check lives in the two dev sets; that is stated plainly. This audit checks the derivation
rule, not label *correctness* — whether the annotators were right is out of scope.

Related: audit 37 ([snli-annotator-agreement-census](../snli-annotator-agreement-census/)) is the first
member of this family. The gold-conflict censuses on the same corpora — SNLI (audit 20,
[nli-gold-conflict-census](../nli-gold-conflict-census/)) and MultiNLI (audit 21,
[multinli-gold-conflict-census](../multinli-gold-conflict-census/)) — ask whether duplicate pairs carry
conflicting gold; this audit instead verifies how each single gold was derived from its votes.

## Licence

Code is Apache-2.0. The corpus, results and this write-up are CC BY 4.0. MultiNLI 1.0 is released for
research use (Williams, Nangia and Bowman, "A Broad-Coverage Challenge Corpus for Sentence
Understanding through Inference", NAACL 2018), derived from the Open American National Corpus. Authored
by AI agents working in MV2's name (Munim, Inc.).
