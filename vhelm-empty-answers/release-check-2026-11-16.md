# Audit 123: release check (2026-11-16, after pre-registration, before the sealed run)

This note answers a limit the pre-registration left open ("we did not check whether VHELM's current leaderboard shows
the thinking-64k model"). It was read by hand (WebFetch) from HELM's public files and code. It changes no prediction
and is not counted as one. The pre-registered README is unchanged.

The work is carried out by AI agents working in MV2's name (MV2 of Munim, Inc.).

## What we read

- **The live leaderboard is suite v2.1.2.** `crfm.stanford.edu/helm/vhelm/latest/config.js` sets the suite to v2.1.2
  and loads results from `crfm-helm-public/vhelm/benchmark_output/`. The suite's `summary.json` is dated 2025-05-01.
- **The published tables list 48 models; 51 have runs.** The group tables `groups/toxicity.json` and
  `groups/vibe_eval.json` of suite v2.1.2 each have 48 model rows. Neither has a row for **Claude 3.7 Sonnet
  (2025-02-19)**, **Claude 3.7 Sonnet (thinking, 64k)** or **Gemini 2.0 Flash Thinking (01-21)**, though all three have
  run folders in the same suite (for example `blink:category=Counting,...` lists all three). So the all-empty
  thinking-64k runs are public as files but are **not part of the published leaderboard**.
- **Why that model's answers are empty, as stored.** In the thinking-64k BLINK Counting run (`max_tokens` 1) and
  Vibe-Eval normal run (`max_tokens` 100), every request state read stores `success: false`, the error
  `Anthropic response has empty content`, `is_retriable: false`, `is_fatal: false`, and an empty completion
  (BLINK Counting: every record in the part of `scenario_state.json` read; Vibe-Eval normal: 33 of the 33 records
  read, 0 successes). HELM's client returns such a failure as a non-fatal empty result, and the metrics then score it like an
  answer: the Vibe-Eval run's stored `prometheus_vision` mean is 2.0237 over 169 records, with `num_output_tokens` 0 and
  `finish_reason_unknown` 1.0.
- **The deployment is not in HELM's code.** HELM's current `model_deployments.yaml` defines Claude 3.7 Sonnet thinking
  only as `thinking-10k` (`thinking_budget_tokens: 10000`, `stream: true`), added in PR #3622 (merged 2025-05-28; PR #3640
  is titled "Use 10k default budget tokens for Claude extended thinking"). We found no `thinking-64k` entry, so the VHELM runs used a configuration that is not in the
  repository, and its exact budget is not public.
- **HELM Capabilities does not have this problem.** Its thinking-10k runs (for example Claude Sonnet 4 thinking-10k
  on MMLU-Pro, run folder v1.6.0) set `max_tokens` to 14,096, above the 10,000 budget, and store a mean of 325.194 output
  tokens and a chain-of-thought correctness of 0.843.

## What this changes

- The thinking-64k finding is a **stored-files** finding, not a leaderboard one: HELM appears to have left these three
  models out of the published v2.1.2 tables. We make no claim about why.
- The two questions that matter for the published leaderboard stay open and are what the sealed run measures: how
  many empty answers the **48 published** models store, and what the Prometheus-Vision judge gives them (the judge
  scored 70 of Bingo OCR's 146 empty answers 5 in the unpublished run).
- Audits 118 to 122 also count over the 51 models that have runs. Their per-run results stand, but rank statements
  such as "above 15 of 51 models" include these three unpublished models.

## Licence

This note is CC BY 4.0. Made with AI agents working in MV2's name (Munim, Inc.).
