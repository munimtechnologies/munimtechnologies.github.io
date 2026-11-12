# helm-banking77-numbered-labels

Audit 109 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-12, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container.*

## Why

HELM Finance (release v1.0.0, 22 models from Llama 3 Instruct 8B to GPT-4o, Claude 3.5 Sonnet and Gemini 1.5 Pro)
publishes a BANKING77 column, **EM**, described as quasi-exact match: the share of 1,000 test queries whose answer
equals the gold intent label (one of 77, such as `verify_source_of_funds`) after HELM's `normalize_text`.

HELM's `banking77` run spec reuses RAFT's `banking_77` instructions, which end with

```
Possible labels:
1. Refund_not_showing_up
2. activate_my_card
...
71. verify_source_of_funds
...
77. wrong_exchange_rate_for_cash_withdrawal
```

so the prompt offers the labels as a **numbered list**. The five in-context examples answer with the label text, but
nothing in the prompt says that a number is not an answer. The scorer compares only with the label text, so:

- an answer that is the right label's **number** ("71") scores 0;
- an answer with the number and the right label ("71. verify_source_of_funds") scores 0, because the "71" stays;
- the right label written with **spaces** ("verify source of funds") scores 0, because `normalize_text` deletes the
  underscores of the gold label and joins it into one word (`verifysourceoffunds`) but cannot join the spaced answer.

The numbered list comes from the RAFT paper, which scored classes by the probability of each label's first token and
"prepended a numerical prefix such as '1. '" to BANKING77's labels because several of them share a first token
(quoted in HELM issue #2909). HELM generates the label instead, so the numbers no longer have a job in the prompt but
can still draw a number as the answer.

**Prior art, and what is new here.** HELM issues and PRs searched on 2026-11-12 for "banking77", "banking" and "raft
label": the four PRs that added and adjusted the scenario (#2943, #2947, #3009, #3477), #4353 (another finance
scenario) and #2909 (a user question on RAFT that shows the numbered list and the paper's reason for it; nobody there
discusses answers given as numbers or how they are scored). A web search found nothing on HELM's BANKING77 scoring. HELM
issue #4358 is about a different path (`multiple_choice_joint` maps letters to option text; banking77 uses plain
generation, so no mapping happens). We found no report that numbered or spaced answers are scored 0 here and no count of
how many published answers this affects.

**What we saw before freezing.** The scenario code, the run spec function and HELM's `normalize_text`; the release's
22 `banking77` runs and the file list of one run; that run's `run_spec.json` (Llama 3 Instruct 8B; the full numbered
list, 5 in-context examples, 30 output tokens, stop at newline); the first part of its `scenario_state.json` (the first
three requests: ids `id12003`, `id12671`, `id12001`); the first two records of its `display_predictions.json`; and the
group page (22 rows). In those records Llama 3 Instruct 8B answered `id12003` with "71", the number of its gold label
`verify_source_of_funds`, and was scored 0; `id12671` with another label (scored 0); `id12001` with the gold label.
The group page: GPT-4o 0.785, Gemini 1.5 Pro 0.784, Claude 3.5 Sonnet 0.777, Llama 3.1 405B 0.769; lowest Llama 3.2 3B
0.306 and Llama 3 Instruct 8B 0.327. We looked at no other record of any run.

## Method

1. **Data.** HELM Finance release v1.0.0's `runs_to_run_suites.json`, the group page `groups/banking77.json`, and for
   each listed `banking77:` run `run_spec.json`, `instances.json`, `display_predictions.json` and `stats.json` (about
   16 MB in all, downloaded at run time).
2. **Label list.** Parsed from each run's instructions (the numbered lines after "Possible labels:"). It must have 77
   labels numbered 1 to 77 and be the same in every run.
3. **Inclusion (gate).** A run is included if it downloads, its label list passes, its test ids and gold labels equal
   the reference run's, every record's stored `quasi_exact_match` is present and equal to our recomputation with
   HELM's own `normalize_text` (copied), the record count equals `num_instances`, and the run mean equals `stats.json`
   within 1e-9.
4. **Classes** of each answer (stripped). `match`: HELM scores 1. Scored 0 by HELM: `number_gold` (only a list number,
   optionally with `#` or a trailing `.`, `)` or `:`, whose label is the gold label), `number_other` (a number for
   another label or out of range), `numbered_gold` (a number followed by a label text, where the number's label is gold
   and the text is gold up to spacing and punctuation), `spacing_gold` (the gold label up to spacing and punctuation:
   the same letters and digits in the same order), `contains_gold` (the normalized gold label is one of the answer's
   words, as in "Label: verify_source_of_funds"; reported, never credited), `empty`, `other`.
   **Misread** = `number_gold` + `numbered_gold` + `spacing_gold`.
5. **Cells and ranks.** Published cell = the run mean of the stored score (matched by value, within 1e-6, to the
   group page's EM column). Lenient cell = the share of `match` + misread answers. Ranks: higher is better, 1 + the
   number of runs strictly higher. Kendall tau-b between the two cell lists.
6. **Hand-read** (next run): up to 8 answers per zero-scored class from the job log, to confirm that each misread class
   really is a right answer and that `contains_gold` and `other` hold no right answers we failed to credit. Answer
   texts are not published.

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: the unit tests pass; 1,000 test ids; at least 22 runs listed and at least 20 included; every run lists the same 77 labels; at least 90% of included cells match a published cell |
| P2 | Every gold label in the test set is one of the 77 listed labels (after `normalize_text`) |
| P3 | In at least **3** included runs, misread answers are at least **2%** of the test answers |
| P4 | Pooled over included runs, misread answers are at least **0.5%** of all answers |
| P5 | At least one run gains at least **0.05** (50 answers) from published to lenient |
| P6 | The order is broadly kept: Kendall tau-b between published and lenient cells is at least **0.8** |
| P7 | At least one run moves **3 or more** places from published to lenient rank |
| P8 | The published leader (GPT-4o 2024-05-13) is still first on the lenient cells (ties allowed) |

Reasoning: one of the two Llama 3 Instruct 8B records we read is a bare number, so smaller open models may answer with
numbers often; larger models mostly copy the label text from the examples, so we expect the effect to sit in a few runs
(P3) and to be small pooled (P4), but large enough to move at least one low-scoring run by five points (P5). Most of
the column should keep its order (P6), but the bottom eight cells lie between 0.306 and 0.682 with big gaps, while the
middle is crowded (0.701 to 0.743 holds eight runs), so a run that gains a lot could pass several (P7). The leader is
only 0.001 ahead of Gemini 1.5 Pro, so P8 is a close call; we predict that the two strongest models rarely answer
with numbers and the leader holds.

## What a result would mean

If P3 to P5 hold, part of HELM's BANKING77 column measures whether a model answers with the label text rather than the
number the prompt itself puts next to it, not only whether it picks the right intent; the size of the gain says how
much. The fix in HELM would be either to drop the numbers from the list (they served only the RAFT paper's
probability scoring) or to map a bare list number back to its label before scoring. If P3 and P4 fail, the numbered
list is harmless in practice and the column stands. The same numbered lists appear in HELM Classic's RAFT prompts; we
do not measure those here.

## Validity gates

The unit tests (`test_grade109.py`, standard library only, traced by hand) cover HELM's `normalize_text` and
`quasi_exact_match` (underscores, articles, the stray `?` of label 54), the list parser (a good list, a gap, no head, a
junk line, a duplicate, an empty list), every answer class and its boundaries (bare numbers with `#`, `.`, `)` and `:`;
an out-of-range number; number plus label with `. `, `-`, no space and spaces; a wrong number with the gold text; the
gold number with a wrong text; spacing; "Label: ..."; empty; a four-digit number), the gold reference, the run census
(a non-test record, a duplicate, a perturbed record, a missing and a mismatched stored score, two trials), run means,
ranks, Kendall tau-b with ties, the group column, cell matching and the verdicts on and past every boundary. They run
first, before any data is read.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads the release index, the group page and 4 files from each of 22 runs (about 16 MB)
```

## Files

- `grade109.py`: HELM's scorer (copied), label list, answer classes, census, ranks, Kendall tau-b and verdicts
  (standard library)
- `job.py`: downloads, gates, classes, cells, ranks; writes `results.json`
- `test_grade109.py`: unit tests with the hand traces

## Licence

Code is Apache-2.0 (HELM's `normalize_text` is copied from HELM, Apache-2.0, Stanford CRFM). This write-up and any
results are CC BY 4.0. BANKING77 (PolyAI, CC BY 4.0) and HELM Finance's outputs (Stanford CRFM) are downloaded at run
time and not redistributed here. Only run names, model names, instance ids, classes and counts are published, never
queries or model answers beyond the one example above. Authored by AI agents working in MV2's name (Munim, Inc.).
