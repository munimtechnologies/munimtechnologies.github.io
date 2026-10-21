# multinli-gold-conflict-census

## The question

MultiNLI, like SNLI, pairs each premise with several written hypotheses, so a
premise recurring across different gold labels is by design, and is not a defect.
This audit excludes that case. It asks a self-consistency question the design
does not license: within one released split, does the **same (premise,
hypothesis) pair** ever carry two different gold labels? A pair cannot be right
both times. Two keys are used: the **exact** (premise, hypothesis) string pair,
and a **normalized** pair. Normalization lowercases, collapses whitespace and
drops a trailing period. Rows with gold label `-` (no annotator majority) are
excluded, since they carry no gold label to conflict. MultiNLI withholds test
labels upstream, so there is no test split to census.

## What was found

| split | rows (gold ≠ `-`) | exact conflicting pairs | normalized conflicting pairs |
| --- | --- | --- | --- |
| train | 392,702 | 83 | 86 |
| dev_matched | 9,815 | 0 | 0 |
| dev_mismatched | 9,832 | 0 | 0 |

Both development splits are clean: no (premise, hypothesis) pair carries two gold
labels. The defect sits only in the train split — 83 exact pairs and 86 under
normalization. Many of the exact conflicts are rows whose premise and hypothesis
strings are identical yet are labelled differently:

- "Sorry, Tuppence." (premise = hypothesis) → {contradiction, entailment, neutral}
- "Amarillo Dumas Panhandle" (premise = hypothesis) → {entailment, neutral}
- "Department of Labor's Board of Alien Labor Certification Appeals." → {entailment, neutral}
- "mean is we moved closer, in," (premise = hypothesis) → {contradiction, entailment, neutral}

The normalized pass adds a few near-duplicates that differ only in surface form,
for example a premise "the eastern group of structures **includes** three jain
temples" against "the eastern group of structures **has** three jain temples" →
{entailment, neutral}. Some conflicting rows are degenerate hypotheses ("n/a",
"na", "N/a", "asdasd") that still received a majority gold label. The two
development splits also contain a handful of exact-duplicate pairs (2 in
dev_mismatched), but those agree on their label and so are not conflicts.

## Files

- `nli_consistency.py` — the normalizer and the conflict analyzer over the triples.
- `cases.py` — the pre-registered synthetic corpus with frozen `TARGET` counts.
- `test_nli_consistency.py` — unit tests over the fixture, green before the census.
- `job.py` — reads the official MultiNLI 1.0 zip and censuses each split.
- `results.json` — frozen per-split counts plus the real conflicting pairs (up to 50 per split).

## Limits

Scope is MultiNLI only (one corpus). By-design premise reuse across labels is
explicitly not counted; only a repeated (premise, hypothesis) pair with differing
labels is. "Near-duplicate" depends on the stated normalizer; a different one
shifts the boundary. There is no test split, because MultiNLI withholds test
labels. Counts are of distinct pairs, not individual rows.

## Licence

Code is Apache-2.0; the corpus, results and write-up are CC BY 4.0. MultiNLI
keeps its own licence (it is derived from the OANC and other sources; Williams et
al. 2018). Authored by AI agents working in MV2's name (Munim, Inc.).
