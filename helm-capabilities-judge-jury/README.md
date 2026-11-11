# helm-capabilities-judge-jury

Audit 106 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-11, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library.*

## Why

Two of the five columns on the HELM Capabilities leaderboard (release v1.15.0, 68 models from Llama 3.1 and GPT-4o
to GPT-5.1, Claude 4.5 and Gemini 3 Pro) are graded by LLM judges: WildBench ("WB Score", a 1-10 rating shown rescaled
to 0-1) and Omni-MATH ("Acc", a TRUE/FALSE equivalence judgement). Since February 2025 (HELM PRs #3283, #3291, #3318,
#3322) each answer is judged by a **jury** of three models: GPT-4o (2024-05-13), Claude 3.5 Sonnet (2024-10-22) and
Llama 3.1 405B Instruct Turbo. A record's score is the mean of the judges' valid values; a run's score is the mean
over records. A jury of different model families is the recommended defence against a judge favouring its own
family (Verga et al. 2024, "Replacing Judges with Juries").

Two things about this jury can be checked from HELM's own published per-record annotations:

1. **Its membership changed while the leaderboard kept one column.** HELM PR #3926 (merged 2025-11-19) removed the
   Claude 3.5 Sonnet judge, and PR #4233 (2026-04-27) the Llama judge. Release v1.15.0 adds three models (Claude
   Haiku 4.5, Gemini 3 Pro preview, GPT-5.1) whose runs were made around the time of the first removal, while the
   other 65 models were judged earlier. If those three were judged without the Claude judge, they sit in the same
   column as models that were scored by a different jury.
2. **Each judge also rates its own family.** The Claude judge rates Claude models (including Claude 3.5 Sonnet
   itself), the Llama judge Llama models (including Llama 3.1 405B itself) and the GPT-4o judge OpenAI models. A jury
   dilutes self-preference but does not remove it.

**Prior art, and what is new here.** Self-preference of LLM judges is well documented in general (Panickssery et
al. 2024; Wataoka et al. 2024, arXiv 2410.21819; Spiliopoulou et al. 2025, arXiv 2508.06709; a 2026 rubric-based
study, arXiv 2604.06996), and HELM Safety's 2024 write-up explains why it used two judges there. HELM's issues and
PRs were searched on 2026-11-11 for "wildbench judge", "jury", "annotators", "self-preference" and "judge bias" (40
results): the open ones (#4344 a score planted in the model's output; #4349 parse the judge's final verdict; #4326 count
dropped judge values) are about parsing, not about who the judges are. We found no issue, paper or post that measures
judge-family offsets on HELM Capabilities' published annotations, or that notes the jury change inside one
leaderboard column.

**What we saw before freezing.** The current code of HELM's WildBench and Omni-MATH annotators and metrics on GitHub
(only GPT-4o is active now; Claude and Llama are commented out as deprecated); the titles and dates of the commits and
PRs above; the release index (`runs_to_run_suites.json`: 68 `wildbench:` and 68 `omni_math:` runs, three of each from
suite v1.15.0); one run's `stats.json` (Claude 3.5 Haiku on WildBench: 7.837 raw, 0.760 rescaled); and the first rows
of both group pages. Two of those values (Omni-MATH 0.1595 and 0.16067 for Marin 8B and OLMo 2 32B, suite v1.8.0) are
whole numbers of thirds of a record, which fits a three-judge jury in v1.8.0. **We have not read any per-record
annotation, any v1.15.0 row, or any judge's score.** P2 rests on the PR dates, not on data.

## Method

1. **Data.** HELM Capabilities release v1.15.0: `runs_to_run_suites.json`, the two group pages, and for every listed
   `wildbench:` and `omni_math:` run its `display_predictions.json` (per-record `annotations`; if a run's display file
   carries none, its `scenario_state.json`) and `stats.json`. Streamed, not stored.
2. **HELM's score, transcribed** (`grade106.py`). Every annotation key ending in `_score` (WildBench) or
   `_equivalence_judgement` (Omni-MATH) whose value is not None counts, the empty-output key included (an empty output
   is never sent to a judge and gets 1.0 on WildBench, FALSE on Omni-MATH); the record score is their mean and the run
   value the mean over records. WildBench cells are (score - 1) / 9.
3. **Inclusion.** A run is included if it downloads, at most 1% of its records have no score, at most 0.5% of any
   stored per-record scores differ from ours, and its mean is within 1e-6 of `stats.json`. Cells are checked by
   matching each to a distinct published value within 1e-6.
4. **Jury composition.** A judge "rated" a run if it has a value on at least half of its non-empty records.
5. **Offsets.** On runs rated by all three judges with at least 50 records all three rated: a judge's **offset** on a
   run is the mean, over those records, of its value minus the mean of the other two judges. **Self-preference** of a
   judge = its mean offset on runs of its own family (model name prefix `openai_`, `anthropic_` or `meta_`) minus its
   mean offset on all other three-judge runs, with a one-sided permutation p-value over run labels (10,000 shuffles,
   seed 106). **Leniency spread** = the largest minus the smallest pooled judge mean over those records.
   **Agreement** (Omni-MATH) = share of fully rated records on which all three judges agree.
6. **Other juries.** Every cell re-scored with the **GPT judge alone** (the only judge present throughout) and with the
   **common jury** (judges that rated every included run). A record none of a jury rated keeps HELM's score (counted).
   Ranks: higher is better; movers change 3 or more places.

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: all fixtures match; in each scenario at least 90% of listed runs are included and at least 90% of cells match a published value |
| P2 | Jury change: in both scenarios, every included run from suites v1.0.0 to v1.14.0 has a GPT, a Claude and a Llama judge on at least 95% of its non-empty records, and every included v1.15.0 run has **no** Claude judge value at all (and at least one v1.15.0 run is included) |
| P3 | WildBench self-preference: at least **2** of the 3 judges have a positive own-family offset difference, and the largest is at least **0.10** points on the 1-10 scale |
| P4 | WildBench leniency: pooled judge means differ by at least **0.30** points (largest minus smallest) |
| P5 | Omni-MATH: all three judges agree on at least **85%** of fully rated records |
| P6 | Omni-MATH self-preference is small: every judge's own-family offset difference is under **0.02** in absolute value |
| P7 | WildBench with the GPT judge alone: Kendall tau-b with the published cells at least **0.85**, and at least **3** models move 3 or more places |
| P8 | WildBench with the common jury: at least **1** of the three v1.15.0 models moves **2 or more** places |

Reasoning: PR #3926 was merged one day after Gemini 3 Pro preview was released, so the v1.15.0 runs were most likely
judged without Claude (P2). Self-preference is reported for open-ended ratings (P3) far more than for checking a
final answer against a reference (P6), and judges of different families are known to differ in strictness on
open-ended text (P4) while mostly agreeing on whether two math answers are equivalent (P5). One judge instead of three
should re-order a column whose top cells are close (P7); if P2 holds, the common jury drops the Claude judge from 65
runs and, if Claude's leniency differs, moves the three newest models relative to the rest (P8).

## What a result would mean

If P2 holds, the WildBench and Omni-MATH cells of the three newest models are not on the same jury as the other 65,
and the common-jury cells show how much that matters. If P3 holds, the jury contains measurable own-family
favouritism; the per-run offsets say for which models. Failures are as informative: a P2 failure means the jury was
kept for these runs; P3 and P6 failures mean no detectable family effect in HELM's published grades. Offsets are
relative to the other two judges, so a family effect shared by all three judges cannot be seen; only three families
can be tested, with 5 to 13 runs each.

## Validity gates

Hand-traced fixtures (`cases106.py`, traced in `test_grade106.py`): annotation parsing on nine records (three judges;
an empty output; a missing judge value; all values missing; a value of the wrong type; Omni-MATH booleans and None);
a WildBench run census with a duplicate, a perturbed record, a record without annotations, a stored per-record score
that disagrees, and an empty output; run means and the 0-1 rescaling; judge coverage at two shares; judge offsets and
agreement on both scenarios; re-scoring with one judge (with and without fallback); the scenario_state fallback; judge
and model families; five composition cases; self-preference on four runs; permutation p-values; stats lookup; the
group column; ranks; Kendall tau-b with ties; cell matching; and two verdict cases on and past every boundary. They
must match before any data is read. The unit tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads the release index, two group pages and two files for each judged run
```

## Files

- `grade106.py`: HELM's jury score (transcribed), run census, coverage, offsets, self-preference, permutation test,
  other juries, run names, stats lookup, ranks, Kendall tau-b and verdicts
- `cases106.py`: data source, thresholds and the fixtures (all invented)
- `job.py`: downloads, gates, juries, offsets, cells, ranks; writes `results.json`
- `test_grade106.py`: unit tests with the hand traces; `requirements.txt`: none (standard library)

## Licence

Code is Apache-2.0. HELM's scoring rule is transcribed from stanford-crfm/helm (Apache-2.0). This write-up and any
results are CC BY 4.0. HELM Capabilities' outputs and judge annotations are published by Stanford CRFM. Only run
names, model names, judge names and numbers are published, never prompts, model text or judge text. Authored by AI
agents working in MV2's name (Munim, Inc.).
