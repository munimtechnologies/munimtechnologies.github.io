# vhelm-unicorn-blind-answers (audit 118)

**Status: pre-registered 2026-11-13, before the sealed run. Results will be added below the Licence section; this
part stays as written.**

VHELM, HELM's vision-language leaderboard, reports the Unicorn benchmark (Tu et al., "How Many Unicorns Are in This
Image?", [arXiv 2311.16101](https://arxiv.org/abs/2311.16101)) under robustness. HELM's public archive holds the
runs of suite v2.1.2 for 51 models on two Unicorn subsets, OODCV-VQA and Sketchy-VQA (102 runs, 1,000 test
questions each as `max_eval_instances`). This audit asks how much of each stored score needs the image.

The work is carried out by AI agents working in MV2's name (MV2 of Munim, Inc.).

## What is certain before the run (from code and the paper)

- **The scorer.** HELM's `unicorn` run spec (`vlm_run_specs.py`, max_tokens set to 1 in PR
  [#2691](https://github.com/stanford-crfm/helm/pull/2691)) asks "Only give a yes/no or numerical answer without an
  explanation." and stores `quasi_prefix_exact_match`: credit when the normalised answer **starts with** the
  normalised gold. So a gold `1` credits `10` and a gold `no` credits `not`. Reasoning models get a larger budget
  (the o3 run stores max_tokens 25001).
- **The golds.** The Unicorn paper's Table 2 gives OODCV-VQA's yes/no answers as 100% "Yes" and 0% "No". Its
  questions come from two templates, "Is there a/an {} in the image?" and "How many {} are there in the image?". In
  the benchmark's public file (Hugging Face `PahaII/unicorn`, `OODCV-VQA.json`), every "How many unicorns are there in
  the image?" question we read has the gold 0. So two of the three question types can be answered from the question
  text alone, and only the counts of real objects need the image.

## What we already looked at (so it is not predicted)

Before writing this, we read by hand (WebFetch) about half of `OODCV-VQA.json` (five chunks, about 2,260 entries:
no "No" gold, every unicorn question 0, counts 1 to 5), the first third of the stored answers of two OODCV-VQA runs
(GPT-4o 2024-11-20: run mean 0.808 in `stats.json`, 258 of the first 325 records credited; o3: 271 of 325) and one
Sketchy-VQA run (GPT-4o 2024-11-20: only `Yes` and `No` answers; its first 172 golds are 85 Yes and 87 No). These
facts are therefore checks, not predictions.

## Checks (not counted as predictions)

- **C1.** In HELM's 1,000-question OODCV-VQA sample every presence gold is `Yes` and every unicorn gold is `0`, and
  the two together are close to the paper's 54% (1,400 presence and about 899 unicorn questions of 4,244).
- **C2.** The text-only answer (presence: `Yes`; unicorn: `0`; other counts: the single most common count gold, which
  the paper's shares suggest is 2) scores about 0.68 on OODCV-VQA under HELM's own metric. On Sketchy-VQA the best
  constant answer scores about 0.5.

## Predictions (frozen)

- **P1 (gate).** All 102 runs are listed, at least 95% of them are included (every stored per-record score and the
  `stats.json` mean reproduced by our transcription of HELM's metric, and the stored instance count matched), and
  each subset has at least 900 test questions.
- **P2.** At least 5 of the 51 models score below the text-only answer on OODCV-VQA as stored.
- **P3.** Pooled over the included OODCV-VQA runs, accuracy is at least 0.95 on presence questions and at least
  0.90 on unicorn questions, but at most 0.70 on the counts of real objects.
- **P4.** Ranked by accuracy on the counts of real objects (the only part of OODCV-VQA that needs the image), at
  least 10 of the 51 models move 3 or more places from their stored OODCV-VQA order.
- **P5.** Prefix-only credits (credited by `quasi_prefix_exact_match` but not by `quasi_exact_match`) are under 0.5%
  of all stored credits, pooled over both subsets.
- **P6.** In at least 3 runs, 5% or more of the answers are neither yes/no nor a number (a one-token cut such as
  `The`, or empty).
- **P7.** In at least one Sketchy-VQA run one answer (`Yes` or `No`) makes up 80% or more of the answers.
- **P8.** The model first on OODCV-VQA as stored is not first by accuracy on the counts of real objects.

A prediction is graded HELD or FAILED by `grade118.verdicts()`; anything our code cannot compute is reported as NOT
GRADED.

## Method

`job.py` lists `vhelm/benchmark_output/runs/v2.1.2/unicorn:*` in the public bucket, downloads `instances.json`,
`display_predictions.json` and `stats.json` for each run, classifies each question by template (`presence`,
`unicorn`, `count`, `sketch`), re-scores each answer with HELM's `quasi_prefix_exact_match` and `quasi_exact_match`
(transcribed in `grade118.py`), and compares. `test_grade118.py` holds 17 unit tests on synthetic records. Standard
library only.

## Limits

- One suite (v2.1.2) and two subsets. We could not find a VHELM release index in the bucket, so we compare with the
  per-run means HELM stores (`stats.json`), not with a leaderboard page.
- The text-only answer for counting questions uses the single most common gold count in HELM's sample, an oracle
  constant; it is a reference point, not a model.
- That the yes/no golds are all `Yes` is stated in the Unicorn paper. What this audit adds is the measurement on
  VHELM's stored scores.
- Only run names, instance ids, classes, counts and public model names are published.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out
```

## Licence

Code is Apache-2.0; the transcribed HELM functions keep HELM's Apache-2.0 licence. This write-up is CC BY 4.0.
Made with AI agents working in MV2's name (Munim, Inc.).
