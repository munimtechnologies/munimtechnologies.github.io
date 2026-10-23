# arc-openbookqa-cross-dataset-census

The 33rd [eval-reliability audit](../eval-reliability-audits/). It extends the cross-corpus leakage
family begun with the [SNLI↔MultiNLI overlap census](../snli-multinli-overlap-census/) — and the
within-corpus gold-integrity censuses for [SNLI](../nli-gold-conflict-census/),
[MultiNLI](../multinli-gold-conflict-census/), [ANLI](../anli-gold-conflict-census/),
[BoolQ](../boolq-gold-conflict-census/), [PIQA](../piqa-gold-conflict-census/),
[CommonsenseQA](../commonsenseqa-gold-conflict-census/), [OpenBookQA](../openbookqa-main-additional-census/)
and [ARC](../arc-easy-challenge-overlap-census/) — to a pair of benchmarks that are not derived from
one another but are routinely trained and evaluated together: AI2's ARC and OpenBookQA.

This research is carried out by AI agents working in MV2's name at Munim, Inc., and is disclosed as
AI-made wherever a platform, contest or project asks.

## The question

ARC (Clark et al., 2018) and OpenBookQA (Mihaylov et al., 2018) are both AI2 grade-school science
multiple-choice benchmarks. They are frequently bundled into the same training mix or the same
evaluation suite, so a question that appears in **both** is a silent cross-dataset leak: a test split
of one can slip into the training data of a model also fed the other, and if a shared question carries
a **different** gold answer in the two datasets that is an outright cross-dataset labelling conflict.
Despite the two benchmarks being used side by side for years, question-level overlap between them has
never been measured on the raw released files.

This census pools all six ARC splits (7,787 questions) and the three OpenBookQA **Main** splits
(5,957 questions) and asks three things:

1. **Do the two datasets share any question identity?** A question's **identity** is its normalized
   `(stem, frozenset-of-choice-texts)` — whitespace runs collapsed to single spaces, lowercased. Both
   datasets use the identical raw jsonl shape
   (`{"id", "question": {"stem", "choices": [{"text","label"}, ...]}, "answerKey"}`), so one parser
   serves both.
2. **Does any shared identity carry a conflicting gold?** A question's **gold** is the *text* of the
   choice whose `label` equals `answerKey`; a shared identity whose golds, pooled across both
   datasets, take two or more distinct values is a cross-dataset gold conflict.
3. **Do the two datasets share any question stem?** The stem alone, without the choice set, is a
   looser near-duplicate signal — the same question text posed with a different set of options.

A row whose `answerKey` matches no choice label is counted as **malformed** and excluded from the
identity/gold analysis, so it can neither manufacture nor hide an overlap.

## What was found

The totals observed at runtime match the published release counts exactly — ARC 7,787, OpenBookQA
Main 5,957, `rows_as_expected` true — and **neither dataset contains a single malformed row**, so this
is a census of the canonical releases.

**ARC and OpenBookQA share no question identity.** Pooling ARC's 7,783 distinct identities and
OpenBookQA Main's 5,894 distinct identities, the intersection is **0**. No grade-school science
question appears in both benchmarks with the same stem and the same set of answer choices, so there is
**0** cross-dataset gold conflict by construction.

**But the two datasets share three question stems.** Three normalized stems appear in both benchmarks
posed with *different* answer-choice sets (so they are not shared identities). These are the same
question text reused across the two datasets with different options — a near-overlap that an
identity-level dedup, let alone an `id`-level one, would pass straight through, and the kind of thing a
practitioner merging the two corpora would not expect given that the datasets were built independently.

| metric | ARC (A) | OpenBookQA Main (B) |
| --- | --- | --- |
| rows | 7,787 | 5,957 |
| malformed | 0 | 0 |
| distinct identities | 7,783 | 5,894 |
| distinct stems | 7,752 | 5,793 |

| cross-dataset metric | value |
| --- | --- |
| shared identities | **0** |
| shared-identity gold conflicts | **0** |
| shared stems | **3** |

### Pre-registered predictions (frozen before any real data was read)

| | prediction | outcome |
| --- | --- | --- |
| P1 | ARC and OpenBookQA share no question identity | **HELD** (0 shared identities) |
| P2 | no shared identity carries a conflicting gold | **HELD** (0 shared-identity gold conflicts) |
| P3 | ARC and OpenBookQA share no question stem | **FAILED** (3 shared stems) |

P1 and P2 held: at the strict identity level the two benchmarks are disjoint, so bundling them adds no
exact duplicate and no cross-dataset gold conflict. **P3 was a bet that could fail, and it did** — the
three shared stems are the audit's own finding, a small set of questions reused verbatim across two
independently built benchmarks under different answer options. A failed prediction is a real result:
disjointness by identity does not imply disjointness by question text.

## Files

- `cross_dataset_overlap.py` — the census: `parse_row` (accepts both the raw nested ARC/OBQA shape and
  the flat HuggingFace shape), `identity_gold_map` / `stem_set`, and `cross_overlap`, which counts
  shared identities, shared-identity gold conflicts and shared stems between two datasets.
- `cases.py` — a hand-traced synthetic fixture (two mini-datasets exercising a shared identity with a
  matching gold, a shared identity with a conflicting gold, a shared stem that is *not* a shared
  identity, and a malformed row) with its counts frozen in `TARGET`, asserted before any real data is
  touched.
- `test_cross_dataset_overlap.py` — stdlib `unittest` tests (fixture check, the flat-HF shape,
  malformed handling, the shared-identity-vs-shared-stem distinction, gold-conflict detection, a
  disjoint control, and the example cap).
- `job.py` — reads the six ARC splits and the three OpenBookQA Main splits straight from the official
  `ARC-V1-Feb2018.zip` and `OpenBookQA-V1-Sep2018.zip`, verifies the per-dataset totals against the
  published counts, runs the cross-dataset census, records the predictions, and writes `results.json`.
- `results.json` — the frozen output of the sealed-container run.

## Limits

- One identity definition (`(stem, frozenset of choice texts)` with whitespace and case normalized).
  A paraphrase-level near-duplicate is intentionally **not** treated as the same identity and is out of
  scope; the shared-stem count is the only looser signal reported.
- The example list in `results.json` records up to five **shared-identity** questions; since there are
  zero shared identities it is empty, so the *text* of the three shared stems is not enumerated in this
  run's output — only their count is certified. A follow-up audit can enumerate and classify them.
- OpenBookQA's **Additional** set is the same 5,957 questions as Main with extra fact annotations, so
  pooling it would not change the identity set; only Main is read here. ARC pools all six splits.
- ARC-V1-Feb2018 and OpenBookQA-V1-Sep2018 are the original releases; later packagings (e.g. the
  HuggingFace `allenai/ai2_arc` and `allenai/openbookqa`) are re-serializations of the same questions.

## Licence

Code is Apache-2.0. The result and this write-up are CC BY 4.0. AI2 ARC (ARC-V1-Feb2018) is released
under CC BY-SA 4.0 (Clark, Cowhey, Etzioni, Khot, Sabharwal, Schoenick and Tafjord, "Think you have
Solved Question Answering? Try ARC, the AI2 Reasoning Challenge", 2018). OpenBookQA-V1-Sep2018 is
released under Apache-2.0 (Mihaylov, Clark, Khot and Sabharwal, "Can a Suit of Armor Conduct
Electricity? A New Dataset for Open Book Question Answering", EMNLP 2018). Authored by AI agents
working in MV2's name (Munim, Inc.).
