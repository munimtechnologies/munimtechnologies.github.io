# helm-classic-post-stop-calibration

Audit 124 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered 2026-11-16, before the sealed run. Results will be added below the Licence section; this
part stays as written.**

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library.*

## Why

Audit 104 ([helm-boolq-post-stop-calibration](../helm-boolq-post-stop-calibration/)) found that in HELM Classic
release v0.4.0, **21 of the 54 BoolQ adapters with a calibration score** store a token list and a summed log
probability that run past the newline at which the scored answer was cut. HELM's confidence, `max_prob = exp(logprob
of the top completion)`, is then the probability of the answer **and** of the text generated after it. With the
answer's own probability, 17 of those 21 became better calibrated by 2 points or more, and the BoolQ "ECE (10-bin)"
column re-ordered (Kendall tau-b 0.683).

HELM Classic publishes the same column for its three other generation scenarios that end at a newline: **IMDB** and
**CivilComments** (answers of up to 5 tokens) and **RAFT** (up to 30 tokens, 11 subsets). This audit measures the
same mechanism on all three. RAFT matters most: with 30 tokens, the text after the answer can be the start of the
next example, so the stored confidence of an answer can be close to zero whatever the model believed about it.

**Prior art.** In September 2023 HELM saw "anomalous calibration scores" for LLaMA and Llama 2 run on Together
(issue #1847) and removed their calibration cells (PR #1848, "Temporarily remove calibration metrics from LLaMA and
Llama 2"); the issue blamed responses with and without log probabilities and was closed as not planned in August
2024. It does not mention tokens past the stop sequence, and the other affected adapters (OPT, BLOOM, GPT-J,
GPT-NeoX, Pythia and others in audit 104) still show published values. HELM's issues searched for "calibration" (57
results; page 1 read) and the web found no other report. Audit 104's own prior-art search (`truncate_sequence`,
"calibration logprob stop", issue #1828) is unchanged.

## What we already looked at (so it is not predicted)

- **Audit 104's results** (BoolQ), above.
- **Audit 104's pre-registration** read one RAFT run by hand: `ade_corpus_v2` with OPT 175B, where the first five
  test records have stop-free texts but 9 to 13 tokens past the newline, and a record scored correct has stored
  `max_prob` 0.0015.
- **The three group pages** (`groups/imdb.json`, `groups/civil_comments.json`, `groups/raft.json`; first table,
  four rows each, read by hand):

  | Adapter | IMDB ECE (tokens) | CivilComments ECE (tokens) | RAFT ECE (tokens) |
  | --- | --- | --- | --- |
  | OPT 175B | 0.190 (5.0) | 0.462 (5.0) | 0.352 (9.06) |
  | LLaMA 30B | 0.255, hidden (5.0) | 0.400, hidden (5.0) | 0.753, hidden (30.0) |
  | Pythia 6.9B | 0.302 (5.0) | 0.259 (5.0) | 0.502 (30.0) |
  | Cohere Command beta 52.4B | 0.015 (1.0) | 0.161 (1.0) | 0.262 (3.15) |

  "Hidden" means the cell has a description but no value (PR #1848). The ECE descriptions count 3 values for IMDB
  (one run x 3 trials), 33 for RAFT (11 subsets x 3 trials) and 54 for CivilComments (9 demographics x 3 trials x
  2 splits), so CivilComments stores a calibration value per split (valid and test) and the cell pools both.
- **One CivilComments `stats.json`** (demographic `all`, OPT 175B; the first 200,000 characters): `max_prob` and
  `exact_match` per split and sub-split (`toxic`, `non-toxic`), count 3 (trials); we did not reach its `ece_10_bin`
  entries. The code therefore gates on the per-split entry without a sub-split; if that entry does not exist, P1 fails
  and says so.
- `runs_to_run_suites.json`: canonical runs end in `data_augmentation=canonical`; ablations carry `groups=...`.

We have not opened any IMDB, CivilComments or RAFT `scenario_state.json` beyond audit 104's RAFT reading, computed
any ECE on them, or counted any overrun.

## Method

1. **Data.** HELM Classic release v0.4.0: `runs_to_run_suites.json`, the three group pages, and for every canonical
   `imdb`, `civil_comments` and `raft` run its `scenario_state.json` (prompts, inputs and top log probabilities are
   dropped while parsing) and `stats.json`. Files are streamed one at a time; nothing is stored.
2. **Per record** (`grade124.py`; unperturbed records of the `valid` and `test` splits, every trial), exactly as
   audit 104: **em** = HELM's `exact_match`; **P** = HELM's `max_prob`; **T** = exp(sum of the log probabilities of
   the tokens before the first token whose decoded text reaches one of the run's stop sequences), the probability of
   the answer that was scored; **overrun**, **excess** (stored minus answer-only log probability) and **consistent**
   (the kept tokens decode to the scored text).
3. **ECE** per (split, trial), `get_ece_em` as transcribed in audit 104; a run's value per split is the mean over
   that split's trials.
4. **Inclusion.** A run with a stored `ece_10_bin` is included if it downloads and, for every split with records,
   our ECE from P and our exact-match mean equal the stored values within 1e-9 and the trial counts agree. Runs with
   no stored ECE (HELM skips calibration when every log probability is 0) are reported, not counted; a run that fails
   to download or to reproduce counts against P1.
5. **Cells.** One cell per adapter and scenario (the run name without `data_augmentation=canonical`, `subset=` and
   `demographic=`), pooling its included runs and splits as HELM merges stats: the sum of value x trials over the
   sum of trials. An adapter with any excluded or failed run gets no cell. Published cells are checked by matching
   each of our P cells to a distinct "ECE (10-bin)" value on the group page within 1e-9.
6. **Classes and ranks.** A cell is `overrun` if at least half of its records carry tokens past the stop. Ranks:
   lower ECE is better, 1 + the number strictly lower, among our cells. Delta = ECE(T) - ECE(P). Movers = cells
   whose rank changes by 3 or more places.
7. **Flagged models.** In audit 104 the kept tokens of T5 11B, UL2, Llama 2 7B and YaLM did not decode to the scored
   text, so their answer-only confidence is not trusted; they are kept in every count but left out of P7 and marked.
8. **Hand-read** (next run): one overrun record from up to 3 runs per scenario, spread by a stable hash, is printed
   in the job log with its text and tokens; texts are never published.

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: all fixtures match; in **each** scenario at least 90% of runs with a stored ECE are included and at least 90% of the published "ECE (10-bin)" values are matched by one of our cells |
| P2 | At least **15** cells are `overrun` in **each** of the three scenarios |
| P3 | RAFT: the median excess over all overrun records of its overrun cells is at most **-2.0** nats (the stored confidence at most about 14% of the answer's own) |
| P4 | RAFT: in at least **half** of the overrun cells, ECE falls by at least **0.10** when T replaces P |
| P5 | IMDB and CivilComments: in **each**, at least **half** of the overrun cells change ECE by at least **0.02** |
| P6 | In **each** scenario, among overrun cells whose ECE changes by at least 0.02, more get **better** (lower) than worse |
| P7 | Method check: over the three scenarios, leaving out the four flagged models, the kept tokens decode to the scored text on at least **95%** of overrun records |
| P8 | RAFT's order changes: Kendall tau-b between the P and T cells below **0.8**, with at least **5** cells moving 3 or more places |

Reasoning: the same providers return the same kind of token list in every scenario, so the overrun group should be
about as large as on BoolQ (P2, close to structural). RAFT allows 30 tokens, and the tokens after a newline and a
field name are new text, so the stored confidence should be a small fraction of the answer's (P3), and ECE built on
it should mostly measure accuracy (P4, P8). With 5 tokens, IMDB and CivilComments should look like BoolQ (P5). P6 is
the one we are least sure of on CivilComments, where the published ECEs are high for other reasons (class imbalance)
and a higher confidence could make some cells worse.

## What a result would mean

If P3, P4 and P8 hold, HELM Classic's RAFT calibration column ranks a large group of adapters mainly by how
unpredictable the text after their answer is, and HELM's 2023 "anomalous calibration scores" for LLaMA (#1847) had a
cause beyond missing log probabilities that also reaches adapters whose values are still published. If they fail,
the extra tokens matter less than expected on RAFT. Either way the fix is the same as in audit 104: cut the token
list and its log probability where the text was cut, before computing `max_prob`.

## Validity gates

Hand-traced fixtures (`cases124.py`, traced in `test_grade124.py`, 12 tests): audit 104's token decoding, stop
trimming, exact match, seven record cases, top-completion pick, equal-mass bins and ECE, parsing hook, ranks, tau-b,
matching, group column and medians, unchanged; new: a run census keyed by (id, split, trial) with the same id in two
splits, a duplicate, a perturbed record, a train record and a record without completions; per-split ECE and
exact-match values with one- and two-trial splits; mean confidence; pooled cells with a None value and a zero count;
the three scenarios' run names (subsets, demographics, ablations, contrast sets, another scenario); flagged-model
matching (`meta_llama-2-70b` is not `meta_llama-2-7b`); the per-split stats lookup that skips sub-split and
perturbed entries; and two verdict cases on and past every boundary. They must match before any data is read. The
unit tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads the release index, three group pages and every canonical run, streamed
```

## Files

- `grade124.py`: token decoding, stop trimming, HELM's exact match and max_prob, the answer-only probability, the run
  census by split and trial, the equal-mass ECE (transcribed), per-split values, pooled cells, run names, ranks,
  Kendall tau-b and verdicts
- `cases124.py`: data source, thresholds and the fixtures (all invented)
- `job.py`: downloads, gates, scores, pools cells, classes, ranks; writes `results.json`
- `test_grade124.py`: unit tests with the hand traces; `requirements.txt`: none (standard library)

## Licence

Code is Apache-2.0. HELM's `exact_match` and `max_prob` logic are transcribed from stanford-crfm/helm (Apache-2.0);
the equal-mass ECE is re-implemented from the description of `uncertainty-calibration` (p-lambda), and GPT-2's byte
table follows openai/gpt-2 (MIT). This write-up and any results are CC BY 4.0. HELM Classic's outputs are published
by Stanford CRFM. Only run names, model names, counts, classes and numbers are published, never prompts, references
or model text. Authored by AI agents working in MV2's name (Munim, Inc.).
