# helm-dyck-last-token

Audit 100 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-10, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library.*

## Why

HELM Classic's "Dyck" column asks a model to write the closing brackets that complete a Dyck-3 prefix (three bracket
types). HELM's scenario (`dyck_language_scenario.py`) cuts 1 to 3 closers off the end of a balanced sequence, and the
gold answer is those closers joined by single spaces, for example ` ) ] }`. The run spec (`classic_run_specs.py`,
`max_tokens=5`, stop at newline) scores it with `exact_match_indicator`, the column's main metric in
`schema_classic.yaml` (shown on the leaderboard as "EM").

HELM's `exact_match_indicator` (`evaluate_reference_metrics.py`) keeps only the text after the **last** occurrence of
its `indicator` in both gold and prediction, then applies exact match. The default indicator is a single space, and
the metric is mapped with no other argument. So for the gold ` ) ] }` only `}` is compared: `] ) }`, `( }` and `}`
all score 1, and a right answer written without spaces, `)]}`, scores 0. With three bracket types, a model that only
gets the outermost bracket right scores 1 on every instance.

**Prior art, and what is new here.** The HELM paper (arXiv 2211.09110) says that for Dyck "we report strict
exact-match results", and describes the metric as exact match "up to a specified indicator", the default for Dyck and
GSM8K. A search of HELM's issues and PRs for "dyck" (17 results, all closed: the task's PRs #111, #237, #272, a split
fix #868) and for "exact_match_indicator" (5 results) found no discussion of how the indicator works for Dyck; the
PR that added the task (#237) reports the metric's value only. A web search found no report that HELM's Dyck scores
compare only the last bracket. Older work on other Dyck tasks (Yu et al. 2019) criticises metrics that look at one
bracket; we found nothing on HELM's. We found no count of last-bracket-only credits in HELM's published scores.

**What we saw before freezing.** The scenario, run spec and metric code above. The release index lists about 68
`dyck_language_np=3` runs, all in suite v0.3.0 (a few with `stop=hash` or `global_prefix=nlg`). For one run
(text-davinci-003): `stats.json` has `exact_match_indicator` on the test split, mean 0.751 over 3 trials and 500
instances per trial, and no `exact_match` or `quasi_exact_match`; `display_predictions.json` records carry
`instance_id`, `train_trial_index`, `predicted_text` and per-record stats including `exact_match_indicator` and
`num_output_tokens`; `instances.json` has one correct reference per instance. The group page
(`groups/dyck_language.json`) has one table with an "EM" column (first row J1-Jumbo v1, 0.445, "sum=1.336 (3)") and no
run names in the score cells. We did not look at any prediction text.

## Method

1. **Data.** HELM Classic release v0.4.0: `runs_to_run_suites.json`, the group page, and for each listed
   `dyck_language` run `instances.json`, `display_predictions.json` and `stats.json`.
2. **Grades** (`grade100.py`), per test record and trial, on the stripped prediction: **IND** = HELM's
   `exact_match_indicator` (transcribed); **strict** = the prediction, whitespace removed, equals the gold sequence;
   **lenient** = the prediction's bracket characters equal the gold sequence (other text around a right answer is
   forgiven). An IND credit that is not strict is classed `format_only` (lenient: the right closers plus other text)
   or, on the prediction's brackets, `missing_leading` (a proper suffix of the gold), `extra_leading` (the gold is a
   proper suffix of it), `wrong_same_length` or `other`. A **wrong credit** = IND 1 and lenient 0. An **under-credit**
   = lenient 1 and IND 0. Each record's depth = the number of closers in its gold (1 to 3).
3. **Inclusion.** A run is included if it downloads, every test record's stored `exact_match_indicator` equals our
   IND, the number of records equals HELM's `num_instances` sum, and our run mean (mean of trial means) equals
   `stats.json` within 1e-6.
4. **Cells and ranks.** One cell per run (HELM's "Model/adapter" rows): the mean of its trial means, as exact
   Fractions; published cells are checked by matching each run's IND cell to a distinct value of the group page's EM
   column within 1e-9. The lenient and strict cells use the same rule. Ranks: higher is better, 1 + the number of runs
   strictly higher.
5. **Hand-read** (next run, by class): up to 8 records per class, at most one per run, spread over runs by a stable
   hash, are printed in the job log with gold and prediction; texts are never published.

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: all fixtures match; at least 60 runs listed; at least 90% included; at least 90% of included runs' cells match a published EM cell |
| P2 | Wrong credits are at least **5%** of all IND credits (pooled over included runs) |
| P3 | The wrong-credit share of IND credits is higher on 3-closer golds than on 2-closer golds |
| P4 | At least one run's cell falls by at least **0.05** under the lenient grade |
| P5 | At least **5** runs move **3 or more** places in the column under the lenient grade |
| P6 | The order is broadly kept: Kendall tau-b between published and lenient cells is at least **0.8** |
| P7 | `missing_leading` credits are fewer than **half** of the wrong credits |

Reasoning: a model that closes only the outermost bracket correctly, or gets the count right but the inner order
wrong, is fully credited, and with three bracket types even a guess at the last bracket succeeds often (P2). A
3-closer gold has two inner closers to get wrong, a 2-closer gold one (P3). Weaker models should lose most (P4, P5)
while the strongest, which mostly write whole right answers, stay on top (P6). A model that writes fewer closers than
needed usually writes the inner ones first, which are not the gold's last bracket, so a credited short answer should
be rarer than a credited answer of the right length with wrong inner brackets (P7).

## What a result would mean

If P2 holds, part of HELM Classic's Dyck column is credit for closing sequences that are wrong, and the column does
not measure the strict exact match the HELM paper describes. P4 to P6 say how much this changes the published table.
If P2 fails, last-bracket-only scoring is harmless here in practice. Only this column is measured; GSM8K also uses
`exact_match_indicator`, where comparing the last token of a worked answer is the intended design.

## Validity gates

Hand-traced fixtures (`cases100.py`, traced in `test_grade100.py`: the transcribed metric; fifteen grade cases
covering a right answer, each wrong-credit class, glued closers, an empty prediction, padding, a doubled space and a
right answer inside other text; a multi-reference case; a run census with a valid-split record, a duplicate, a
perturbed record, a missing stored score, a stored-score mismatch and a record at the token cap; run means; ranks;
Kendall tau-b with ties; the group column; cell matching; and three verdict cases on, past and without every
boundary) must match before any data is read. The unit tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads the release index, the group page and about 68 runs (tens of MB)
```

## Files

- `grade100.py`: HELM's `exact_match` and `exact_match_indicator` (transcribed), the strict and lenient grades,
  classes, census, cells, ranks, Kendall tau-b and verdicts
- `cases100.py`: data source, thresholds and the fixtures (all invented)
- `job.py`: downloads, gates, grades, rebuilds cells, ranks; writes `results.json`
- `test_grade100.py`: unit tests with the hand traces; `requirements.txt`: none (standard library)

## Licence

Code is Apache-2.0 (`exact_match` and `exact_match_indicator` are transcribed from stanford-crfm/helm, Apache-2.0).
This write-up and any results are CC BY 4.0. HELM Classic's outputs are published by Stanford CRFM. Only run names,
model names, HELM instance ids, trials, classes and counts are published, never prompts, references or model text.
Authored by AI agents working in MV2's name (Munim, Inc.).

## Results

Graded 2026-11-11. The sealed job `helm-dyck-last-token-v1` ran on 2026-11-11 from 00:35 to 00:38 UTC (176 s, Python
3.12, standard library only). All unit tests and all fixture gates passed before any data was read. Full numbers:
[results.json](results.json) (per-run classes, the 69-row table, verdicts). **6 of 7 predictions held; P6 failed
because the order changes far more than we expected.**

| # | Verdict | Measured |
| --- | --- | --- |
| P1 | HELD | all fixtures match; 69 runs listed, **69 of 69 included** (every stored per-record score, record count and run mean reproduced); **69 of 69** cells match a published EM cell |
| P2 | HELD | **24,395 of 40,778 published credits (59.8%) are wrong closing sequences** (threshold 5%) |
| P3 | HELD | wrong share of credits by gold length: 1 closer 42.3% (5,493 of 13,001), 2 closers 57.8% (7,257 of 12,564), **3 closers 76.5%** (11,645 of 15,213) |
| P4 | HELD | every cell falls; the largest fall is **0.600** (YaLM: 0.633 published, 0.033 lenient) |
| P5 | HELD | **54 of 69 runs** move 3 or more places |
| P6 | **FAILED** | Kendall tau-b published vs lenient **0.589** (vs strict 0.592); threshold 0.8 |
| P7 | HELD | `missing_leading` is 6,349 of 24,395 wrong credits (26.0%), under half |

**Totals.** 78,500 test records (157 trials of 500). HELM's indicator credits 40,778 (51.9% of records). Only 16,383
(20.9%) are strictly right, and 16,417 (20.9%) are right under the lenient grade. No credit is a right answer that only
differs in format (`format_only` = 0), so the strict and lenient grades differ only by 34 under-credits.

**What the wrong credits are** (24,395): `extra_leading` 8,689 (35.6%: the right closers with extra ones in front),
`other` 7,335 (30.1%), `missing_leading` 6,349 (26.0%: only the last one or two of the closers) and
`wrong_same_length` 2,022 (8.3%: the right number of closers, wrong inner brackets). 11,614 of the wrong credits
(47.6%) are on outputs that stopped at the 5-token cap; 35,882 of all 78,500 records (45.7%) did.

**Under-credits** (34): all in the two `stop=hash` runs (T5 11B 32, UL2 2). The stored prediction keeps the `#` stop
character glued to the last closer, so the last token is `]#`, not `]`.

**The table.** Published as the mean of trial means and re-computed the same way:

- The two leaders swap: Anthropic-LM v4-s3 goes from 0.849 (1st) to 0.526 (2nd), and code-davinci-002 from 0.805
  (2nd) to 0.567 (1st). TNLG v2 530B (4th to 3rd) and GPT-NeoX 20B (6th to 4th) rise. Pythia 12B falls from 3rd to
  9th (0.798 to 0.342).
- Large falls in place: Llama 30B 11th to 46th (0.706 to 0.128), Vicuna 13B v1.3 14th to 50th (0.686 to 0.114),
  RedPajama-INCITE-Instruct 3B 10th to 39th (0.708 to 0.162), YaLM 22nd to 62nd, Luminous Supreme 8th to 27th,
  Llama 2 13B 23rd to 54th.
- Rises: Jurassic-1 Large 54th to 31st, TNLG v2 7B 33rd to 15th, text-davinci-002 27th to 14th.
- Post-hoc, counted by hand from the table: in **56 of 69 runs more than half of the published score is credit for a
  wrong closing sequence** (the lenient cell is under half the published one). GPT-J 6B keeps 0.001 of its 0.337.

**Hand-read** (by AI agents; 8 records per wrong-credit class from 8 different runs, plus both under-credit examples
the job printed). All 32 wrong credits are wrong closing sequences, and every class label agrees with the record. In
2 of the 8 `other` records the model wrote the right closers and then kept closing (one more `]`, or two more `}`),
which over-closes the sequence. The two under-credits are right answers with the glued `#`. No text is published.

**What this means.** HELM Classic's Dyck column does not measure the strict exact match the HELM paper describes. Six
in ten of its published credits are for closing sequences that are wrong, and the share grows with the number of
closers the model has to write. Scored on the whole sequence, the column's order is only loosely related to the
published one (tau-b 0.589). The fix is small: score Dyck with `exact_match` after collapsing whitespace (or pass an
indicator that cannot occur inside the answer). The 34 under-credits are a separate, minor issue of stop sequences
kept in the stored output.

**Limits.** One release (Classic v0.4.0, all 69 Dyck runs, suite v0.3.0). Our lenient grade forgives other text around
a right answer; in this column that changes nothing except the 34 `#` cases. We did not re-query any model: a model
cut off at 5 tokens might have stopped correctly with more room, but no grade of the stored text can credit a
sequence that is wrong as written. The 56-of-69 count is post-hoc. The prior-art search was repeated on 2026-11-11
(HELM issues and PRs for "dyck": still 17, all closed, none about the metric).
