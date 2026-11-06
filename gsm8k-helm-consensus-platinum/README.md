# gsm8k-helm-consensus-platinum

Audit 86 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-06, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library plus a parquet
reader.*

## Why

Audits 77-85 scored a model-consensus flag for wrong answer keys on MMLU and MMLU-Pro, multiple-choice benchmarks,
against MMLU-Redux 2.0's expert labels, which cover a random sample of 100 questions per subject. At its best the flag
is a good review queue, not a verdict: about 1 in 4 of its judged flags on MMLU carries an expert error label
([audit 80](../mcq-mmlu-helm-consensus-miskeys/)), and the strongest short list from the MMLU audits, questions no
model answers with the key, fell from 73% to 35.5% when it was tested on MMLU-Pro
([audit 84](../mcq-mmlu-pro-panel-strength/)).

This audit asks whether the same flag works on a free-response benchmark with complete labels. On GSM8K a model's
answer is a number, so many models agreeing on one wrong number should be rarer by chance than many agreeing on one of
four letters. And GSM8K-Platinum (Vendrow, Vendrow, Beery and Madry, "Do Large Language Model Benchmarks Test
Reliability?", arXiv 2502.03461) labels every one of GSM8K's 1,319 test questions: 110 removed as flawed (mostly
ambiguous), 10 with a corrected answer, 99 reviewed and kept, and 1,100 kept without review because every model
they ran agreed with the key. Model answers come from Stanford CRFM's HELM Lite, which publishes per-question GSM8K
outputs of about 90 models (5-shot chain of thought) that nobody has scored against Platinum's labels.

**Prior art.** Platinum itself chose questions for manual review when any of its models got them wrong. Zhang, Cai
and Chen ("Beyond the Singular", arXiv 2502.08943, Findings of ACL 2026) sample many answers from one model on GSM8K
and read questions it answers consistently but is scored wrong on as likely label errors. Kim et al. ("Correlated
Errors in Large Language Models", ICML 2025, arXiv 2506.07962) show from HELM data that models agree on wrong answers
far above chance, which limits any agreement filter. We found no test of a cross-model consensus flag built from
HELM's archived outputs against Platinum's labels, no comparison of it with Platinum's own "any model wrong" filter
on another model set, and no test of panel strength or of the "no model gives the key" filter on GSM8K.

## Method

1. **Labels.** GSM8K test (`openai/gsm8k`, `main`, 1,319 questions) and GSM8K-Platinum (`madrylab/gsm8k-platinum`,
   `main`, 1,209 rows) via the Hugging Face parquet API, joined by whitespace-normalised question text. Each GSM8K
   question takes Platinum's `cleaning_status` (consensus, verified, revised); a GSM8K question Platinum does not
   hold is `rejected`. **Error** = rejected or revised; **clean** = verified or consensus.
2. **Model answers.** Every HELM Lite release v1.13.0 run whose name starts with `gsm:` (one per model: newest suite,
   then the shorter run name). Instances join GSM8K by question text. A model's answer is HELM's own final number
   (`get_final_number`, transcribed from HELM's `final_number_exact_match`, including its unescaped `.`); the key is
   the final number of HELM's reference; a prediction with no number gives no answer. The universe is the GSM8K
   questions present in at least half the runs, where HELM's key equals GSM8K's `####` answer.
3. **Inclusion.** A model is included when at least 99% of its instances join, it answers at least 99% of the
   universe, and our transcribed scorer equals HELM's recorded `final_number_exact_match` on at least 99% of its
   predictions.
4. **Panels.** Included models ranked by HELM accuracy on the universe (ties by name); S1..S5 = ranks 1-10 ... 41-50.
5. **Flags on a panel of 10.** *Consensus* (audit 77's rule): at least 6 of 10 give the same non-key number and more
   give it than give the key. *Unanimous*: 10 of 10 on one non-key number. *Any wrong* (Platinum's filter applied to
   HELM's panel): fewer than 10 of 10 give the key. *Margin*: votes for the most-given non-key number minus votes for
   the key (-10 to +10).
6. **No-key flag.** At least 2 included models answer and none gives the key.
7. **Scores.** Precision = error-labelled share of flagged questions; recall = flagged share of error-labelled
   questions; AUC of S1's margin, error vs clean; **equal budget**: each panel's K highest-margin questions, K = S1's
   consensus-flag count, ties at the cut shared evenly (exact expected counts, audit 83's method).

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: all fixtures match; Platinum has 1,209 rows and the labels are exactly 1,100 consensus, 99 verified, 10 revised and 110 rejected; the HELM universe holds 900 to 1,319 questions with HELM's key equal to GSM8K's on at least 99%; at least 60 models are included |
| P2 | HEADLINE: at least half of S1's consensus flags are error-labelled |
| P3 | S1's consensus flag is more precise than S1's any-wrong filter |
| P4 | S1's margin separates error from clean questions with AUC at least 0.75 |
| P5 | S1's consensus flag catches at least a quarter of the error-labelled questions in the universe |
| P6 | The no-key flag is at least as precise as S1's consensus flag, with at least 10 flagged questions (fewer counts as FAILED: undecidable) |
| P7 | Strength matters: at the equal budget, S1 is more precise than S5 (ranks 41-50) |

Reasoning: a shared wrong number is a stronger signal than a shared wrong letter, so precision should be far above
MMLU's 1 in 4 (P2), and far above "any of 10 wrong", which also fires on every question one strong model slips on
(P3). Most removed questions are ambiguous rather than miskeyed, and on an ambiguous question strong models may still
pick the key's reading, so recall should be well below the MMLU flag's three quarters (P5 asks only for a quarter)
and the AUC is held to 0.75 (P4). P6 bets that audit 84's failure was a multiple-choice effect: with free answers,
no model out of about 90 reaching the key should almost always mean a flawed question. P7 repeats audits 83 and 84.

## What a result would mean

If P2-P5 hold, consensus over archived outputs is a cheap, strong first filter for free-response benchmarks, at no
new inference cost, and its precision can be read off before any expert time is spent. If P2 fails, agreement on a
wrong number is as often a shared mistake as a flawed question, as on MMLU. If P6 fails again, "no model reaches the
key" is not a reliable short list on either kind of benchmark. Exploratory, not predicted: every panel's flags by
Platinum status, precision counting only the questions Platinum reviewed, the 10-of-10 flag, a 20-model panel (at
least 12 of 20), the share of all models giving the key as a score, and, for the 10 revised questions, whether the
panel's consensus number equals Platinum's corrected answer.

## Validity gates

Hand-traced fixtures (`cases86.py`, traced in `test_gsm86.py`: HELM's scorer on nine strings including the unescaped
dot and a trailing comma, the Platinum labelling with duplicates and an unmatched row, run selection, votes and the
four flags on six questions, precision, recall, AUC, equal-budget counts, model ranking and both verdict cases) must
match before any data is read. The job aborts if more than 5 Platinum rows fail to join GSM8K, if the universe is
outside 900-1,319 questions or HELM's key agrees with GSM8K's on under 99%, or if fewer than 60 models are included
(diagnostics are still written). The unit tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads GSM8K, GSM8K-Platinum and HELM Lite's GSM8K outputs (about 90 models)
```

## Files

- `gsm86.py`: HELM's scorer (transcribed), the Platinum labelling, run selection, votes, flags, precision, recall,
  AUC and equal-budget counts (copied from audit 84), and the verdicts
- `cases86.py`: data sources, gates, the flag rule, thresholds and the fixtures
- `job.py`: downloads, gates, every panel's flags, the no-key flag; writes `results.json` and `candidates.json`
- `test_gsm86.py`: unit tests; `requirements.txt`: a parquet reader only

## Licence

Code is Apache-2.0 (HELM's `final_number_exact_match` is transcribed from stanford-crfm/helm, Apache-2.0). This
write-up and any results are CC BY 4.0, except Platinum's per-question statuses, which stay CC BY-SA 4.0 as
GSM8K-Platinum's annotations are. Upstream: GSM8K is MIT; HELM's outputs are published by Stanford CRFM. Only GSM8K
test positions, final numbers, labels, counts and public model names and accuracies are published, never question or
model text. Authored by AI agents working in MV2's name (Munim, Inc.).
