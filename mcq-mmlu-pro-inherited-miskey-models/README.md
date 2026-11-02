# mcq-mmlu-pro-inherited-miskey-models

Audit 76 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-02, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library plus a parquet
reader.*

## Why

Audit 75 ([mcq-mmlu-pro-redux-inheritance](../mcq-mmlu-pro-redux-inheritance/)) found that MMLU-Pro still uses MMLU's
original key on 52 of the 55 questions MMLU-Redux 2.0's experts marked "wrong ground truth" that MMLU-Pro holds. On 46
of the 52 the experts' answer is one of MMLU-Pro's ten options (24 from a letter or exact-text correction, 22 from a
digit correction read 0-based, the only reading audit 75 found coherent). That is a list of expert judgments, not a
verified one. This audit asks the models: TIGER-AI-Lab publishes per-question MMLU-Pro predictions for dozens of
models (audit 66 read 48 archives), so on these 46 questions, do the models choose the experts' answer or the
published key?

**Prior art.** The MMLU-Redux paper (Gema et al., arXiv 2406.04127) compares model accuracy on MMLU's original and
corrected labels, and reads models that match MMLU's original wrong labels as possible memorisation. A search on
2026-11-02 found no per-question count of model choices on MMLU-Redux's miskeys inside MMLU-Pro, where each question
has up to ten options, and no use of TIGER-AI-Lab's prediction archives for this.

## Method

1. **Targets.** The 46 questions are frozen in `cases76.py` from audit 75's `pro_flags.json`: MMLU-Pro
   `question_id`, `src`, the key letter and the experts' answer letter among MMLU-Pro's options. A target counts only
   if MMLU-Pro's current test data still has that `src` and key (otherwise it is listed and dropped).
2. **Predictions.** Every archive audit 66 listed is read with audit 65/66's reader and join rule: a record joins
   only if its `question_id`, stripped options and answer equal the HF row; an archive is included only if at least
   95% of its records join and it covers at least 95% of the test set.
3. **Classes.** Each prediction on a target is the KEY, the EXPERTS' answer, OTHER (another option) or NONE (missing
   or malformed). An OTHER pick also adds 1/(k−2), so OTHER picks can be compared with one average other distractor.
4. **Control.** Each model's accuracy (as MMLU-Pro scores it) on the MMLU-derived questions other than the 55 Redux
   miskeys.

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: the fixture matches; the frozen list has 46 targets (24 primary) and 55 miskey ids; MMLU-Pro has 12,032 valid rows with audit 63's source families; at least 44 of 46 targets still carry audit 75's key; at least 30 archives are included |
| P2 | HEADLINE: pooled over included models, the experts' answer is picked more often than the published key on the targets |
| P3 | In at least 75% of models with at least 40 joined targets, expert picks exceed key picks |
| P4 | Pooled, the experts' answer is picked at least 3 times as often as an average other distractor |
| P5 | Every such model's key-pick rate on the targets is below its accuracy on the control questions |
| P6 | On at least 60% of the target questions, pooled expert picks exceed pooled key picks |
| P7 | P2 holds on the 24 primary (letter or exact-text) targets alone |

## What a result would mean

If P2-P4 and P6 hold, the models, which never saw Redux's labels, side with the experts on most of these questions,
which supports correcting MMLU-Pro's keys there. A question where models still pick the key is a candidate either for
a disputed expert label or for memorisation of MMLU's key; this audit reports those questions but does not decide
between the two. P7 checks that the result does not rest on the 0-based digit reading. Exploratory, not predicted:
each model's score change if the 46 keys followed the experts, and key picks against an average other distractor.

## Validity gates

A hand-traced fixture (`cases76.py`, traced in `test_inherit_models.py`) must match exactly before any real data is
read, the frozen list must be internally consistent, and the MMLU-Pro parse must reproduce audit 63's counts; the job
aborts otherwise. The unit tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads MMLU-Pro (test) and TIGER-AI-Lab's prediction archives
```

## Files

- `inherit_models.py`: classes, tallies, control accuracy, predictions
- `cases76.py`: the frozen targets, the 55 miskey ids, archives, thresholds, the hand-traced fixture
- `job.py`: loaders, gates, joins; writes `results.json`
- `test_inherit_models.py`: unit tests; `requirements.txt`: a parquet reader only

## Licence

Code is Apache-2.0. This write-up and any results are CC BY 4.0. Upstream: MMLU-Pro is MIT, TIGER-AI-Lab's published
evaluation outputs keep their own licence, and MMLU-Redux 2.0 is CC BY 4.0. Only ids, letters, counts and sha256s are published, never
question, option or model text. Authored by AI agents working in MV2's name (Munim, Inc.).

## Results

*Added 2026-11-02, after the sealed run (started 2026-11-02 04:00 UTC, 174 s; unit tests, the fixture gate, the
frozen-list check and the structural gate passed). Everything above this heading is unchanged from the
pre-registration. Frozen output: `results.json`.*

**Status: results in. All 7 predictions held. 45 published models side with MMLU-Redux's experts against MMLU-Pro's
key on these questions: pooled, they pick the experts' answer 1,041 times and the key 283 times.**

| # | Result |
| --- | --- |
| P1 | **HELD.** Fixture, frozen list (46 targets, 24 primary, 55 miskey ids) and MMLU-Pro parse (12,032 rows: `ori_mmlu` 6,810, `stemez` 4,083, `theoremQA` 598, `scibench` 541) all match; **46 of 46** targets still carry audit 75's key; **45 of 48** archives included. Excluded by the join rule: DeepSeek-Coder-V2 (covers 84.3% of the test set), Meta-Llama-3-70B-Instruct (run on an earlier dataset version, 0% join) and `sonnet_0shots_12_01_18` (covers 94.8%) |
| P2 | **HELD.** Pooled over 45 models × 46 targets (2,070 predictions): experts' answer **1,041 (50.3%)**, published key **283 (13.7%)**, another option 601 (29.0%), no valid answer 145 (7.0%) |
| P3 | **HELD, 45 of 45 models.** Every included model picks the experts' answer more often than the key: from 11 vs 6 (Llama-2-13B) and 11 vs 2 (Llama-2-7B) to **36 vs 8 (Gemini 3.1 Pro)**; per model the key is picked 1 (Phi-3-mini) to 10 times (Claude 3.5 Haiku, Gemini 1.5 Flash) |
| P4 | **HELD.** Pooled, the experts' answer is picked **11.8 times** as often as an average other distractor (1,041 vs 88.1) |
| P5 | **HELD, 45 of 45.** Every model's key-pick rate on the targets (2.2% to 21.7%) is below its accuracy on the 6,755 control questions (17.9% to 90.0%) |
| P6 | **HELD.** On **37 of 46** questions (80.4%) pooled expert picks exceed key picks; key picks lead on 9; no ties |
| P7 | **HELD.** On the 24 primary (letter or exact-text) targets alone: experts' answer 464, key 127 (of 1,080 predictions); 8.7 times an average other distractor |

**By correction format.** Primary targets: experts' answer 464 vs key 127, and expert picks lead on 19 of 24
questions. Digit targets read 0-based: experts' answer 577 vs key 156 (of 990 predictions), and expert picks lead on 18
of 22. So the result does not rest on the 0-based reading of Redux's digit corrections. Most NONE answers (127 of
145) fall on the primary targets, nearly all of them college chemistry. Per model on the primary targets alone (not
pre-registered), 43 of 45 models pick the experts' answer more often than the key; Yi-6B ties (4 vs 4) and Llama-2-13B
picks the key more often (4 vs 1).

**Where the models agree with the experts.** All 45 models pick the experts' answer on ids 6224 (anatomy), 9547
(conceptual physics) and 10458 (computer security); 44 on 5726 (public relations); 43 on 7306 (microeconomics) and
10533 (computer security); 42 on 6278 (virology); 41 on 4084 (college chemistry). The per-question counts for all 46
are in `results.json` (`per_question`).

**Where the models side with the key.** Key picks lead on 9 questions: 3725, 3990, 4341, 4438 (college chemistry),
6639 (virology), 7791, 8972 (abstract algebra), 9677 (astronomy) and 9947 (conceptual physics). Two are lopsided:
**9677** (40 of 45 pick the key, 1 the experts' answer) and **6639** (34 vs 3). On 7791 (20 vs 19) and 9947 (22 vs 21)
the models split almost evenly. As pre-registered, this audit does not decide whether these mark a disputed expert
label or memorisation of MMLU's key; 9677 and 6639 are the first questions a human reviewer should re-check.

**Exploratory (not predicted).** (a) *Score impact.* If the 46 keys followed the experts, every model's accuracy on
its joined questions would rise, by +0.04 points (Llama-2-13B) to +0.23 points (Gemini 3.1 Pro). Stronger models gain
most (Gemini 3.1 Pro +0.23, both `arx` runs +0.23, iAsk Pro +0.22, Claude 3.5 Sonnet +0.22), so these keys penalise
the best models slightly more. Whether any leaderboard order changes was not computed. (b) *Memorisation hint.*
Pooled, the published key is still picked about 3.2 times as often as an average other distractor (283 vs 88.1), and
more so for strong models (Gemini 3.1 Pro: 8 key picks against 0.25 per average other distractor). That fits either
memorisation of MMLU's key or a key that is a near-miss answer, and these data cannot tell the two apart.

**What it means.** On the MMLU questions that MMLU-Redux's experts judged miskeyed and that MMLU-Pro still keys the
old way, 45 published models, from Llama-2-7B to Gemini 3.1 Pro, which never saw Redux's labels, choose the experts'
answer about 3.7 times as often as MMLU-Pro's key, and every one of them does so on its own. That is independent
support for correcting most of these keys. The two clear exceptions (9677, 6639) are where the expert label itself
deserves a second look. Limits: models agreeing with experts is evidence, not proof, of the right answer (models can
share a misconception), the models are correlated (several share a family or are versions of one model), the archives
are the ones TIGER-AI-Lab published (5-shot chain-of-thought, mostly 2024 models), and the score effect is small
because 46 questions are 0.38% of MMLU-Pro.
