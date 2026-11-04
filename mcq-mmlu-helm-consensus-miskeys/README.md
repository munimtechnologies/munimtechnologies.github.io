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
