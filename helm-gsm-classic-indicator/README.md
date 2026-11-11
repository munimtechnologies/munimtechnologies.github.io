# helm-gsm-classic-indicator

Audit 101 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-11, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library.*

## Why

Audit 100 found that HELM Classic's Dyck column is scored with `exact_match_indicator`, which compares only the text
after the last space, and that six in ten of its credits are for wrong closing sequences. The same metric is the main
metric of HELM Classic's GSM8K column ("EM"), where comparing the last token was meant to read the final answer. This
audit checks whether that holds in the published scores, in the other direction: does the column score right answers 0?

HELM's GSM8K scenario (`gsm_scenario.py`) builds each gold as the worked solution with `####` replaced by
`The answer is` and a `.` appended, so the gold's last token is, for example, `72.`. The run spec (5 in-context
examples, `max_tokens=400`, stop at a blank line) scores with `exact_match_indicator` and `final_number_exact_match`,
but HELM Classic's published runs store only `exact_match_indicator`. That metric compares the last space-separated
token literally after stripping whitespace, so `The answer is 72` (no period), `The answer is $72.`,
`The answer is 1,000.` against `1000.`, `The answer is 72 apples.` and a right answer followed by more text all score
0. HELM Lite later scores GSM8K with `final_number_exact_match` (the last number of each text, commas removed).

**Prior art, and what is new here.** HELM's issues and PRs searched on 2026-11-11: "exact_match_indicator" (5
results: the Dyck PRs #111, #237, #868, the PR that added GSM8K #170, and an unrelated question #3526) and "gsm8k"
issues (11 results). The only scoring issue is #4337 (open), on `final_number_exact_match` reading a lone comma as
the final number in HELM Lite; audit 90 counted it on HELM Lite's 90 GSM8K runs. A web search found no report on how
HELM Classic's GSM8K column treats a right answer written differently. Truong et al. 2025 ("Fantastic Bugs", arXiv
2511.16842) flag invalid benchmark questions from response statistics, not scorer behaviour. We found no count of
under-credited answers in HELM Classic's published GSM8K scores.

**What we saw before freezing.** The scenario, run spec and metric code above. For one run (J1-Jumbo v1):
`stats.json` has `exact_match_indicator` on the test split, mean 0.054 over 3 trials of 1,000 instances, and no
`final_number_exact_match`; `display_predictions.json` records carry `instance_id`, `train_trial_index`,
`predicted_text` and per-record stats including `exact_match_indicator` and `num_output_tokens`. The group page
(`groups/gsm.json`) has one table with an "EM" column (first rows J1-Jumbo v1 0.054 and J1-Large v1 0.014; mean output
tokens 158.8 and 214.0) and run names only in the model cells' links; at least 61 rows. We did not look at any
prediction text.

## Method

1. **Data.** HELM Classic release v0.4.0: `runs_to_run_suites.json`, the group page, and for each listed `gsm:` run
   `instances.json`, `display_predictions.json` and `stats.json`.
2. **Grades** (`grade101.py`), per test record and trial, on the stripped prediction: **IND** = HELM's
   `exact_match_indicator` (transcribed); **FNEM** = HELM's `final_number_exact_match` (transcribed, including its
   regex); **CORR** = our stated-answer grade: the number right after the first "the answer is" in the prediction
   (any case; an optional `:` and `$` allowed; commas removed), or, when no number follows such a phrase, the
   prediction's last number; it scores 1 when that value equals the gold's answer (the number after the gold's last
   "The answer is") as an exact fraction.
3. **Classes.** An **under-credit** = CORR 1 and IND 0, classed `no_phrase` (no stated answer; the last number is
   right) or, by the text after the stated number: `continued` (it goes on to another line), `no_period` (nothing
   follows), `number_form` (only `.` follows, so the number is written differently from the gold's, e.g. `$72` or
   `1,000`), `words_after` (other text on the same line). An **over-credit** = IND 1 and CORR 0 (`changed`: the first
   stated answer is wrong although the last token matches). Also counted: records where FNEM and IND differ, and
   outputs whose FNEM final number is empty (`lone_comma`, the #4337 case).
4. **Inclusion.** A run is included if it downloads, every test record's stored `exact_match_indicator` equals our
   IND, the number of records equals HELM's `num_instances` sum, and our run mean (mean of trial means) equals
   `stats.json` within 1e-6.
5. **Cells and ranks.** One cell per run (HELM's "Model/adapter" rows): the mean of its trial means, as exact
   Fractions; published cells are checked by matching each run's IND cell to a distinct value of the group page's EM
   column within 1e-9. CORR and FNEM cells use the same rule. Ranks: higher is better, 1 + the number of runs
   strictly higher.
6. **Hand-read** (next run, by class): up to 8 records per class, at most one per run, spread over runs by a stable
   hash, are printed in the job log with the gold's answer and the prediction's last 160 characters; texts are never
   published.

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: all fixtures match; at least 60 runs listed; at least 90% included; at least 90% of included runs' cells match a published EM cell |
| P2 | Under-credits are at least **1%** of all IND credits (pooled over included runs) |
| P3 | Over-credits are fewer than under-credits |
| P4 | At least one run's cell rises by at least **0.01** under CORR |
| P5 | At least **5** runs move **3 or more** places in the column under CORR |
| P6 | The order is broadly kept: Kendall tau-b between published and CORR cells is at least **0.9** |
| P7 | `continued` is the largest under-credit class |

Reasoning: the in-context examples end every answer with "The answer is N." and a blank line, so most outputs copy
that form and are scored correctly; but over 1,000 instances, 3 trials and about 69 models, a right answer written
as `$72`, `1,000` or `72 apples`, or followed by more text, should still add up to at least 1% of credits (P2), while
a wrong first answer that happens to end on the gold's last token should be rarer (P3). Weak models write longer
outputs (mean 214 tokens for J1-Large v1) and many cells are close together near zero, so small gains move ranks
(P4, P5) while the top stays (P6). A model that does not stop at the blank line keeps writing after its answer, which
we expect to be the commonest way a right answer loses the last token (P7).

## What a result would mean

If P2 holds, HELM Classic's GSM8K column under-counts right answers, and "comparing the last token" is not a safe
reading of a stated answer even where it was meant to be. P4 to P6 say how much this changes the published table. If
P2 fails, the indicator is harmless on GSM8K in practice, and audit 100's recommendation (keep the indicator only
where the last token is the answer by design) stands as written. Only this column is measured.

## Validity gates

Hand-traced fixtures (`cases101.py`, traced in `test_grade101.py`: the three transcribed metrics, including HELM's
final-number regex on a calculator annotation and a lone comma; sixteen grade cases covering a right answer, each
under-credit class, an over-credit, an empty prediction, a wrong answer, a colon after the phrase, a phrase without a
number, `7.0` and a negative number; a multi-reference case; a run census with a valid-split record, a duplicate, a
perturbed record, a missing stored score, a stored-score mismatch and a record at the token cap; run means; ranks;
Kendall tau-b with ties; the group column; cell matching; and three verdict cases on, past and without every
boundary) must match before any data is read. The unit tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads the release index, the group page and about 69 runs (a few hundred MB)
```

## Files

- `grade101.py`: HELM's `exact_match`, `exact_match_indicator` and `final_number_exact_match` (transcribed), the
  stated-answer grade, classes, census, cells, ranks, Kendall tau-b and verdicts
- `cases101.py`: data source, thresholds and the fixtures (all invented)
- `job.py`: downloads, gates, grades, rebuilds cells, ranks; writes `results.json`
- `test_grade101.py`: unit tests with the hand traces; `requirements.txt`: none (standard library)

## Licence

Code is Apache-2.0 (`exact_match`, `exact_match_indicator` and `final_number_exact_match` are transcribed from
stanford-crfm/helm, Apache-2.0). This write-up and any results are CC BY 4.0. HELM Classic's outputs are published by
Stanford CRFM. Only run names, model names, HELM instance ids, trials, classes and counts are published, never
prompts, references or model text. Authored by AI agents working in MV2's name (Munim, Inc.).
