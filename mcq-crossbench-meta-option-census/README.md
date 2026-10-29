# mcq-crossbench-meta-option-census

Audit 57 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.

The work is carried out by AI agents working in MV2's name and is disclosed as AI-made wherever a platform,
contest or project asks.

## What this audit targets

[Audit 56](../mcq-mmlu-meta-option-census/) found that MMLU's "the answer tends to be last" tilt
(audits [53](../mcq-gold-position-census/)/[54](../mcq-mmlu-subject-position-census/)) is **mostly** an
artifact of unshufflable **meta options** — "All of the above", "None of these", "Both A and B", Roman-numeral
statement sets — which are conventionally written last and are the gold far above chance. That raises the
obvious next question: **is the meta-option mechanism a general MCQ-authoring convention, or is it specific to
MMLU?**

This audit ports audit 56's classifier to four other popular multiple-choice benchmarks — **ARC-Easy**,
**ARC-Challenge**, **CommonsenseQA** and **HellaSwag** — and measures, for each, how many questions carry a
meta option, where those options sit, how often they are the gold, and (as an independent lens) whether the
gold **position** rejects a uniform distribution the way MMLU's does. Everything measured here is a property of
**how each benchmark was built**, distinct from a *model's* position / selection bias.

## Method

- **Reuse already-passed cores verbatim.** The meta-option classifier (`meta_option.py`) and the gold-position
  census (`position_census.py`) are reused **unchanged** from audit 56 (priority `roman` > `aota` > `nota` >
  `letterref` > `plain`; a meta phrase counts only if it is a "short" option of ≤ 10 whitespace tokens). The
  hand-traced position and meta fixtures and their unit tests are reused too.
- **Per-benchmark loaders.** `loaders.py` reads each benchmark from the HuggingFace auto-converted parquet via
  the datasets-server parquet API, keeps only gold-bearing splits (CommonsenseQA and HellaSwag ship a goldless
  `test`, which is excluded), and normalises each into (choices, gold-index) records. Expected per-split row
  counts are hard-coded and checked before any census runs.
- **Pre-register before measuring.** Both fixtures are asserted for exact equality before any real file is read;
  the five predictions below were fixed — each a finding either way — before any real number was seen.
- **Chi-square without scipy.** The Pearson statistic and df are reported with a hard-coded critical value at
  α = 0.001 so a reader can recompute an exact p-value. MMLU numbers are **cited from audit 56**, not recomputed.

## Findings

All four benchmarks parse cleanly on their gold-bearing splits and the per-split counts match exactly
(ARC-Easy 5,197, ARC-Challenge 2,590, CommonsenseQA 10,962, HellaSwag 49,947; 0 bad keys, 0 degenerate
everywhere — **P1 HELD**).

### Meta options are essentially absent outside MMLU

| benchmark | n (gold-bearing) | meta questions | meta rate | MMLU reference (audit 56) |
| --- | --- | --- | --- | --- |
| ARC-Easy | 5,197 | 0 | 0.00% | 4.86% |
| ARC-Challenge | 2,590 | 0 | 0.00% | 4.86% |
| CommonsenseQA | 10,962 | 0 | 0.00% | 4.86% |
| HellaSwag | 49,947 | 1 | 0.002% | 4.86% |
| ARC (Easy+Challenge pooled) | 7,787 | 0 | 0.00% | 4.86% |

- **P2 (HellaSwag essentially no meta) HELD.** Rate 0.002% (1 of 49,947) < 0.5% threshold.
- **P3 (CommonsenseQA essentially no meta) HELD.** Rate 0.00% (0 of 10,962) < 0.5% threshold.
- **P4 (headline) FAILED — and that is the finding.** The pre-registered guess that **ARC carries meta options
  at an exam-like rate (> 1%), like MMLU** is wrong: ARC's pooled meta rate is **0.00%** (0 of 7,787). The
  meta-option mechanism that explains most of MMLU's last-option tilt is **not** shared by these four
  benchmarks — it is specific to MMLU among them. ARC is drawn from standardised science exams yet, unlike
  MMLU, its authors did not write "all of the above"-type options.
- **P5 (meta options sit last ≥ 90%) FAILED — vacuously.** With only 1 meta option across all four benchmarks
  (far below the pre-set n ≥ 30 floor) there is nothing to test; the single HellaSwag "all of those"-type
  option sat at position 1, not last. The emptiness is itself the point.

### None of the four shows MMLU's gold-position skew

At each benchmark's modal option count (coverage ≥ 99.5% everywhere):

| benchmark | n | k | gold-position rates | best constant | χ² (df) | rejects uniform at 0.001 |
| --- | --- | --- | --- | --- | --- | --- |
| ARC-Easy | 5,173 | 4 | .250 / .255 / .261 / .234 | pos 2, 26.1% | 8.16 (3) | no |
| ARC-Challenge | 2,577 | 4 | .219 / .262 / .263 / .256 | pos 2, 26.3% | 13.61 (3) | no |
| CommonsenseQA | 10,962 | 5 | .196 / .203 / .200 / .204 / .197 | pos 3, 20.4% | 2.75 (4) | no |
| HellaSwag | 49,947 | 4 | .250 / .251 / .249 / .250 | pos 1, 25.1% | 0.19 (3) | no |

Not one rejects uniformity at α = 0.001 (critical value 16.27 for df 3, 18.47 for df 4). MMLU's gold position,
by contrast, rejects strongly (audit 53: χ² = 42.93, df 3), and audit 56 showed that rejection is carried by
the meta options now shown to be MMLU-specific. So **MMLU's "the answer is D" tilt — both the meta-option
mechanism and the resulting position skew — does not generalise to ARC-Easy, ARC-Challenge, CommonsenseQA or
HellaSwag.** A position-only or "pick the all-of-the-above option" guesser that banks a measurable edge on MMLU
earns essentially nothing on these four.

## Why this is new

Model-side position / selection bias on MCQ benchmarks is heavily studied, and audit 56 established the
construction-side meta-option mechanism *within* MMLU. A prior-art check (Oct 2026) found **no source that ports
a meta-option / "all of the above" census across ARC, CommonsenseQA and HellaSwag to test whether MMLU's
mechanism is benchmark-specific**. The clean cross-benchmark result — meta options are an MMLU idiosyncrasy, and
these four benchmarks' gold positions are consistent with uniform — is, to our knowledge, first reported here.

## Limits

- The classifier is the conservative regex-based one from audit 56; it may miss an unusually phrased meta option
  in these corpora. But it would have to miss hundreds to overturn the "essentially absent" result, and the
  single HellaSwag hit shows it does fire when the phrase appears.
- CommonsenseQA and HellaSwag ship a goldless `test` split, excluded here; the census is over train+validation.
- This measures construction only. Whether a given model exploits positions differently across these benchmarks
  is a separate, model-side question.

## Files

- `meta_option.py`: the meta-option classifier, reused verbatim from audit 56.
- `position_census.py`: the gold-position census core, reused verbatim from audits 53/54/56.
- `loaders.py`: per-benchmark parquet readers with hard-coded expected split counts.
- `cases.py`: the hand-traced position and meta fixtures and their exact targets (reused from audit 56).
- `test_position_census.py`, `test_meta_option.py`, `test_loaders.py`: unit tests for the census core, the
  classifier predicates, both fixtures, the chi-square statistic and the loader normalisation.
- `job.py`: the runner. It checks both fixtures, fetches each benchmark's parquet, classifies, runs the census
  and the five predictions, and writes `results.json`.
- `results.json`: the frozen output, reproduced in a sealed container.

## Licence

Code is Apache-2.0. This write-up and `results.json` are CC BY 4.0. The benchmarks are read via the HuggingFace
datasets-server parquet API and are not redistributed here; each keeps its own upstream licence (ARC-Easy /
ARC-Challenge CC BY-SA 4.0; CommonsenseQA MIT; HellaSwag MIT; MMLU MIT, cited from audit 56). Authored by AI
agents working in MV2's name (Munim, Inc.).
