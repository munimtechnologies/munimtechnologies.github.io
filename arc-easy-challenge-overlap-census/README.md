# arc-easy-challenge-overlap-census

The 32nd [eval-reliability audit](../eval-reliability-audits/). It extends the gold-integrity family —
the within-corpus gold-conflict censuses for [SNLI](../nli-gold-conflict-census/),
[MultiNLI](../multinli-gold-conflict-census/), [ANLI](../anli-gold-conflict-census/),
[BoolQ](../boolq-gold-conflict-census/), [PIQA](../piqa-gold-conflict-census/),
[CommonsenseQA](../commonsenseqa-gold-conflict-census/) and
[OpenBookQA](../openbookqa-main-additional-census/), the cross-corpus
[SNLI↔MultiNLI overlap census](../snli-multinli-overlap-census/), and the structural
[WinoGrande nesting census](../winogrande-nested-subset-census/) — to AI2's ARC, a
multiple-choice science benchmark whose two-set construction makes disjointness and leakage
promises nobody has verified on the raw files.

This research is carried out by AI agents working in MV2's name at Munim, Inc., and is disclosed as
AI-made wherever a platform, contest or project asks.

## The question

ARC (Clark et al., 2018) splits 7,787 grade-school science questions into a **Challenge Set** — the
2,590 questions that both a retrieval solver and a word co-occurrence solver answered wrong — and an
**Easy Set** of the remaining 5,197, and ships each set with its own `train`/`dev`/`test` `.jsonl`
files. Each row is `{"id", "question": {"stem", "choices": [{"text","label"}, ...]}, "answerKey"}`.
That construction makes three structural promises a user relies on but that are never checked on the
raw release:

1. **Easy and Challenge are disjoint** — a question is in exactly one set, so training on Easy cannot
   leak a Challenge test item.
2. **No cross-split leakage within a set** — a question in `train` does not reappear in `dev` or
   `test` of the same set.
3. **No self-contradicting duplicate** — no split carries the same question twice with a different
   gold answer.

This census checks all three. A question's **identity** is its normalized
`(stem, frozenset-of-choice-texts)` (whitespace runs collapsed to single spaces, lowercased); its
**gold** is the *text* of the choice whose `label` equals `answerKey`. A row whose `answerKey`
matches no choice label is counted as **malformed** and excluded from the gold comparisons, so it can
neither manufacture nor hide a conflict. Disjointness and leakage are measured both by the dataset's
own stable `id` and by identity, because an `id`-level check misses a question that recurs verbatim
under a different id.

## What was found

The split counts observed at runtime match the published release totals exactly — Challenge
`train` 1,119 / `dev` 299 / `test` 1,172, Easy `train` 2,251 / `dev` 570 / `test` 2,376 (7,787 total),
`rows_as_expected` true — and **no split contains a single malformed row or a missing id**, so this is
a census of the canonical release.

**Easy and Challenge are fully disjoint.** Pooling each set's three splits, they share **0** ids,
**0** identities and therefore **0** gold conflicts. The headline promise holds not just by id but at
the stronger identity level: no question text with the same choice set appears in both sets.

**No question id leaks across the train/dev/test boundary** in either set — every one of the six
cross-split pairs has `shared_ids = 0`. But the identity-level check surfaces something the id check
cannot:

| pair | shared ids | shared identities | gold conflicts |
| --- | --- | --- | --- |
| Challenge `train`\|`dev` | 0 | 0 | 0 |
| Challenge `train`\|`test` | 0 | 0 | 0 |
| Challenge `dev`\|`test` | 0 | 0 | 0 |
| Easy `train`\|`dev` | 0 | 0 | 0 |
| **Easy `train`\|`test`** | **0** | **3** | **0** |
| Easy `dev`\|`test` | 0 | 0 | 0 |

**Three Easy questions recur verbatim across the train→test boundary under different ids.** The same
normalized stem with the same set of answer choices appears once in `train` and once in `test`, each
with its own distinct `id`, and all three carry the **same** gold answer. An id-based dedup (the usual
leakage guard) would pass these straight through; they are a small train/test near-leak that only an
identity-level check catches. None is a gold contradiction.

**One Challenge-train question is an identity duplicate, gold-consistent.** Within-split, every split
has unique ids and no gold conflict; the only duplicated identity anywhere is in Challenge `train`
(1,118 distinct identities over 1,119 rows — one pair of rows shares the same stem and choice set with
the same gold):

| split | rows | unique ids | dup ids | distinct identities | dup-identity groups | gold-conflicting |
| --- | --- | --- | --- | --- | --- | --- |
| Challenge `train` | 1,119 | 1,119 | 0 | 1,118 | **1** | 0 |
| Challenge `dev` | 299 | 299 | 0 | 299 | 0 | 0 |
| Challenge `test` | 1,172 | 1,172 | 0 | 1,172 | 0 | 0 |
| Easy `train` | 2,251 | 2,251 | 0 | 2,251 | 0 | 0 |
| Easy `dev` | 570 | 570 | 0 | 570 | 0 | 0 |
| Easy `test` | 2,376 | 2,376 | 0 | 2,376 | 0 | 0 |

### Pre-registered predictions (frozen before any real data was read)

| | prediction | outcome |
| --- | --- | --- |
| P1 | Easy and Challenge share no question id | **HELD** (0 shared ids) |
| P2 | Easy and Challenge share no question identity | **HELD** (0 shared identities) |
| P3 | no question id leaks across train/dev/test within a set | **HELD** (0 shared ids in all 6 pairs) |
| P4 | no split carries a self-contradicting duplicate question | **HELD** (0 gold conflicts anywhere) |

All four held — ARC keeps its id-level disjointness and leakage promises cleanly, and carries no gold
contradiction. The audit's own contribution is the identity-level layer the predictions did not bet
on: three Easy questions do recur verbatim across the train/test boundary under different ids, and one
Challenge-train question is a verbatim duplicate. Both are gold-consistent, so they are latent
near-duplicates rather than errors — but a leakage guard that keys only on `id` would not see them.

## Files

- `arc_consistency.py` — the census: `parse_row` (accepts both the raw nested ARC shape and the flat
  HuggingFace shape), `within_file` duplicate/gold-conflict detection on the
  `(stem, choice-set)` identity, and `overlap` for shared ids, shared identities and shared-identity
  gold conflicts between any two splits.
- `cases.py` — a hand-traced synthetic fixture (two mini-splits exercising a within-split gold
  conflict, a malformed row, a shared id, and a shared identity with and without a gold conflict) with
  its counts frozen in `TARGET`, asserted before any real data is touched.
- `test_arc_consistency.py` — stdlib `unittest` tests (fixture check, the flat-HF shape, the
  duplicate-vs-conflict distinction, malformed handling, overlap counting, a disjoint control).
- `job.py` — reads the six splits straight from the official `ARC-V1-Feb2018.zip`, verifies per-split
  counts against the published totals, runs the within-split, Easy↔Challenge and cross-split censuses,
  records the predictions, and writes `results.json`.
- `results.json` — the frozen output of the sealed-container run.

## Limits

- One dataset, one checker, one identity definition (`(stem, frozenset of choice texts)` with
  whitespace and case normalized). A paraphrase-level near-duplicate is intentionally **not** treated
  as the same identity and is out of scope.
- The frozenset-of-choice-texts identity ignores choice order and option labels, so two questions with
  the same stem and the same *set* of choices count as one identity even if the choices are ordered
  differently; this is deliberate (the answer text, not the label, defines the gold).
- The census reports the *count* and location of the duplicate and recurring identities, not their
  text.
- ARC-V1-Feb2018 is the original release used here; later packagings (e.g. the HuggingFace
  `allenai/ai2_arc`) are re-serializations of the same questions.

## Licence

Code is Apache-2.0. The result and this write-up are CC BY 4.0. AI2 ARC (ARC-V1-Feb2018) is released
under CC BY-SA 4.0 (Clark, Cowhey, Etzioni, Khot, Sabharwal, Schoenick and Tafjord, "Think you have
Solved Question Answering? Try ARC, the AI2 Reasoning Challenge", 2018). Authored by AI agents working
in MV2's name (Munim, Inc.).
