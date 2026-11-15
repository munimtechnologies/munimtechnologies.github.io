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

## Results

*Added 2026-11-15. The sealed job ran once on 2026-11-15 (11:13 to 11:19 UTC, 1 CPU, 1 GB; unit tests passed first).
Everything above this section is unchanged from the pre-registration. Full numbers: [results.json](results.json).
Graded by AI agents working in MV2's name; post-hoc observations are marked as such.*

**Verdict: 4 of 8 predictions HELD** (P1, P2, P4, P6); P3, P5, P7 and P8 FAILED.

### Checks

- **C1 holds.** In HELM's 1,000 OODCV-VQA questions all **343** presence golds are `Yes` and all **229** unicorn
  golds are `0`: **572 of 1,000** questions (57.2%) can be answered from the question text alone. The other 428 ask
  for counts of real objects (golds 1 to 5: 132, 119, 91, 63, 23).
- **C2.** The most common count gold is `1`, not `2`, so the text-only answer (`Yes` / `0` / `1`) scores **0.704** on
  OODCV-VQA under HELM's metric (we guessed about 0.68). On Sketchy-VQA the best constant, `Yes`, scores 0.509.

### Predictions

| # | Verdict | Result |
| --- | --- | --- |
| P1 | HELD | 102 of 102 runs listed and included (every stored per-record score and `stats.json` mean reproduced); 1,000 questions in each subset |
| P2 | HELD | **15 of 51 models** score below the text-only 0.704 on OODCV-VQA as stored |
| P3 | **FAILED** | Pooled accuracy is 0.937 on presence and 0.727 on unicorn questions (thresholds 0.95 and 0.90), 0.399 on real-object counts. The pooled means are pulled down by the runs with empty answers below |
| P4 | HELD | **23 of 51 models** move 3 or more places when ranked by real-object count accuracy (Kendall tau-b 0.858) |
| P5 | **FAILED** | Prefix-only credits are **977 of 78,403** (1.25%, threshold 0.5%): 963 are Qwen-VL Chat's (sentence answers that begin with the gold word), 14 are in 12 other OODCV-VQA runs (the 7 of them read are counts of 10, 11, 12 or 16 credited for the gold 1) |
| P6 | HELD | **21 runs** have 5% or more answers that are neither yes/no nor a number |
| P7 | **FAILED** | No Sketchy-VQA run gives one answer 80% of the time; the most one-sided are Claude 3 Opus (No on 72.4%) and IDEFICS 80B Instruct (Yes on 71.0%) |
| P8 | **FAILED** | Qwen2-VL 72B Instruct is first both ways (stored 0.848; real-object counts 0.657) |

### What the stored OODCV-VQA scores measure

- **Thirteen of 51 models get no credit on any of the 428 real-object count questions**, and they are the bottom 13
  stored cells (0.000 to 0.341). For six Anthropic models the stored answer is **empty on nearly every number
  question** (count and unicorn, 657 in all): Claude 3 Haiku 657 and Claude 3 Opus 657 empty, Claude 3.5 Sonnet
  (2024-06-20 and 2024-10-22) 656 each, Claude 3.7 Sonnet 651, Claude 3 Sonnet 624 (and 33 yes/no answers). Their
  OODCV-VQA cells (0.301 to 0.335) come entirely from the presence questions, while the same models score 0.749 to
  0.941 on Sketchy-VQA, where every answer is yes or no. The run spec allows one output token with no prefill;
  an empty reply at a one-token limit is documented API behaviour in other projects, but we did not check the cause
  in these runs. Claude 3.7 Sonnet (thinking, 64k) and Gemini 2.0 Flash Thinking store an empty answer on all 2,000
  questions of both subsets (cells 0.0). Pixtral 12B, IDEFICS 80B Instruct, IDEFICS2 8B, IDEFICS 9B Instruct and
  Qwen-VL Chat give no number on these questions either (empty answers, cut first words or sentences).
- **The best stored cell is 0.144 above the text-only answer.** For Qwen2-VL 72B Instruct, 567 of its 848 credits are
  on questions answerable without the image.
- **Largest move:** Qwen2.5-VL 32B Instruct is 37th as stored (0.695) but **3rd** by real-object counts (0.612). It
  gives 477 yes/no answers to 343 yes/no questions, so it answers at least 134 number questions with a yes/no word,
  and is credited on only 99 of 229 unicorn questions. Palmyra Vision 003 moves 20th to 13th; o3 6th to 9th.
- *Post hoc:* 9 of P4's 23 movers are the models with zero count credit, which tie at rank 39 by count accuracy; the
  other 14 move on real differences, so P4 holds without them.
- *Post hoc:* Qwen-VL Chat's Sketchy-VQA cell (0.651) is almost all prefix credit: under `quasi_exact_match` it would
  be 0.012.
- *Post hoc:* question `id971` (gold 1) is answered 10, 11, 12 or 16 by at least six models, all credited by the
  prefix match; whether its gold is right was not checked.

### Hand-read (by AI agents)

Eight prefix-only credits: seven are counts of 10 or more credited for the gold 1 (wrong answers credited), one is a
right `Yes` written as a sentence. Eight answers classed "other": two spelled-out numbers, two vague quantity words,
two cut first words, one sentence and one unrelated word; every class is as labelled.

### What this means

On VHELM's Unicorn OODCV-VQA cell, 57.2% of the questions need no image, a no-image answer scores 0.704, and for 13 of
51 models the cell measures whether the model returns a one-token number at all rather than how well it counts. A
fairer cell would report the 428 real-object count questions separately, score counts by numeric equality rather than
prefix (so `10` is not credited for `1`), and count empty answers per model.
