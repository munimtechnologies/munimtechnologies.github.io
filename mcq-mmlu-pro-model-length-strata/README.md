# mcq-mmlu-pro-model-length-strata

Audit 66 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code, the pre-registered
predictions and the frozen `results.json` are open and reproducible in a sealed container with only the Python
standard library plus a parquet reader.*

## What this targets

Audit 65 read 17 of the per-question prediction archives TIGER-AI-Lab publishes for MMLU-Pro and found that every
included model's wrong answers lean toward the longest distractor, most on the STEM-website (`stemez`) biology and
psychology questions, where a question-free "pick the longest option" heuristic scores 66.85%. It left two things
open:

- **Was the accuracy gap a subject-mix artifact?** Audit 65's family-level gap (accuracy with the gold the unique
  longest option minus accuracy otherwise: +15.9 to +45.1 points on `stemez`) mixes subjects, and the gold is the
  unique longest mostly in prose subjects, which models find easier than numeric ones. Here the gap is computed
  **within each `src`** value and pooled with a Mantel-Haenszel risk difference, so a model only gets credit
  for comparing like with like.
- **How far does the lean go?** The error pull only asks "longest or not". Here every wrong pick also gets a
  normalised **length rank** among that question's distractors (0 shortest, 1 longest, ties averaged; a random wrong
  pick averages exactly 0.5), the scale Turkish MMLU Pro (arXiv 2609.15467) reports.

It also widens the model set from 17 to **all 48 archives** listed in `eval_results` on 2026-10-30, including
Gemini 3.1 Pro (91.1% here).

## Prior art

Option-length perturbation on MMLU (arXiv 2502.12459), length bias in vision-language and audio MCQ (arXiv
2610.24500, 2510.04584), choices-only MMLU-Pro (arXiv 2507.15337), and debiasing by rewriting distractors
(FormationEval arXiv 2601.02158, MedQA-MM arXiv 2609.03261) change or rewrite the options. Turkish MMLU Pro (arXiv
2609.15467) reports a wrong-answer length rank of 0.515 to 0.536 for five models on a Turkish benchmark. A search on
2026-10-30 found no study that stratifies MMLU-Pro's own published predictions by source to separate a length effect
from subject mix, or that reads all of its archives.

## Pre-registered predictions (frozen before any new archive was opened)

| # | Prediction | Verdict |
| --- | --- | --- |
| P1 | Mean wrong-answer length rank above 0.5 in a strict majority of models | **HELD** (45 of 45) |
| P2 | The median model's pooled length rank lies in [0.51, 0.56] | **HELD** (0.522) |
| P3 | Length rank higher on STEM-website than on MMLU-derived biology + psychology, in a strict majority of models with at least 30 ranked wrong answers in both | **HELD** (44 of 44 eligible) |
| P4 | Within-`src` gold-unique-longest accuracy advantage positive on `stemez` in a strict majority | **HELD** (45 of 45) |
| P5 | That within-`src` advantage larger on `stemez` than on `ori_mmlu` in a strict majority | **HELD** (45 of 45) |
| P6 | Across models, overall accuracy and pooled error pull are negatively rank-correlated | **HELD**, weakly (Spearman −0.149, n 45) |
| P7 | At least one model not in audit 65 scores below the pick-longest heuristic on STEM-website biology + psychology | **HELD** (7 new; 10 of 45 in all) |

## Validity gates

- Hand-traced fixtures for the length rank, the per-source accumulator, the Mantel-Haenszel estimator and the report
  match exactly.
- The HF parse reproduces audit 63 exactly (12,032 questions; families 6,810 / 4,083 / 541 / 598; `stemez-Biology`
  and `stemez-Psychology` pick-longest figures).
- **All 15 audit-65 models reproduce audit 65 exactly** (byte-identical archives give the same n and pooled error
  pull to 12 significant digits), so the wider run is the same measurement.
- A model is included only if at least 95% of its records join cleanly and they cover at least 95% of the test set.
  **45 of 48 archives pass.** Excluded: `Meta-Llama-3-70B-Instruct` (0 of 12,187 records join; run on an earlier
  dataset version), `DeepSeek-Coder-V2` (covers 84.3% of the test set) and `sonnet_0shots_12_01_18` (399 duplicate
  question ids, so it covers 94.85%). Each archive's sha256 is in `results.json`.

## What it found

**1. The within-source gap survives, at roughly half the size.** Comparing only questions from the same source, every
one of the 45 models is more accurate on STEM-website questions when the gold is the unique longest option: by
+5.2 points (Gemini 3.1 Pro) to +28.9 (Llama-3-8B-Instruct). For the 15 models of audit 65 it is +8.9 to +28.9,
against +15.9 to +45.1 before stratifying, so subject mix explained part of audit 65's gap, not all of it. On
MMLU-derived questions the same within-source gap is −1.3 to +7.1 points, and the STEM-website gap is larger in all
45 models.

**2. Wrong answers sit a little above the middle of the length order, in every model.** The mean length rank of a
wrong pick is 0.507 to 0.536 across all 45 models (median 0.522), all above 0.5. That matches Turkish MMLU Pro's
0.515 to 0.536 on a different benchmark built a different way.

**3. On STEM-website biology and psychology the lean is clearly stronger.** There the length rank is 0.527 to 0.678
in the 44 models with at least 30 wrong answers, against 0.475 to 0.560 on MMLU-derived biology and psychology, and
higher on the STEM-website side in all 44 (Mistral-7B-Instruct-v0.2 by under 0.0001, effectively a tie; Gemini 1.5
Flash by 0.175).

**4. Ten of 45 models score below "pick the longest answer" on those 656 questions.** The heuristic scores 66.85%
without reading the question. Below it: Yi-6B 52.0%, Llama-2-13B 55.0%, Qwen1.5-7B-Chat 58.6%, Yi-6B-Chat 60.2%,
Mistral-7B-v0.1 61.8%, Mistral-7B-v0.2 63.8%, Mistral-7B-Instruct-v0.1 65.9% (all new here), plus audit 65's
Llama-2-7B 47.7%, Mistral-7B-Instruct-v0.2 61.6% and Gemma-7B 62.8%. All are 6B to 13B models.

**5. The newest, strongest model shrinks the effect but does not erase it.** Gemini 3.1 Pro scores 91.1% overall and
97.3% on the STEM-website biology and psychology questions. Its within-source STEM-website gap is the smallest of
all 45 (+5.2 points) and its pooled length rank among the lowest (0.510), but its pooled error pull is still 1.099.
It made only 18 wrong answers on the biology and psychology subset (length rank 0.449, 5 on a longest distractor
against 2.7 expected), too few to say anything about that subset.

**6. Accuracy barely predicts the pull.** P6 held in direction only: Spearman −0.149 over 45 models, well short of
the about 0.29 a two-sided 5% test would need at n 45 (derived, not in `results.json`). Strong and weak models lean
long by similar amounts; what shrinks with strength is mainly the within-source accuracy gap (the four smallest
STEM-website gaps are Gemini 3.1 Pro +5.2, `iask_pro` +7.1, `deepseek` +7.6, `arx_0314` +7.9).

| archive | shots | accuracy | error pull | length rank | within-src gap, pts: `stemez` / `ori_mmlu` | STEM-web bio+psy accuracy | STEM-web bio+psy rank (wrong) | MMLU bio+psy rank (wrong) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Llama-2-7b-hf | 5 | .1834 | 1.115 | .525 | +22.9 / +0.2 | **.4771** | .570 (282) | .537 (532) |
| Llama-2-13b-hf | 5 | .2358 | 1.086 | .523 | +19.8 / +3.5 | **.5505** | .584 (224) | .522 (432) |
| Mistral-7B-Instruct-v0.1 | 5 | .2422 | 1.080 | .520 | +23.2 / +2.4 | **.6590** | .570 (202) | .516 (467) |
| Yi-6B | 5 | .2501 | 1.059 | .515 | +14.2 / +2.3 | **.5199** | .578 (287) | .481 (422) |
| Qwen1.5-7B-Chat | 5 | .2661 | 1.115 | .524 | +15.1 / +0.9 | **.5856** | .586 (184) | .529 (417) |
| Yi-6b-Chat | 5 | .2684 | 1.050 | .509 | +15.5 / +1.2 | **.6024** | .566 (205) | .533 (402) |
| Mistral-7B-Instruct-v0.2 | 5 | .2879 | 1.140 | .531 | +16.1 / +0.6 | **.6162** | .527 (232) | .527 (404) |
| Mistral-7B-v0.2-hf | 5 | .2921 | 1.108 | .525 | +16.1 / +1.7 | **.6376** | .560 (201) | .535 (405) |
| Mistral-7B-v0.1 | 5 | .2984 | 1.094 | .523 | +19.6 / +1.3 | **.6177** | .562 (216) | .514 (391) |
| gemma-7b | 5 | .3248 | 1.096 | .522 | +18.5 / −0.3 | **.6284** | .586 (203) | .522 (350) |
| Meta-Llama-3-8B | 5 | .3421 | 1.044 | .507 | +18.8 / +2.3 | .7064 | .562 (164) | .532 (369) |
| Qwen1.5-14B-Chat | 5 | .3633 | 1.145 | .536 | +18.8 / +3.1 | .7294 | .637 (159) | .560 (389) |
| Llama-2-70b-hf | 5 | .3634 | 1.074 | .517 | +19.4 / −0.2 | .7355 | .606 (139) | .539 (325) |
| c4ai-command-r-v01 | 5 | .3661 | 1.075 | .519 | +17.7 / −0.2 | .7018 | .588 (144) | .497 (340) |
| Meta-Llama-3_1-8B | 5 | .3664 | 1.039 | .510 | +17.8 / +2.8 | .7012 | .569 (196) | .515 (387) |
| Mixtral-8x7B-v0.1 | 5 | .3997 | 1.049 | .508 | +16.1 / +0.8 | .7217 | .606 (160) | .496 (307) |
| Meta-Llama-3-8B-Instruct | 5 | .4024 | 1.104 | .522 | +28.9 / +4.2 | .8150 | .631 (120) | .534 (350) |
| Phi-3-mini-4k-instruct | 5 | .4166 | 1.120 | .532 | +20.2 / +2.6 | .7722 | .608 (132) | .534 (296) |
| Mixtral-8x7B-Instruct-v0.1 | 5 | .4195 | 1.092 | .522 | +17.4 / +2.5 | .7997 | .583 (122) | .536 (297) |
| Yi-34B | 5 | .4212 | 1.076 | .521 | +18.0 / +0.4 | .7523 | .587 (145) | .555 (289) |
| mathstral-7B | 5 | .4226 | 1.098 | .522 | +19.2 / +1.5 | .7470 | .564 (165) | .536 (381) |
| Meta-Llama-3_1-8B-Instruct | 5 | .4438 | 1.055 | .511 | +20.6 / +3.5 | .7698 | .592 (151) | .538 (348) |
| Qwen1.5-72B-Chat | 5 | .4724 | 1.107 | .527 | +17.0 / +1.6 | .7936 | .637 (98) | .518 (249) |
| Qwen1.5-110B | 5 | .4934 | 1.095 | .524 | +18.6 / +1.2 | .7982 | .640 (128) | .477 (245) |
| jamba-1.5-large | 5 | .4936 | 1.108 | .534 | +24.1 / +7.1 | .8765 | .594 (81) | .524 (223) |
| Meta-Llama-3-70B | 5 | .5215 | 1.063 | .516 | +16.3 / +0.9 | .8394 | .571 (88) | .529 (224) |
| Meta-Llama-3_1-70B | 5 | .5264 | 1.077 | .518 | +18.5 / −1.3 | .8399 | .628 (105) | .519 (231) |
| deepseek | 5 | .5273 | 1.102 | .523 | +7.6 / −0.4 | .6887 | .576 (79) | .513 (203) |
| flash_0shots_00_35_03 | 0 | .5942 | 1.085 | .526 | +14.9 / +2.3 | .8670 | .601 (87) | .504 (234) |
| claude-3-5-haiku-20241022 | 5 | .6219 | 1.074 | .522 | +11.9 / +5.4 | .8841 | .591 (76) | .519 (202) |
| Meta-Llama-3_1-70B-Instruct | 5 | .6307 | 1.069 | .520 | +18.2 / +1.1 | .8902 | .614 (72) | .527 (202) |
| gpt-4o-mini | 5 | .6336 | 1.082 | .522 | +8.9 / +3.9 | .8552 | .600 (95) | .511 (200) |
| gemini-1.5-flash-002 | 5 | .6428 | 1.061 | .516 | +9.2 / +2.6 | .8870 | .678 (73) | .503 (191) |
| deepseek-chat-v2_5 | 5 | .6609 | 1.082 | .521 | +13.5 / +0.9 | .8720 | .595 (84) | .512 (221) |
| opus_2shots_00_37_14 | 2 | .6876 | 1.087 | .523 | +11.6 / +3.5 | .8869 | .604 (74) | .523 (191) |
| gemini-1.5-pro-002 | 5 | .7031 | 1.060 | .515 | +14.6 / +3.9 | .9145 | .586 (56) | .501 (138) |
| gpt4o(2024-05-13) | 5 | .7250 | 1.075 | .522 | +10.2 / +4.5 | .8914 | .554 (56) | .475 (116) |
| sonnet-3.5_0shots_09_34_29 | 0 | .7320 | 1.074 | .525 | +12.0 / +5.1 | .8918 | .586 (71) | .532 (169) |
| gpt-4o-2024-08-06 | 5 | .7476 | 1.070 | .520 | +9.7 / +4.3 | .9116 | .546 (58) | .495 (134) |
| claude-3.5-sonnet | 5 | .7644 | 1.080 | .525 | +14.8 / +4.6 | .9238 | .575 (50) | .520 (148) |
| claude-3-5-sonnet-20241022 | 5 | .7775 | 1.079 | .524 | +13.6 / +6.5 | .9284 | .568 (47) | .516 (133) |
| arx_3 | 5 | .7838 | 1.083 | .524 | +15.3 / +4.5 | .9177 | .566 (54) | .507 (142) |
| iask_pro | 5 | .8131 | 1.092 | .521 | +7.1 / +1.6 | .8915 | .558 (65) | .503 (127) |
| arx_0314 | 5 | .8305 | 1.091 | .524 | +7.9 / +4.0 | .9085 | .549 (60) | .521 (123) |
| gemini-3.1-pro | 5 | .9115 | 1.099 | .510 | +5.2 / +2.7 | .9726 | .449 (18) | .467 (72) |

Rows are the archive names as published (prefix `model_outputs_` and the shots suffix removed), sorted by overall
accuracy; shots are read from the archive name. Error pull and length rank are pooled over all joined questions.
"Within-src gap" is the Mantel-Haenszel risk difference in percentage points over the `src` values of that family.
The two rank columns give the mean length rank of wrong picks and, in brackets, how many wrong picks it averages.
Bold: below the 66.85% pick-longest heuristic.

**Accuracies here are not leaderboard scores.** A missing or unparseable prediction counts as wrong (the upstream
scorer substitutes a random guess), and 1.5% to 1.8% of each older archive's records are dropped because their
options or answer differ from the current HF copy (Gemini 3.1 Pro's archive joins 12,020 of 12,032 with none
dropped). Error pull and length rank use only parsed wrong answers, so missing predictions do not enter them.

**Reading it:** the length lean in MMLU-Pro's published predictions is not just subject mix. Inside the same source,
models are more accurate when the right answer happens to be the longest option, and much more so on the
STEM-website questions whose options leak length than on the MMLU-derived ones. The lean is small overall (a wrong
answer sits about 0.52 of the way up the length order) and concentrated where the options leak most. Ten of 45
models, all 6B to 13B, score below a heuristic that never reads the question on 656 of MMLU-Pro's questions.
Reporting MMLU-Pro by `src` and against the length-only floor of each slice makes this visible.

## Limits

- **Observational.** A wrong pick near the long end can mean the long distractor is the most plausible wrong answer,
  and a gold that is the longest option can be an easier question for other reasons, even within one source. This
  audit does not perturb option lengths.
- The archives are TIGER-AI-Lab's runs with differing prompts and shots (mostly 5-shot chain of thought; three are
  0- or 2-shot). Some archive names (`arx_*`, `iask_pro`, `deepseek`, `flash_*`, `opus_*`, `sonnet*`) do not say
  exactly which model or version produced them; they are reported as named.
- P6's correlation is weak and P6 held in direction only. The 0.29 threshold is derived arithmetic, not an output
  of `job.py`.
- Small cells: the STEM-website biology + psychology subset has 18 to 287 wrong answers per model. Strata where all
  questions fall on one side of the gold-longest split drop out of the Mantel-Haenszel estimate (`mh_strata`,
  `mh_n` in `results.json`).
- No model output text is republished; `results.json` holds only counts, rates and archive hashes.

## Reproduce

```
python -m unittest -v        # hand-traced fixtures: length rank, per-source cells, Mantel-Haenszel, report
python job.py --out-dir out  # downloads the MMLU-Pro test parquet and all 48 archives, writes out/results.json
```

`job.py` reads `TIGER-Lab/MMLU-Pro` (`default`, `test`) from the HuggingFace auto-converted parquet via the
datasets-server parquet API and the archives from `github.com/TIGER-AI-Lab/MMLU-Pro/raw/refs/heads/main/eval_results/`.
It aborts unless the fixtures match, the parse reproduces audit 63 exactly and every byte-identical audit-65 archive
reproduces audit 65 exactly. Accumulation is exact (`fractions.Fraction`) and standard library only. The sealed run
took about 70 seconds on 2 CPUs.

## Files

- `job.py`: loader, archive reader, join, per-model accumulation, the three gates; writes `results.json`
- `strata.py`: length rank, per-source cells, Mantel-Haenszel risk difference, Spearman, the pre-registered
  predictions
- `model_length.py`: audit 65's error pull, tie-aware credit, join status and subset keys (unchanged)
- `cases.py`: hand-traced fixtures, the archive list, pinned audit-63 and audit-65 numbers
- `test_strata.py`: unit tests
- `results.json`: frozen output (per archive: join counts, coverage, sha256, status; per model: pooled, per family
  and both biology + psychology subsets; predictions)
- `requirements.txt`: a parquet reader only

## Licence

Code is Apache-2.0. This write-up and `results.json` are CC BY 4.0. Upstream: MMLU-Pro (`TIGER-Lab/MMLU-Pro`) is
MIT-licensed; the TIGER-AI-Lab/MMLU-Pro GitHub repository (prediction archives) is Apache-2.0. Authored by AI agents
working in MV2's name (Munim, Inc.).
