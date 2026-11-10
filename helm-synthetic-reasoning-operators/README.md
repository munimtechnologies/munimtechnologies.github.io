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
