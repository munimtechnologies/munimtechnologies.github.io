# mcq-mmlu-pro-length-census

Audit 61 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code, the pre-registered
predictions and the frozen `results.json` are open and reproducible in a sealed container with only the Python
standard library plus a parquet reader.*

## What this targets

Audit 59 ([mcq-mmlu-pro-meta-option-census](../mcq-mmlu-pro-meta-option-census/)) showed that MMLU-Pro's 10-option
expansion **erases** MMLU's "the answer is D" artifact: the gold position becomes consistent with uniform and
"all of the above" stops being a cue. Audits 52 and 60 measured MMLU's other question-free shortcut, answer
**length**: a tie-aware "pick the longest option" heuristic scores **0.2805** on MMLU against a 0.25 baseline
(+3.05 points), concentrated in a law/clinical/social cluster.

This audit asks the matching question on the length axis: **does the same 10-way expansion also erase the
pick-longest shortcut?** For every question in MMLU-Pro (`TIGER-Lab/MMLU-Pro`, config `default`, test split, 12,032
questions, 3 to 10 options, modal 10), keyed by MMLU-Pro's 14 categories, it measures how often the gold is the
unique longest / unique shortest option, the accuracy of a tie-aware pick-longest heuristic against the exact
random-choice baseline (accumulated as the mean of 1/k, since option counts vary), and the mean gold vs mean
distractor length (characters after `str.strip()`, with a whitespace-token view alongside).

This measures **agreement with a length heuristic**, a construction property of how the options were written,
not the correctness of any model. The census core (`gold_length.py`) is reused verbatim from audits 51, 52 and 60.

## Prior art

The MMLU-Pro paper (Wang et al., NeurIPS 2024 Datasets and Benchmarks) motivates the expansion by the shortcut
risk of MMLU's three distractors; its added distractors were generated with GPT-4-Turbo and reviewed by experts.
MMLU-Pro+ (arXiv 2409.02257) studies anchoring and multiple-correct-answer shortcuts, not length. Choices-only
studies such as "Artifacts or Abduction" (arXiv 2402.12483) predate MMLU-Pro. Length censuses of other benchmarks
exist (e.g. FormationEval, arXiv 2601.02158). We found no published measurement of a pick-longest baseline on
MMLU-Pro, pooled or by category, at the time of writing (2026-10-29).

## Pre-registered predictions (frozen before any real number)

| # | Prediction | Verdict |
| --- | --- | --- |
| P1 | Structural gate: the pooled parse reproduces audit 59 exactly (n 12,032, modal 10, identical option-count histogram) and every category parses with 0 bad_key / 0 degenerate | **HELD** |
| P2 | The expansion **weakens** the length shortcut: pooled pick-longest lift over chance is smaller than MMLU's +3.05 points | **FAILED** (+7.29) |
| P3 | A length bias survives in direction: pooled mean gold is longer than the mean distractor | **HELD** (43.24 vs 36.10) |
| P4 | The cue is **not** pervasive: a strict minority of the 14 categories show a positive pick-longest lift | **FAILED** (14/14) |

Each is a finding either way. P2 and P4 failed, and how they failed is the headline.

## Validity gate (must match audit 59 exactly)

| quantity | this audit | audit 59 | match |
| --- | --- | --- | --- |
| valid questions | 12,032 | 12,032 | ✓ |
| modal option count | 10 | 10 | ✓ |
| option-count histogram | {3:21, 4:606, 5:52, 6:93, 7:158, 8:320, 9:801, 10:9981} | same | ✓ |
| bad_key / degenerate | 0 / 0 | 0 / 0 | ✓ |

## What it found

**MMLU-Pro's expansion did not erase the length shortcut. It more than doubled it.**

- **Pooled:** pick-longest scores **0.1838** against a chance baseline of **0.1109**, a **+7.29-point** lift, 2.4
  times MMLU's +3.05. Relative to chance that is **1.66×** (MMLU: 1.12×). The gold is the unique longest option
  in **13.75%** of questions and the unique shortest in only **6.16%**; it averages **43.24** characters against
  **36.10** for distractors (+7.14, versus MMLU's +1.68). The token view agrees (pick-longest 0.1676, +5.67 points).
- **Every one of the 14 categories** shows a positive lift (P4 FAILED). The size varies widely:

| category | n | chance | pick-longest | lift (pts) | gold unique-longest | mean gold / distractor (chars) |
| --- | --- | --- | --- | --- | --- | --- |
| biology | 717 | .1108 | .4461 | +33.5 | .4240 | 98.4 / 61.6 |
| psychology | 798 | .1085 | .3300 | +22.2 | .3170 | 78.5 / 56.4 |
| economics | 844 | .1200 | .2440 | +12.4 | .2156 | 63.4 / 52.0 |
| engineering | 969 | .1100 | .2193 | +10.9 | .1280 | 30.4 / 29.4 |
| law | 1,101 | .1149 | .1889 | +7.4 | .1826 | 89.2 / 81.3 |
| chemistry | 1,132 | .1040 | .1471 | +4.3 | .0627 | 21.0 / 20.2 |
| physics | 1,299 | .1016 | .1383 | +3.7 | .0701 | 21.7 / 21.4 |
| computer science | 410 | .1174 | .1534 | +3.6 | .1268 | 38.5 / 33.1 |
| business | 789 | .1025 | .1272 | +2.5 | .0520 | 16.9 / 17.3 |
| history | 381 | .1189 | .1402 | +2.1 | .1260 | 51.0 / 47.9 |
| philosophy | 499 | .1265 | .1436 | +1.7 | .1182 | 38.4 / 36.7 |
| other | 924 | .1172 | .1305 | +1.3 | .1050 | 46.5 / 34.5 |
| health | 818 | .1191 | .1254 | +0.6 | .1051 | 32.3 / 31.2 |
| math | 1,351 | .1042 | .1066 | +0.2 | .0340 | 12.4 / 12.6 |

- **Biology is the extreme.** Picking the longest of up to ten options without reading the question scores
  **44.6%**, about four times the 11.1% chance rate; the gold is the unique longest option 42.4% of the time and
  averages 98.4 characters against 61.6 for distractors. Psychology follows at 33.0% (three times chance).
- **The mean length gap is a poor proxy for the cue.** Engineering's gold is only 1.0 character longer on average,
  yet pick-longest gains +10.9 points, because the gold is almost never the shortest option (6 of 969, 0.6%) and
  often ties for longest. "Other" has a +12.0-character gap but only a +1.3-point lift. In business and math the
  mean gold is slightly *shorter* than the mean distractor, yet the lift is still (barely) positive.
- **Quantitative categories carry little of it.** Math (+0.2), health (+0.6) and philosophy (+1.7) are near
  chance; the shortcut lives in the verbal, explanation-style categories.

So a closed-book MMLU-Pro accuracy should be read against a length-only floor of about **18% pooled** rather than
the ~11% random baseline, and about **45% in biology** and **33% in psychology**. Combined with audit 59, the
expansion traded one artifact for another: the position / "all of the above" cue is gone, but the gap between
how the correct answers and the distractors were written got larger.

## Limits and next step

This audit does not say *which* options carry the bias. MMLU-Pro mixes questions inherited from MMLU with new
ones (STEM websites, TheoremQA, SciBench), and its distractors mix MMLU's originals with options added during the
expansion. A follow-up audit (62) joins MMLU-Pro's MMLU-derived questions back to MMLU to separate the original
distractors from the added ones and test whether the added options are what made the gold stand out. Length is
measured on raw option text; LaTeX or units can lengthen an option without changing its content.

## Reproduce

```
python -m unittest -v        # hand-traced fixtures, structural gate and prediction logic
python job.py --out-dir out  # downloads MMLU-Pro test parquet, writes out/results.json
```

`job.py` reads `TIGER-Lab/MMLU-Pro` (`default`, `test`) from the HuggingFace auto-converted parquet via the
datasets-server parquet API. The structural gate fails the run if the pooled parse drifts from audit 59's, so a
loader change cannot silently move the per-category cut. All statistics are standard library.

## Files

- `job.py`: loader, per-category length census, structural gate, predictions; writes `results.json`
- `gold_length.py`: length / unique-longest / pick-longest logic (verbatim from audits 51/52/60)
- `cases.py`: hand-traced synthetic fixture, real-data config, pinned audit-59 and MMLU reference numbers
- `test_mmlu_pro_length.py`: unit tests
- `results.json`: frozen output (pooled, per category, gate, predictions)
- `requirements.txt`: a parquet reader only

## Licence

Code is Apache-2.0. This write-up and `results.json` are CC BY 4.0. Upstream: MMLU-Pro (`TIGER-Lab/MMLU-Pro`) is
MIT-licensed. Authored by AI agents working in MV2's name (Munim, Inc.).
