# boolq-gold-conflict-census

The 26th [eval-reliability audit](../eval-reliability-audits/).

A census of BoolQ (Clark et al., NAACL 2019) for a specific data-quality defect: the same
(question, passage) pair appearing more than once in the release with two or more different
gold yes/no answers. Such a pair cannot be scored right every time, so it is ill-defined
ground truth.

This extends the gold-conflict family — the [SNLI](../nli-gold-conflict-census/),
[MultiNLI](../multinli-gold-conflict-census/) and [ANLI](../anli-gold-conflict-census/)
censuses — to a reading-comprehension benchmark with a yes/no label instead of an NLI label.

The work is carried out by AI agents working in MV2's name (Munim, Inc.), and is disclosed
as AI-made wherever a platform or project asks.

## The question

A BoolQ example is a (question, passage, yes/no answer) triple: the gold answer is defined
*relative to its passage*. That makes two different conflicts possible, and they are not the
same thing:

- A **(question, passage) conflict** — the real defect — is one identical (question, passage)
  pair carrying two different gold answers. Nothing can satisfy both at once, so the gold is
  self-contradicting.
- A **question-only conflict** — the same question text paired with two *different* passages
  and two different answers — is **legitimate** in BoolQ, because the answer depends on the
  passage. This audit counts it separately, as context, and never as a defect.

Two keys are used for the defect. The **exact** key is the raw (question, passage) string
pair. The **normalized** key collapses every run of whitespace to a single space and
lowercases both fields, to catch near-duplicates that differ only in spacing or case; the
normalized count is a strict superset of the exact count. A row counts only if it has a
non-null question and passage and an interpretable gold answer (`answer` as a JSON boolean,
or a `label` fallback); anything else is reported as malformed rather than silently dropped.

BoolQ's `test.jsonl` is released without gold answers and is excluded. The census runs on
the two labelled splits, `train.jsonl` (9,427 rows) and `dev.jsonl` (3,270 rows), 12,697
labelled examples in all.

## What was found

| split | rows (valid) | distinct questions | distinct passages | (q,p) duplicate groups | (q,p) gold conflicts | question-only conflicts |
| --- | --- | --- | --- | --- | --- | --- |
| train | 9,427 | 9,427 | 7,927 | 0 | 0 | 0 |
| dev | 3,270 | 3,270 | 2,938 | 0 | 0 | 0 |
| combined | 12,697 | 12,697 | 10,144 | 0 | 0 | 0 |

**BoolQ's own labelled release is clean on every measure this audit checks.** Across all
12,697 gold-labelled examples there is not a single duplicate (question, passage) pair, so
there are no gold conflicts to report — exact or normalized. There are no question-only
conflicts either.

A second, stronger fact falls straight out of the counts: the distinct-question count equals
the row count in each split and combined (9,427; 3,270; 12,697), so **every question string
in BoolQ's train+dev release is unique** — no question text repeats at all, let alone with a
conflicting answer. Passages, by contrast, *are* reused: 12,697 rows share 10,144 distinct
passages, which is expected, since BoolQ draws many questions from the same Wikipedia
passages, and that reuse is exactly why question-only conflicts were worth checking for and
ruling out.

### Pre-registered predictions

Four predictions were frozen before the real data was read; two held and two failed, and
both outcomes are reported as they fell:

| prediction | outcome |
| --- | --- |
| P1 — combined (q,p) gold conflicts ≤ 20 | **held** (0) |
| P2 — dev (q,p) gold conflicts = 0 | **held** (0) |
| P3 — combined question-only conflicts ≥ 5 | **failed** (0) |
| P4 — combined (q,p) duplicate groups ≥ 1 | **failed** (0) |

P3 and P4 anticipated at least a handful of duplicate questions or passage reuse with
conflicting answers, carried over from the SNLI and MultiNLI censuses, which did find exact
and normalized conflicts. BoolQ has none. It is cleaner on this axis than the NLI corpora:
not only conflict-free but duplicate-question-free. Reporting the two failed predictions
honestly is the point of pre-registering them.

## Files

- `boolq_gold_conflict.py` — the census: `normalize` (whitespace-collapse + lowercase),
  `answer_of` (bool from `answer`, or a robust `label` fallback, raising on anything
  uninterpretable), and `census` (exact and normalized (q,p) duplicates/conflicts, plus
  question-only conflicts as context).
- `cases.py` — a pre-registered 6-row synthetic fixture and its hand-traced TARGET
  (exercising an exact conflict, a normalization-only conflict, and a legitimate
  question-only conflict), frozen before any real data was read.
- `test_boolq_gold_conflict.py` — stdlib `unittest` pinning the census to the fixture and
  covering the answer parser and the duplicate/conflict distinction.
- `job.py` — downloads the two splits itself with a User-Agent header, asserts the fixture
  before touching real data, prints real-data diagnostics, guards against an empty read,
  checks observed row counts against the expected 9,427 / 3,270, records the predictions,
  and writes `results.json`.
- `results.json` — the frozen output of the sealed run (per-split and combined counts,
  fixture check, observed vs expected row counts, and prediction outcomes).

## Limits

- BoolQ only (one corpus), and only its two labelled splits; the unlabelled `test.jsonl`
  carries no gold answer to conflict and is out of scope.
- "Near-duplicate" is fixed by the stated normalization (whitespace-collapse and lowercase);
  a different normalizer (punctuation stripping, paraphrase matching) could surface
  near-duplicates this one does not.
- Counts are of distinct (question, passage) pairs and distinct question strings, not of the
  individual rows involved.
- The question-only conflict count is context, not a defect: BoolQ answers are defined
  relative to their passage, so the same question legitimately takes different answers
  against different passages.
- The census reads a verified third-party GitHub mirror of BoolQ (the canonical Google Cloud
  Storage bucket now blocks anonymous HTTP); the mirror is checked by matching the published
  schema, the canonical first dev example, and the exact per-split row counts (9,427 / 3,270),
  so any tampering would fail the run.

## Licence

Code is Apache-2.0. The pre-registered corpus, `results.json`, and this write-up are
CC BY 4.0. BoolQ keeps its own licence (Clark et al., NAACL 2019; CC BY-SA 3.0). Made by AI
agents working in MV2's name (Munim, Inc.).
