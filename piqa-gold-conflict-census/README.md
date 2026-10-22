# piqa-gold-conflict-census

The 27th [eval-reliability audit](../eval-reliability-audits/).

A census of PIQA (Bisk et al., AAAI 2020) for a specific data-quality defect: the same
(goal, sol1, sol2) triple appearing more than once in the release with two or more different
gold labels. A PIQA gold label in {0, 1} names which of the two solutions is correct, so a
triple that recurs with two different labels cannot be scored right every time — it is
ill-defined ground truth.

This extends the gold-conflict family — the [SNLI](../nli-gold-conflict-census/),
[MultiNLI](../multinli-gold-conflict-census/), [ANLI](../anli-gold-conflict-census/) and
[BoolQ](../boolq-gold-conflict-census/) censuses — to a physical-commonsense benchmark whose
label is a *choice between two candidate solutions* rather than an NLI or yes/no label.

The work is carried out by AI agents working in MV2's name (Munim, Inc.), and is disclosed
as AI-made wherever a platform or project asks.

## The question

A PIQA example is a (goal, sol1, sol2) triple with a gold label 0 or 1 picking the correct
solution. That makes two different repetitions possible, and they are not the same thing:

- A **triple conflict** — the real defect — is one identical (goal, sol1, sol2) triple
  carrying two different gold labels. Nothing can satisfy both at once, so the gold is
  self-contradicting.
- A **goal reuse** — the same goal text paired with two *different* solution pairs — is
  **legitimate** in PIQA by design: the benchmark builds many distinct solution pairs around
  a shared goal, so the same goal can correctly take label 0 in one example and label 1 in
  another. This audit counts goal reuse separately, as context, and never as a defect.

Two keys are used for the defect. The **exact** key is the raw (goal, sol1, sol2) string
triple. The **normalized** key collapses every run of whitespace to a single space and
lowercases all three fields, to catch near-duplicates that differ only in spacing or case;
the normalized count is a strict superset of the exact count. Labels live in a separate
line-aligned `.lst` file (one `0`/`1` per example); the loader zips each `.jsonl` with its
`.lst` and treats any missing or uninterpretable label as malformed rather than silently
reading it as a single class.

PIQA's `tests.jsonl` is released without gold labels and is excluded. The census runs on the
two labelled splits, `train.jsonl` (16,113 rows) and `valid.jsonl` (1,838 rows), 17,951
labelled examples in all.

## What was found

| split | rows | unique goals | unique triples | triple duplicate groups | triple gold conflicts | goals reused (context) |
| --- | --- | --- | --- | --- | --- | --- |
| train | 16,113 | 14,874 | 16,107 | 6 | 0 | 485 |
| valid | 1,838 | 1,803 | 1,838 | 0 | 0 | 27 |
| combined | 17,951 | 16,531 | 17,944 | 6 | 0 | 522 |

**PIQA's labelled release carries no self-contradicting gold.** Across all 17,951 labelled
examples there is not a single (goal, sol1, sol2) triple that appears twice with conflicting
labels — zero exact conflicts and zero after normalization, in each split and combined.

But unlike BoolQ, PIQA is *not* duplicate-free. Six exact-duplicate triples occur in the
train split (16,113 rows share 16,107 distinct triples), and every one of those six repeats
with the **same** gold label — a consistent duplicate, not a conflict. So the defect this
audit looks for is absent, while a milder redundancy (a handful of verbatim-repeated training
triples) is present and quantified. Goal reuse, the legitimate kind, is heavy and expected:
17,951 rows draw on 16,531 distinct goals, with 522 goals appearing in more than one example.

### Pre-registered predictions

Four predictions were frozen before the real data was read; all four held, and each is
reported as it fell:

| prediction | outcome |
| --- | --- |
| P1 — combined triple gold conflicts ≤ 20 | **held** (0) |
| P2 — valid triple gold conflicts = 0 | **held** (0) |
| P3 — combined goals reused ≥ 1 | **held** (522) |
| P4 — combined triple duplicate groups ≥ 1 | **held** (6) |

P4 is the interesting one: it predicted that *some* verbatim-duplicate triples exist in PIQA,
and six do — all in train, all label-consistent. The audit confirms duplicates without
conflicts, which is a weaker but real data-quality note, not a clean-slate like BoolQ's.

## Files

- `piqa_gold_conflict.py` — the census: `normalize` (whitespace-collapse + lowercase),
  `label_of` (0/1 from the `.lst` label, raising on anything uninterpretable), and `census`
  (exact and normalized (goal, sol1, sol2) duplicates/conflicts, plus goal reuse as context).
- `cases.py` — a pre-registered 7-row synthetic fixture and its hand-traced TARGET
  (exercising an exact conflict, a normalization-only conflict, and legitimate goal reuse),
  frozen before any real data was read.
- `test_piqa_gold_conflict.py` — stdlib `unittest` pinning the census to the fixture and
  covering the label parser and the duplicate/conflict/goal-reuse distinctions.
- `job.py` — downloads the four files itself with a User-Agent header, zips each `.jsonl`
  with its line-aligned `.lst` (fatal on a length mismatch), asserts the fixture before
  touching real data, prints real-data diagnostics, guards against an empty read, checks
  observed row counts against the expected 16,113 / 1,838, records the predictions, and
  writes `results.json`.
- `results.json` — the frozen output of the sealed run (per-split and combined counts,
  fixture check, observed vs expected row counts, and prediction outcomes).

## Limits

- PIQA only (one corpus), and only its two labelled splits; the unlabelled `tests.jsonl`
  carries no gold label to conflict and is out of scope.
- "Near-duplicate" is fixed by the stated normalization (whitespace-collapse and lowercase);
  a different normalizer (punctuation stripping, paraphrase matching) could surface
  near-duplicates this one does not.
- Counts are of distinct (goal, sol1, sol2) triples and distinct goal strings, not of the
  individual rows involved (the triple-conflict-rows figure is reported separately in
  `results.json`).
- Goal reuse is context, not a defect: PIQA pairs each goal with multiple distinct solution
  pairs by design, so the same goal legitimately takes different labels in different examples.
- The census reads the authors' own GitHub Pages repo (`ybisk/ybisk.github.io`), whose four
  uncompressed files match the canonical AI2 distribution; the source is checked by the
  published schema, the canonical first validation example, the per-split row counts
  (16,113 / 1,838), and an exact `.jsonl`/`.lst` length match, so any tampering or
  misalignment would fail the run.

## Licence

Code is Apache-2.0. The pre-registered corpus, `results.json`, and this write-up are
CC BY 4.0. PIQA keeps its own licence (Bisk et al., AAAI 2020; Academic Free License v3.0).
Made by AI agents working in MV2's name (Munim, Inc.).
