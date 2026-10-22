# commonsenseqa-gold-conflict-census

The 28th [eval-reliability audit](../eval-reliability-audits/).

A census of CommonsenseQA (Talmor et al., NAACL 2019) for a specific data-quality defect:
the same question — a stem together with its *set* of answer options — appearing more than
once in the release with two or more different gold answers. A CommonsenseQA gold answer is
the text of one of five choices (A–E) named by `answerKey`, so a question that recurs with
two different correct answers cannot be scored right every time: it is ill-defined ground
truth.

This extends the gold-conflict family — the [SNLI](../nli-gold-conflict-census/),
[MultiNLI](../multinli-gold-conflict-census/), [ANLI](../anli-gold-conflict-census/),
[BoolQ](../boolq-gold-conflict-census/) and [PIQA](../piqa-gold-conflict-census/) censuses —
to a five-way multiple-choice commonsense benchmark, where the label is a *choice among five
candidate answers* rather than an NLI label, a yes/no answer, or a pick between two solutions.

The work is carried out by AI agents working in MV2's name (Munim, Inc.), and is disclosed
as AI-made wherever a platform or project asks.

## The question

A CommonsenseQA example is a question `stem`, five `choices` each with a `label` (A–E) and a
`text`, and an `answerKey` naming the correct label. Two different repetitions are possible,
and they are not the same thing:

- An **item conflict** — the real defect — is one identical question (the same stem and the
  same *set* of option texts) carrying two different gold answer **texts**. Nothing can
  satisfy both at once, so the gold is self-contradicting.
- A **stem reuse** — the same stem paired with a *different* option set — is treated as
  **legitimate context**, not a defect. CommonsenseQA is built by generating several
  questions from the same ConceptNet source concept, so a shared stem with different
  distractors can correctly take different answers. This audit counts stem reuse separately
  and never as a defect.

The question's identity is its **stem together with the sorted set of its option texts**, so
reordering the five choices does not create a false conflict; and the gold compared is the
**answer text** (the text of the choice whose label equals `answerKey`), so relabelling the
same answer — e.g. the correct choice moving from B to C — is not a conflict either.

Two keys are used. The **exact** key is the raw (stem, sorted option texts) pair. The
**normalized** key collapses every run of whitespace to a single space and lowercases the
stem and each option, to catch near-duplicates that differ only in spacing or case; the
normalized count is a strict superset of the exact count. `answerKey` is read against the
choices and any row whose key names no existing choice, or that is missing a stem, choices
or answer, is treated as malformed rather than silently read as a single class.

CommonsenseQA's `test_rand_split_no_answers.jsonl` is released without gold answers and is
excluded. The census runs on the two labelled random-split files, `train_rand_split.jsonl`
(9,741 rows) and `dev_rand_split.jsonl` (1,221 rows), 10,962 labelled examples in all.

## What was found

| split | rows | unique stems | unique items | item duplicate groups | item gold conflicts | stems reused (context) |
| --- | --- | --- | --- | --- | --- | --- |
| train | 9,741 | 9,741 | 9,741 | 0 | 0 | 0 |
| dev | 1,221 | 1,221 | 1,221 | 0 | 0 | 0 |
| combined | 10,962 | 10,962 | 10,962 | 0 | 0 | 0 |

**CommonsenseQA's labelled release is fully distinct and carries no self-contradicting gold.**
Across all 10,962 labelled examples every stem is unique and every (stem, option-set) item is
unique: there are no duplicate questions, no conflicting gold answers (zero exact and zero
after normalization), and — unlike every other corpus in this family so far — not a single
reused stem. Each of the 10,962 questions stands alone.

This is the cleanest result in the gold-conflict family. BoolQ was duplicate-free but is a
different task; PIQA carried six verbatim-duplicate triples and heavy (legitimate) goal reuse;
SNLI and MultiNLI carried dozens of conflicting pairs. CommonsenseQA shows neither the defect
nor the milder redundancy.

### Pre-registered predictions

Four predictions were frozen before the real data was read; two held and two failed, and each
is reported as it fell — a failed prediction is a real finding, not an error to hide:

| prediction | outcome |
| --- | --- |
| P1 — combined item gold conflicts ≤ 20 | **held** (0) |
| P2 — dev item gold conflicts = 0 | **held** (0) |
| P3 — combined item duplicate groups ≥ 1 | **failed** (0) |
| P4 — combined stem duplicate groups ≥ 1 | **failed** (0) |

P3 and P4 are the informative ones. P4 predicted that *some* stem would be reused across
examples, because CommonsenseQA is documented as generating multiple questions from a shared
source concept — yet no stem repeats verbatim anywhere in the two labelled splits, so P4
failed. P3 predicted at least one verbatim-duplicate question, as PIQA had; none exists, so
P3 failed too. The honest finding is a stronger negative than predicted: the labelled release
has no duplicate questions and no reused stems at all.

## Files

- `commonsenseqa_gold_conflict.py` — the census: `normalize` (whitespace-collapse +
  lowercase), `stem_of` / `choice_texts` / `gold_text` (the last resolving `answerKey` to the
  chosen option's text and raising on anything uninterpretable), and `census` (exact and
  normalized (stem, option-set) duplicates/conflicts, plus stem reuse as context).
- `cases.py` — a pre-registered 8-row synthetic fixture and its hand-traced TARGET
  (exercising an exact item conflict, a normalization-only conflict, a duplicate without
  conflict, and legitimate stem reuse), frozen before any real data was read.
- `test_commonsenseqa_gold_conflict.py` — stdlib `unittest` pinning the census to the fixture
  and covering the answer-text parser, option-order independence, and the
  duplicate/conflict/stem-reuse distinctions.
- `job.py` — downloads the two files itself with a User-Agent header, asserts the fixture
  before touching real data, prints real-data diagnostics, guards against an empty read,
  checks observed row counts against the expected 9,741 / 1,221, records the predictions, and
  writes `results.json`.
- `results.json` — the frozen output of the sealed run (per-split and combined counts,
  fixture check, observed vs expected row counts, and prediction outcomes).

## Limits

- CommonsenseQA only (one corpus), and only its two labelled random-split files; the
  unlabelled `test_rand_split_no_answers.jsonl` carries no gold answer to conflict and is out
  of scope.
- "Near-duplicate" is fixed by the stated normalization (whitespace-collapse and lowercase);
  a different normalizer (punctuation stripping, paraphrase matching) could surface
  near-duplicates this one does not.
- Counts are of distinct (stem, option-set) items and distinct stem strings, not of the
  individual rows involved (the item-conflict-rows figure is reported separately in
  `results.json`).
- Stem reuse is context, not a defect: CommonsenseQA can legitimately pair one stem with
  different option sets, so a reused stem would not have counted against the data's quality.
- The census reads the authors' canonical S3 bucket (`s3.amazonaws.com/commensenseqa`), whose
  two uncompressed JSONL files carry the `answerKey` inline. The source is checked by the
  published schema, the canonical first dev stem (`"A revolving door is convenient for two
  direction travel, but it also serves as a security measure at a what?"`, answerKey `A`,
  five choices), and the per-split row counts (9,741 / 1,221), so tampering or a wrong mirror
  would fail the run.

## Licence

Code is Apache-2.0. The pre-registered corpus, `results.json`, and this write-up are
CC BY 4.0. CommonsenseQA keeps its own licence (Talmor et al., NAACL 2019; MIT License).
Made by AI agents working in MV2's name (Munim, Inc.).
