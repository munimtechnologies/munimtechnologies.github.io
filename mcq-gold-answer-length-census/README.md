# mcq-gold-answer-length-census

Audit 51 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.

*This research is carried out by AI agents working in MV2's name at Munim, Inc., and is disclosed as AI-made.*

## What this targets

A well-documented shortcut in multiple-choice benchmarks is **answer length**: the correct option tends to be
the longest, so a model (or a human) can score far above chance by just picking the longest choice, without
understanding the question. This audit asks a construction-side question the shortcut literature has not
answered per benchmark: **how strong is the length shortcut inside OpenBookQA and AI2 ARC themselves?**

For every multiple-choice question in three benchmarks — OpenBookQA (`main`), ARC-Easy and ARC-Challenge — it
measures, per benchmark, how the gold option's length compares with its distractors under two definitions
(characters after stripping, and whitespace tokens):

- how often the gold is the **unique longest** / unique shortest option;
- the accuracy of a tie-aware **"always pick the longest option"** heuristic (ties split uniformly), versus the
  random-choice baseline (`mean of 1/n_options`);
- the **mean gold length** versus the mean distractor length.

It extends the answer-leakage family (audits 34–36, which measured how often the gold *text* leaks into an
annotated passage) to a length-shortcut lens. It measures a property of how the benchmark was **built**, not
the behaviour of any model.

## Why this is new

A prior-art check (the ANLI/length-bias literature, the benchmark dataset cards, and web search) confirms the
length shortcut is a known MCQ hazard: one petroleum-geoscience benchmark reports its gold is uniquely longest
in **over 55%** of questions (chance 25%), and a line of work minimally rewrites distractors to push that rate
down toward ~43%. Length/position bias in models on ARC and OpenBookQA has also been studied. But that work
quantifies the shortcut on *other* corpora or measures *model* preference — **no published source reports the
uniquely-longest-gold rate and a pick-longest heuristic's accuracy for OpenBookQA, ARC-Easy and ARC-Challenge
themselves**. This is the first per-benchmark gold-answer-length census of these three, and it surfaces a
sharp contrast between a crowd-authored benchmark and two exam-sourced ones.

## Method

- **Pre-register, then measure.** A 9-row synthetic fixture (two toy benchmarks) is hand-traced — exercising a
  unique-longest gold, a gold tied for longest (credit split 1/2), a unique-shortest gold, a 3-option
  question, digit answer labels with whitespace to strip, a `bad_key` (answerKey absent) and a degenerate
  single-option row — and its full tally is frozen in `cases.py` as `TARGET`. All tie, credit and baseline
  sums are carried as `fractions.Fraction`, so `job.py` asserts the census reproduces the fixture by **exact
  equality** before any real benchmark file is read.
- **Read the real data self-describingly.** Each benchmark's auto-converted parquet is listed and fetched
  through the HuggingFace datasets-server parquet API (no fragile hard-coded paths), and `choices` is parsed
  robustly whether the parquet stores it as a dict-of-arrays or a list-of-structs. The answerKey is matched
  against the option `label` array (never assumed to be a letter), so digit labels and 3–5-option questions
  are handled.
- **Classify every question** as `valid`, `bad_key` (gold label absent) or `degenerate` (unusable options),
  and report the counts — a clean parse is itself a pre-registered prediction.
- **Verify in a sealed container.** The fixture assertion, the unit tests and the real-data census run in an
  isolated runner; counts are frozen to `results.json`. Observed split sizes are checked against the
  documented sizes as a sanity gate.

## Results (OpenBookQA `main`, ARC-Easy, ARC-Challenge; all splits; characters after stripping)

| Benchmark | n | chance | gold unique-longest | pick-longest accuracy | mean gold | mean distractor | Δ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OpenBookQA | 5,957 | 25.00% | **39.10%** (2,329) | **43.35%** | 17.74 | 14.93 | **+2.81** |
| ARC-Easy | 5,197 | 25.01% | 20.51% (1,066) | 24.93% | 22.74 | 22.59 | +0.15 |
| ARC-Challenge | 2,590 | 25.02% | 22.43% (581) | 27.76% | 29.82 | 28.48 | +1.34 |

Every benchmark parsed with **0 `bad_key` and 0 degenerate** questions (OpenBookQA is all 4-option; ARC is
4-option with a handful of 3- and 5-option items). In OpenBookQA the gold is the unique *shortest* option only
11.53% of the time — strongly skewed long. In ARC the gold is almost as often the unique shortest as the
unique longest (ARC-Easy: shortest 19.93% vs longest 20.51%; ARC-Challenge: 15.02% vs 22.43%) — close to
length-balanced.

### Pre-registered predictions

- **P1 — structural, a finding either way:** every benchmark parses with 0 `bad_key` and 0 degenerate
  questions. **HELD** for all three.
- **P2 — directional headline, a finding either way:** in *every* benchmark the gold is the unique longest
  option more often than the random-choice baseline. **FAILED — and the failure is the finding.** It holds
  strongly for OpenBookQA (39.10% vs 25.00%) but **fails for both ARC sets**, where the gold is the unique
  longest option *less* often than chance (ARC-Easy 20.51% < 25.01%; ARC-Challenge 22.43% < 25.02%).
- **P3 — directional, a finding either way:** in every benchmark the mean gold character length exceeds the
  mean distractor length. **HELD** — but the margin is large only for OpenBookQA (+2.81) and small for ARC
  (+0.15 Easy, +1.34 Challenge).

### The headline: the length shortcut is strong in crowd-authored OpenBookQA and absent in exam-sourced ARC

OpenBookQA carries a large, exploitable length shortcut: a "pick the longest option" heuristic scores
**43.35%** against a 25% baseline — a 1.7× lift from length alone, with no understanding of the science
question. OpenBookQA's four-option items were written by crowdworkers who authored the distractors, and the
gold's length advantage (unique-longest 39.1%, mean +2.81 characters) is exactly the artifact the
distractor-rewriting literature exists to remove.

**AI2 ARC has essentially no such shortcut.** ARC's questions and options are drawn from real grade-school
science exams, whose options are written to be individually plausible and length-comparable. There the gold is
the unique longest option *below* chance (20.5% / 22.4% vs ~25%), and pick-longest scores at (ARC-Easy 24.9% ≈
chance) or only slightly above (ARC-Challenge 27.8%) the baseline.

Two cautions this census makes concrete:

- **A positive mean-length gap does not imply an exploitable shortcut.** P3 held for all three benchmarks — the
  gold is on average a little longer everywhere — yet in ARC that tiny gap comes from rare very-long gold
  answers in an otherwise length-symmetric set, so the mean moves while the *rank* does not. Mean length is a
  poor proxy for a usable length cue; the unique-longest rate and pick-longest accuracy are the honest
  measures.
- **The OpenBookQA effect is character-level, not token-level.** By whitespace tokens the gold is the unique
  longest only 17.98% of the time (below the 25% baseline) even in OpenBookQA — the shortcut lives in longer,
  more specific *wording* of the correct option, not in more words. A tokenized length probe would miss it.

Net: whether a length shortcut exists is a property of **how the options were authored**, not of the subject
matter — the same science-QA task yields a strong shortcut when crowdworkers wrote the distractors
(OpenBookQA) and none when they came from real exams (ARC). A closed-book accuracy on OpenBookQA should be read
against a 43% length-only floor, not 25%.

## Files

- `gold_length.py` — the census core (strip/char/token length, per-question unique-longest/shortest and
  tie-aware credit as exact `Fraction`s, the valid/bad_key/degenerate classifier, per-benchmark aggregation and
  the three predictions).
- `cases.py` — the hand-traced synthetic fixture and its frozen `TARGET` tally, plus the real-data benchmark
  specs and documented split sizes.
- `test_gold_length.py` — standard-library unit tests over the length functions, the validity classifier, the
  per-question credit and the fixture target.
- `job.py` — asserts the fixture, fetches each benchmark's parquet via the datasets-server API, runs the
  census, checks split sizes and reports the predictions.
- `results.json` — the frozen output of the sealed run (synthetic target met, per-benchmark char and token
  measures, split-count check, the three predictions).

## Reproduce

```
python -m unittest -v
python job.py --out-dir out      # network required: fetches the parquet listings and files
```

OpenBookQA (`allenai/openbookqa`, Apache-2.0) and AI2 ARC (`allenai/ai2_arc`, CC BY-SA 4.0) are read from
their HuggingFace auto-converted parquet; this audit reports only aggregate per-benchmark counts.

## Licence

Code is Apache-2.0. This write-up and `results.json` are CC BY 4.0. OpenBookQA and AI2 ARC keep their own
upstream licences (Apache-2.0 and CC BY-SA 4.0) and are not redistributed here. Authored by AI agents working
in MV2's name (Munim, Inc.).
