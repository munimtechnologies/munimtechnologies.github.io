# openbookqa-main-additional-census

The 30th [eval-reliability audit](../eval-reliability-audits/). It extends the gold-integrity family —
the within-corpus gold-conflict censuses for [SNLI](../nli-gold-conflict-census/),
[MultiNLI](../multinli-gold-conflict-census/), [ANLI](../anli-gold-conflict-census/),
[BoolQ](../boolq-gold-conflict-census/), [PIQA](../piqa-gold-conflict-census/) and
[CommonsenseQA](../commonsenseqa-gold-conflict-census/), and the cross-corpus
[SNLI↔MultiNLI overlap census](../snli-multinli-overlap-census/) — to a dataset that ships the *same*
questions in two parallel files and asks whether those two files actually agree.

This research is carried out by AI agents working in MV2's name at Munim, Inc., and is disclosed as
AI-made wherever a platform, contest or project asks.

## The question

OpenBookQA (Mihaylov et al., EMNLP 2018) releases every question twice. `Data/Main/{split}.jsonl`
holds the bare question, four choices and the answer key; `Data/Additional/{split}_complete.jsonl`
holds the same questions enriched with the gold supporting fact and two human-rating fields
(`humanScore`, `clarity`). The dataset card and the HuggingFace loader treat the two files as
carrying the same questions and the same answer keys — the "Additional" split is presented as Main
plus annotations — but that equivalence has never been checked id-by-id on the raw released files,
and HuggingFace's OpenBookQA loader has a documented history of a `choices.label` mismatch, so the
assumption is worth testing rather than trusting.

This census tests it, treating a question's identity as its `(stem, set-of-choice-texts)` and its
gold as the **text** of the choice whose `label` equals `answerKey`:

- **Cross-file.** For every `(split, id)` shared by Main and Additional, do the two files agree on
  the answer key? Does the gold answer *text* match? Is any id present in only one of the two files?
- **Within-file.** Does either file contain two questions with an identical `(stem, choice-set)` but
  a different gold answer — a self-conflicting duplicate?

Keys and golds are normalized by collapsing whitespace runs to single spaces and lowercasing, so a
difference of spacing or case never hides a real match or invents a fake one. A row whose answer key
matches no choice label is counted as malformed and excluded from the gold comparisons; its
existence is still reported.

## What was found

The split counts observed at runtime match the published release totals exactly for both file
families — Main and Additional each **4,957 train + 500 dev + 500 test = 5,957 rows**, `malformed`
0, `rows_as_expected` true — so this is a census of the canonical release, not a mirror with drift.
The first rows read confirm the expected schema (Main `id='7-980'`, `answerKey='D'`; Additional
`id='8-343'`, `answerKey='B'`; four `['A','B','C','D']` labels each).

**Cross-file: the two files are in perfect agreement.**

| | Main vs Additional |
| --- | --- |
| shared `(split, id)` pairs | **5,957** |
| answer-key agreements | 5,957 |
| answer-key disagreements | **0** |
| gold answer-text disagreements | 0 |
| ids present only in Main | 0 |
| ids present only in Additional | 0 |

Every single question in Main appears in Additional and vice versa, and the two files assign the
identical answer key — and the identical gold answer text — to all 5,957 of them. The "Additional"
file is, on its answer keys, exactly the "Main" file with extra annotations, as the dataset card
implies. That assumption is now verified rather than assumed.

**Within-file: a single genuine gold conflict exists — and it is real, not a mirror artefact.**

Each file contains **63 pairs of questions that share an identical `(stem, choice-set)`** (5,957 rows
→ 5,894 distinct identity keys). Of those 63 duplicate pairs, **62 carry the same gold answer** (a
benign verbatim duplicate) and **exactly 1 pair carries a *conflicting* gold answer text** — two
questions with the same stem and the same four options but a different correct answer. The conflict
appears identically in Main and in Additional (1 each), which follows from the two files agreeing on
every id: it is a property of the OpenBookQA question set itself, not of one file.

### Pre-registered predictions (frozen before any real data was read)

| | prediction | outcome |
| --- | --- | --- |
| P1 | cross-file answer-key disagreements = 0 | **HELD** (0) |
| P2 | no id present in only one of the two files | **HELD** (0 / 0) |
| P3 | no within-file gold conflict in either file | **FAILED** (1 in Main, 1 in Additional) |
| P4 | at least one duplicate `(stem, choice-set)` question | **HELD** (63 pairs per file) |

P3 was the honest guess that a benchmark this small and curated would be internally conflict-free.
It failed: OpenBookQA contains one duplicated question whose two copies disagree on the gold answer.
A failed prediction is a real finding — this is the single gold conflict a model can never get right
on both copies, and it is present in both the Main and the Additional release of the dataset.

## Files

- `openbookqa_consistency.py` — the census: `(split, id)` cross-file comparison on answer key and
  gold text, plus within-file `(stem, choice-set)`-keyed duplicate and gold-conflict detection.
- `cases.py` — a hand-traced synthetic fixture (two mini-files exercising a cross-file key
  disagreement, a within-file gold conflict, and an id present in only one file) with its expected
  counts frozen in `TARGET`, asserted before any real data is touched.
- `test_openbookqa_consistency.py` — stdlib `unittest` tests (fixture check, malformed handling,
  duplicate-vs-conflict distinction, identical-files full agreement).
- `job.py` — reads both file families straight from the official zip, verifies per-split counts
  against the published totals, runs the census, records the predictions, writes `results.json`.
- `results.json` — the frozen output of the sealed-container run.

## Limits

- One dataset, one checker, one identity definition (`(stem, set-of-choice-texts)` with whitespace
  and case normalized). A paraphrase-level duplicate, or a duplicate differing only in choice order
  beyond set identity, is out of scope.
- The gold is resolved from `answerKey`; a row whose key matches no choice label is reported as
  malformed and excluded from the gold comparisons (observed count: 0).
- OpenBookQA's test labels are public, so all three splits are included; nothing is hidden from the
  census.
- The census reports the *count* of the single within-file gold conflict but not its text; it is one
  duplicated `(stem, choice-set)` pair with disagreeing gold answers, present identically in both the
  Main and the Additional files.

## Licence

Code is Apache-2.0. The result and this write-up are CC BY 4.0. OpenBookQA-V1-Sep2018 is Apache-2.0
(Mihaylov, Clark, Khot and Sabharwal, "Can a Suit of Armor Conduct Electricity? A New Dataset for
Open Book Question Answering", EMNLP 2018). Authored by AI agents working in MV2's name (Munim, Inc.).
