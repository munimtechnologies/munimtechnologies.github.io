# helm-boolq-post-stop-calibration

Audit 104 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-11, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library.*

## Why

HELM Classic (release v0.4.0) publishes an "ECE (10-bin)" calibration column for BoolQ (and for its other core
scenarios). The confidence behind it is `max_prob = exp(logprob of the top completion)` (`basic_metrics.py`), and
the ECE is the equal-mass 10-bin expected calibration error of `max_prob` against `exact_match`
(`uncertainty-calibration`'s `get_ece_em`), computed once per trial over the unperturbed records and then averaged
over trials.

Some providers of the time return the answer **text** already cut at the stop sequence (`"\n"`) but a **token list
and summed log probability that run past it** up to `max_tokens` (BoolQ asks for at most 5 tokens), e.g. text
`" Yes"` with tokens `" Yes"`, newline, newline, `"Pass"`, `"age"`. HELM's client-side `truncate_sequence` leaves such
a completion unchanged: the returned text has no stop sequence left to find, and byte-level token strings (`"Ċ"` for a
newline) do not start with `"\n"`. If so, the confidence that enters ECE is the probability of the answer **and** of
the tokens generated after it, not of the answer that was scored.

**Prior art, and what is new here.** HELM's issues and PRs searched on 2026-11-11 for `truncate_sequence` (13
results, none about this) and for "calibration logprob stop" (4 results). The response pasted in issue #1828 (2023,
about Together's response format) happens to show the pattern (text `'wolf'`, tokens `'▁w', 'olf', '<0x0A>',
'<0x0A>', 'Pass'`), but nobody raised it there and no issue or paper we found measures its effect on any published
number. allenai/olmo-eval PR #294 (2026) fixed a related per-token stop-matching bug in another harness. A web search
found no count of HELM Classic completions whose log probability includes post-stop tokens, and no re-computed
calibration column.

**What we saw before freezing.** The code above (HELM v0.3.0 `together_client.py`, `client.py`, `basic_metrics.py`,
`metric.py`; `uncertainty-calibration`'s `utils.py`). The BoolQ group page (`groups/boolq.json`): the "ECE (10-bin)"
column (OPT 175B 0.194, GPT-J 6B 0.062), and "# output tokens" of exactly 5.0 for 13 adapters (BLOOM, T0pp, GPT-J,
GPT-NeoX, Pythia 6.9B and 12B, T5, UL2, OPT 175B and 66B, LLaMA 7B, 13B and 30B), about 2.0 for the seven AI21
adapters and about 1.0 for the rest we could read. `runs_to_run_suites.json` lists 66 canonical BoolQ runs (suite
v0.3.0). For **RAFT** (not BoolQ), `ade_corpus_v2` with OPT 175B: the first five test records have stop-free texts but
9 to 13 tokens running past the newline, the stored log probability equals the sum over all of them, and record
`id10` has stored `max_prob` 0.0015 (= exp(-6.51)) while scored correct. We have not opened any BoolQ
`scenario_state.json` or per-instance file, computed any ECE, or counted any overrun on BoolQ. Because of the
"# output tokens" column, P2 is close to a structural expectation; the other predictions are not.

## Method

1. **Data.** HELM Classic release v0.4.0: `runs_to_run_suites.json`, the BoolQ group page, and for each of the 66
   canonical BoolQ runs `scenario_state.json` (prompts, inputs and top log probabilities are dropped while parsing)
   and `stats.json`. About 66 x 100 MB are streamed; nothing is stored.
2. **Per record** (`grade104.py`; unperturbed eval-split records, every trial): **em** = HELM's `exact_match` of
   the stripped top completion; **P** = HELM's `max_prob`; **T** = exp(sum of the log probabilities of the tokens
   before the first token whose decoded text reaches one of the run's stop sequences), the probability of the answer
   that was scored (T = P when no token is past the stop). Token strings are decoded as GPT-2 byte-level BPE,
   SentencePiece (`▁`, `<0x0A>`) or AI21 (`<|newline|>`). **overrun** = tokens past the stop; **excess** = stored
   minus answer-only log probability; **consistent** = the kept tokens decode to the scored text.
3. **ECE.** `get_ece_em` transcribed (equal-mass bins via `np.array_split`, midpoint boundaries plus 1.0,
   de-duplicated; left search; bin-weighted mean of |mean prob - mean label|), per trial, mean over trials.
4. **Inclusion.** A run with a published `ece_10_bin` is included if it downloads, our ECE from P equals the published
   value within 1e-9, our exact_match mean equals the published one within 1e-9 and the trial counts agree. Runs
   without a published ECE (HELM skips calibration when every log probability is 0) are reported, not counted; a
   run that fails to download counts against P1.
5. **Run class.** `overrun` if at least half of a run's records have tokens past the stop, else `clean`.
6. **Cells and ranks.** One cell per adapter (one run each). Published cells are checked by matching each P cell to a
   distinct "ECE (10-bin)" value within 1e-9. Ranks: lower ECE is better, 1 + the number strictly lower. Delta =
   ECE(T) - ECE(P). Movers = adapters whose rank changes by 3 or more places.
7. **Hand-read** (next run): one overrun record from up to 4 runs per class, spread by a stable hash, is printed in the
   job log with its text and tokens; texts are never published.

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: all fixtures match; at least 90% of runs with a published ECE are included; at least 55 cells; at least 90% of cells match a published "ECE (10-bin)" value |
| P2 | At least **8** adapters are `overrun` |
| P3 | In at least **half** of the overrun adapters, the median record's excess is at most **-0.1** nats (the published confidence at least about 10% too low) |
| P4 | In at least **half** of the overrun adapters, ECE changes by at least **0.02** (2 points) when T replaces P |
| P5 | Method check: in overrun runs, the kept tokens decode to the scored text on at least **95%** of overrun records |
| P6 | At least **3** adapters move **3 or more** places in the ECE ranking |
| P7 | The order is broadly kept: Kendall tau-b between the P and T cells at least **0.8** |
| P8 | Among overrun adapters whose ECE changes by at least 0.02, more get **better** (lower ECE with T) than worse |

Reasoning: the "# output tokens" column suggests a large group of adapters whose completions always run to
`max_tokens` (P2). After " Yes" a few-shot BoolQ prompt makes a newline likely, but the tokens after it (the start of
the next "Passage:") are not certain, so the published confidence should be noticeably lower than the answer's (P3).
ECE is sensitive to a uniform downward shift of confidence, so several overrun adapters' ECE should move by at least
2 points (P4), enough to move a few adapters in a 60-row column (P6) without re-ordering it (P7). If the extra tokens
mostly push confidence below accuracy, the answer-only confidence should calibrate better (P8); this is the
prediction we are least sure of.

## What a result would mean

If P3 and P4 hold, HELM Classic's BoolQ calibration column measures, for the overrun adapters, partly how predictable
the text after the answer is, not how well the model's confidence in its answer matches its accuracy, and ECE(T) is
a like-for-like alternative. If P4 fails, the extra tokens are too predictable to matter for this column. Only BoolQ
in one release is measured; the same mechanism may reach other Classic calibration columns, and MS MARCO, which ranks
passages by this log probability; those are not measured here.

## Validity gates

Hand-traced fixtures (`cases104.py`, traced in `test_grade104.py`): token decoding (GPT-2 byte characters,
SentencePiece, byte tokens, AI21's newline token, plain text); stop trimming including a newline first, a stop split
over two tokens (`###`) and no stops; HELM's exact match; seven record cases (overrun, clean, empty answer,
SentencePiece, a kept token that disagrees with the text, missing golds or completion); the top-completion pick; a
run census with a duplicate, a perturbed record, a train-split record and a record without completions; equal-mass
bins with uneven chunks, duplicates and more bins than records; ECE; run classes on the boundary; run names;
stats.json lookup; the parsing hook; ranks; Kendall tau-b with ties; cell matching; the group column; medians; and two
verdict cases on and past every boundary. They must match before any data is read. The unit tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads the release index, the group page and 66 runs (about 6-7 GB, streamed)
```

## Files

- `grade104.py`: token decoding, stop trimming, HELM's exact match and max_prob, the answer-only probability, the run
  census, the equal-mass ECE (transcribed), run names, ranks, Kendall tau-b and verdicts
- `cases104.py`: data source, thresholds and the fixtures (all invented)
- `job.py`: downloads, gates, scores, classes, rebuilds cells, ranks; writes `results.json`
- `test_grade104.py`: unit tests with the hand traces; `requirements.txt`: none (standard library)

## Licence

Code is Apache-2.0. HELM's `exact_match` and `max_prob` logic are transcribed from stanford-crfm/helm (Apache-2.0);
the equal-mass ECE is re-implemented from the description of `uncertainty-calibration` (p-lambda), and GPT-2's
byte table follows openai/gpt-2 (MIT). This write-up and any results are CC BY 4.0. HELM Classic's outputs are
published by Stanford CRFM. Only run names, model names, HELM instance ids, trials, classes and counts are published,
never prompts, references or model text. Authored by AI agents working in MV2's name (Munim, Inc.).
