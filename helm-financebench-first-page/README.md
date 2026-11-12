# helm-financebench-first-page

Audit 108 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-12, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container.*

## Why

HELM Finance (release v1.0.0, 22 models from Claude 3 Opus to GPT-4o, Gemini 1.5 Pro and Llama 3.1 405B) publishes a
FinanceBench column, **Correct Answer**: the share of 140 test questions whose answer a GPT-4o judge
(`gpt-4o-2024-05-13`, temperature 0) labels `correct_answer` rather than `incorrect_answer` or `failure_to_answer`.
FinanceBench (Islam et al. 2023, arXiv:2311.11944) is an open-book benchmark: every question comes with the evidence an
annotator cited, as a **list** of items, each with a snippet, a document, a page number and that page's full text.

HELM's `FinanceBenchScenario` builds each prompt as

```
Evidence: <evidence[0].evidence_text_full_page>
Question: <question>
```

so **only the first cited page reaches the model**. A question whose answer needs a second or third page (a ratio of a
balance-sheet figure to an income-statement figure, say) is then asked without the numbers it needs. The judge sees the
question, the gold answer and the response, not the evidence, so an honest "the given page does not show total
assets" is labelled `failure_to_answer`, and a guess is usually `incorrect_answer`; both count as not correct. The
FinanceBench paper's own "Oracle" setting put **all** cited pages in the prompt (for metrics-generated questions, the
full page of every base metric, without duplicates); HELM's column is described as open-book question answering and
cites the paper.

**Prior art, and what is new here.** HELM issues and PRs searched on 2026-11-12 for "financebench": #4072 (a Japanese
FinQA scenario), #2831 (XSTest) and #2798 (the PR that added the scenario; no description and no review comments).
None mentions evidence pages. A web search for HELM FinanceBench with first or multiple evidence pages found nothing on
HELM; it found that FinanceBench's evidence field is a list, that some questions cite several pages, and that the
paper's Oracle setting used all of them. We found no report that HELM uses only the first page and no count of what
that does to the published column.

**What we saw before freezing.** The scenario code, the judge (`financebench_annotator.py`) and one run spec (GPT-4o:
5 in-context examples, 300 output tokens); the release's 22 `financebench` runs; for that run the file list, the key
names of `display_predictions.json` (per-record `annotations.financebench.label` and the stat
`annotation_financebench_label_correct_answer`) and `stats.json` for two runs: GPT-4o 2024-05-13 (140 instances;
correct 0.664, incorrect 0.286, failure 0.05; prompts 5,088 tokens on average, none truncated, 5 in-context examples)
and Llama 3 Instruct 8B (correct 0.193, incorrect 0.179, failure 0.629). GPT-4o's label counts are 93, 40 and 7, and
its seven `failure_to_answer` ids are 00499, 06272, 10130, 00711, 01912, 02024 and 06247. The group page (22 rows;
leader Claude 3 Opus 0.7; Claude 3 Sonnet and Claude 3.5 Sonnet 0.65; GPT-4o 0.664; lowest Llama 3 Instruct 8B 0.193).
In FinanceBench's file, the first 13 of its 150 records: 5 cite more than one item (00499 cites three pages, the
income statement, the balance sheet and the cash-flow statement, and the balance-sheet snippet is not in the first
page; 02987, 07966 and 04735 cite two; 03856 at least two). We did not look at any other record, any other run's
labels, or which questions are metrics-generated.

## Method

1. **Data.** FinanceBench's `financebench_open_source.jsonl` at the commit HELM pins (`d7beebe`, downloaded at run
   time, not redistributed); HELM Finance release v1.0.0's `runs_to_run_suites.json`, the group page
   `groups/financebench.json`, and for each listed `financebench:` run `instances.json`, `display_predictions.json`
   and `stats.json`.
2. **Evidence classes** (per question; whitespace is ignored in every comparison). `single`: one cited item.
   For each later item: it is covered if it is on the same page as item 0 (same document and page number, or the same
   page text) or its snippet is found in item 0's page. `missing`: some later item is on another page, its snippet is
   not in item 0's page, and it is found in its own page. `unverifiable`: otherwise (a snippet found in no page).
   `covered`: every later item is covered. **Complete** = `single` + `covered`.
3. **Prompt check.** Each test instance's input text must equal `Evidence: <item 0's page>\nQuestion: <question>`.
4. **Inclusion (gate).** A run is included if it downloads, its 140 test ids are the same as the reference run's,
   every record has one of the three labels and a stored correct-answer stat that agrees with it, the record count
   equals `num_instances`, and the three label shares equal `stats.json` within 1e-9.
5. **Cells and ranks.** Published cell = share of `correct_answer` over all 140 (matched by value, within 1e-6, to the
   group page's "Correct Answer" column). Complete-only cell = the same share over complete questions. Ranks: higher
   is better, 1 + the number of runs strictly higher.
6. **Hand-read** (next run): up to 8 missing questions (the question, the pages cited, the head of the given page and
   the missing snippet, from the job log) to confirm the needed numbers are really absent, and up to 8 judge
   explanations each for `failure_to_answer` on missing and on complete questions and for `correct_answer` on missing
   questions. Texts are never published.

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: the unit tests pass; all 140 test ids are FinanceBench records; in every run at least 95% of test prompts equal item 0's page plus the question; at least 90% of all cited snippets are found in their own page; at least 22 runs listed, at least 20 included; at least 90% of included cells match a published cell |
| P2 | At least **20%** of the 140 test questions are `missing` |
| P3 | Pooled over included runs, the `failure_to_answer` share on missing questions is at least **twice** that on complete questions |
| P4 | In at least **80%** of included runs, the correct share on missing questions is lower than on complete questions |
| P5 | Among metrics-generated questions only, the pooled correct share is at least **0.10** lower on missing than on complete questions (NOT GRADED if either has fewer than 10 questions) |
| P6 | The order is broadly kept: Kendall tau-b between published and complete-only cells is at least **0.8** |
| P7 | At least one run moves **3 or more** places from published to complete-only rank |
| P8 | The published leader (Claude 3 Opus) is still first on complete questions only |

Reasoning: FinanceBench's metrics-generated questions are ratios built from two or three statements, so we expect a
fifth or more of the questions to cite a page HELM leaves out (P2; 5 of the first 13 records cite several items).
Asked without the needed page, careful models should say so, which the judge labels `failure_to_answer` (P3), and
models generally should do worse there (P4). Missing questions may also simply be harder, so P5 compares them with
complete questions of the same kind (metrics-generated). Every model loses on the same questions, so the order should
broadly hold (P6), but many of the 22 cells are close together (eight lie between 0.50 and 0.56), so some should
move (P7); the leader is 0.036 ahead of
second and should hold (P8).

## What a result would mean

If P2 and P3 hold, part of HELM's published FinanceBench column measures whether a model guesses or declines when the
prompt lacks the numbers it needs, not open-book financial question answering as in the paper's Oracle setting; P4
to P8 say how much that changes the table. The fix in HELM would be to join the full pages of every cited item
(without duplicates), as the paper did. If P2 fails, the first page is usually enough and the scenario is sound in
practice. The judge itself (GPT-4o judging its own answers, a 64-token limit) is not measured here.

## Validity gates

The unit tests (`test_grade108.py`, standard library only, traced by hand) cover whitespace-insensitive matching, every
evidence class (same page by number and by text, a snippet found in the given page, missing, unverifiable, an empty
snippet, another document with the same page number, both document-name keys), the prompt check, a run census with a
non-test record, a duplicate, a perturbed record, an unknown label, a missing and a mismatched stored stat, run means
over trials, class tallies, ranks, Kendall tau-b with ties, the group column, cell matching and the verdicts on, past
and without every boundary. They run first, before any data is read.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads FinanceBench's 150 open-source questions, the release index, the group page and 22 runs (about 13 MB)
```

## Files

- `grade108.py`: evidence classes, prompt check, census, cells, ranks, Kendall tau-b and verdicts (standard library)
- `job.py`: downloads, gates, class tallies, cells, ranks; writes `results.json`
- `test_grade108.py`: unit tests with the hand traces

## Licence

Code is Apache-2.0. This write-up and any results are CC BY 4.0. FinanceBench (Patronus AI) is downloaded at run time
and not redistributed here. HELM Finance's outputs are published by Stanford CRFM (HELM is Apache-2.0). Only run names,
model names, FinanceBench ids, classes, question types and counts are published, never questions, evidence, answers,
model text or judge explanations. Authored by AI agents working in MV2's name (Munim, Inc.).
