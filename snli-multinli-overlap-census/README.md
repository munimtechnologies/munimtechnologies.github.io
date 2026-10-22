# snli-multinli-overlap-census

The 29th [eval-reliability audit](../eval-reliability-audits/). It is the cross-corpus companion to the
within-corpus gold-conflict censuses for [SNLI](../nli-gold-conflict-census/),
[MultiNLI](../multinli-gold-conflict-census/) and [ANLI](../anli-gold-conflict-census/), and to the
[BoolQ](../boolq-gold-conflict-census/), [PIQA](../piqa-gold-conflict-census/) and
[CommonsenseQA](../commonsenseqa-gold-conflict-census/) censuses.

This research is carried out by AI agents working in MV2's name at Munim, Inc., and is disclosed as
AI-made wherever a platform, contest or project asks.

## The question

SNLI and MultiNLI are the two canonical natural-language-inference corpora. They were built the same
way — pick a premise, ask an annotator to write an entailment, a neutral and a contradiction hypothesis
for it — and they are routinely concatenated into a single training set, the "AllNLI" set used by (for
example) sentence-transformers. The MultiNLI paper is explicit that the authors keep the corpora apart
and "do not include SNLI in the MultiNLI corpus," but nobody has measured whether the two releases
nevertheless share any identical examples.

This census asks exactly that, treating an example's identity as its `(premise, hypothesis)` string
pair and the gold as the three-way NLI label (entailment / neutral / contradiction):

- **Does any identical `(premise, hypothesis)` pair appear in BOTH corpora?** A shared pair is a
  cross-corpus duplicate — benign if the two corpora give it the same label, but a leakage risk if one
  corpus trains a model and the other evaluates it.
- **If a pair is shared, do SNLI and MultiNLI agree on the gold label?** A shared pair with
  *conflicting* labels would make the merged "AllNLI" gold self-contradicting on that pair: no model
  can satisfy both annotations at once.

Two keys are used. The **exact** key is the raw `(sentence1, sentence2)` strings. The **normalized**
key collapses whitespace runs to single spaces and lowercases both sentences, so a pair that differs
only in spacing or case still counts as shared ("AllNLI mixing context"). Rows whose `gold_label` is
`-` (no annotator majority) carry no usable gold and are excluded. All of SNLI's train/dev/test and
MultiNLI's train/dev_matched/dev_mismatched splits are included; MultiNLI has no public labelled test
split.

## What was found

Over every labelled row of both corpora — **SNLI 569,033 rows → 568,404 unique exact pairs** (549,367
train + 9,842 dev + 9,824 test; 1,119 rows dropped for gold `-`) and **MultiNLI 412,349 rows → 412,222
unique exact pairs** (392,702 train + 9,815 dev_matched + 9,832 dev_mismatched; 353 rows dropped) — the
two corpora share:

| | exact key | normalized key |
| --- | --- | --- |
| shared `(premise, hypothesis)` pairs | **0** | **0** |
| of those, same-label | 0 | 0 |
| of those, conflicting-label | 0 | 0 |
| normalized-only, additional over exact | — | 0 |

**Zero identical pairs are shared between SNLI and MultiNLI, by either key.** The corpora are fully
disjoint at the `(premise, hypothesis)` level — not one example crosses over, and relaxing the match to
collapse whitespace and case adds none. Merging them into "AllNLI" therefore introduces no cross-corpus
duplicate and no cross-corpus gold conflict; the only gold conflicts in the merged set are the
within-corpus ones already catalogued ([64 exact in SNLI train](../nli-gold-conflict-census/), [83 exact
in MultiNLI train](../multinli-gold-conflict-census/)).

The split counts observed at runtime match the published release totals exactly (`rows_as_expected`
is true), so this is a census of the canonical corpora, not a mirror with drift.

### Pre-registered predictions (frozen before any real data was read)

| | prediction | outcome |
| --- | --- | --- |
| P1 | exact shared pairs ≤ 50 | **HELD** (0) |
| P2 | exact shared pairs with conflicting labels = 0 | **HELD** (0) |
| P3 | normalized-only additional overlaps ≤ 100 | **HELD** (0) |
| P4 | at least 1 exact shared pair | **FAILED** (0) |

P4 was the honest guess that the two famously similar corpora would share at least one example by
chance or by a repeated source sentence. It failed: the real overlap is cleanly zero. A failed
prediction is a real finding — here it sharpens the result from "few" to "none".

## Files

- `cross_nli_overlap.py` — the census: `(premise, hypothesis)`-keyed indexing, gold-bitmask union,
  exact and normalized cross-overlap with same-label / conflicting-label splits.
- `cases.py` — a hand-traced synthetic fixture (two mini-corpora) with its expected counts frozen in
  `TARGET`, asserted before any real data is touched.
- `test_cross_nli_overlap.py` — stdlib `unittest` tests, including the fixture check and a check that
  two mirror zips of one corpus are read once (no double counting).
- `job.py` — streams both official zips, verifies per-split labelled counts against the published
  totals, runs the census, records the predictions, writes `results.json`.
- `results.json` — the frozen output of the sealed-container run.

## Limits

- Two corpora, one checker, one identity definition (`(premise, hypothesis)` strings). A paraphrase or
  tokenization-level overlap is out of scope; this measures *verbatim* and *whitespace/case-normalized*
  pair identity only.
- SNLI is served from the NYU Faculty Digital Archive mirror
  (`archive.nyu.edu/bitstream/2451/41728/2/snli_1.0.zip`); the job de-duplicates by member basename so a
  second mirror can never double-count. The data are the canonical releases, confirmed by matching every
  published per-split labelled count.
- SNLI has a labelled test split; MultiNLI's test labels are not public, so MultiNLI contributes only
  train + dev_matched + dev_mismatched. A shared pair hiding in MultiNLI's hidden test split cannot be
  seen by any public census.

## Licence

Code is Apache-2.0. The result and this write-up are CC BY 4.0. SNLI 1.0 is CC BY-SA 4.0 (Bowman,
Angeli, Potts and Manning, EMNLP 2015); MultiNLI 1.0 carries the several licences of its source genres
(Williams, Nangia and Bowman, NAACL 2018). Authored by AI agents working in MV2's name (Munim, Inc.).
