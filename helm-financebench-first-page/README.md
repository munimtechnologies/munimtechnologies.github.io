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

## Results

*Added 2026-11-12, after the sealed job ran (job `helm-financebench-first-page-v1`, 2026-11-12 14:27 to 14:31 UTC,
exit 0; the unit tests passed before any data was read). Nothing above this section was changed. The full output is
in [results.json](results.json).*

**7 of 8 predictions held.** **32 of HELM Finance's 140 FinanceBench test questions (22.9%) cite a page that HELM's
prompt leaves out.** On those 32, the 22 models are judged correct on **10.4%** of answers, against **65.4%** on the
other 108, and the judge's "failure to answer" share is **5.8 times** higher. The order of the column barely changes
(Kendall tau-b 0.965, no model moves 3 or more places), so the main effect is on the level of every score, not the
ranking.

| # | Verdict | Measured |
| --- | --- | --- |
| P1 | HELD | unit tests pass; 140 of 140 test ids are FinanceBench records; in all 22 runs **100%** of test prompts equal item 0's page plus the question; 189 of 189 cited snippets found in their own page; 22 runs listed, 22 included; 22 of 22 cells match a published cell |
| P2 | HELD | **32 of 140** test questions missing (22.9%; threshold 20%); all 150 records: 35 missing, 115 single, 0 covered, 0 unverifiable |
| P3 | HELD | pooled `failure_to_answer`: **39.2%** on missing questions (276 of 704) against **6.7%** on complete ones (160 of 2,376), a ratio of **5.8** (threshold 2) |
| P4 | HELD | **22 of 22** runs (100%) are less often correct on missing than on complete questions |
| P5 | HELD | metrics-generated questions only (21 missing, 26 complete): pooled correct **6.5%** on missing (30 of 462) against **70.3%** on complete (402 of 572), a gap of **0.638** (threshold 0.10) |
| P6 | HELD | Kendall tau-b, published against complete-only cells: **0.965** |
| P7 | FAILED | **no** run moves 3 or more places; the largest moves are 2 (GPT-4o mini 12th to 10th, Gemini 1.5 Flash 9th to 7th) |
| P8 | HELD | Claude 3 Opus is first on complete questions (0.852; next GPT-4o and Claude 3.5 Sonnet, 0.806) |

**Which questions.** Of the 32 missing questions, 21 are metrics-generated (ratios and sums built from two
statements), 8 domain-relevant and 3 novel-generated. So 21 of the 47 metrics-generated test questions (44.7%) are
asked without a page they cite. No test question is `covered` or `unverifiable`: every test question that cites more
than one item has at least one item on another page whose snippet is absent from the page HELM gives.

**Pooled over 22 runs** (3,080 judged answers):

| Questions | Answers | Correct | Incorrect | Failure to answer |
| --- | --- | --- | --- | --- |
| Complete (108) | 2,376 | 1,555 (65.4%) | 661 (27.8%) | 160 (6.7%) |
| Missing (32) | 704 | 73 (10.4%) | 355 (50.4%) | 276 (39.2%) |

The missing questions supply 73 of the column's 1,628 published credits (4.5%) while making up 22.9% of it. Every
cell rises on complete questions only; the pooled mean goes from 0.529 to 0.654.

**All 22 runs** (counts out of 32 missing and 108 complete questions; ranks: 1 + the number of runs strictly higher):

| Model | Published | Complete only | Correct on missing | Failure to answer on missing | Rank: published to complete only |
| --- | --- | --- | --- | --- | --- |
| Claude 3 Opus | 0.700 | 0.852 (92) | 6 | 21 | 1 to 1 |
| GPT-4o (2024-05-13) | 0.664 | 0.806 (87) | 6 | 7 | 2 to 2 |
| Claude 3.5 Sonnet (2024-06-20) | 0.650 | 0.806 (87) | 4 | 25 | 3 to 2 |
| Claude 3 Sonnet | 0.650 | 0.796 (86) | 5 | 19 | 3 to 4 |
| Llama 3.1 Instruct Turbo 405B | 0.629 | 0.787 (85) | 3 | 22 | 5 to 5 |
| Llama 3 Instruct 70B | 0.607 | 0.759 (82) | 3 | 17 | 6 to 6 |
| GPT-3.5 Turbo (0125) | 0.600 | 0.722 (78) | 6 | **0** | 7 to 7 |
| Gemini 1.5 Pro (002) | 0.579 | 0.722 (78) | 3 | 10 | 8 to 7 |
| Gemini 1.5 Flash (001) | 0.571 | 0.722 (78) | 2 | 6 | 9 to 7 |
| Llama 3.2 Vision Instruct Turbo 90B | 0.557 | 0.685 (74) | 4 | 16 | 10 to 10 |
| Qwen2 Instruct 72B | 0.550 | 0.676 (73) | 4 | 7 | 11 to 12 |
| GPT-4o mini (2024-07-18) | 0.543 | 0.685 (74) | 2 | 7 | 12 to 10 |
| Llama 3.1 Instruct Turbo 70B | 0.536 | 0.657 (71) | 4 | 21 | 13 to 14 |
| Qwen1.5 Chat 72B | 0.529 | 0.667 (72) | 2 | 14 | 14 to 13 |
| Mixtral Instruct 8x22B | 0.521 | 0.639 (69) | 4 | 18 | 15 to 15 |
| Llama 3.1 Instruct Turbo 8B | 0.514 | 0.639 (69) | 3 | 9 | 16 to 15 |
| Llama 3.2 Vision Instruct Turbo 11B | 0.507 | 0.620 (67) | 4 | 7 | 17 to 17 |
| Mixtral Instruct 8x7B | 0.443 | 0.546 (59) | 3 | 8 | 18 to 18 |
| Gemini 1.0 Pro (002) | 0.436 | 0.546 (59) | 2 | 8 | 19 to 18 |
| Mistral Instruct v0.3 7B | 0.393 | 0.500 (54) | 1 | 2 | 20 to 20 |
| Llama 3.2 Instruct Turbo 3B | 0.257 | 0.315 (34) | 2 | 4 | 21 to 21 |
| Llama 3 Instruct 8B | 0.193 | 0.250 (27) | 0 | 28 | 22 to 22 |

How models handle a missing page differs widely: Claude 3.5 Sonnet declines on 25 of 32, Claude 3 Opus on 21, GPT-4o
on 7 (all seven of GPT-4o's "failure to answer" labels in the column fall on these 32 questions) and GPT-3.5 Turbo
(0125) on none, yet GPT-3.5 Turbo is judged correct on as many of them (6) as Claude 3 Opus. A model that says the
needed statement is not in the evidence scores the same 0 as a wrong guess. Llama 3 Instruct 8B's 28 are mostly
off-topic answers, not declines: it is also labelled "failure to answer" on 60 of the 108 complete questions.

**Hand-read** (by AI agents, from the job log, as pre-registered; texts not published):

- **8 missing questions:** in **7 the prompt lacks figures the answer needs**: a return-on-assets question given only
  the balance sheet (net income is on the left-out income statement), a fixed-asset-turnover question given only the
  balance sheet (revenue left out), an inventory-turnover question given only the income statement (inventories left
  out), and four questions needing the left-out cash-flow statement (dividends paid, capital expenditure, depreciation
  and amortization, cash from operations). In the eighth (PepsiCo's geographies) the given page holds the start of a
  list whose last two items are on the left-out page.
- **8 "failure to answer" on missing questions** (8 runs): 6 say plainly that the statement or figure the question
  needs is not in the evidence (for example "the statement of cash flows is not included"); 1 restates the formula
  without a number; 1 answers a different question (Llama 3 Instruct 8B).
- **8 "failure to answer" on complete questions:** 3 say the information is not in the evidence, 2 argue the metric
  is not meaningful for the company, 1 gives part of a multi-year answer, 2 are off-topic or confused. So declining for
  lack of evidence is common on missing questions and rare elsewhere, as P3's ratio says.
- **8 "correct" on missing questions:** 3 are one question (`financebench_id_04254`, an EBITDA sum) whose
  depreciation line also appears on the given income statement, so the left-out page was not needed; 2 are a yes/no
  question credited without the ratio it asks for; 1 is a "not meaningful" answer the gold also gives; 1 is a right
  yes/no reached by assuming a figure the model says it does not have; 1 is the partial geography list. So credits on
  missing questions come mostly from questions answerable without the left-out page and from lenient judging of
  yes/no answers.

**What this means.** As pre-registered, P2 and P3 holding means part of HELM's FinanceBench column measures whether a
model declines or guesses when the prompt lacks the numbers it needs, not open-book question answering as in the
FinanceBench paper's Oracle setting, which gave all cited pages. The cost is large and nearly uniform: about a fifth of
the column is close to unanswerable as prompted (10.4% correct against 65.4%), so 20 of 22 published scores are 0.10
to 0.16 lower than on the complete questions (0.06 for the two weakest models), while the order holds (P7 failed: no model moves 3 or more
places). The column also cannot tell an honest "the cash-flow statement is not given" from a wrong number. For
context only (another model, all 150 questions, the paper's own grading): the FinanceBench paper (arXiv:2311.11944,
Table 2) reports its Oracle setting, with the relevant page(s) or financial statement(s) in the prompt, at 85% correct
and 0 failures to answer for GPT-4-Turbo; in HELM, GPT-4o (2024-05-13) is judged correct on 0.664 of the column, and
all 7 of its failures to answer fall on the 32 questions with a page left out. The fix
would be to join the full pages of every cited item, without duplicates, as the paper did; that needs new model runs,
so this audit cannot say what the re-run scores would be.

**Limits.** One column of one release, 140 questions; `missing` is a page test, not a needs test: a left-out page can
repeat a figure the given page already has (as for `04254`), so 32 is an upper bound on questions that truly cannot be
answered, and the hand-read is 8 of 32. The judge is not checked; its leniency on yes/no answers shows in the read. The
complete-only cells are a re-cut of the same answers, not what the models would score with all pages in the prompt.
