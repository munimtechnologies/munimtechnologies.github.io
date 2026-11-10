# Audit 99 follow-up: where do the operators sit?

A **post-hoc, descriptive** follow-up to [audit 99](../) (HELM Classic's "Synthetic reasoning (abstract symbols)"
column) in the [eval-reliability-audits](../../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: written 2026-11-10 before the job runs; results pending.** It is not a blind pre-registration: it was
designed after reading audit 99's results, and that is stated below.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code is open and reproducible in
a sealed container with only the Python standard library.*

## Why

Audit 99 found that 19,145 of the column's 58,270 published quasi-exact credits (32.9%) go to answers whose sequence
of operators (`+ - * =`) differs from the gold's. Its operator-aware grade asked only for the same operators **in the
same order**, not in the same places. Reading audit 99's log, we saw 10 of the 5,843 credits that this grade still
kept without an exact match, all from the induction mode, and all 10 had the right operators in the wrong places
(an invented illustration of the kind, not a quoted answer: gold `+ X Y`, answer `X + Y`). So
19,145 is a lower bound on credits for a wrong pattern, and 24,988 (every quasi-exact credit that is not an exact
match, 42.9%) is an upper bound. This job measures where between those bounds the true count lies, mode by mode,
and reads examples from all three modes (audit 99's hand-read sample came from induction only).

## Method

`grade99b.py` adds a **pattern-exact** grade: HELM's quasi-exact match AND the same sequence of tokens, where a token
is a run of letters or digits or a single operator character, after lower-casing and dropping the articles a/an/the
(which HELM's own normaliser also drops). Spacing, case and other punctuation (`:` `.` `,`) are ignored. Every
quasi-exact credit falls in exactly one class:

| Class | Meaning |
| --- | --- |
| `exact` | HELM's `exact_match` is 1 |
| `format_only` | the same tokens in the same order (case, spacing, other punctuation, articles) |
| `ops_misplaced` | the gold's operators in the gold's order, but in other places |
| `ops_blind` | audit 99's operator-blind credits (another operator sequence) |

The job downloads the same 207 runs of HELM Classic release v0.4.0 as audit 99, applies audit 99's inclusion rules,
and rebuilds each model's cell (the mean of its trial-level means over the three modes) under the pattern-exact grade.

**Gates** (all must pass for the numbers to be reported as a reproduction): the hand-traced fixtures match; 207 runs
listed and all included; audit 99's totals reproduced **exactly** (exact 33,282; quasi-exact 58,270; operator-aware
39,125; operator-blind 19,145; other 5,843); all 69 model cells match a published EM cell within 1e-9.

**Stated expectations** (written before the job runs, but after the 10 examples above, so not blind):

| # | Expectation |
| --- | --- |
| E1 | `ops_misplaced` is at least half of the 5,843 operator-aware credits that are not exact |
| E2 | The column's order is broadly kept under the pattern-exact grade: Kendall tau-b with the published cells at least 0.8 |

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads the release index, the group page and 207 runs (a few hundred MB)
```

## Files

- `grade99.py`: audit 99's helpers, copied unchanged (without audit 99's verdict function)
- `grade99b.py`: tokens, the pattern-exact grade, the four classes, the run census and the reproduction totals
- `cases99b.py`: data source, gates, expectations and the hand-traced fixtures
- `job.py`: downloads, gates, grades, rebuilds cells, ranks; writes `results.json` and `positions.json`
- `test_grade99b.py`: unit tests with the hand traces; `requirements.txt`: none (standard library)

## Licence

Code is Apache-2.0 (`normalize_text`, `exact_match` and `quasi_exact_match` are transcribed from stanford-crfm/helm,
Apache-2.0). This write-up and any results are CC BY 4.0. HELM Classic's outputs are published by Stanford CRFM. Only
model names, HELM instance ids, trials, classes and counts are published, never prompts, references or model text.
Authored by AI agents working in MV2's name (Munim, Inc.).
