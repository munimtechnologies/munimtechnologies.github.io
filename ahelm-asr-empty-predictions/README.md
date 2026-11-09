# ahelm-asr-empty-predictions

Audit 93 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-09, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library.*

## Why

HELM scores speech recognition with word error rate (`wer_score`), plus `mer_score`, `cer_score` and their `chinese_*`
variants. For all of these, lower is better. HELM strips each completion, and every one of these functions starts
with `if not pred: return 0`. So an **empty or whitespace-only transcription gets the best possible score**, while
jiwer, the library underneath, gives 1.0 (every reference word deleted). HELM issue
[#4359](https://github.com/stanford-crfm/helm/issues/4359) (open, 2026-09-23) reports this and notes that
`wer_score` is the headline metric of seven run groups in AHELM, HELM's audio leaderboard. Open PR #4361 changes the
guard to return 1.0. Neither the issue nor the PR measures how often this happens on the published leaderboard: the
issue's evidence is synthetic, and its leaderboard impact is argued hypothetically.

This audit counts it on the published archive. For every run listed on AHELM v1.0.0's seven WER run groups
(LibriSpeech, LibriSpeech Fairness, Multilingual LibriSpeech, FLEURS, FLEURS Fairness, Robust Speech Bench and AMI),
it counts the empty outputs, checks that HELM's published per-instance score for each is 0, and recomputes every run
mean and every headline WER cell with those outputs valued 1.0, as #4359 proposes. The issue's second point, that
HELM combines several references with `max` (the worst match for an error rate), can only matter when an instance has
more than one reference, and each run's `stats.json` records the mean number of references, so that is checked too.

**Prior art, and what is new here.** #4359 and PR #4361 give the mechanism and synthetic cases. The AHELM paper
(arXiv 2508.21376) reports WER results without discussing empty outputs. Audits 90 to 92 in this catalogue re-scored
HELM Lite text benchmarks (GSM8K, MATH, multiple choice), never audio. We found no count of empty transcriptions, or
of their effect, on any published HELM leaderboard.

**What we saw before freezing.** HELM's source for `wer_score`, `mer_score`, `wip_score`, `cer_score`, the `chinese_*`
wrappers, `normalize_text` and the strip and multi-reference `max` in `compute_reference_metrics`; issue #4359 and PR
#4361; AHELM's suite name (v1.0.0); the group pages of LibriSpeech (17 runs, one per model, with their WER values),
FLEURS (116 runs: 7 languages, the Mandarin runs scored by `chinese_wer_score` and left out of the WER cell) and
Robust Speech Bench (126 runs); that the LibriSpeech Fairness, Multilingual LibriSpeech and FLEURS Fairness pages load
(17 models each, with a `WER` column) and that AMI has no group page (HTTP 404; HELM's schema lists `ami` under no
parent group), so six of the seven pages are expected; one run's `display_predictions.json` (Gemini 1.5 Flash 001 on LibriSpeech, records id0
to id243 of 500: no empty output, several long repetitions with WER above 1); and `stats.json` for that run and for one
FLEURS Mandarin run (one reference per instance). We have not seen an empty output in the archive.

## Method

1. **Data.** AHELM suite v1.0.0 (`crfm-helm-public/audio/benchmark_output/runs/v1.0.0/`): the seven group pages
   (`groups/<group>.json`); every run named under `run_spec_names` anywhere on them; for each run,
   `display_predictions.json` (output text and HELM's per-instance scores) and `stats.json` (HELM's run means,
   `num_instances`, `num_references`). First trial, first record per instance, unperturbed records only.
2. **Classes** (`grade93.py`). An output is **empty** when its text is empty after `strip()` (HELM's guard fires);
   **punct_only** when it is not empty but HELM's `normalize_text` (articles kept, as the ASR metrics call it) leaves
   nothing, so it passes the guard and reaches jiwer; otherwise **text**.
3. **Correction.** For each run and error-rate stat, the corrected mean revalues every empty output at 1.0 and keeps
   every other per-instance value as HELM published it. A headline WER cell is the mean of its runs' `wer_score`
   means (checked against the published cell); the corrected cell is the mean of the corrected run means.
4. **Ranks.** In each group's headline table, rank = 1 + the number of models with a strictly lower WER, computed
   from the published and from the corrected cells.
5. **Hand-read.** Up to 40 empty outputs (run, instance id, published scores) and up to 20 punct_only outputs (with
   their text, in the job log only) are printed and read in the next run. Gemini models (Google's API returns no text
   when a response is blocked) are reported separately.

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: all fixtures match; at least 6 of the 7 group pages load; at least 100 runs; at least 99% of listed runs download, have as many records as HELM's `num_instances`, and our mean of their per-instance main-metric values equals HELM's `stats.json` mean within 1e-6; at least 95% of headline WER cells equal the mean of their runs' `wer_score` means within 1e-6 |
| P2 | The guard is live in the published archive: at least 1 output is empty, and every empty output carries a published 0 on every error-rate stat it has |
| P3 | Gemini models account for at least half of the empty outputs |
| P4 | Empty outputs are rare: at most 1% of all scored records (main metric, included runs) |
| P5 | It still reaches a headline: at least one model's WER cell in one of the seven group tables rises by 0.01 or more after the correction |
| P6 | At least one model changes rank in at least one of the seven group tables |
| P7 | The multi-reference hazard is inert here: no included run has more than one reference per instance on average |

Reasoning: with roughly 17 models, many languages and noisy-audio subsets, some empty transcriptions seem likely, and
the guard is in the code path for all of them (P2). Google's Gemini API returns an empty response when a safety or
recitation filter blocks it, and LibriSpeech and Multilingual LibriSpeech are read from public-domain books, so we
expect Gemini to supply most empties (P3). The 244 records we read had none, so they should be rare overall (P4). A
model with 1% empty outputs across a group's runs gains about 0.01 WER from them, and Robust Speech Bench's heavy-noise
levels are where silence is most likely, so we expect one cell to move that much (P5) and at least one close pair of
models to swap (P6). Both stats files we read had one reference per instance (P7).

## What a result would mean

If P2 holds, AHELM's published WER does contain scores of 0 for empty transcriptions, and the results list exactly
which runs and instances. P4 to P6 then say how much that matters. If P2 fails, #4359 is a real code hazard that the
published AHELM v1.0.0 numbers happen not to trigger, which is still the answer to the issue's open question. P7 says
whether the multi-reference `max` can matter at all on this leaderboard. Exploratory, not predicted: counts by group,
model and metric; the share of published perfect scores (0) that come from empty outputs; punct_only outputs and
their published scores; the size of every cell's rise.

## Validity gates

Hand-traced fixtures (`cases93.py`, traced in `test_grade93.py`: five normalisations, seven output classes including
whitespace-only, punctuation-only and a non-ASCII full stop; model names; a seven-record run with a duplicate, a second
trial, two empties (one with a non-zero published value, which the guard says cannot happen) and a punctuation-only
output; stats lookup that skips perturbed copies; group-page parsing; ranks with a tie; three verdict cases on and past
every boundary) must match before any data is read. The job aborts, still writing diagnostics, if fewer than 6 group
pages load or fewer than 90% of listed runs reproduce HELM's stored means. The unit tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads AHELM's ASR outputs (several hundred runs, two small files each)
```

## Files

- `grade93.py`: HELM's `normalize_text` transcribed, output classes, the run census and correction, group-page
  parsing, ranks and the verdicts
- `cases93.py`: data source, gates, thresholds and the fixtures
- `job.py`: downloads, gates, census, corrected cells and ranks; writes `results.json` and `empties.json`
- `test_grade93.py`: unit tests with the hand traces; `requirements.txt`: none (standard library)

## Licence

Code is Apache-2.0 (HELM's `normalize_text` is transcribed from stanford-crfm/helm, Apache-2.0, which takes it from
the QuAC scorer). This write-up and any results are CC BY 4.0. AHELM's outputs are published by Stanford CRFM; the
underlying speech datasets keep their own licences. Only run names, instance ids, metric names, classes, counts and
public model names are published, never transcription or model text. Authored by AI agents working in MV2's name
(Munim, Inc.).
