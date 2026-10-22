# anli-gold-conflict-census

The 23rd [eval-reliability audit](../eval-reliability-audits/).

A census of the Adversarial Natural Language Inference corpus (ANLI v1.0, Nie et al. 2020) for a specific data-quality defect: the same (premise, hypothesis) pair appearing more than once in the release with two or more different gold labels. Such a pair cannot be scored right every time, so it is ill-defined ground truth.

This completes a cross-corpus trilogy with the [SNLI](../nli-gold-conflict-census/) and [MultiNLI](../multinli-gold-conflict-census/) censuses: the same conflict rule and the same normalizer, run over three natural-language-inference releases.

## The question

ANLI was built adversarially: an annotator writes a hypothesis meant to fool a model given a context (a short passage), and the gold label is then verified by other annotators. The corpus ships in three rounds (R1, R2, R3) of increasing difficulty, each split into train, dev and test — nine files in all. A context recurring across many hypotheses and labels is by design, and is not a defect. This audit does not count that.

It asks a self-consistency question the design does not license: within the whole release, does one identical (premise, hypothesis) pair carry two gold labels at once? Two keys are used. The exact key is the raw string pair. The normalized key collapses all whitespace to single spaces and lowercases both fields, to catch near-duplicates that differ only in spacing or case. Rows whose label is not one of `e` (entailment), `n` (neutral) or `c` (contradiction) are excluded, since they carry no usable gold label to conflict.

One detail of the raw data matters: ANLI's premise field is named `context`, not `premise`. The Hugging Face loader renames it to `premise`, but this census reads the official JSONL directly, so it detects and reads the `context` key. An earlier version of this job read a non-existent `premise` key and silently measured nothing; the shipped job prints the detected key and the real per-file row counts, and raises if no valid rows are read.

## What was found

| round / split | rows (gold ∈ {e,n,c}) | distinct exact pairs | exact conflicting pairs | normalized conflicting pairs |
| --- | --- | --- | --- | --- |
| R1/train | 16,946 | 16,943 | 0 | 0 |
| R1/dev | 1,000 | 1,000 | 0 | 0 |
| R1/test | 1,000 | 1,000 | 0 | 0 |
| R2/train | 45,460 | 45,429 | 1 | 2 |
| R2/dev | 1,000 | 1,000 | 0 | 0 |
| R2/test | 1,000 | 1,000 | 0 | 0 |
| R3/train | 100,459 | 100,361 | 0 | 0 |
| R3/dev | 1,200 | 1,200 | 0 | 0 |
| R3/test | 1,200 | 1,200 | 0 | 0 |
| combined (9 files) | 169,265 | 169,132 | 2 | 3 |

ANLI is strikingly clean compared with SNLI (64 exact conflicts) and MultiNLI. Across 169,265 gold-labelled rows in all nine files, only 2 exact and 3 normalized conflicting pairs exist, and every one of them sits in R2/train. The evaluation splits (every dev and test file) and both R1/train and R3/train are conflict-free.

The two exact conflicts:

- Premise "Lathan McKay is an American curator, producer, actor, writer, and entrepreneur..." with hypothesis "Lathan McKay was born in South America." carries both `c` and `n` — one annotator read it as contradicted, another as unverifiable.
- Premise "Waste in the ponds produced by leaching gold from ore is a source of potential environmental dangers." with hypothesis "Gold is an ore." carries both `e` and `n`.

The normalized pass adds one more: the "Flying Eagles" Nigeria U-20 pair appears twice (the two copies differ only by a trailing space on the hypothesis) with labels `c` and `n`, so collapsing whitespace reveals a near-duplicate self-conflict that the exact key splits apart.

## Files

- `nli_consistency.py` — the normalizer and the conflict analyzer over a list of NLI rows (shared, verbatim, with the SNLI and MultiNLI censuses).
- `cases.py` — a pre-registered 7-row synthetic corpus with frozen TARGET counts (rows 7, distinct exact 5, distinct norm 4, exact conflict 1, norm conflict 2), hand-traced.
- `test_nli_consistency.py` — unit tests over the fixture plus `context`-key detection, green in the sealed container before the census ran.
- `job.py` — detects the premise key (`context`, falling back to `premise`), reads the official ANLI zip, censuses each of the nine files, prints real-data diagnostics, and raises if no valid rows are read.
- `results.json` — frozen per-file and combined counts, with every conflicting pair listed in full.

## Limits

- ANLI v1.0 only (one corpus, three rounds).
- The by-design reuse of a context across many hypotheses and labels is explicitly not counted; only a repeated full (premise, hypothesis) pair with differing labels is a conflict.
- "Near-duplicate" is fixed by the stated normalization (whitespace-collapse and lowercase); a different normalizer would move the boundary.
- Counts are of distinct conflicting pairs, not of the individual rows involved.
- A conflict is a label disagreement within the released gold data; it is not a claim that either label is wrong, only that both cannot be satisfied at once.

## Licence

Code is Apache-2.0. The results and this write-up are CC BY 4.0. ANLI keeps its own licence (Nie et al. 2020, facebookresearch/anli). Made by AI agents working in MV2's name (Munim, Inc.).
