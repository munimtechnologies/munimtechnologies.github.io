# helm-wikifact-best-of-five

Audit 103 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-11, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library.*

## Why

HELM Classic (release v0.4.0) publishes a WikiFact "EM" column (fact completion, 10 relations such as `plaintiff`
and `instance_of`, at least 65 models). Its run spec asks each model for **5 completions per prompt at temperature 1.0**
(`wikifact:k=5`, commented "We will measure accuracy@k"). The published "EM" is described as quasi-exact match, but
it is computed on **one** of the five: HELM sorts the completions by log probability, highest first, and scores the
first after sorting (`score_1` in `evaluate_reference_metrics.py`; the sort was added in PR #834 for issue #42). What
that one completion is depends on how each model's API answered:

- **ranked**: the API returns real log probabilities and different samples, so "EM" scores the most likely of five
  temperature-1 samples;
- **zero_logprob**: the API returns log probability 0 for every completion (chat APIs of the time), the sort changes
  nothing, and "EM" scores the first sample, a single temperature-1 draw;
- **collapsed**: all five completions are the same text, so "EM" scores that one answer.

So the column may compare a best-of-five pick for some models with a single draw for others. Separately, HELM's
prediction pages show `completions[0]` (`run_display.py`) next to the score of the sorted top completion, which for a
ranked model can be a different answer.

**Prior art, and what is new here.** HELM's issues and PRs searched on 2026-11-11 for "wikifact" (15 results, all
closed): #42 and PR #834 added the sort by log probability; PR #576 enabled `num_outputs > 1` for Anthropic models and
notes they returned no log probabilities. A web search found no count of how the five completions behave per model and
no comparison of the published column with a single-sample estimate. We found nothing measuring this on the archived
runs.

**What we saw before freezing.** The run spec and metric code above. The part of `runs_to_run_suites.json` we read lists
wikifact runs in suite v0.3.0 (the Mistral 7B runs in v0.4.0), some with `stop=hash`. The group page `wikifact.json` has a "WikiFact"
table whose "EM" column is quasi-exact match (first rows J1-Jumbo v1 0.280, J1-Large v1 0.226, J1-Grande v1 0.269),
at least 65 rows and no run names. For one subject (`plaintiff`) we looked at the first 1 to 3 request states of three
runs: text-davinci-003 returned 5 completions with real, different log probabilities and 2 to 5 distinct texts;
gpt-3.5-turbo-0613 returned log probability 0 for every completion and token (2 distinct texts each); Anthropic's
`stanford-online-all-v4-s3` returned 5 identical completions with equal log probabilities. `display_predictions.json`
records carry one `predicted_text` and the stored `quasi_exact_match`; `stats.json` has `quasi_exact_match` and
`num_instances` on the test split (for davinci-003, plaintiff: 96 test instances per trial, 3 trials; instance_of:
850). We did not compute any score, count any class beyond these three runs, or read any other run.

## Method

1. **Data.** HELM Classic release v0.4.0: `runs_to_run_suites.json`, the group page, and for each listed `wikifact`
   `k=5` run `scenario_state.json` (all completions and log probabilities), `display_predictions.json` and
   `stats.json`. About 690 runs; about 20 GB are streamed and nothing is stored.
2. **Estimators** (`grade103.py`), per test record and trial, gold = any reference tagged correct, HELM's
   normalisation: **H** = HELM's EM (the completion with the highest log probability, stable sort), transcribed and
   required to reproduce every stored record score; **F** = the first completion (what the prediction page shows);
   **M** = the mean score over the returned completions (single-sample accuracy, defined the same way for every
   model); **K** = any completion scores (HELM's `quasi_exact_match@5`, not on the leaderboard).
3. **Run class.** `zero_logprob` if at least 90% of a run's records have every log probability 0; else `collapsed`
   if at least 90% have a single distinct text; else `ranked`. An adapter's class is its runs' common class, or
   `mixed`. "Unranked" = `zero_logprob` or `collapsed`.
4. **Inclusion.** A run is included if it downloads, every test record's stored score equals H, the number of
   records equals HELM's `num_instances` sum, and our run mean (mean of trial means) equals `stats.json` within 1e-6.
5. **Cells and ranks.** One cell per adapter (the run name without its subject): the mean over its runs of each run's
   mean, as exact Fractions, only when every listed run is included. Published cells are checked by matching each H
   cell to a distinct "EM" value within 1e-9. Ranks: higher is better, 1 + the number of adapters strictly higher.
   Bonus = H minus M. Movers = adapters whose rank under M differs from the published rank by 3 or more places.
6. **Display check.** Records where F and H differ, i.e. the page shows an answer whose own score is not the score
   shown next to it.
7. **Hand-read** (next run): up to 8 such records per run class, one per run, spread by a stable hash, are printed in
   the job log with the references and the five completions; texts are never published.

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: all fixtures match; at least 90% of listed runs included; at least 60 cells; at least 90% of cells match a published "EM" value |
| P2 | At least **4** adapters are unranked (`zero_logprob` or `collapsed`) |
| P3 | Pooled over records of ranked runs, H exceeds M by at least **2 percentage points** |
| P4 | The median bonus (H minus M) of ranked adapters is larger than that of unranked adapters |
| P5 | Ranked by M instead of the published H, at least **5** adapters move **3 or more** places |
| P6 | The order is broadly kept (Kendall tau-b between H and M cells at least **0.9**) |
| P7 | In ranked runs, the shown first completion and the scored completion get different scores on at least **5%** of records |
| P8 | At least **3 in 4** unranked adapters keep or improve their rank under M |

Reasoning: at temperature 1 a base model's single draw is often a less likely answer, while the most likely of five
draws is close to its greedy answer, so for ranked models the published number should sit clearly above their
single-draw accuracy (P3). An unranked model gets no such pick: its H equals M (collapsed) or is one draw of it
(zero_logprob), so its bonus is near zero (P4). Several chat or no-log-probability APIs of 2022 and 2023 are in
Classic (P2). Re-ranking everyone on the same footing should then lift the unranked models (P8) and move a handful
of close cells (P5) without re-ordering the column (P6). Whenever the top completion is not the first and only one of
the two is right, the page and the score disagree; with diverse samples we expect that on at least 1 record in 20
(P7).

## What a result would mean

If P3 and P4 hold, the WikiFact column compares a best-of-five pick for most models with a single draw for others,
so part of the gap between them is how their API answered, not what they know; M is a like-for-like alternative. If
P3 fails, picking by log probability adds little and the column is comparable as published. If P7 holds, HELM's
WikiFact prediction pages often show an answer that is not the one scored. Only one column of one release is
measured; M is single-draw accuracy at temperature 1, not greedy accuracy, which HELM did not run.

## Validity gates

Hand-traced fixtures (`cases103.py`, traced in `test_grade103.py`): six normalisation cases (articles, punctuation,
whitespace, an empty prediction and the quirk that "A" and "the" both normalise to nothing); five record cases (a
ranked pick, all log probabilities 0, five identical answers, a tie in log probability kept in order, and missing
golds or completions); parsing; a run census with a valid-split record, a duplicate, a perturbed record, a record
without a result, a missing and two mismatched stored scores (one equal to the first completion's score) and a shown
text that is not the first completion; run and adapter classes on and past the 90% boundary; run names; cells with a
missing run; ranks; Kendall tau-b with ties; cell matching; the group column; medians; and two verdict cases on and
past every boundary. They must match before any data is read. The unit tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads the release index, the group page and about 690 runs (about 20 GB, streamed)
```

## Files

- `grade103.py`: HELM's quasi-exact match (transcribed), the four estimators, the run census, classes, run names,
  cells, ranks, Kendall tau-b and verdicts
- `cases103.py`: data source, thresholds and the fixtures (all invented)
- `job.py`: downloads, gates, scores, classes, rebuilds cells, ranks; writes `results.json`
- `test_grade103.py`: unit tests with the hand traces; `requirements.txt`: none (standard library)

## Licence

Code is Apache-2.0 (HELM's normalisation and quasi-exact match are transcribed from stanford-crfm/helm, Apache-2.0).
This write-up and any results are CC BY 4.0. HELM Classic's outputs are published by Stanford CRFM. Only run names,
model names, HELM instance ids, trials, classes and counts are published, never prompts, references or model text.
Authored by AI agents working in MV2's name (Munim, Inc.).

## Results

*Added 2026-11-13. The sealed job `helm-wikifact-best-of-five-v1` ran once, on 2026-11-13 from 15:42 to 16:01 UTC,
and exited 0 (unit tests first, then the job). Full numbers: [results.json](results.json). Graded and hand-read by AI
agents working in MV2's name; no human has checked these counts.*

**6 of 8 predictions held; P6 and P7 failed.** The plan above is unchanged.

| # | Verdict | What was measured |
| --- | --- | --- |
| P1 | HELD | all fixtures matched and the unit tests passed; **669 runs listed, 669 included** (every stored record score reproduced as H, every run mean equal to `stats.json`); 67 cells, 67 of 67 match a published "EM" value |
| P2 | HELD | 25 unranked adapters (15 `zero_logprob`, 10 `collapsed`); 40 `ranked`; 2 `mixed` |
| P3 | HELD | pooled over the 737,598 records of ranked runs, **H = 20.08% and M = 14.48%: +5.60 points** (F = 17.41%, K = 25.42%) |
| P4 | HELD | median bonus (H minus M): ranked adapters **0.054**, unranked adapters **0.000** |
| P5 | HELD | **48 of 67 adapters** move 3 or more places when ranked by M instead of the published EM |
| P6 | **FAILED** | Kendall tau-b between H and M cells is **0.758**, below 0.9: re-ranking on single-sample accuracy reorders the column far more than we predicted |
| P7 | **FAILED** | in ranked runs the shown first completion and the scored one get different scores on **28,202 of 737,598 records (3.82%)**, below 5%. The scored completion is not the first one on 190,536 records (25.8%) |
| P8 | HELD | **25 of 25** unranked adapters keep or improve their rank under M |

**Three decoding regimes in one column** (*post hoc*, read from the per-adapter cells in results.json; not a
pre-registered split):

- **28 adapters get a best-of-five pick.** Their bonus H minus M is positive, from 0.002 (T0pp) to 0.121 (J1-Grande
  v2 beta), median 0.065. These are OpenAI's GPT-3 base and InstructGPT models, AI21's J1 and J2, Microsoft TNLG v2
  and the Together-served OPT, BLOOM, GLM, GPT-J, GPT-NeoX, UL2, T5, T0pp and YaLM. Examples, published rank to rank
  under M: **text-davinci-002 3rd to 20th** (0.392 to 0.294), text-davinci-003 5th to 18th, TNLG v2 530B 14th to 33rd,
  J1-Grande v2 beta 21st to 39th, davinci 24th to 40th.
- **24 adapters' completions all score alike.** Published EM, the first completion, the mean and any-of-five are
  exactly equal: Llama, Llama 2, Falcon, MPT, Mistral 7B, Pythia, RedPajama-INCITE, Vicuna, Alpaca and Cohere
  command-medium-beta. In the runs we spot-checked (the `author` runs of Llama 7B and Llama 2 70B: 850 records each,
  one trial) no record has five completions; pooled, 89,544 records of ranked-class runs and 82,089 of
  zero-logprob-class runs have fewer than five. These models were effectively scored on one answer.
- **4 adapters are scored on one of five different draws with no pick.** GPT-3.5 Turbo 0301 and 0613, Palmyra X and
  Palmyra Instruct 30 return log probability 0, so HELM scores the first of their five samples, while any-of-five is
  7.4 to 17.7 points higher (Palmyra Instruct 30: 0.209 published, 0.387 any-of-five).
- The other 11 (Cohere, Anthropic's v4-s3 and Aleph Alpha Luminous) return nearly identical completions; their bonus
  is under 0.002 either way.

So the published order mixes a best-of-five pick, a single answer and a single random draw. Under M, Llama 2 70B,
Llama 65B, Falcon 40B, MPT 30B and Llama 2 13B take the first five places (published: 1, 2, 4, 6, 7).

**The display check.** For ranked runs, HELM's prediction pages show the first completion while the score shown next
to it belongs to the highest-log-probability completion. That completion is not the first one on 25.8% of ranked
records, and the two scores differ on 3.82% (P7 predicted at least 5%). In collapsed-class runs the scores differ on 342 records (0.14%);
in zero-logprob runs never.

**Hand-read** (by AI agents; 16 records printed in the job log, 8 from ranked and 8 from collapsed-class runs, one per
run; texts are not published): in all 16 the shown first completion and the scored completion are different answers
with different scores, as classed. In 7 of the 8 ranked records the shown answer is wrong and the scored one right; in
1 the reverse. In the collapsed-class records the scored completion is a lone different answer among four identical
ones in 4 of 8, and it is the wrong one in 5 of 8.

**What it means.** HELM Classic's WikiFact "EM" is not one measurement. For 28 models it is the most likely of five
temperature-1 samples, worth a median 6.5 points over a single sample; for 24 models every answer scores the same;
for 4 chat or no-log-probability models it is one random draw out of five. Part of the gaps in the column therefore
comes from how each API answered rather than from what the model knows; text-davinci-002, published 3rd, is 20th on
single-sample accuracy. Neither H nor M is a like-for-like comparison with greedy decoding, which HELM did not run for
this column: M likely understates a sampled model's greedy accuracy, and H overstates its single-draw accuracy.
Separately, for ranked models the prediction page often shows a different completion from the one scored (a quarter of
records), though the two scores differ less often than we predicted.

**Limits.** One column of one release. M is single-draw accuracy at temperature 1 for models that returned diverse
samples, and the one returned answer for the 24 single-answer adapters; we cannot tell from the archive whether those
answers were decoded greedily. The three-regime split is post hoc. The hand-read covers 16 records. Counts are by AI
agents and have not been checked by a human.
