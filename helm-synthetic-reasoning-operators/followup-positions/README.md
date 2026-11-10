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

## Results

Graded 2026-11-10 from the sealed job `helm-synreason-positions-v1` (finished 21:40 UTC; unit tests passed).
Outputs: [`results.json`](results.json) (totals, classes by mode, every model's cells and ranks under four grades)
and [`positions.json`](positions.json) (all 5,843 operator-aware credits that are not exact, by run, instance id,
trial and class; no text). **Every gate passed and both stated expectations were met.**

**Gates.** All fixtures matched; 207 runs listed, 207 included; audit 99's totals reproduced exactly (exact 33,282;
quasi-exact 58,270; operator-aware 39,125; operator-blind 19,145; other 5,843); 69 of 69 cells match a published EM
cell.

**Classes of the 58,270 published credits.**

| Class | Credits | Share |
| --- | --- | --- |
| `exact` | 33,282 | 57.1% |
| `format_only` | 7 | 0.01% |
| `ops_misplaced` | 5,836 | 10.0% |
| `ops_blind` | 19,145 | 32.9% |

So 5,836 of the 5,843 operator-aware credits that are not exact (99.9%) have the gold's operators in the wrong
places (E1 met; the threshold was half). Only 7 differ from the gold in formatting alone. The pattern-exact grade
credits **33,289** answers, and the credits for a wrong pattern are **24,981 of 58,270 (42.9%)**: the upper bound of
audit 99, less 7.

**By mode** (share of each mode's credits that are a wrong pattern, `ops_blind` + `ops_misplaced`):

| Mode | Credits | Exact | Format only | Misplaced | Operator-blind | Wrong-pattern share |
| --- | --- | --- | --- | --- | --- | --- |
| induction | 3,839 | 1,352 | 0 | 276 | 2,211 | 64.8% |
| pattern_match | 27,134 | 16,852 | 0 | 3,171 | 7,111 | 37.9% |
| variable_substitution | 27,297 | 15,078 | 7 | 2,389 | 9,823 | 44.7% |

**Cells and ranks.** Because only 7 credits separate the two grades, the pattern-exact cells are within 0.0013 of the
exact-match cells, and Kendall tau-b with the published cells is **0.910** for both (E2 met; the threshold was 0.8;
the operator-aware grade gave 0.917). **29 of 69 models move 3 or more places** (26 under the operator-aware grade).
The largest fall is 0.155 (Llama 2 13B: 0.324 published, 0.169 pattern-exact; 17th to 20th). code-davinci-002 stays
first (0.540 to 0.501) and GPT-3.5 Turbo 0613 second; text-davinci-003 and Palmyra X swap 3rd and 4th. Further down,
Cohere Command xlarge beta goes from 25th to 35th, Cohere xlarge (2022-11-08) from 31st to 38th and Mistral 7B v0.1
from 7th to 10th, while LLaMA 7B rises from 54th to 44th, Falcon 40B Instruct from 36th to 27th and LLaMA 13B from
37th to 29th. (Post-hoc, counted by hand from `results.json`: for **39 of the 69 models**, more than half of the
published cell is credit for a wrong pattern.)

**Hand-read (log only; no text published).** This time the job spread its prints across all three modes by a stable
hash, capped per mode and class: 24 operator-blind credits, 24 misplaced credits and 6 of the 7 format-only credits.
Read by AI agents, not a human: **all 24 misplaced credits are wrong patterns** (for example, the gold's operators
moved from between two variables to before them, or a closing `=` moved inside), and so are all 24 operator-blind
credits (operators dropped, added or changed). 5 of the 6 format-only credits are the gold followed by a stray `|`,
and 1 writes the gold's `* *` as `**`; we count all 6 as the right pattern. The gold strings in this scenario are
symbol sequences, not equations with equivalent rewritings, so a different token order is a different answer.

**Reading.** In HELM Classic's synthetic-reasoning (abstract symbols) column as published, **42.9% of the credited
answers are the wrong pattern**; the true right-pattern score of each model is, to within 7 records across the whole
column, its exact-match score. The table's top survives, but the column's quasi-exact metric adds between 0.034 and
0.155 to every model with a non-zero score. A fix for this scenario is exact match after collapsing case and spaces
(which our pattern-exact grade is, apart from articles and non-operator punctuation).

**Limits.** Post-hoc and descriptive, not a blind pre-registration (stated above). One release, one column, test
split, unperturbed records. The pattern-exact grade is our own; it ignores articles and punctuation other than
`+ - * =`, which this scenario's golds never use as content as far as we saw.
