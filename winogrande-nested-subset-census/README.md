# winogrande-nested-subset-census

The 31st [eval-reliability audit](../eval-reliability-audits/). It extends the gold-integrity family —
the within-corpus gold-conflict censuses for [SNLI](../nli-gold-conflict-census/),
[MultiNLI](../multinli-gold-conflict-census/), [ANLI](../anli-gold-conflict-census/),
[BoolQ](../boolq-gold-conflict-census/), [PIQA](../piqa-gold-conflict-census/),
[CommonsenseQA](../commonsenseqa-gold-conflict-census/) and
[OpenBookQA](../openbookqa-main-additional-census/), and the cross-corpus
[SNLI↔MultiNLI overlap census](../snli-multinli-overlap-census/) — to a benchmark whose releases make
a *structural* promise: that its five training sizes are exact nested subsets of one another.

This research is carried out by AI agents working in MV2's name at Munim, Inc., and is disclosed as
AI-made wherever a platform, contest or project asks.

## The question

WinoGrande (Sakaguchi et al., AAAI 2020) ships its training set in five sizes —
`train_xs` ⊂ `train_s` ⊂ `train_m` ⊂ `train_l` ⊂ `train_xl` — plus a `dev` split, each as a
`.jsonl` file of `{qID, sentence, option1, option2, answer}` objects alongside a parallel
`-labels.lst`. AllenAI's dataset card states that "these training sets are nested subsets of each
other (e.g. all the instances in xs are in s)", and because WinoGrande has no official validation
split, at least one published adaptation benchmark *builds* one out of the instances unique to
`train_xl` — a construction that is only sound if the nesting is exact. That promise, and the
companion assumptions a user relies on when training on these files, have never been checked
id-by-id on the raw release.

This census checks four of them. A question's **identity** is its normalized
`(sentence, option1, option2)` triple (whitespace runs collapsed to single spaces, lowercased); its
**gold** is the `answer` field (`"1"` or `"2"`).

- **Nesting (P1/P2).** For each adjacent pair (`xs→s`, `s→m`, `m→l`, `l→xl`): is every `qID` in the
  smaller size present in the larger one, and does a shared `qID` keep the same gold answer?
- **Within-split gold conflicts (P3).** Does any split contain two rows with an identical identity
  but a different gold — a self-contradicting duplicate?
- **Train/dev leakage (P4).** Does `dev` share any `qID` (or any identity) with `train_xl`?
- **Label cross-check.** Do the inline `answer` fields match the parallel `-labels.lst` files
  line-for-line?

## What was found

The split counts observed at runtime match the published release totals exactly — `xs` 160, `s` 640,
`m` 2,558, `l` 10,234, `xl` 40,398, `dev` 1,267, `rows_as_expected` true — so this is a census of the
canonical release, not a mirror with drift. The first row read confirms the expected schema
(`qID='3QHITW7OYO7Q6B6ISU2UMJB84ZLAQE-2'`, `option1='Ian'`, `option2='Dennis'`, `answer='2'`).

**The nesting promise holds exactly.** For all four adjacent pairs, every `qID` in the smaller size
is present in the next larger size, and every shared `qID` keeps the same gold answer:

| pair | qIDs in smaller | shared with larger | missing from larger | answer conflicts |
| --- | --- | --- | --- | --- |
| `xs→s` | 160 | 160 | **0** | **0** |
| `s→m` | 640 | 640 | **0** | **0** |
| `m→l` | 2,558 | 2,558 | **0** | **0** |
| `l→xl` | 10,234 | 10,234 | **0** | **0** |

So `train_xs ⊂ train_s ⊂ train_m ⊂ train_l ⊂ train_xl` is an exact nesting by `qID`, with no gold
flipping across sizes — the structural promise the dataset card makes and that downstream work relies
on is now verified rather than assumed. The `dev` split is also clean: it shares **0** `qID`s and
**0** identities with `train_xl`, so the common "validation = xl-unique instances" construction
introduces no train/dev leakage. And the inline `answer` fields match the `-labels.lst` files exactly
in every split (**0** mismatches across all 53,990 training rows + 1,267 dev rows).

**But `train_xl` contains two verbatim-identical questions with opposite gold answers.** Treating
identity as the exact `(sentence, option1, option2)` triple:

| split | rows | distinct identities | duplicate-identity groups | of those, gold-**conflicting** |
| --- | --- | --- | --- | --- |
| `xs` | 160 | 160 | 0 | 0 |
| `s` | 640 | 638 | 2 | 0 |
| `m` | 2,558 | 2,556 | 2 | 0 |
| `l` | 10,234 | 10,232 | 2 | 0 |
| `xl` | 40,398 | 40,394 | **4** | **2** |
| `dev` | 1,267 | 1,267 | 0 | 0 |

Two identity groups are already duplicated at the `s` size and stay benign all the way up — the same
sentence and options appear twice with the *same* gold. Two further identity groups appear only once
`train_xl` is reached, and **both of those carry conflicting gold**: the identical sentence with the
identical two options is labelled `answer='1'` in one row and `answer='2'` in another. These are not
WinoGrande's intentional *twins* — a twin pair differs in its trigger word, so the two sentences are
not identical and never share an identity here. These two are genuine self-contradictions in the
largest training split: a model cannot be right on both copies, and the contradiction is invisible to
anyone training on a smaller size.

### Pre-registered predictions (frozen before any real data was read)

| | prediction | outcome |
| --- | --- | --- |
| P1 | nesting holds; no `qID` in a smaller size is lost from the larger | **HELD** (0 lost across all 4 pairs) |
| P2 | no shared `qID` flips its gold across sizes | **HELD** (0 cross-size conflicts) |
| P3 | no split contains a self-conflicting duplicate identity | **FAILED** (2 in `train_xl`) |
| P4 | `dev` shares no `qID` with `train_xl` | **HELD** (0 shared) |

P3 was the honest guess that a curated, adversarially-filtered benchmark would carry no
verbatim-identical question with two different golds. It failed: `train_xl` has two. A failed
prediction is a real finding — these are the two training items on which the released gold
contradicts itself, present only at the `xl` size and consistent with every other integrity check
passing.

## Files

- `winogrande_consistency.py` — the census: per-split `within_file` duplicate/gold-conflict
  detection on the `(sentence, option1, option2)` identity, adjacent-pair `nesting` subset-and-gold
  checks, and a `dev`-vs-`xl` `overlap` leakage check.
- `cases.py` — a hand-traced synthetic fixture (two mini-splits exercising a nesting violation, a
  cross-size gold flip, a within-file gold conflict and a benign duplicate) with its counts frozen in
  `TARGET`, asserted before any real data is touched.
- `test_winogrande_consistency.py` — stdlib `unittest` tests (fixture check, the duplicate-vs-conflict
  distinction, a perfect-subset control, overlap counting).
- `job.py` — reads the five nested sizes plus `dev` straight from the official zip, verifies per-split
  counts against the published totals, runs the census, cross-checks the inline answers against the
  `-labels.lst` files, records the predictions, writes `results.json`.
- `results.json` — the frozen output of the sealed-container run.

## Limits

- One dataset, one checker, one identity definition (`(sentence, option1, option2)` with whitespace
  and case normalized). A paraphrase-level near-duplicate, or a twin differing only in its trigger
  word, is intentionally **not** treated as the same identity — those are by design and out of scope.
- Nesting is checked by `qID`, the dataset's own stable key; identity is used for the within-split and
  leakage checks. The two conflicts are counted by identity, not by `qID`.
- WinoGrande's `test` split ships without public labels, so it is excluded; the census covers the five
  labelled training sizes and `dev`.
- The census reports the *count* and location of the two conflicts (both in `train_xl`) but not their
  text.

## Licence

Code is Apache-2.0. The result and this write-up are CC BY 4.0. WinoGrande 1.1 is released under
Apache-2.0 / CC-BY (Sakaguchi, Le Bras, Bhagavatula and Choi, "WinoGrande: An Adversarial Winograd
Schema Challenge at Scale", AAAI 2020). Authored by AI agents working in MV2's name (Munim, Inc.).
