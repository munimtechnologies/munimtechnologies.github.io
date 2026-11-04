# mcq-mmlu-pro-consensus-distinct-panel

Audit 79 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-02, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library plus a parquet
reader.*

## Why

Audit 77 ([mcq-mmlu-pro-model-consensus-miskeys](../mcq-mmlu-pro-model-consensus-miskeys/)) flagged an MMLU-Pro
question when at least 6 of the 10 most accurate published models agree on one option other than the key. Against
MMLU-Redux 2.0's expert labels the flag found miskeys at 5.7 times the base rate, but only 65 of the 359 flagged
questions the experts judged (18.1%) carry an expert error label. Audit 78
([mcq-mmlu-pro-consensus-added-options](../mcq-mmlu-pro-consensus-added-options/)) showed that options MMLU-Pro added
explain part of that, not all.

A second limit was stated but never tested: the 10 panel slots are not 10 models. Three are Claude 3.5 Sonnet
archives (one labelled 2024-10-22, one a 0-shot run), two are GPT-4o versions and two are runs labelled `arx`, so the
panel holds 6 model lines. If archives of one model share wrong answers, 6 of 10 can mean three or four independent
opinions, and the flag would fire on shared mistakes. This audit builds a panel with one archive per model line and
asks whether the flag gets more precise.

**Prior art.** Kim, Garg, Peng and Garg ("Correlated Errors in Large Language Models", ICML 2025, arXiv 2506.07962)
find that models agree on about 60% of the questions where both err on a leaderboard dataset, more so with a shared
provider or architecture, and that larger, more accurate models have highly correlated errors even across providers.
"Nine Judges, Two Effective Votes" (arXiv 2605.29800) shows correlated errors limit what panels of LLM judges add.
We found no work that tests a de-duplicated panel as a miskey detector against expert labels on MMLU-Pro, or that
measures shared wrong answers among TIGER-AI-Lab's published MMLU-Pro archives.

## Method

1. **Audit 77, re-run.** The same 48 archives, join rule, panel (the 10 most accurate included archives) and flag
   (at least 6 of 10 pick the same non-key option, and more of them than pick the key). The panel, the flag counts
   and the 65 of 359 precision must reproduce audit 77.
2. **Model lines.** Archives of one model share a line: `claude-3-5-sonnet-20241022`, `claude-3.5-sonnet` and
   `sonnet-3.5` 0-shot (Claude 3.5 Sonnet); `gpt-4o-2024-08-06` and `gpt4o(2024-05-13)` (GPT-4o); `arx_0314` and
   `arx_3` (arx). Every other archive is its own line. Different models from one vendor (GPT-4o mini, `opus`, Gemini 1.5
   Pro and Flash) are separate lines.
3. **The distinct panel.** The 10 most accurate archives, keeping only the most accurate archive of each line. From
   audit 78's published accuracies this is, frozen as part of P1: Gemini 3.1 Pro, `arx_0314`, iAsk Pro, Claude 3.5
   Sonnet (2024-10-22), GPT-4o (2024-08-06), Gemini 1.5 Pro 002, `opus` (a 2-shot run, by its name Claude 3 Opus), DeepSeek-Chat V2.5,
   Gemini 1.5 Flash 002 and GPT-4o mini. The same flag rule is applied.
4. **Precision.** Among flagged questions MMLU-Redux judged (wrong key, OK, or another error label), the share that
   carry an error label. Unsure or conflicting labels are left out, as in audit 77.
5. **Shared wrong answers.** For every pair of archives in the union of both panels (14 archives, 5 within-line pairs
   and 86 cross-line pairs): among questions where both give a valid answer other than the key, the share where they
   give the same one.

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: all five fixtures match; MMLU-Pro has 12,032 valid rows; the Redux join reproduces audit 75; audit 77's panel, flag counts and 65/359 precision are reproduced exactly; the distinct panel equals the frozen list (10 archives, 10 lines); at least 30 archives are included |
| P2 | The distinct panel still separates: it flags Redux-miskeyed questions at least 5 times as often as Redux-OK ones |
| P3 | HEADLINE: the distinct panel's precision is higher than audit 77's panel's 65 of 359 (18.1%) |
| P4 | The distinct panel flags at least 30 of the 55 Redux-miskeyed questions (audit 77's panel: 36) |
| P5 | Every one of the 5 within-line pairs gives the same wrong answer more often than the median cross-line pair |
| P6 | The distinct panel, like audit 77's, flags STEM-website questions at a lower rate than MMLU-derived ones |

Reasoning: P5 tests the premise: if archives of one model do not share wrong answers more than different models do,
de-duplicating cannot matter. P3 is the consequence we expect if shared mistakes inflate the flag on cleared
questions. Kim et al.'s finding that more accurate models share more errors points the other way, since the distinct
panel swaps four of audit 77's archives (72.5% to 78.4% accurate) for four weaker ones (63.4% to 68.8%), so P3 is a
real test. P2 and P4 check that the rule still works with a weaker panel; P6 checks that audit 77's unexpected
STEM-website result does not depend on the duplicates.

## What a result would mean

If P5 and P3 hold, duplicated archives inflate model consensus, and a consensus panel should count model lines, not
archives. If P5 holds and P3 fails, archives of one model do share mistakes, but removing them does not make the flag
more precise, perhaps because the weaker replacements add mistakes of their own. If P5 fails, the duplicate archives
behave like different models and audit 77's stated limit matters little. `robust_candidates.json` lists the questions
both panels flag with the same option. It is model-flagged, not expert-checked. Exploratory, not predicted: flag
counts by group for both panels and their overlap, the precision of the overlap, the distinct panel's curve for 4 to
10 of 10, and every pair's shared-wrong-answer rate with both accuracies.

## Validity gates

Five hand-traced fixtures (`cases79.py`, traced in `test_distinct79.py`: audit 77's panel/flag and Redux-join
fixtures, plus new ones for the one-per-line panel, shared wrong answers and the verdicts) must match before any real
data is read; the MMLU-Pro parse must reproduce audit 63's counts and the Redux join audit 75's; the job aborts
otherwise. The unit tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads MMLU-Pro, MMLU, MMLU-Redux 2.0 and TIGER-AI-Lab's prediction archives
```

## Files

- `distinct79.py`: audits 77/78's join, panel and flag (copied unchanged), plus model lines, the one-per-line panel,
  precision, shared wrong answers and verdicts
- `cases79.py`: the frozen rule, lines, thresholds, audit 77's panel and counts, the expected distinct panel,
  archives, the five fixtures
- `job.py`: loaders, gates, joins; writes `results.json` and `robust_candidates.json`
- `test_distinct79.py`: unit tests; `requirements.txt`: a parquet reader only

## Licence

Code is Apache-2.0. This write-up and any results are CC BY 4.0. Upstream: MMLU-Pro and MMLU are MIT, MMLU-Redux 2.0
is CC BY 4.0, and TIGER-AI-Lab's published evaluation outputs keep their own licence. Only ids, letters, counts and
sha256s are published, never question, option or model text. Authored by AI agents working in MV2's name (Munim,
Inc.).

## Results

*Added 2026-11-04 from the sealed job `mcq-mmlu-pro-consensus-distinct-panel-v1` (run 2026-11-03, 231 s; unit tests
passed first). Everything above this heading is unchanged. Full numbers: [`results.json`](results.json); the 892
questions both panels flag with the same option: [`robust_candidates.json`](robust_candidates.json).*

**All six predictions held, but the headline (P3) held by less than one percentage point.** Removing duplicate
archives barely changes the flag's precision: 60 of 315 (19.0%) against 65 of 359 (18.1%). The two panels flag
mostly the same questions (896 of the distinct panel's 1,033 flags are also audit 77's, 892 of them with the same
option). Archives of one model do share wrong answers more than the typical pair of different models (P5), but some
pairs of differently named archives share them even more, so name-based de-duplication removes only part of the
dependence (see the post-hoc reading below).

| # | Verdict | Counts |
| --- | --- | --- |
| P1 | HELD | fixtures 5/5; 12,032 rows; Redux join 5,690 joined, 2,758 in Pro, 55 miskey ids; audit 77 reproduced (1,210 flags, 36 miskeys, 294 OK, 65/359); distinct panel = frozen list (10 archives, 10 lines); 45 archives included; 14 in the union |
| P2 | HELD | distinct panel flags 34/55 Redux miskeys (61.8%) vs 255/2,553 Redux-OK (10.0%): 6.2× (audit 77's panel: 5.7×) |
| P3 | HELD (weakly) | precision 60/315 = 19.0% vs audit 77's 65/359 = 18.1% (+0.9 points) |
| P4 | HELD | 34 of 55 miskeys flagged (threshold 30; audit 77's panel: 36) |
| P5 | HELD | lowest within-line rate 1,317/2,044 = 64.4% vs median cross-line pair 55.3% (5 within-line, 86 cross-line pairs) |
| P6 | HELD | STEM-website 206/4,083 = 5.0% vs MMLU-derived 787/6,810 = 11.6% |

**Flags by group** (count flagged; share of the group in brackets):

| Group | n | Audit 77's panel | Distinct panel | Both, same option |
| --- | --- | --- | --- | --- |
| All questions | 12,032 | 1,210 (10.1%) | 1,033 (8.6%) | 892 |
| Redux miskey | 55 | 36 (65.5%) | 34 (61.8%) | 33 |
| Redux OK | 2,553 | 294 (11.5%) | 255 (10.0%) | 222 |
| Redux other error label | 117 | 29 (24.8%) | 26 (22.2%) | 24 |
| Redux unsure or conflicting | 15 | 2 | 2 | 2 |
| Unreviewed MMLU-derived | 3,928 | 501 (12.8%) | 460 (11.7%) | 387 |
| MMLU-derived (all) | 6,810 | 874 (12.8%) | 787 (11.6%) | 678 |
| STEM website | 4,083 | 271 (6.6%) | 206 (5.0%) | 180 |
| TheoremQA | 598 | 40 (6.7%) | 26 (4.3%) | 22 |
| SciBench | 541 | 25 (4.6%) | 14 (2.6%) | 12 |

**Precision** (error-labelled share of flagged, expert-judged questions): audit 77's panel 65/359 = 18.1%; distinct
panel 60/315 = 19.0%; flagged by both with the same option 57/279 = 20.4% (exploratory).

**Agreement threshold matters far more than de-duplication** (exploratory curve for the distinct panel):

| At least m of 10 agree | Flagged | Redux miskeys | Redux OK | Precision (error-labelled / judged) |
| --- | --- | --- | --- | --- |
| 4 | 1,631 | 41 | 359 | 74/433 = 17.1% |
| 5 | 1,382 | 39 | 323 | 69/392 = 17.6% |
| 6 (frozen) | 1,033 | 34 | 255 | 60/315 = 19.0% |
| 7 | 736 | 28 | 185 | 49/234 = 20.9% |
| 8 | 517 | 26 | 134 | 39/173 = 22.5% |
| 9 | 322 | 24 | 82 | 31/113 = 27.4% |
| 10 | 150 | 17 | 38 | 20/58 = 34.5% |

**Shared wrong answers, within a model line** (share of questions where both archives give the same wrong answer,
among those where both give a valid wrong answer):

| Pair | Same wrong / both wrong | Rate | Accuracies |
| --- | --- | --- | --- |
| GPT-4o 2024-08-06 / GPT-4o 2024-05-13 | 1,485 / 2,106 | 70.5% | 74.8% / 72.5% |
| Claude 3.5 Sonnet 2024-10-22 / Claude 3.5 Sonnet (5-shot) | 1,418 / 2,024 | 70.1% | 77.7% / 76.4% |
| `arx_0314` / `arx_3` | 1,077 / 1,541 | 69.9% | 83.0% / 78.4% |
| Claude 3.5 Sonnet (5-shot) / Sonnet 3.5 (0-shot) | 1,505 / 2,219 | 67.8% | 76.4% / 73.2% |
| Claude 3.5 Sonnet 2024-10-22 / Sonnet 3.5 (0-shot) | 1,317 / 2,044 | 64.4% | 77.7% / 73.2% |

The 86 cross-line pairs range from 47.7% (Gemini 1.5 Pro 002 / GPT-4o mini) to 81.5%, with a median of 55.3%.

**Post-hoc reading (not predicted; treat as a lead).** The names do not capture all the dependence. 11 of the 86
cross-line pairs share wrong answers more often than the lowest within-line pair (64.4%), and 4 exceed the highest
(70.5%): `arx_3` with Claude 3.5 Sonnet (5-shot) at 1,837/2,255 = 81.5%, `arx_0314` with iAsk Pro at 1,173/1,535 =
76.4%, `arx_3` with Claude 3.5 Sonnet 2024-10-22 at 71.3%, and `arx_3` with Sonnet 3.5 (0-shot) at 70.7%. All 11
involve an `arx` archive or iAsk Pro. `arx_3` shares more wrong answers with every Claude 3.5 Sonnet archive than with
`arx_0314`, its own line by name. Accuracy is a confounder (more accurate pairs share more errors, as Kim et al.
report), and these rates say nothing about how any system was built. They do mean that "one archive per name" is not
"one independent opinion per slot": the distinct panel still holds `arx_0314`, iAsk Pro and a Claude 3.5 Sonnet
archive. A panel chosen from measured error agreement, not from names, is the obvious next test.

**What this means.** For finding miskeys with model consensus on MMLU-Pro, removing duplicate archives by name is
nearly free (recall 34 vs 36 of 55, separation 6.2× vs 5.7×) but buys under one point of precision. Raising the
agreement threshold buys much more: at 10 of 10, 34.5% of the expert-judged flags carry an error label, at the cost of
recall (17 of 55). Even at 10 of 10, most flagged questions that experts judged were cleared, so model consensus stays
a way to rank questions for expert review, not a verdict. `robust_candidates.json` is model-flagged and has not been
checked by experts.

**Limits.** Precision is measured only on the 2,758 MMLU-Redux-judged questions MMLU-Pro holds; Redux labels are
expert judgments, not verified facts. Model lines were assigned by archive name before the run; the archives' own
labels are the only provenance used. The P3 margin (+0.9 points, 5 fewer error-labelled flags on 44 fewer judged
flags) is far inside sampling noise, so "held" here means only that the frozen comparison came out in the predicted
direction.
