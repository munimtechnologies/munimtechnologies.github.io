# gsm8k-split-overlap-census

GSM8K (Cobbe et al. 2021) is the standard grade-school math word-problem benchmark:
7,473 training problems and 1,319 test problems, each a question with a worked
solution ending in a `#### <final answer>` line. A benchmark is only trustworthy if
its test split is disjoint from its train split — a question that appears in both lets
a model score by memorization, and if the two copies carry different final answers the
ground truth is self-contradictory. This audit asks a narrow, checkable question about
GSM8K's own released files: does any question string appear in **both** `train.jsonl`
and `test.jsonl`, and if so do the two splits' final answers agree?

The work was carried out by AI agents working in MV2's name (Munim, Inc.), and is
disclosed as AI-made wherever a platform or project asks.

## The question

Two questions are an **exact** overlap when their question strings are byte-for-byte
identical across the two splits. They are a **normalized** overlap when they become
identical after the one near-duplicate rule used here: collapse every run of
whitespace to a single space, then lowercase. No punctuation stripping, no stemming,
nothing else — so the normalized count is a strict superset of the exact count. For
each overlapping question we also compare the **final answer**, defined as the text
after the last `####`, stripped, with thousands commas and a leading `$` removed; if
the train copy and the test copy disagree, that is an answer conflict. A row counts
only if it has a non-empty question and a parseable `####` answer.

## What was found

| Split | rows (valid) | distinct questions (exact) |
|---|---|---|
| train.jsonl | 7,473 | 7,473 |
| test.jsonl | 1,319 | 1,319 |

| Overlap measure | pairs | answer conflicts |
|---|---|---|
| exact (identical question) | 0 | 0 |
| normalized (whitespace + case) | 0 | 0 |

GSM8K's own train and test releases share **no** questions — zero exact matches and
zero that collapse together under whitespace-and-case normalization — so there are no
answer conflicts to report either. A second fact falls out of the counts: the distinct
exact question count equals the valid-row count in each split (7,473 and 1,319), so
GSM8K's released files contain no exact-duplicate question *within* train or *within*
test, not just across them.

This is a negative result, and a deliberate one: it is a first-of-kind execution
verification that GSM8K is clean of train/test question overlap in its own release,
rather than an assumption carried over from the paper. The analysis also detects
answer conflicts, so had any overlap existed the audit would have surfaced it; it ran
on the full 8,792 problems and found none.

## Files

- `split_overlap.py` — the census: `normalize` (whitespace-collapse + lowercase),
  `final_answer` (text after the last `####`, commas/`$` stripped), and `analyze`
  (per-split index plus exact and normalized cross-split overlap with answer-conflict
  counts and examples).
- `cases.py` — the pre-registered 3-train/4-test fixture and its hand-traced TARGET,
  frozen before any real data was read.
- `test_split_overlap.py` — stdlib `unittest` pinning the analysis to the fixture.
- `job.py` — loads the official `train.jsonl`/`test.jsonl`, runs the census, and
  writes `results.json`.
- `results.json` — the frozen output of the sealed run (counts and examples).

## Limits

One corpus (GSM8K's `openai/grade-school-math` release) and one normalizer; a
different near-duplicate rule (punctuation or number stripping, paraphrase matching)
could surface near-duplicates this one does not. Counts are of distinct question
strings, not of rows. The audit compares question text and final answers only; it does
not judge whether two problems are semantically equivalent while worded differently.
The `_socratic` variant files are out of scope here and are the subject of a separate
census.

## Licence

Code is Apache-2.0. The pre-registered corpus, `results.json`, and this write-up are
CC BY 4.0. GSM8K keeps its own licence (GSM8K, Cobbe et al. 2021). Made by AI
agents working in MV2's name (Munim, Inc.).
