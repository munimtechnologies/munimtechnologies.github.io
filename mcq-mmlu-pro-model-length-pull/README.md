# mcq-mmlu-pro-model-length-pull

Audit 65 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code, the pre-registered
predictions and the frozen `results.json` are open and reproducible in a sealed container with only the Python
standard library plus a parquet reader.*

## What this targets

Audits 61 to 63 measured a property of MMLU-Pro's answer options: a question-free "pick the longest option"
heuristic scores 18.4% pooled (chance 11.1%) and 66.85% on the 656 STEM-website biology and psychology questions
(`src` `stemez-Biology` and `stemez-Psychology`). That says the options leak. It does not say whether models
follow the leak.

This is the first model-side audit in the catalogue. TIGER-AI-Lab publishes per-question predictions for MMLU-Pro
(`eval_results/*.zip` in github.com/TIGER-AI-Lab/MMLU-Pro). This audit downloads 17 of those archives (5-shot
chain-of-thought runs chosen before any was opened to span families and sizes), joins each record to the HF test
row by `question_id` with identical stripped options and answer, and measures per model:

- **error pull**: of the model's wrong answers, the share that land on a longest distractor, divided by the exact
  tie-aware share a uniformly random wrong choice would give. 1.0 means no lean; above 1 means wrong answers are
  drawn toward long options;
- **accuracy when the gold is the unique longest option** versus when it is not;
- accuracy on the STEM-website biology and psychology questions, against the 66.85% pick-longest heuristic.

All are computed pooled, by source family (`ori_mmlu`, `stemez`, `scibench`, `theoremQA`) and on two matched
subsets: STEM-website biology + psychology and MMLU-derived biology + psychology.

## Prior art

Option-length perturbation on MMLU (arXiv 2502.12459), length bias in vision-language MCQ (arXiv 2610.24500) and
audio LMs (arXiv 2510.04584), and choices-only MMLU-Pro (arXiv 2507.15337) study length or choices-only cues by
changing the inputs. The closest is Turkish MMLU Pro (arXiv 2609.15467), which reports a mean length rank of the
options five models choose when wrong (0.515 to 0.536 against 0.5) on a Turkish benchmark built by borrowing options
from other questions. A search on 2026-10-30 found no study that reads MMLU-Pro's own published predictions to ask
whether models' errors fall on the longest distractor, or how that differs by source.

## Pre-registered predictions (frozen before any archive was opened)

| # | Prediction | Verdict |
| --- | --- | --- |
| P1 | Error pull above 1 in a strict majority of models | **HELD** (15 of 15) |
| P2 | Error pull larger on `stemez` than on `ori_mmlu` in a strict majority of models | **FAILED** (1 of 15) |
| P3 | On STEM-website biology + psychology every model is more accurate when the gold is the unique longest | **HELD** (15 of 15, +12.9 to +32.3 pts) |
| P4 | Models below the median accuracy have a larger mean error pull | **HELD** (1.106 vs 1.075) |
| P5 | At least a quarter of models score below the pick-longest heuristic on STEM-website biology + psychology | **FAILED** (3 of 15) |

Each is a finding either way.

## Validity gates

- Hand-traced fixtures for the accumulator, the tie-aware credit, the join and the subset keys match exactly.
- The HF parse reproduces audit 63 exactly: 12,032 questions; families 6,810 / 4,083 / 541 / 598;
  `stemez-Biology` 351 at 0.66707…, `stemez-Psychology` 305 at 0.67009….
- A model is included only if at least 95% of its records join cleanly and they cover at least 95% of the test
  set. 15 of 17 archives pass (98.2% to 98.5% of records join; the rest differ in options or answer from the current
  HF copy, a sign of dataset revisions). Excluded: **Meta-Llama-3-70B-Instruct** (12,187 records, 0 join: 11,962
  have different options and 225 have no matching id, so it was run on an earlier dataset version) and
  **DeepSeek-Coder-V2** (10,351 records cover only 84.3% of the test set). Each archive's sha256 is in
  `results.json`.

## What it found

**1. Every model's wrong answers lean toward the longest distractor, a little.** Pooled error pull is 1.055 to
1.140 in all 15 models (P1). The weakest in standard-deviation terms, Gemini 1.5 Pro's 1,485 wrong answers on a longest distractor
against 1,400.9 expected, is about 2.9 standard deviations under a conservative binomial approximation (derived,
not in `results.json`).

**2. The lean is strongest exactly where the options leak most.** On the 656 STEM-website biology and psychology
questions, wrong answers land on a longest distractor 1.23 to 2.31 times as often as a random wrong choice. On the
708 to 712 MMLU-derived biology and psychology questions the same models score 1.01 to 1.43. STEM-website is higher
in 14 of 15 models (Mistral-7B-Instruct-v0.2 is the exception). For the three strongest models the MMLU-derived
pull is essentially absent (Claude 3.5 Sonnet 1.01, GPT-4o 1.02, Gemini 1.5 Pro 1.06) while the STEM-website pull is
1.7 to 2.0. This comparison was not pre-registered, and the STEM-website counts are small (50 to 58 wrong answers for
those three models; GPT-4o: 19 on a longest distractor vs 9.7 expected, about 3.3 SD by the same approximation).

**3. Why P2 failed.** At the family level the `stemez` pull (1.04 to 1.12) is below the `ori_mmlu` pull (1.07 to
1.19) in 14 of 15 models. Most `stemez` questions are physics, chemistry and engineering problems with numeric
options that tie in length: a random wrong choice already lands on a longest distractor about half the time
(baseline 0.48 to 0.56, against 0.21 to 0.25 on `ori_mmlu`), which leaves little room for a ratio above 1. The lean
shows where the gold is a long prose answer, as in the biology and psychology subset.

**4. Three of 15 models score below "pick the longest answer" on the STEM-website biology and psychology
questions.** The heuristic scores 66.85% there without reading the question. Llama-2-7B scores 47.7%,
Mistral-7B-Instruct-v0.2 61.6% and Gemma-7B 62.8%. P5 needed four. Every model is more accurate on these questions
when the gold is the unique longest option (P3): by 12.9 points (Gemini 1.5 Pro) to 32.3 (Phi-3-mini).

**5. On MMLU-derived questions, whether the gold is longest makes no difference.** Across all `ori_mmlu`
questions, accuracy with the gold unique-longest minus accuracy otherwise is −3.0 to +2.6 points in every model.
Across all `stemez` questions it is +15.9 to +45.1 points. That family-level gap is confounded by subject mix (the
gold is the unique longest mostly in prose subjects, which models find easier than numeric ones), so P3's
within-subset gap is the cleaner measure.

| model | accuracy (all) | missing preds | error pull: all / `ori_mmlu` / `stemez` | STEM-web bio+psy: accuracy | gold unique-longest / not | wrong answers | error pull | MMLU-derived bio+psy error pull |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Llama-2-7B | .1834 | 2,052 | 1.115 / 1.144 / 1.101 | **.4771** | .5856 / .2658 | 282 | 1.478 | 1.362 |
| Mistral-7B-Instruct-v0.2 | .2879 | 2,226 | 1.140 / 1.181 / 1.116 | **.6162** | .6852 / .4820 | 232 | 1.226 | 1.352 |
| Gemma-7B | .3248 | 1,571 | 1.096 / 1.108 / 1.106 | **.6284** | .7199 / .4505 | 203 | 1.724 | 1.247 |
| Llama-2-70B | .3634 | 1,428 | 1.074 / 1.091 / 1.090 | .7355 | .8264 / .5586 | 139 | 1.701 | 1.227 |
| Llama-3-8B-Instruct | .4024 | 887 | 1.104 / 1.152 / 1.107 | .8150 | .9051 / .6396 | 120 | 2.041 | 1.287 |
| Phi-3-mini-4k-instruct | .4166 | 1,849 | 1.120 / 1.189 / 1.093 | .7722 | .8819 / .5586 | 132 | 1.764 | 1.358 |
| Mixtral-8x7B-Instruct | .4195 | 1,416 | 1.092 / 1.074 / 1.118 | .7997 | .8889 / .6261 | 122 | 1.548 | 1.198 |
| Yi-34B | .4212 | 1,025 | 1.076 / 1.097 / 1.085 | .7523 | .7986 / .6622 | 145 | 1.648 | 1.426 |
| Llama-3.1-8B-Instruct | .4438 | 29 | 1.055 / 1.129 / 1.038 | .7698 | .8406 / .6323 | 151 | 1.454 | 1.270 |
| Qwen1.5-72B-Chat | .4724 | 2,193 | 1.107 / 1.126 / 1.118 | .7936 | .8727 / .6396 | 98 | 1.886 | 1.107 |
| Llama-3.1-70B-Instruct | .6307 | 4 | 1.069 / 1.088 / 1.085 | .8902 | .9561 / .7623 | 72 | 2.210 | 1.160 |
| GPT-4o-mini | .6336 | 1 | 1.082 / 1.194 / 1.047 | .8552 | .9122 / .7444 | 95 | 2.313 | 1.161 |
| Gemini 1.5 Pro (002) | .7031 | 8 | 1.060 / 1.082 / 1.057 | .9145 | .9583 / .8296 | 56 | 1.718 | 1.061 |
| GPT-4o (2024-08-06) | .7476 | 66 | 1.070 / 1.164 / 1.050 | .9116 | .9561 / .8251 | 58 | 1.957 | 1.020 |
| Claude 3.5 Sonnet | .7644 | 3 | 1.080 / 1.140 / 1.072 | .9238 | .9723 / .8296 | 50 | 1.892 | 1.013 |

Rows are sorted by overall accuracy. Bold: below the 66.85% pick-longest heuristic. "Wrong answers" and the two
right-hand error-pull columns refer to the STEM-website biology + psychology subset (654 to 656 joined questions)
and the MMLU-derived biology + psychology subset (708 to 712).

**Accuracies here are not leaderboard scores.** A missing or unparseable prediction counts as wrong. The upstream
scorer substitutes a random guess instead, so models with many missing predictions (Llama-2-7B, Mistral-7B,
Qwen1.5-72B) score lower here than on the leaderboard. Giving each missing prediction on the STEM-website subset a
10% random-guess credit would move Llama-2-7B to about 48.6%, Mistral-7B to about 61.9% and Gemma-7B to about 63.5%
(derived), still below 66.85%. Error pull uses only parsed wrong answers, so missing predictions do not enter it.

**Reading it:** MMLU-Pro's length leak is not only a property of the options. Models' wrong answers follow it,
weakly overall and about twice as strongly as chance on the STEM-website biology and psychology questions, including
the strongest models in this set. On those 656 questions, three widely used 7B-class models score below a heuristic
that never reads the question. Reporting MMLU-Pro by `src`, and comparing a model against the length-only floor of
the slice it is scored on, makes this visible.

## Limits

- **Observational.** A pull toward a long distractor can mean the long distractor is the most plausible wrong
  answer, not that length itself attracts the model. This audit does not perturb option lengths.
- The predictions are TIGER-AI-Lab's archived runs (5-shot chain of thought) from 2024; newer models and other
  prompting setups are not covered. 1.5% to 1.8% of each model's records were dropped because the archived options
  or answer differ from the current HF copy.
- The STEM-website subset is small: 50 to 282 wrong answers per model. The pooled numbers rest on 2,782 to 7,595.
- The standard-deviation figures and the random-guess credit are derived arithmetic on the frozen counts, not
  outputs of `job.py`.
- No model output text is republished; `results.json` holds only counts, rates and archive hashes.

## Reproduce

```
python -m unittest -v        # hand-traced fixtures for the accumulator, credit, join and keys
python job.py --out-dir out  # downloads the MMLU-Pro test parquet and 17 prediction archives, writes out/results.json
```

`job.py` reads `TIGER-Lab/MMLU-Pro` (`default`, `test`) from the HuggingFace auto-converted parquet via the
datasets-server parquet API and the archives from `github.com/TIGER-AI-Lab/MMLU-Pro/raw/refs/heads/main/eval_results/`.
It aborts unless the fixtures match and the parse reproduces audit 63 exactly. Accumulation is exact
(`fractions.Fraction`) and standard library only.

## Files

- `job.py`: loader, archive reader, join, per-model accumulation, gates and predictions; writes `results.json`
- `model_length.py`: error pull, tie-aware credit, join status, subset keys and the pre-registered predictions
- `cases.py`: hand-traced fixtures, the archive list (fixed before any was opened), pinned audit-63 numbers
- `test_model_length.py`: unit tests
- `results.json`: frozen output (per archive: join counts, coverage, sha256, status; per model: pooled, per family
  and both biology + psychology subsets; predictions)
- `requirements.txt`: a parquet reader only

## Licence

Code is Apache-2.0. This write-up and `results.json` are CC BY 4.0. Upstream: MMLU-Pro (`TIGER-Lab/MMLU-Pro`) is
MIT-licensed; the TIGER-AI-Lab/MMLU-Pro GitHub repository (prediction archives) is Apache-2.0. Authored by AI agents
working in MV2's name (Munim, Inc.).
