# nli-gold-conflict-census

The 20th [eval-reliability audit](../eval-reliability-audits/). A census of the
Stanford Natural Language Inference corpus (SNLI 1.0) for a specific
data-quality defect: the **same** `(premise, hypothesis)` pair appearing twice
within one released split with **different** gold labels. Such a pair cannot be
scored right both times.

## The question

SNLI is built by pairing each premise with three written hypotheses — one meant
to entail it, one to contradict it, one neutral — so **a premise recurring
across different labels is by design, and is not a defect.** This audit does not
count that. It asks a self-consistency question the design does not license:
within a single split, does one identical `(premise, hypothesis)` pair carry
two gold labels at once?

Two keys are used. The **exact** key is the raw string pair. The **normalized**
key lowercases, collapses whitespace and drops a trailing period, to catch
near-duplicate pairs that differ only in surface form. Rows whose gold label is
`-` (no annotator majority) are excluded, since they carry no gold label to
conflict.

## What was found

| split | rows (gold ≠ `-`) | exact conflicting pairs | normalized conflicting pairs |
|-------|------------------:|------------------------:|-----------------------------:|
| train | 549,367 | **64** | **82** |
| dev   | 9,842   | 0 | 0 |
| test  | 9,824   | 0 | 0 |

The evaluation splits (dev, test) are **clean**: no duplicate pair carries
conflicting labels in either. The defect is confined to **train**, where 64
identical pairs and 82 normalized pairs disagree with themselves.

Many of the exact conflicts are rows where the premise and hypothesis are
*identical strings* yet were labelled both `entailment` and `neutral` (a few
even span all three labels):

- premise = hypothesis = "A black dog walks on the beach near the rocks." →
  `{entailment, neutral}`
- premise = hypothesis = "A boy with blue face paint sucks his thumb." →
  `{contradiction, entailment, neutral}`
- premise = hypothesis = "The image links are broken." →
  `{contradiction, entailment, neutral}`

The normalized pass adds genuine near-duplicates, e.g. "A man is walking."
against "a man walking down an alleyway" labelled `{entailment, neutral}`. A
handful of the conflicting rows are degenerate hypotheses ("N/A", "fo",
"Problem. see below") that still received a majority gold label.

## Files

- `nli_consistency.py` — the normalizer and the conflict analyzer over
  `(premise, hypothesis, gold_label)` triples.
- `cases.py` — the pre-registered 6-row synthetic corpus and its frozen
  `TARGET` counts (exact vs normalized conflicts, duplicate pairs).
- `test_nli_consistency.py` — unit tests over the fixture; green in the sealed
  container before the census ran.
- `job.py` — reads the official SNLI zip and censuses each split.
- `results.json` — frozen per-split counts plus the real conflicting pairs
  (up to 50 examples per split).

## Limits

SNLI only (one corpus). The by-design reuse of a premise across labels is
explicitly **not** counted — only a repeated full `(premise, hypothesis)` pair
with differing labels is. "Near-duplicate" is defined precisely by the stated
normalization; a different normalizer would move the boundary. Counts are of
distinct conflicting *pairs*, not of the individual rows involved.

## Licence

Code is Apache-2.0. The corpus, results and write-up are CC BY 4.0. SNLI keeps
its own licence (CC BY-SA 4.0, Bowman et al. 2015). Made by AI agents working in
MV2's name (Munim, Inc.).
