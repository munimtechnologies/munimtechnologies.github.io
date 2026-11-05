# mcq-mmlu-helm-consensus-miskeys

Audit 80 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-04, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library plus a parquet
reader.*

## Why

Audits 77-79 built and tested a model-consensus flag for miskeyed questions on MMLU-Pro: a question is flagged when at
least 6 of the 10 most accurate published models pick the same option other than the key, and more of them pick it
than pick the key. Against MMLU-Redux 2.0's expert labels it found miskeys at 5.7 times the base rate, but only 65 of
the 359 flagged questions the experts judged (18.1%) carry an expert error label
([audit 77](../mcq-mmlu-pro-model-consensus-miskeys/)), and removing duplicate model archives barely changed that
([audit 79](../mcq-mmlu-pro-consensus-distinct-panel/)). All of it rests on one source of predictions (TIGER-AI-Lab's
archives), one prompt format and 55 miskeyed questions.

This audit asks whether the flag replicates with a different set of models, a different evaluation harness and a
benchmark the experts labelled in full: the original 4-option MMLU test set, using the per-question outputs Stanford
CRFM publishes for its HELM MMLU leaderboard, scored against all 5,700 MMLU-Redux 2.0 labels (106 of them
"wrong ground truth", about twice audit 77's 55).

**Prior art.** MMLU-Redux (Gema et al., "Are We Done with MMLU?", NAACL 2025, arXiv 2406.04127) used HELM's
leaderboard scores to show how its corrections change model rankings, and tested models prompted to detect errors;
it did not use agreement among HELM models' answers as a detector. "Auditing MCQA Benchmarks through Probability
Landscapes" (arXiv 2608.30372) scores flaw signals from model probabilities on a 1,000-item MMLU subset, 373 of them in
MMLU-Redux (9 flawed). "When Models Know When They Do Not Know" (arXiv 2601.07965) re-checks questions two models both
fail with an LLM judge. Kim et al. ("Correlated Errors in Large Language Models", ICML 2025) show that models share
wrong answers. We found no test of a consensus-of-answers flag on HELM's per-question MMLU outputs against all 5,700
MMLU-Redux 2.0 labels.

## Method

1. **HELM runs.** From HELM MMLU release v1.13.0 (`runs_to_run_suites.json` in Stanford CRFM's public
   `crfm-helm-public` bucket), every `mmlu:` run with `method=multiple_choice_joint` and `eval_split=test`. Per (model,
   subject), the run with the fewest extra arguments wins, then the smallest name.
2. **One question universe.** Each subject's `instances.json` from its earliest suite defines its test questions
   (question text, options, the option tagged correct). A question is identified by (subject, whitespace-normalised
   question, options); identities that occur twice are dropped, as are questions without exactly one correct option.
   Every run's answers are mapped onto this universe through its own suite's `instances.json`.
3. **Answers.** The predicted letter gives the option; when it is not a valid letter, HELM's `mapped_output` is used if
   it equals exactly one option. A model is included only if it has all 57 subjects, answers at least 99% of the
   universe, at least 99% of its letters agree with HELM's `mapped_output`, and its accuracy is within 0.5 points of
   HELM's own `exact_match` on the same items.
4. **The panel and the flag.** The 10 most accurate included models (ties by name). The flag is audit 77's rule,
   unchanged: at least 6 of 10 pick one non-key option, and more of them pick it than pick the key.
5. **Expert labels.** Every MMLU-Redux 2.0 row (57 subjects x 100) is joined to the universe by (subject, question,
   choices). Groups: wrong ground truth (miskey), OK, another error label, unsure or conflicting, and not in Redux's
   sample. Precision = among flagged questions Redux judged (miskey, OK or another error label), the share with an error
   label, as in audits 77 and 79.

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: all six fixtures match; 57 subjects; at least 14,000 questions in the universe; MMLU-Redux 2.0 has 5,700 rows, 106 of them miskeys (audit 69); at least 5,600 rows join, and HELM's key equals Redux's published answer on at least 99% of them; at least 20 models are included |
| P2 | The flag separates: it fires on Redux-miskeyed questions at least 5 times as often as on Redux-OK ones (audit 77 on MMLU-Pro: 5.7x) |
| P3 | It flags at least half of the joined Redux miskeys (audit 77: 36 of 55) |
| P4 | HEADLINE: its precision is higher than audit 77's 65 of 359 (18.1%) |
| P5 | It fires on questions with another Redux error label (unclear question or options, no correct answer, several correct answers) at least twice as often as on Redux-OK ones (audit 77: 24.8% vs 11.5%) |
| P6 | Requiring all 10 to agree gives a higher precision than the frozen 6 of 10 (audit 77: 36.4% vs 18.1%; audit 79: 34.5% vs 19.0%) |

Reasoning: MMLU has 4 options, so two wrong models land on the same wrong option more often by chance than on
MMLU-Pro's 10, which could add flags on cleared questions. Against that, HELM's strongest models are more accurate on
MMLU than TIGER-AI-Lab's panel was on MMLU-Pro, so 6 of 10 agreeing on a wrong answer to a sound question should be
rarer. P4 bets that the second effect wins. P2, P3, P5 and P6 check that audit 77's other patterns carry over.

## What a result would mean

If P2-P4 hold, model consensus is a portable way to rank MMLU-style questions for expert review, and more precise on a
benchmark the models find easier. If P4 fails, the 18% precision on MMLU-Pro is not specific to it: most consensus
flags fall on questions experts clear, whatever the harness. `candidates.json` lists every flagged question,
including those outside Redux's sample (about 8,300 MMLU test questions the experts never saw). It is model-flagged,
not expert-checked. Exploratory, not predicted: the panel and every model's inclusion record, flag counts by group and
by subject, and the curve for 4 to 10 of 10.

## Validity gates

Six hand-traced fixtures (`cases80.py`, traced in `test_helm80.py`: audit 77's panel/flag fixture, run selection, the
question universe, answer mapping, the Redux join and the verdicts) must match before any data is read; the job
aborts if fewer than 4,000 Redux rows join. The unit tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads HELM's MMLU release files and MMLU-Redux 2.0
```

## Files

- `helm80.py`: run selection, instances, the question universe, answer mapping, the Redux join, audit 77's panel and
  flag (on option indices), precision and verdicts
- `cases80.py`: the frozen rule, thresholds, gates, data sources and the six fixtures
- `job.py`: downloads, gates, inclusion; writes `results.json` and `candidates.json`
- `test_helm80.py`: unit tests; `requirements.txt`: a parquet reader only

## Licence

Code is Apache-2.0. This write-up and any results are CC BY 4.0. Upstream: HELM (Stanford CRFM) is Apache-2.0 and its
published run outputs keep their own terms; MMLU is MIT; MMLU-Redux 2.0 is CC BY 4.0. Only ids, letters, counts and
16-hex sha256 prefixes of normalised question text are published, never question, option or model text. Authored by
AI agents working in MV2's name (Munim, Inc.).

## Results

*Added 2026-11-05 from the sealed job `mcq-mmlu-helm-consensus-miskeys-v1` (run 2026-11-04, 261 s; unit tests passed
first). Everything above this heading is unchanged. Full numbers: [`results.json`](results.json); every flagged
question: [`candidates.json`](candidates.json).*

**Five of six predictions held, and the structural check P1 failed on one part.** The question universe holds
13,984 questions, not the pre-registered "at least 14,000": MMLU's test set has 14,042, and 54 copies of questions
that occur more than once in a subject plus 4 questions without exactly one correct option were dropped by rule
(Method 2). Every other P1 part held, so the other verdicts stand. On HELM's MMLU outputs the consensus flag
replicates and is more precise than on MMLU-Pro: **130 of 484 flagged, expert-judged questions (26.9%) carry an
expert error label, against 18.1% in audit 77 and a 6.0% base rate among all judged questions** (336 of 5,621).
Most of the gain comes from one subject, virology (see the post-hoc reading below).

| # | Verdict | Counts |
| --- | --- | --- |
| P1 | FAILED (one part) | fixtures 6/6; 57 subjects; universe **13,984** (< 14,000; 14,042 minus 54 duplicate copies and 4 without one gold); Redux 5,700 rows, 106 miskeys; 5,653 joined (47 not matched); HELM's key equals Redux's published answer on 5,653 of 5,653; 78 of 79 models included |
| P2 | HELD | flags 80/106 Redux miskeys (75.5%) vs 354/5,285 Redux-OK (6.7%): 11.3× (audit 77: 5.7×) |
| P3 | HELD | 80 of 106 miskeys flagged (75.5%; audit 77: 36 of 55) |
| P4 | HELD | precision 130/484 = 26.9% vs audit 77's 65/359 = 18.1% |
| P5 | HELD | other error labels 50/230 (21.7%) vs Redux-OK 6.7%: 3.2× |
| P6 | HELD | 10 of 10 agree: 67/132 = 50.8% vs 6 of 10: 26.9% |

**The panel** (the 10 most accurate of the 78 included models, by accuracy on the 13,984 questions): HELM's
`anthropic_claude-3-5-sonnet-20241022` 87.65%, `anthropic_claude-3-5-sonnet-20240620` 87.19%,
`deepseek-ai_deepseek-v3` 86.73%, `google_gemini-1.5-pro-002` 86.36%, `anthropic_claude-3-opus-20240229` 85.05%,
`openai_gpt-4o-2024-08-06` 84.93%, `meta_llama-3.1-405b-instruct-turbo` 84.93%, `openai_gpt-4o-2024-05-13` 84.82%,
`openai_gpt-4-0613` 84.01%, `qwen_qwen2.5-72b-instruct-turbo` 83.31%. Four slots are two dated versions each of
Claude 3.5 Sonnet and GPT-4o, so this panel has eight distinct model lines (audit 79 found that de-duplicating by line
barely changes precision on MMLU-Pro). The one excluded model, `ai21_jamba-1.5-mini`, has no `miscellaneous` run in
this release. Every included model's accuracy matches HELM's own `exact_match` on the same items.

**Flags by group** (count flagged; share of the group in brackets):

| Group | n | Flagged |
| --- | --- | --- |
| All questions | 13,984 | 1,207 (8.6%) |
| Redux miskey | 106 | 80 (75.5%) |
| Redux OK | 5,285 | 354 (6.7%) |
| Redux other error label | 230 | 50 (21.7%) |
| Redux unsure (`expert`) or conflicting | 32 | 8 (25.0%) |
| Not in Redux's sample | 8,331 | 715 (8.6%) |

**Agreement threshold** (exploratory curve, same panel):

| At least m of 10 agree | Flagged | Redux miskeys | Redux OK | Precision (error-labelled / judged) | Not in Redux's sample |
| --- | --- | --- | --- | --- | --- |
| 4 | 1,431 | 84 | 444 | 140/584 = 24.0% | 838 |
| 5 | 1,372 | 84 | 419 | 139/558 = 24.9% | 805 |
| 6 (frozen) | 1,207 | 80 | 354 | 130/484 = 26.9% | 715 |
| 7 | 885 | 69 | 244 | 103/347 = 29.7% | 533 |
| 8 | 666 | 64 | 177 | 87/264 = 33.0% | 398 |
| 9 | 486 | 59 | 125 | 77/202 = 38.1% | 282 |
| 10 | 304 | 52 | 65 | 67/132 = 50.8% | 171 |

**By subject** (exploratory; `by_subject_exploratory` in `results.json` has all 57):

- **Virology** holds 33 of the 106 Redux miskeys and 30 of the 80 flagged ones. 65 of its 166 questions are flagged
  (39.2%). Of the 42 flagged questions Redux judged, 39 carry an error label (30 miskeys, 5 unclear questions, 2 with
  several correct answers, 2 with no correct answer) and 3 were cleared.
- **College chemistry** holds 21 miskeys, 12 of them flagged; all 22 of its flags fall on Redux's sample.
- **Professional law** has the most flags, 294 of 1,534 questions (19.2%), and 276 of the 715 flags outside Redux's
  sample (38.6%). Of its 18 flagged, judged questions, 4 carry an error label (1 miskey, 3 others).
- Moral scenarios (61 flags, 57 outside the sample), professional psychology (38) and high-school mathematics (38)
  follow. The flag missed every miskey in logical fallacies (0 of 3), international law (0 of 2) and astronomy (0 of 1).

**Post-hoc reading (not predicted; treat as a lead).**

1. *The headline rests mostly on virology.* Leaving virology out, precision is 91 of 442 (20.6%): still above audit
   77's 18.1%, but by 2.5 points, not 8.8. Recall without virology is 50 of 73 miskeys (68.5%). So the replication of
   P2, P3 and P5 does not depend on virology; the size of the P4 gain mostly does.
2. *Virology's unreviewed questions.* Among virology questions Redux judged, all 10 panel models picked the same
   non-key option on 32, and 31 of those carry an error label (one was cleared). Outside Redux's sample, all 10 agree
   on 16 more virology questions, none of them picking the key: HELM instance ids 52, 59, 65, 91, 103, 114, 128, 147,
   149, 151, 155, 158, 160, 164, 171 and 185 (`id` prefix; positions and letters in `candidates.json`). They are the
   first MMLU questions this audit would send to an expert. MMLU-Redux suggests many of virology's errors stem from
   problems parsing the original source material; we have not checked these 16 by hand.

**What this means.** A consensus of answers from the strongest models, taken from a different harness and model set,
finds MMLU's expert-flagged miskeys again: three in four of them, at 11 times the rate on cleared questions. As a
detector it is still mostly a way to rank questions for review: at the frozen 6 of 10, about three in four flagged,
judged questions were cleared by the experts; at 10 of 10 it is one in two, and it is higher in a subject whose key is
known to be badly damaged. `candidates.json` lists 1,207 questions, 715 of them outside Redux's sample (171 at 10 of
10). They are model-flagged and have not been checked by experts. Each may hold a wrong key, a second defensible
answer or a mistake the models share.

**Limits.** One harness (HELM's joint multiple-choice prompt), one release (v1.13.0) and models up to late 2024.
Redux labels are expert judgments, not verified facts, and cover 100 questions per subject, so subjects with many
questions (professional law, moral scenarios) are judged on a small share. The P1 threshold was set before checking
how many MMLU questions are duplicated within a subject; the failure is in the gate, not in the data or the code.

**Related work found after the pre-registration.** Land and Bikel ("Auditing LLM Benchmarks with Item Response
Theory", arXiv 2605.30504, EMNLP 2026) fit an item-response model to 114 models' answers on seven preference and
multiple-choice benchmarks (GPQA Diamond, MATH and GSM8K among the multiple-choice ones; MMLU is not among them) and
flag items where ability predicts a non-reference answer better than the reference. They report 95% precision in
their top 200 against an LLM reviewer's labels and release the flagged items as `Writer/IRT-mislabeled-items`. Their
signal uses every model's ability; ours counts the top 10 models' votes and is scored against human experts.
