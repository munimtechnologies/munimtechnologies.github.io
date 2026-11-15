# vhelm-empty-answers (audit 123)

**Status: pre-registered 2026-11-15, before the sealed run. Results will be added below the Licence section; this
part stays as written.**

VHELM, HELM's vision-language leaderboard, stores every answer of its run suite v2.1.2 (51 models) in HELM's public
bucket. Audit 118 found that on VHELM's Unicorn runs six Claude models store an empty answer on nearly every number
question, and two "thinking" models on every question. This audit counts empty answers across **every run of the
suite**, and asks what the metrics give an empty answer, in particular the Prometheus-Vision judge that scores VHELM's
open-ended scenarios (Bingo, Vibe-Eval, Mementos, Crossmodal-3600, Flickr30k) from 1 to 5.

The work is carried out by AI agents working in MV2's name (MV2 of Munim, Inc.).

## What we already looked at (so it is not predicted)

Before writing this, we read by hand (WebFetch):

- **Code.** HELM's `vlm_run_specs.py`: the answer budgets are 1 token (multiple-choice joint, Unicorn, BLINK,
  MM-Star), 20 (short answers), 100 (Bingo, Mementos, Vibe-Eval) and up to 2,000 (image-to-code). HELM's
  `anthropic_client.py`: when a deployment has a thinking budget, the request gets
  `thinking: {"type": "enabled", "budget_tokens": ...}` and keeps the run spec's `max_tokens`; a response with no text
  block becomes a failed, empty result. Anthropic's extended-thinking documentation says `budget_tokens` must be at
  least 1,024 and **less than `max_tokens`**. So a 64k thinking budget under a 1 to 2,000-token answer budget is a
  request the API should refuse. We did not check HELM's deployment settings for this model or its request logs, so
  this cause is likely, not proven.
- **Runs of Claude 3.7 Sonnet (thinking, 64k)**: BLINK Counting, all 120 answers empty; Bingo OCR, all 146 empty;
  Vibe-Eval (normal), all 169 empty; VQAv2 (`vqa_base`), the first 332 records read are all empty and `stats.json`
  stores 0 output tokens and `finish_reason_unknown` 1.0; Unicorn (audit 118), all 2,000 empty.
- **The judge on those empty answers**: Bingo OCR scores the 146 empty answers 1 (74 times), 3 (2) and **5 (70)**,
  mean 2.945, which is the run's stored `prometheus_vision` mean; Vibe-Eval (normal) scores its 169 empty answers
  1 (108), 2 (10), 3 (19), 4 (3) and 5 (29), mean 2.02.
- **Other runs**: Claude 3 Haiku and Gemini 2.0 Flash Thinking each answer all 120 BLINK Counting questions with a
  letter (0 empty); Gemini 2.0 Flash Thinking is empty on all 2,000 Unicorn questions (audit 118).
- **Prior art.** HELM's issues and PRs have no report on `thinking-64k` (0 results), and none on the Prometheus judge
  scoring empty answers (2 results for `prometheus`, both 2024 PRs adding it). Close relatives: HELM issue #4359 and
  our audit 93 (an empty transcription scored as a perfect WER), PR #2471 (empty completions for Claude
  content-filter blocks), issue #582 (2022, an Anthropic model returning only empty completions on
  RealToxicityPrompts). A web search found no write-up of empty answers on VHELM.

## Checks (not counted as predictions)

- **C1.** The runs listed above are empty as read.
- **C2.** For every judge-scored run, our mean of the per-record `prometheus_vision` scores reproduces the stored
  `stats.json` mean (so empty answers are part of the published cell).

## Predictions (frozen)

"Empty" means a blank `predicted_text` after stripping whitespace; only unperturbed records count.

- **P1 (gate).** At least 2,000 runs are listed, and at least 95% of them have a readable `display_predictions.json`.
- **P2.** Claude 3.7 Sonnet (thinking, 64k) stores an empty answer on at least 99% of its records, pooled over at
  least 30 runs.
- **P3.** Every other model stores an empty answer on less than 50% of its records.
- **P4.** Gemini 2.0 Flash Thinking has at least one run outside Unicorn where 50% or more answers are empty.
- **P5.** For the six other Claude models (3 Haiku, 3 Sonnet, 3 Opus, 3.5 Sonnet 2024-06-20 and 2024-10-22, 3.7
  Sonnet), at least 80% of their empty answers are in Unicorn runs.
- **P6.** Pooled over every judge-scored empty answer, the Prometheus-Vision mean is at least 2.0 (of 5) and at least
  20% of them score 5.
- **P7.** In at least one judge-scored run group (the same scenario and subset), a run with 95% or more empty answers
  has a higher judge mean than a run of another model with 5% or fewer empty answers.
- **P8.** At least 10 models have at least one run with 5% or more empty answers.

A prediction is graded HELD or FAILED by `grade123.verdicts()`; anything our code cannot compute is reported as NOT
GRADED. Also reported, without predictions: empty answers per model and scenario, the mean each stored metric gives
empty answers in each scenario, and where each all-empty run ranks in its judge-scored group.

## Method

`job.py` lists every run of `vhelm/benchmark_output/runs/v2.1.2/` in the public bucket, downloads each run's
`display_predictions.json` (and, for judge-scored runs, `stats.json`), and summarises it with `grade123.py`.
`test_grade123.py` holds 11 unit tests on synthetic records. Standard library only.

## Limits

- One suite (v2.1.2). We compare with the per-run means HELM stores, not with a leaderboard page, and we did not check
  whether VHELM's current leaderboard shows the thinking-64k model.
- An empty answer can have several causes (a refused request, a content-filter block, a one-token limit). We count
  them; we read the cause only where the code and documentation above show it.
- Only run names, counts, metric names and public model names are published; no model text.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out
```

## Licence

Code is Apache-2.0. This write-up is CC BY 4.0. Made with AI agents working in MV2's name (Munim, Inc.).
