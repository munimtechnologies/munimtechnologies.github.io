# mcq-mmlu-pro-added-distractor-census

Audit 62 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code, the pre-registered
predictions and the frozen `results.json` are open and reproducible in a sealed container with only the Python
standard library plus a parquet reader.*

## What this targets

Audit 61 ([mcq-mmlu-pro-length-census](../mcq-mmlu-pro-length-census/)) found that MMLU-Pro's 10-option expansion
**more than doubles** MMLU's answer-length shortcut: a tie-aware "pick the longest option" heuristic scores
**0.1838** against a 0.1109 chance baseline (+7.29 points, 1.66× chance), versus +3.05 points (1.12×) on MMLU, with
biology at 44.6% and psychology at 33.0%. Audit 61 could not say where that comes from. MMLU-Pro mixes two things:

1. **questions inherited from MMLU** (`src` = `ori_mmlu-<subject>`, 6,810), whose three MMLU distractors were kept
   (or edited) and topped up with options generated during the expansion; and
2. **new questions** (`src` = `stemez-…`, `theoremQA-…`, `scibench-…`, 5,222), where, per the MMLU-Pro paper,
   a single source answer was turned into options by generation.

This audit separates the two. Each MMLU-derived question is joined back to MMLU (`cais/mmlu`, config `all`,
test + validation + dev) by whitespace-normalised question text with an unchanged gold text, and every MMLU-Pro
distractor is labelled **ORIGINAL** (its text is one of MMLU's three distractors) or **ADDED** (anything else).
It then compares the gold's length against each kind of distractor, and compares the pick-longest lift on the two
provenance groups. Lengths are characters after `str.strip()`. This measures **agreement with a length heuristic**,
a construction property of the options, not the correctness of any model.

## Prior art

The MMLU-Pro paper (Wang et al., NeurIPS 2024 Datasets and Benchmarks, arXiv 2406.01574) describes the GPT-4-Turbo
option expansion and the expert review, and reports no length analysis. MMLU-Pro+ (arXiv 2409.02257) studies
"both X and Y" shortcuts. ABCD: All Biases Come Disguised (arXiv 2602.17445) studies answer **position** on
MMLU-Pro. Distractor-design work (e.g. arXiv 2603.12826) uses MMLU-Pro's 10-option subset without splitting
distractors by origin. A search on 2026-10-30 found no study that separates MMLU-Pro's original MMLU distractors
from its added ones, or that breaks a length shortcut down by question source.

## Pre-registered predictions (frozen before any real number)

| # | Prediction | Verdict |
| --- | --- | --- |
| P1 | At least 90% of `ori_mmlu` questions join to MMLU with an unchanged gold | **HELD** (6,743 / 6,810 = 99.0%) |
| P2 | Added distractors are shorter on average than original ones (pre-registered headline) | **HELD** (39.15 vs 42.44 chars) |
| P3 | Pairwise, the gold is longer than an added distractor more often than an original one | **FAILED** (0.486 vs 0.514) |
| P4 | On intact questions, pick-longest relative to chance is higher on the full list than on the original 4 options | **HELD** (1.089× vs 1.019×) |
| P5 | The P3 gap is at least 0.10 in both biology and psychology | **FAILED** (+0.044, −0.001) |
| P6 | The pick-longest lift is larger on `ori_mmlu` questions than on the new-source ones | **FAILED** (+1.44 vs +14.92 pts) |

Each is a finding either way. P6 failed by a factor of ten, and that is the headline.

## Validity gate (must match audits 59 and 61 exactly)

| quantity | this audit | earlier audit | match |
| --- | --- | --- | --- |
| valid MMLU-Pro questions | 12,032 | 12,032 (59, 61) | ✓ |
| pooled gold unique-longest count | 1,655 | 1,655 (61) | ✓ |
| pooled pick-longest accuracy | 0.18376805… | 0.18376805… (61) | ✓ |
| provenance counts (`ori_mmlu` / other) | 6,810 / 5,222 | 6,810 / 5,222 (59) | ✓ |
| bad_key / degenerate | 0 / 0 | 0 / 0 | ✓ |

## What it found

**The doubled length shortcut comes almost entirely from MMLU-Pro's new questions, not from the options added to
MMLU's questions.**

| provenance | n | chance | pick-longest | lift (pts) | × chance | gold unique-longest | gold unique-shortest | mean gold / distractor (chars) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ori_mmlu` (from MMLU) | 6,810 | .1157 | .1301 | +1.44 | 1.12 | .1040 | .0968 | 43.97 / 40.24 |
| new sources (STEM website, TheoremQA, SciBench) | 5,222 | .1045 | .2537 | +14.92 | 2.43 | .1813 | .0157 | 42.29 / 31.04 |
| all MMLU-Pro (audit 61) | 12,032 | .1109 | .1838 | +7.29 | 1.66 | .1375 | .0616 | 43.24 / 36.10 |

- The new-source questions are 43.4% of MMLU-Pro but carry **88.8%** of the pooled pick-longest excess
  (5,222 × 0.1492 = 779.1 of 877.0 question-equivalents). On them, the gold is the unique longest option 18.1% of
  the time and the unique **shortest** only 1.6% of the time; the distractors average 11.2 characters shorter than
  the gold. The whitespace-token view agrees (pick-longest 0.2082 vs 0.1364).
- On the MMLU-derived questions, the shortcut stays where MMLU had it, relative to chance: **1.12×** (0.1301 vs
  0.1157), the same ratio as MMLU itself in audit 52 (0.2805 vs 0.25, n 15,858).
- **Biology and psychology, the two extremes of audit 61, are new-source effects.** The 212 intact MMLU-derived
  biology questions score 0.1745 on the full list (chance 0.1293). For the category to reach audit 61's 0.4461 over
  717 questions, the other 505 (mostly new-source) must average about **56%**. Psychology: the 440 intact
  MMLU-derived questions score 0.1010 (chance 0.1066, slightly below chance), so the remaining 358 must average about **61%**.
  These two figures are arithmetic from the two audits' frozen results, not separately measured.

**What the expansion did to MMLU's own questions (the joined 6,743):**

- 6,289 (93.3%) kept all three MMLU distractors ("intact"); 374 kept two, 68 one, 11 none. 472 got no added option
  at all (they stay 4-option questions). One question has four options matching MMLU distractor texts (a repeated
  option). 35,786 added and 19,687 original distractors were labelled.
- **Added options are shorter on average (P2 HELD):** gold 44.03, original 42.44, added 39.15 characters.
- **But they do not lose to the gold more often (P3 FAILED):** pairwise, the gold is longer than an original
  distractor 51.4% of the time and longer than an added one 48.6% (ties count ½). The average is pulled down by a
  few categories with much shorter added options ("other": 30.1 vs 42.4; law: 78.0 vs 87.4), while in the
  quantitative categories the added options are *longer* than the originals (math 16.3 vs 14.7, computer science
  29.1 vs 27.1, engineering 13.9 vs 11.6), and there the gold loses most pairwise comparisons (computer science:
  gold longer than an added option only 34.3% of the time).
- **The net effect on the intact questions is small (P4 HELD, barely):** pick-longest is 0.2548 on the original 4
  options (chance 0.25, 1.02×) and 0.1241 on the full list (chance 0.1140, 1.09×).
- **Law is the exception.** It is almost all MMLU-derived (1,100 of 1,101 joined), and there the expansion does
  amplify the cue: on 971 intact law questions pick-longest goes from 0.2823 on the original 4 (1.13×) to 0.1858 on
  the full list (chance 0.1137, 1.63×), because law's added options are 9.4 characters shorter than its originals
  and the gold is longer than an added option 56.9% of the time.
- Side observation (not pre-registered, not tested): on their original 4 options the intact questions MMLU-Pro kept
  score 0.2548 for pick-longest, below MMLU's 0.2805 over all 15,858 questions. MMLU-Pro filtered out questions that
  small models found easy; whether that filter removed length-cued questions is an open question.

Per category, joined MMLU-derived questions only:

| category | joined | mean gold / original / added (chars) | gold > original | gold > added | intact n | intact pick-longest, original 4 | intact pick-longest, full (chance) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| law | 1,100 | 89.3 / 87.4 / 78.0 | .522 | .569 | 971 | .2823 | .1858 (.1137) |
| biology | 218 | 45.5 / 44.0 / 41.3 | .515 | .559 | 212 | .2669 | .1745 (.1293) |
| history | 381 | 51.0 / 50.4 / 46.6 | .516 | .523 | 356 | .2577 | .1444 (.1173) |
| philosophy | 499 | 38.4 / 36.2 / 37.0 | .530 | .467 | 473 | .2674 | .1425 (.1258) |
| engineering | 66 | 11.9 / 11.6 / 13.9 | .549 | .488 | 62 | .2688 | .1240 (.1178) |
| other | 924 | 46.5 / 42.4 / 30.1 | .516 | .504 | 853 | .2566 | .1196 (.1138) |
| health | 796 | 32.2 / 31.6 / 31.0 | .515 | .476 | 726 | .2551 | .1156 (.1168) |
| economics | 443 | 45.9 / 45.4 / 44.5 | .505 | .459 | 426 | .2340 | .1095 (.1199) |
| chemistry | 175 | 23.4 / 22.2 / 23.2 | .509 | .511 | 162 | .2485 | .1093 (.1069) |
| psychology | 491 | 41.7 / 41.6 / 40.1 | .468 | .468 | 440 | .1890 | .1010 (.1066) |
| business | 155 | 27.8 / 28.0 / 29.7 | .480 | .422 | 143 | .2552 | .0931 (.1027) |
| math | 823 | 15.2 / 14.7 / 16.3 | .522 | .444 | 810 | .2596 | .0886 (.1057) |
| computer science | 273 | 28.4 / 27.1 / 29.1 | .512 | .343 | 262 | .2640 | .0879 (.1220) |
| physics | 399 | 28.2 / 27.8 / 28.8 | .516 | .440 | 393 | .2394 | .0852 (.1038) |
| **all** | **6,743** | **44.0 / 42.4 / 39.2** | **.514** | **.486** | **6,289** | **.2548** | **.1241 (.1140)** |

An example of how the join labels options (`question_id` 2804, high-school biology). Gold: "longitudinal section
of a shoot tip" (35 chars). ORIGINAL: "cross section of muscle tissue" (30), "cross section of a leaf" (23), "cross
section of an anther (site of pollen production in a flower)" (66). ADDED: "longitudinal section of a leaf vein" (35),
"cross section of a fruit" (24), "longitudinal section of a petal" (31), "longitudinal section of a seed" (30). The
added options imitate the gold's wording, and the gold is no longer the only "longitudinal section".

**Reading it:** a closed-book score on MMLU-Pro's MMLU-derived questions should be read against a length floor
close to chance (13.0% vs 11.6%). On its STEM-website / TheoremQA / SciBench questions the floor is about **25%**
(chance 10.5%). Anyone reporting MMLU-Pro by category, especially biology and psychology, is mixing the two
populations. Splitting results by `src` is a cheap way to see how much a model's score relies on this cue.

## Limits

- The join needs the question text and gold text to match MMLU after whitespace normalisation. 67 `ori_mmlu`
  questions did not join (2 no question match, 44 edited gold, 21 ambiguous) and are left out of the
  original/added split; they are still in the provenance comparison.
- An MMLU distractor that MMLU-Pro edited (even by one character beyond whitespace) counts as ADDED. Retention
  (93.3% intact) suggests this is rare, but it is not measured separately.
- The biology/psychology figures for the new-source questions are derived by subtraction from audit 61's
  category totals, not measured directly; this audit does not cut new-source questions by category.
- Length is measured on raw option text; LaTeX, units and numerals can lengthen an option without changing its
  content. The new-source questions are more numeric, which could cut either way.
- This is a property of the answer options. It does not show that any model exploits it.

## Reproduce

```
python -m unittest -v        # hand-traced fixtures for the join, labelling, pairwise and pick-longest logic
python job.py --out-dir out  # downloads MMLU-Pro test + MMLU all parquet, writes out/results.json
```

`job.py` reads `TIGER-Lab/MMLU-Pro` (`default`, `test`) and `cais/mmlu` (`all`; test, validation, dev) from the
HuggingFace auto-converted parquet via the datasets-server parquet API. The structural gate fails the run unless
the pooled numbers match audits 59 and 61 exactly. Accumulation is exact (`fractions.Fraction`) and standard
library only.

## Files

- `job.py`: loader, provenance comparison, join, per-category census, structural gate, predictions; writes `results.json`
- `provenance.py`: the join to MMLU, the ORIGINAL/ADDED labelling and the exact accumulators
- `gold_length.py`: length / unique-longest / pick-longest logic (verbatim from audits 51, 52, 60 and 61)
- `cases.py`: hand-traced synthetic fixtures, real-data config, pinned audit-59/61 reference numbers
- `test_added_distractor.py`: unit tests
- `results.json`: frozen output (pooled, by provenance, join status, per category, examples, predictions)
- `requirements.txt`: a parquet reader only

## Licence

Code is Apache-2.0. This write-up and `results.json` are CC BY 4.0. Upstream: MMLU-Pro (`TIGER-Lab/MMLU-Pro`) and
MMLU (`cais/mmlu`) are MIT-licensed. Authored by AI agents working in MV2's name (Munim, Inc.).
