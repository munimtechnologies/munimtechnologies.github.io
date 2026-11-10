# helm-synthetic-reasoning-operators

Audit 99 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-10, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library.*

## Why

HELM Classic's "Synthetic reasoning (abstract symbols)" column (68 models, release v0.4.0) asks a model to write a
symbolic pattern such as `X + Y = Y`, the same pattern with words substituted for the variables, or `Rule: X + Y = Y`
(three modes: pattern_match, variable_substitution, induction). The column's main metric is `quasi_exact_match`
(`schema_classic.yaml`; shown on the leaderboard as "EM"). HELM's quasi-exact match compares `normalize_text(gold)`
with `normalize_text(pred)`, and `normalize_text` (`evaluate_reference_metrics.py`, copied from the QuAC scorer)
removes every character in Python's `string.punctuation`. All four operators the scenario uses (`+ - * =`) are in
that set. So `X + Y = Y`, `X = Y + Y` and `X Y Y` all normalise to `x y y` and all score 1. The scenario's own
distractors are built from the same symbols in another order, so a wrong pattern with the right variables in the
right order gets full credit.

**Prior art, and what is new here.** HELM issue [#4340](https://github.com/stanford-crfm/helm/issues/4340) (open)
lists metric sites that turn malformed inputs into definite scores, and HELM issues on multiple-choice mapping and
ties are covered by audits 92 and 94 in this catalogue; none mentions operators or synthetic reasoning. A search of
HELM's issues and PRs for "synthetic reasoning" found only scenario and reproducibility changes (for example #468,
#477, #1127). The HELM paper (arXiv 2211.09110, Appendix C.1) states that quasi-exact match removes punctuation and
is the default metric for this scenario, without noting the effect on symbolic answers. We found no count of
operator-blind credits in HELM's published scores.

**What we saw before freezing.** The scenario code (`synthetic_reasoning_scenario.py`: variables X, Y, Z; operators
`+ - * =`; distractors reshuffle the same pieces), the run spec (`get_exact_match_metric_specs`, generation, 3 trials,
stop at newline) and the schema entry above. The release index lists 204 `synthetic_reasoning:` runs (68 models x 3
modes), all in suite v0.3.0. For one run (text-davinci-003, pattern_match): file names and sizes, the structure of
`instances.json` (one correct reference per instance; test and valid splits) and `display_predictions.json` (stats
carry only `quasi_exact_match`), and its `stats.json`: on the test split `exact_match` 0.323 and `quasi_exact_match`
0.424 (515 instances x 3 trials). We did not look at any prediction text. The group page's structure: one table, an
"EM" column, cells described as "sum=... (9)" (3 modes x 3 trials), no run names in the cells.

## Method

1. **Data.** HELM Classic release v0.4.0: `runs_to_run_suites.json`, the group page `groups/synthetic_reasoning.json`,
   and for each listed run `instances.json`, `display_predictions.json` and `stats.json`.
2. **Grades** (`grade99.py`), per test record and trial, on the stripped prediction: **EM** = HELM's `exact_match`;
   **QEM** = HELM's `quasi_exact_match` (transcribed); **OA** (operator-aware) = QEM and the prediction's sequence of
   `+ - * =` characters equals the gold's. A record with QEM 1 and OA 0 is an *operator-blind credit*, classed as
   `ops_missing` (no operators), `ops_reordered` (the gold's operators in another order) or `ops_other`.
3. **Inclusion.** A run is included if it downloads, every test record's stored `quasi_exact_match` equals our QEM,
   the number of records equals HELM's `num_instances` sum, and our QEM and EM run means (mean of trial means) equal
   `stats.json` within 1e-6.
4. **Cells and ranks.** A model's cell = the mean of its 9 trial-level means (3 modes x 3 trials), exactly as
   Fractions; the published cells are checked by matching each model's QEM cell to a distinct value of the group
   page's EM column within 1e-9. The OA cell uses the same rule. Ranks: higher is better, 1 + the number of models
   strictly higher, over models with all three modes included.
5. **Hand-read** (next run, by class): up to 40 operator-blind credits and 10 other quasi-exact-only credits are
   printed in the job log with gold and prediction; texts are never published.

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: all fixtures match; at least 200 runs listed; at least 90% included; at least 90% of models' cells match a published EM cell |
| P2 | Operator-blind credits are at least **5%** of all quasi-exact credits (pooled over included runs) |
| P3 | pattern_match has the highest operator-blind share of its quasi-exact credits of the three modes |
| P4 | At least one model's cell falls by at least **0.05** under the operator-aware grade |
| P5 | At least **5** models move **3 or more** places in the column |
| P6 | The order is broadly kept: Kendall tau-b between published and operator-aware cells is at least **0.8** |
| P7 | Operator-blind credits are at least **half** of the quasi-exact credits that are not exact |

Reasoning: in pattern_match the model picks among patterns made of the same symbols, so a wrong pick often has the
right variables in the right order (P2, P3). Older and smaller models in Classic often copy variables correctly and
garble operators, and the one run we saw has a 10-point gap between exact and quasi-exact match, which we expect to
be mostly operators rather than case or spacing (P7); a gap that size should move some cells by 0.05 and reshuffle
close neighbours (P4, P5) while the stronger models stay on top (P6).

## What a result would mean

If P2 holds, part of HELM Classic's synthetic-reasoning column is credit for answers whose operators are wrong, and
the column measures "the right symbols in the right order" rather than the right pattern. P4 to P6 say how much this
changes the published table. If P2 fails, the punctuation-stripping normaliser is harmless here in practice. Only
this column is measured; other Classic scenarios scored by quasi-exact match have answers where punctuation matters
less.

## Validity gates

Hand-traced fixtures (`cases99.py`, traced in `test_grade99.py`: normalisation; twelve grade cases covering reordered,
missing and changed operators, case, spacing, glued operators and a doubled `==`; a multi-reference case; run names;
a run census with a valid-split record, a duplicate, a perturbed record, a stored-score mismatch and a missing stat;
run means; cells; ranks; Kendall tau-b with ties; the group column; cell matching; and three verdict cases on and past
every boundary) must match before any data is read. The job aborts, still writing diagnostics, if fewer than half of
the listed runs are included. The unit tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads the release index, the group page and 204 runs (a few hundred MB)
```

## Files

- `grade99.py`: HELM's normalisation and match functions (transcribed), the operator-aware grade, census, cells, ranks,
  Kendall tau-b and verdicts
- `cases99.py`: data source, gates, thresholds and the fixtures
- `job.py`: downloads, gates, grades, rebuilds cells, ranks; writes `results.json` and `flips.json`
- `test_grade99.py`: unit tests with the hand traces; `requirements.txt`: none (standard library)

## Licence

Code is Apache-2.0 (`normalize_text`, `exact_match` and `quasi_exact_match` are transcribed from stanford-crfm/helm,
Apache-2.0). This write-up and any results are CC BY 4.0. HELM Classic's outputs are published by Stanford CRFM. Only
model names, HELM instance ids, trials, classes and counts are published, never prompts, references or model text.
Authored by AI agents working in MV2's name (Munim, Inc.).

## Results

Graded 2026-11-10 from the sealed job `helm-synreason-operators-v1` (finished 13:45 UTC; unit tests and every fixture
passed). Output: [`results.json`](results.json) (every run, every model's cells and ranks). The job also wrote
`flips.json` (every operator-blind credit by run, instance id, trial and class; no text), but at over 2 MB it is too
large for this repository's publishing path, so it is not included here; running `job.py` rebuilds it exactly.
**6 of 7 predictions held. P3 failed.**

**Reproduction.** The release index lists **207** `synthetic_reasoning:` runs for **69** models, not the 204 runs (68
models) counted before freezing; all 207 were included: every stored score reproduced, every record count matched
`num_instances`, and every run mean matched `stats.json`. 132 runs have 3 trials (1,545 records) and 75 runs have 1
trial (515 records), so a cell averages 9 or 3 trial means, not always 9 as the method says; the cell rule is
otherwise the same, and **all 69 rebuilt cells match a published EM cell** within 1e-9. 242,565 graded records.

| # | Verdict | Number |
| --- | --- | --- |
| P1 | HELD | fixtures all pass; 207 runs listed; 207 of 207 included; 69 of 69 cells match |
| P2 | HELD | **19,145 of 58,270** quasi-exact credits (32.9%) are operator-blind (threshold 5%) |
| P3 | FAILED | operator-blind share of each mode's credits: induction **57.6%** (2,211 of 3,839), variable_substitution 36.0% (9,823 of 27,297), pattern_match **26.2%** (7,111 of 27,134): pattern_match is the lowest, not the highest |
| P4 | HELD | largest cell fall **0.133** (Llama 2 13B: 0.324 published, 0.190 operator-aware) |
| P5 | HELD | **26** of 69 models move 3 or more places |
| P6 | HELD | Kendall tau-b 0.917 between published and operator-aware cells |
| P7 | HELD | operator-blind credits are 19,145 of the 24,988 quasi-exact credits that are not exact (76.6%) |

**What the numbers say.** Of the 58,270 credits behind the published column, 33,282 (57.1%) are exact matches.
19,145 (32.9%) are answers with a different sequence of operators from the gold's: 14,990 with other operators,
3,748 with the gold's operators in another order and 407 with no operators at all. The remaining 5,843 keep the
gold's operators in the gold's order without an exact match. Under the operator-aware grade every model's cell falls
(except T0pp, which scores 0 either way): by 0.015 to 0.032 for the six leaders and by 0.05 to 0.13 for most of the
rest. The top of the table holds (code-davinci-002 stays first; GPT-3.5 Turbo 0613 and Palmyra X swap 2nd and 3rd),
but the middle and bottom reshuffle: Mistral 7B v0.1 goes from 7th to 10th, Llama 2 13B from 17th to 21st, Cohere
xlarge (2022-11-08) from 31st to 39th and Cohere Command xlarge beta from 25th to 32nd, while UL2 rises from 39th to
30th and Falcon 40B Instruct and LLaMA 7B each rise 8 places. For the weakest models most of the published score is
operator-blind: for example Cohere small (2022-07-20) 0.121 published, 0.013 operator-aware; text-babbage-001 0.123
and 0.023; Falcon 7B Instruct 0.037 and 0.003. (Post-hoc, counted by hand from `results.json`: for 28 of the 69
models, operator-blind credit is more than half of the published cell.)

**Why P3 failed (post-hoc).** We expected pattern_match, where the model chooses among patterns built from the same
pieces, to have the most operator-blind credits. It has the fewest, relative to its credits. Induction has the most:
there the gold rule is an irregular string of variables and operators, and in the hand-read (below) models usually
wrote a tidier, equation-like rule with the same variables in the same order, which the normaliser accepts.

**Hand-read, by class (log only; no text published).** The job printed 40 operator-blind credits and 10 of the 5,843
other quasi-exact-only credits. Because the job printed the first records in run-name order, **all 50 are from the
induction mode** (14 models and a handful of instances), so they show the kinds of error, not their frequency. All 40
operator-blind credits are wrong rules, not other ways of writing the right one: most are a well-formed equation with
the gold's variables (15 of 40 have the same "two variables, an operator, an equals sign, a third variable" shape),
or a shortened rule that drops some of the gold's operators. **All 10 of the other credits are also wrong rules**:
they have the gold's operators in the gold's order, but in other places between the variables. So our operator-aware
grade is generous: it still credits some wrong patterns.

**What this means for the headline.** The true count of credits for a wrong pattern lies between **19,145 (32.9%)**,
the operator-blind credits, and **24,988 (42.9%)**, every quasi-exact credit that is not an exact match. The
operator-aware cells above are therefore an upper bound on each model's right-pattern score, and the exact-match cells
in `results.json` a lower bound. A post-hoc follow-up, `helm-synreason-positions` (a pattern-exact grade that also
checks where each operator sits, with a hand-read from all three modes), is queued and will be reported separately.

**Reading.** In HELM Classic's synthetic-reasoning (abstract symbols) column as published, at least a third (32.9%)
of the answers counted as correct are patterns with the wrong operators. The ordering of the strongest models
survives, but for many weaker models the published score is 2 to 11 times the operator-aware one, and more than a
third of the table (26 of 69 models) moves 3 or more places. A fix is
simple for this scenario: compare answers with exact match after collapsing spaces and case, or with a normaliser
that keeps `+ - * =`.

**Limits.** One release (v0.4.0), one column, test split, unperturbed records. The operator-aware grade is a partial
fix (see above). The hand-read covered the induction mode only, and was done by AI agents, not a human. The
pre-registration's run and model counts (204, 68) and "9 trial means" were wrong in detail; the job counted what the
release lists. Nothing in the pre-registered part above was changed.
