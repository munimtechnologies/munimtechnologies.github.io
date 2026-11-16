# helm-msmarco-post-stop-ranking

Audit 125 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered 2026-11-16, before the sealed run. Results will be added below the Licence section; this
part stays as written.**

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library.*

## Why

Audit 104 ([helm-boolq-post-stop-calibration](../helm-boolq-post-stop-calibration/)) found that in HELM Classic
release v0.4.0, **21 of the 54 BoolQ adapters with a calibration score** store a token list and a summed log
probability that run past the newline at which the scored answer was cut. Audit 124
([helm-classic-post-stop-calibration](../helm-classic-post-stop-calibration/), queued) measures the same thing on
IMDB, CivilComments and RAFT calibration.

HELM Classic's **MS MARCO** passage ranking uses that log probability directly, not only for calibration. Each
passage is asked about in its own prompt (`Does the passage answer the query?` / `Answer:`), and HELM's
`RankingMetric` (v0.3.0, `metrics/ranking_metrics.py`) orders a query's passages by the **first completion's stored
log probability**: answers "Yes" first, most probable first; then answers "No", least probable first; then anything
else. The run spec allows **5 output tokens** with the stop sequence `"\n"`, exactly as BoolQ. So for an adapter whose
provider returned tokens past the newline, a passage's ranking score is the probability of " Yes" **times** the
probability of the newlines and the start of the next "Passage:" that the model would write after it. The published
**RR@10** (MS MARCO regular track) then partly ranks passages by how predictable the prompt's next line is.

This audit rebuilds every published regular-track RR@10 from the stored per-passage values, then re-ranks with each
passage's log probability cut where its tokens reach the stop.

**Prior art.** HELM's issues and PRs searched for `msmarco` on 2026-11-16 (35 results; the 25 on page 1 read by
title: scenario, metric plumbing, file sizes, #1155 "Hide stats for MSMARCO/calibration for AI21/Anthropic" and
#1601 on `ref*_rank` stats). None is about tokens past the stop. A web search found no report of this mechanism in
HELM or any other ranking evaluation. Audit 104's search
(`truncate_sequence`, "calibration logprob stop", issue #1828, olmo-eval PR #294) is unchanged.

## What we already looked at (so it is not predicted)

- **Audit 104's results** (BoolQ): the overrun adapters there include the five Together-served adapters that also have
  MS MARCO runs (BLOOM, GPT-J 6B, GPT-NeoX 20B, OPT 175B, OPT 66B); every AI21, Cohere, OpenAI, Microsoft and
  Anthropic BoolQ adapter was `clean`. The median overrun record's excess was -0.163 nats.
- **HELM v0.3.0 code**: `metrics/ranking_metrics.py` (described above; RR@10 = pytrec_eval `recip_rank` on the run cut
  to its top 10; "(topk=30)" stats keep only passages whose BM25 rank tag is at most 30), `metrics/metric.py` (a
  query's passage requests are evaluated together per trial, in reference order; the per-trial mean is merged once
  per trial), `scenarios/scenario.py` (`relevance=N`, `rank=N` tags) and `scenarios/msmarco_scenario.py` (the
  candidates are the BM25 top 30 **plus every judged passage**, so a gold passage outside BM25's top 30 is still a
  candidate, with no rank tag); `common_adapter_specs.py` (`get_ranking_binary_adapter_spec`, 5 tokens).
- **One run's files** (`msmarco:track=regular,valid_topk=30,model=together_gpt-j-6b`, suite v0.3.0): `run_spec.json`
  (method `ranking_binary`, `max_tokens` 5, `stop_sequences` `["\n"]`, temperature 0, 1 output, 2 in-context
  examples); `stats.json` (RR@10 0.15220, count 3 = trials; RR@10 (topk=30) 0.08664); the object sizes
  (`scenario_state.json` 71 MB). **We have not opened any `scenario_state.json`, `per_instance_stats.json` or
  `display_predictions.json` of any MS MARCO run**, so no token list, log probability or ranking has been seen.
- **The release index and group page**: `runs_to_run_suites.json` lists 31 canonical regular-track runs (suite
  v0.3.0; 7 AI21, 1 Anthropic, 7 Cohere, 2 Microsoft, 9 OpenAI, 5 Together); `groups/msmarco_regular.json` shows
  an RR@10 for 30 of them (Cohere Command beta 52.4B leads at 0.4721; GPT-J 0.1522, GPT-NeoX 0.1837, BLOOM 0.2362,
  OPT 66B 0.2371, OPT 175B 0.2878), the Anthropic row without a value.

## Method

1. **Data.** HELM Classic release v0.4.0: `runs_to_run_suites.json`, `groups/msmarco_regular.json`, and for each
   canonical `msmarco:track=regular` run `scenario_state.json` (prompts, passage texts, instance inputs and top log
   probabilities are dropped while parsing) and `stats.json`. About 31 x 71 MB are streamed; nothing is stored.
2. **Per passage request** (`grade125.py`; unperturbed valid-split requests, every trial; the first request per
   (instance, trial, reference)): text and stored log probability of the **first** completion (HELM's
   `get_model_output_logprob`; `missing` / 0.0 without one), the reference's gold / relevance / rank tags as HELM
   reads them, and the **answer-only log probability**: the sum over the tokens before the first one whose decoded
   text reaches a stop sequence (the stored value when no token is past the stop). Token strings are decoded as
   GPT-2 byte-level BPE, SentencePiece or AI21 (`<|newline|>`), as in audit 104. **overrun** = tokens past the stop;
   **excess** = stored minus answer-only log probability; **consistent** = the kept tokens decode to the stored text.
3. **Per query and trial**: HELM's order (stable descending sort on (2, lp) for "yes", (1, -lp) for "no", (0, -lp)
   otherwise, on the stripped lower-cased text), once with the stored and once with the answer-only log probability;
   RR@10 = 1 / position of the first passage with relevance at least 1 among the top 10 (0 if none), on all
   candidates and on the BM25 top 30 only.
4. **Run values**: mean over queries per trial, then mean over trials (HELM's merge). **Inclusion**: a run is
   included if our stored-value RR@10 and RR@10 (topk=30) both equal `stats.json` within 1e-9 with the same trial
   count.
5. **Run class**: `overrun` if at least half of a run's passage records have tokens past the stop, else `clean`.
6. **Cells and ranks**: one cell per adapter (one run each). Published cells are checked by matching each stored-value
   cell to a distinct published "RR@10" value within 1e-9. Ranks: higher RR@10 is better, 1 + the number strictly
   higher. Delta = RR@10(answer-only) - RR@10(stored). Movers = adapters whose rank changes by 3 or more places.
7. **Hand-read** (next run): one overrun record from up to 3 runs, chosen by a stable hash, is printed in the job log
   with its text and tokens; texts are never published.

Also reported, not predicted: queries whose RR@10 changes in clean runs (expected 0, a check of the method), queries
whose first gold passage moves, queries with a gold passage outside the BM25 top 30, stored log probabilities that
differ from their token sum, and RR@10 (topk=30) under both scores.

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: all fixtures match; at least 90% of the listed regular-track runs are included; at least 90% of the published RR@10 cells match one of ours within 1e-9 |
| P2 | The `overrun` adapters are **exactly** the five Together-served ones (BLOOM, GPT-J 6B, GPT-NeoX 20B, OPT 175B, OPT 66B) |
| P3 | Pooled over the overrun adapters, the median overrun record's excess is at most **-0.1** nats |
| P4 | In at least **half** of the overrun adapters, RR@10 changes by at least **0.01** when the answer-only log probability replaces the stored one |
| P5 | Method check: in overrun adapters, the kept tokens decode to the stored text on at least **95%** of overrun records |
| P6 | Among overrun adapters whose RR@10 changes by at least 0.01, more get **better** (higher) than worse |
| P7 | At least **one** adapter moves **3 or more** places in the 31-row RR@10 ranking |
| P8 | In the overrun adapters, RR@10 changes on at least **10%** of (query, trial) rankings |

Reasoning: MS MARCO uses the same clients, stop and token limit as BoolQ, so the same adapters should run past the
stop (P2, the prediction closest to a structural expectation; it fails if any AI21, Cohere, OpenAI, Microsoft or
Anthropic run is overrun, or one of the five is not), with a similar excess (P3). The text after the answer is the
same for every passage of a query ("\n\nPassage:"), but its probability still varies from prompt to prompt; where
two "Yes" passages are close, that variation re-orders them, so some query rankings should change (P8) and a few
adapters' RR@10 should move by a point (P4). The published column is tightly packed (GPT-J 0.1522 is within 0.01 of
five other cells), so a one-point change can move an adapter three places (P7). If the post-stop tokens are noise
unrelated to relevance, removing them should help more often than hurt (P6); this is the prediction we are least
sure of, because a model may also be more likely to end its answer cleanly after a passage it finds relevant.

## What a result would mean

If P4 and P8 hold, HELM Classic's MS MARCO RR@10 for the overrun adapters partly ranks passages by the probability
of text the model writes after its answer, and the answer-only RR@10 is a like-for-like alternative. If P8 holds but
P4 fails, the mechanism re-orders passages but averages out in the column. If P8 fails, the post-stop text is too
uniform within a query to matter for ranking, even where it distorts calibration. Only the regular track in one
release is measured; the TREC track (graded relevance, NDCG@10) uses the same ranking and is not measured here.

## Validity gates

Hand-traced fixtures (`cases125.py`, traced in `test_grade125.py`): token decoding and stop trimming (audit 104's);
the first-completion pick, including a missing result; the answer-only log probability (overrun, clean, missing,
inconsistent, newline first, no stops); reference tags; HELM's score key and a tie that a descending stable sort
must keep in reference order; RR@k with and without the BM25 filter; a three-query run census whose first query
changes RR@10 from 1.0 to 0.5 when the post-stop tokens are removed, a query whose gold passage is outside the BM25
top 30, a missing completion, a stored value that differs from its token sum, and a perturbed, a train-split, an
unindexed and a duplicate request; trial means; run names; the stats lookup; the parsing hook; ranks; Kendall tau-b;
cell matching; the group column; medians; and two verdict cases on and past every boundary. They must match before
any data is read. The 13 unit tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads the release index, the group page and 31 runs (about 2.2 GB, streamed)
```

## Files

- `grade125.py`: token decoding, stop trimming, the first completion, the answer-only log probability, reference
  tags, HELM's binary ranking and RR@k (transcribed), the run census, trial means, run names, ranks, Kendall tau-b
  and verdicts
- `cases125.py`: data source, thresholds and the fixtures (all invented)
- `job.py`: downloads, gates, re-ranks, classes, rebuilds cells, ranks; writes `results.json`
- `test_grade125.py`: unit tests with the hand traces; `requirements.txt`: none (standard library)

## Licence

Code is Apache-2.0. HELM's ranking logic (`RankingMetric`) is transcribed from stanford-crfm/helm (Apache-2.0);
pytrec_eval's `recip_rank` is re-implemented from its definition, and GPT-2's byte table follows openai/gpt-2 (MIT).
This write-up and any results are CC BY 4.0. HELM Classic's outputs are published by Stanford CRFM; MS MARCO is
Microsoft's. Only run names, model names, counts, classes and numbers are published, never queries, passages or model
text. Authored by AI agents working in MV2's name (Munim, Inc.).
