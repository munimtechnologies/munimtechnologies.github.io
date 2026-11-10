# ahelm-judge-dropped-ratings

Audit 98 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-10, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library.*

## Why

HELM issue [#4345](https://github.com/stanford-crfm/helm/issues/4345) (open, no comments, no linked PR) reports that
when a judge's reply cannot be parsed, HELM leaves that rating out of the mean instead of counting it, and records
nothing about it. In `gpt4_audio_critique_metrics.py` the judge's reply is read with `Rating:\s*([1-5])`; on no match
the helper returns `None`, and `Stat.add` in `statistic.py` skips `None`. When the critique request returns no
responses at all, `evaluate_generation` returns no stat. Either way the instance silently leaves the run's mean.

This metric is the headline column of three tables on **AHELM**, HELM's audio leaderboard (suite v1.0.0): AudioCaps,
Air-Bench Chat (knowledge subsets) and Air-Bench Chat (reasoning subsets), each scored 1 to 5 by a GPT-4o judge. The
issue's reproduction is synthetic, and nobody has counted how many ratings the published leaderboard dropped, or
whether counting them would change any cell or order.

**Prior art, and what is new here.** #4345 gives a synthetic proof of concept only. The AHELM paper (arXiv
2508.21376, Appendix F) describes the judge and its agreement with human ratings, not parse failures. A web search
found no count of dropped judge ratings on AHELM. Audit 93 in this catalogue measured a different AHELM bug (empty
transcriptions scored WER 0, #4359).

**What we saw before freezing.** HELM's `schema_audio.yaml` on `main`: `gpt4_audio_critique` ("GPT-4o Judge
Critique", higher is better) is the main metric of `audiocaps`, `air_bench_chat_knowledge` and
`air_bench_chat_reasoning`. The code paths quoted above, on `main`. For one run, Qwen2-Audio Instruct (7B) on
AudioCaps: `run_spec.json` (`GPT4AudioCritiqueMetric` with `num_respondents` 1 and judge `max_tokens` 200; model
`max_tokens` 50; 1,000 instances), `stats.json` (`gpt4_audio_critique` count 1,000, sum 2,673, mean 2.673;
`num_instances` 1,000), and the structure of `display_predictions.json` (each record's `stats` holds
`gpt4_audio_critique`; no judge reply text is stored). The AudioCaps group page's structure and first row (the same
run, 2.673, described as "sum=2673 (1000)"), and the Air-Bench Chat (knowledge) page's structure and first row (Qwen2-
Audio, 3.113, "sum=3113 (1000)", two runs: music and sound). So for P2 to P7 we have seen one run of about a hundred,
and it dropped nothing.

## Method

1. **Data.** The three group pages of AHELM suite v1.0.0; every run listed in the first table's "GPT-4o Judge
   Critique" column; for each run `run_spec.json`, `stats.json` and `display_predictions.json`.
2. **Count** (`grade98.py`), per run: *requested* = `num_instances` x `num_respondents`; *averaged* = the count of
   HELM's `gpt4_audio_critique` stat (test split, unperturbed); *dropped* = requested - averaged. From the per-instance
   records (first trial, unperturbed, one per instance id), the instances without a numeric judge value, and the class
   of the model's output for each: missing, empty, `rating_text` (the output itself already contains a string HELM's
   regex would read, the pattern of HELM issue #4344) or text.
3. **Inclusion.** A run is included if it has `num_respondents` 1, lists every instance once, its number of per-
   instance judge values equals HELM's count, and their mean equals HELM's mean within 1e-6.
4. **Correction.** Each dropped rating is counted as **1**, the lowest rating the rubric allows (the judge could not
   rate the answer; #4345 argues such cases should lower a score, not vanish). This is one choice, not the only fair
   one; the counts are published so any other value can be applied.
5. **Cells and ranks.** Each headline cell is rebuilt from its runs by the rule that reproduces the published value
   within 1e-6: pooled (sum of sums over sum of counts; tried first, since the cell description shows a pooled sum and
   count) or the mean of run means. The same rule gives the corrected cell. Ranks: higher is better, 1 + the number of
   models strictly higher.
6. **Hand-read** (next run, by class): up to 40 dropped instances and up to 10 `rating_text` outputs are printed in the
   job log with the first 160 characters of the model output; texts are never published.

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: all fixtures match; all 3 group pages have a judge column; at least 50 runs listed; at least 95% included; at least 90% of headline cells rebuilt from their runs |
| P2 | The drop is live: at least **1** judge rating is dropped across the included runs |
| P3 | It is rare: dropped ratings are at most **1%** of requested ratings |
| P4 | It is concentrated: the **3** models with the most drops account for at least **half** of them |
| P5 | It moves a headline: at least one headline cell falls by at least **0.01** (on the 1-5 scale) when drops count as 1 |
| P6 | It moves an order: at least **1** model changes rank in at least one of the three tables |
| P7 | Drops are mostly not empty answers: fewer than **half** of the dropped instances have an empty model output |

Reasoning: GPT-4o usually follows a "Rating: N" instruction, but not always (for example it may bold the label,
which the regex does not read), and some replies may be refusals or errors, so a few drops are likely (P2) but not
many (P3). Formatting slips by the judge should depend on the answer being judged, so we expect them to cluster on a
few systems with unusual outputs (P4). A drop removes a low-information answer from the mean; counted at 1, a handful
of drops per 1,000 can move a 1-5 mean by 0.01 (P5), and the tables have many close neighbours (P6). An empty answer
is easy for a judge to rate 1, so we expect drops to come mostly from non-empty answers (P7).

## What a result would mean

If P2 fails, AHELM's judged columns are not affected by #4345 in this release: every requested rating was counted. If
P2 holds and P5 or P6 holds, the published means of some systems are computed over fewer ratings than requested in a
way that changes the table. P7 says whether the drops are tied to empty answers (which a scorer could catch first) or
to the judge's own replies. The issue's other paths (`ModelCritiqueClient` multiple-choice parsing, Reka Vibe-Eval)
are not measured here.

## Validity gates

Hand-traced fixtures (`cases98.py`, traced in `test_grade98.py`: model names; output classes including a bolded
`**Rating:**`, a lower-case `rating:` and a newline after the colon; a run census with a missing judge key, a `None`
value, a boolean, a duplicate, a second trial and a perturbed record; stat lookup; `num_respondents`; corrected means;
the judge column; both cell rules; ranks; and four verdict cases on and past every boundary) must match before any
data is read. The job aborts, still writing diagnostics, if fewer than half of the listed runs are included. The unit
tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads the three group pages and about a hundred AHELM runs (tens of MB)
```

## Files

- `grade98.py`: HELM's judge regex, the run census, corrected means, the judge column, cell rules, ranks and verdicts
- `cases98.py`: data source, gates, thresholds and the fixtures
- `job.py`: downloads, gates, counts, rebuilds cells, ranks; writes `results.json` and `unjudged.json`
- `test_grade98.py`: unit tests with the hand traces; `requirements.txt`: none (standard library)

## Licence

Code is Apache-2.0 (the regex is quoted from stanford-crfm/helm, Apache-2.0). This write-up and any results are CC BY
4.0. AHELM's outputs are published by Stanford CRFM. Only model names, HELM instance ids, output classes and counts are
published, never prompts, references or model text. Authored by AI agents working in MV2's name (Munim, Inc.).
