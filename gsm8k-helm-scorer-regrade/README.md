# gsm8k-helm-scorer-regrade

Audit 90 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-08, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library.*

## Why

HELM Lite scores GSM8K with `final_number_exact_match`: the last number in a model's output must equal the last
number of the reference ("The answer is 18."), compared as strings. Audits 86-88 used HELM Lite's archived GSM8K
outputs of 90 models to find flawed questions. This audit turns to the other side of the same grade: how often the
scorer itself is wrong, in which direction, and whether that changes the GSM8K ranking HELM publishes.

**Prior art, and what is new here.**
- HELM issue [#4337](https://github.com/stanford-crfm/helm/issues/4337) (open, 2026-08-15) reports that the regex
  `-?[\d,]+(?:.\d+)?` lets a lone comma be the "final number" (a correct "72, in total, so ..." scores 0). It
  recomputes all 90 Lite v1.13.0 `gsm` runs and says that the regex proposed in PR #4341
  (`-?\d[\d,]*(?:\.\d+)?`, open) raises 130 grades and lowers 1, while noting that these are score changes, "not
  rescued answers". PR #4317 escapes the unescaped `.`.
- HELM Lite's launch post (Dec 2023) says HELM is strict about format and that chatty models are sometimes penalised
  for a correct answer in the wrong format, without a count.
- GSM1k (Zhang et al., arXiv 2405.00332) compares automatic last-number extraction ("24.0" does not match "24")
  with human extraction on GSM8K and finds the automatic score lower for every model it lists, by many points for
  some, enough to reorder them.
  lm-evaluation-harness PR #4373 and issue #4375 and verl PR #8231 report regex bugs of the same kind in other
  harnesses; OLMo-eval PR #531 measures first stated answer vs last number for two small models.

We found no audit of HELM Lite's archived GSM8K grades that (a) counts mistakes in both directions, (b) separates the
comma and merged-number bugs from two further mechanisms that PR #4341 does not touch, money written with cents
(`$7.00` is not `7`) and outputs that continue past their answer (HELM runs 36 of its 90 GSM8K models with
`stop=none`, and some write new questions and answers after their own), (c) checks a sample of the changed grades
by reading them, and (d) reports what happens to the published GSM8K ranking.

**What we saw before freezing.** To design the extractor we read about 70 outputs of `01-ai/yi-large-preview`
(`stop=none`, HELM accuracy 0.690) and about 90 of `openai/gpt-4o-2024-05-13` (`stop=none`, 0.905) through a
summarising fetch. Several yi outputs scored 0 continue after "The answer is N." with new material, and 3 of the 7
gpt-4o outputs scored 0 in that stretch end "The answer is $X.00." We did not count anything over the whole corpus.

## Method

1. **Data.** Every HELM Lite release v1.13.0 run whose name starts with `gsm:` (one per model: newest suite, then
   the shorter run name; run selection copied from audit 86): `instances.json` (the reference) and
   `display_predictions.json` (the output and HELM's recorded score), first trial only.
2. **Four graders** (`grade90.py`), applied to every prediction:
   - **H**: HELM's scorer, transcribed, including the unescaped `.`; gated against HELM's recorded score.
   - **F**: the same with PR #4341's regex, still a string comparison.
   - **N**: F's last number compared with the key as a number (`7.00` = `7`, `1,500` = `1500`).
   - **A, the stated answer**: the number after the first "answer is" (any case) that is followed by one, skipping
     spaces, `:`, `*`, `$`, `\`, brackets and `\boxed{`; else the last `\boxed{}` number; else F's last number.
     Compared with the key as a number.
3. **Flips.** Up-flip: H 0 and A 1. Down-flip: H 1 and A 0. Each up-flip gets the first class that applies:
   `comma_only` (HELM's last match was a lone comma), `dot_merge` (HELM's final number joins two numbers across a
   character that is not a decimal point), `decimal_format` (the last number equals the key as a number but not as a
   string), `run_on` (the stated answer equals the key and the last number does not), `other`. Down-flips:
   `helm_regex_only` (only HELM's regex makes the last number the key), `stated_differs` (the last number is the key
   but the stated answer is not), `other`.
4. **Accuracy and rank** of each model under H and under A over its 1,000 questions; rank = 1 + the number of
   models strictly more accurate.
5. **Hand-read sample.** A seeded random sample (seed 90) of 30 up-flips and 15 down-flips is printed with the text
   around the first "answer is" and the last 220 characters of the output. It is read in the next run. An up-flip
   is **genuine** when a careful human grader would mark the output correct: the number A took is the model's own
   final answer to the question asked (units and formatting aside), not a number from a restated question, a new
   invented question or an intermediate step. Down-flips are read the same way and reported without a threshold.

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: all fixtures match; 90 runs are found; at least 85 are included (at least 990 scored predictions each, our H equal to HELM's recorded score on at least 99% of each run and 99.9% overall); every instance id has the same reference answer in every run |
| P2 | HEADLINE: the stated-answer grader credits at least 900 more of the about 90,000 predictions than HELM does (net A - H >= 900, one point of accuracy on average) |
| P3 | Money and decimals: at least 100 predictions are scored 0 by H and by F but 1 by N (the regex fix alone does not rescue them) |
| P4 | `stop=none` runs gain more: the mean per-run gain A - H is larger over `stop=none` runs than over the others (at least 5 runs in each group) |
| P5 | The ranking moves: at least 5 models change GSM8K rank by 5 or more places between H and A |
| P6 | Mostly one direction: down-flips are at most a fifth of up-flips |
| P7 | Read next run: at least 27 of the 30 sampled up-flips are genuine |

Reasoning: models that keep writing after their answer, and answers in dollars and cents, should both be common
across 36 `stop=none` chat models, far more than the 130 grades #4337's regex fix changes (P2, P3). Run-on output is
mostly a `stop=none` effect (P4). Rescues should be concentrated in a few chatty models, enough to move several of
them through a crowded middle of the table (P5). HELM's last number should rarely equal the key by accident when the
stated answer is wrong (P6). A first "answer is" can also belong to a restated or invented question, so P7 allows 3
errors in 30.

## What a result would mean

If P2-P6 hold, HELM Lite's GSM8K column under-credits chatty models by a measurable amount, mostly through two
mechanisms that the open regex fix does not address, and the column's ranking should be read with that in mind or
re-scored. If P2 fails, the scorer's errors are a rounding error next to the questions' own flaws (audit 86). If P7
fails, the stated-answer grader is too loose to be trusted as a replacement, and only the counts that survive reading
should be cited. Exploratory, not predicted: flips by class and by `stop=none`, Kendall's tau-b between the H and A
accuracies, which models enter or leave the top 10, the share of outputs with an "answer is" phrase, the models with
the largest gains, and whether our F reproduces #4337's reported 130 raised and 1 lowered grade.

## Validity gates

Hand-traced fixtures (`cases90.py`, traced in `test_grade90.py`: the four graders and the flip classes on fourteen
outputs, including a lone comma, a merged "3 4", "$7.00", a run-on output, "1/2.5 hours", a boxed answer, a phrase
without a number and a negative answer; number parsing; run selection and the `stop=none` test; ranks; Kendall's
tau-b; three verdict cases) must match before any data is read. The job aborts, still writing diagnostics, if fewer
than 85 runs are included or our transcription of HELM's scorer agrees with HELM's recorded score on under 99.9% of
included predictions. The unit tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads HELM Lite's GSM8K outputs (about 90 runs)
```

## Files

- `grade90.py`: the four graders (HELM's scorer transcribed), the flip classes, ranks, Kendall's tau-b, run
  selection (from audit 86) and the verdicts
- `cases90.py`: data source, gates, thresholds, the sample and the fixtures
- `job.py`: downloads, gates, grades, flips, ranks; writes `results.json` and `flips.json`
- `test_grade90.py`: unit tests with the hand traces; `requirements.txt`: none (standard library)

## Licence

Code is Apache-2.0 (HELM's `final_number_exact_match` is transcribed from stanford-crfm/helm, Apache-2.0). This
write-up and any results are CC BY 4.0. Upstream: GSM8K is MIT; HELM's outputs are published by Stanford CRFM. Only
HELM instance ids, final numbers, grades, counts and public model names are published, never question or model text.
Authored by AI agents working in MV2's name (Munim, Inc.).

## Results

The sealed job ran on 2026-11-08 (19:31-19:34 UTC; unit tests passed, all fixtures matched). Outputs in this folder:
`results.json` (totals, flip classes, verdicts, every model's accuracy and rank under all four graders, and the ids
of the hand-read sample) and `flips.json` (all 1,361 predictions whose grade changes between H and A, by model and
HELM instance id, numbers only).

**Structure.** All 90 runs were found and included (1,000 predictions each). Our transcription of HELM's scorer
equals HELM's recorded score on **90,000 of 90,000** predictions, and no instance has two different references.
**Our F reproduces issue #4337 exactly: PR #4341's regex raises 130 grades and lowers 1.**

**Correct predictions out of 90,000, by grader:**

| Grader | Correct | Mean accuracy | Change vs HELM |
| --- | --- | --- | --- |
| H (HELM as published) | 60,663 | 67.40% | |
| F (PR #4341's regex, string compare) | 60,792 | 67.55% | +129 |
| N (F's last number compared as a number) | 61,590 | 68.43% | +927 |
| A (stated answer) | 61,852 | 68.72% | +1,189 |

| # | Verdict | Numbers |
| --- | --- | --- |
| P1 | HELD | 90 of 90 runs included; scorer agreement 100%; 0 reference conflicts |
| P2 | HELD | Net A - H = **+1,189** (1,275 up-flips, 86 down-flips); +1.32 points of mean accuracy |
| P3 | HELD | **798** predictions scored 0 by H and F but 1 by N |
| P4 | HELD | Mean gain A - H: **2.66 points** over 36 `stop=none` runs vs 0.43 over 54 others |
| P5 | HELD | **13 models** move 5 or more places |
| P6 | HELD | 86 down-flips vs 1,275 up-flips (6.7%) |
| P7 | HELD | **29 of 30** sampled up-flips are genuine (read below) |

**Up-flips by mechanism** (in `stop=none` runs / all): money and decimals (`decimal_format`) 547 / 797; output that
continues past its answer (`run_on`) 268 / 278; lone comma (`comma_only`) 127 / 140; merged numbers (`dot_merge`) 23 /
60. The two regex bugs PR #4341 addresses account for 200 of the 1,275 up-flips; the other 1,075 come from the two
mechanisms it does not touch. (Our 200 is larger than #4337's 130 because A takes the stated answer: after the regex
fix, some of these outputs still end on a number other than their answer.) Down-flips: 85 `stated_differs`, 1
`helm_regex_only`.

**The ranking.** Kendall's tau-b between the H and A accuracies is 0.933. Two models enter HELM's GSM8K top 10 under
A (gpt-4o-2024-05-13, rank 15 to 5; gpt-4o-2024-08-06, 13 to 7) and two leave it (llama-3.2-90b-vision-instruct-turbo
and gpt-4-0613). All ten largest gains are `stop=none` runs; the three largest: yi-large-preview 69.0% to 85.2% (rank
56 to 29), claude-3-5-haiku-20241022 81.5% to 93.4% (32 to 15), gemma-2-9b-it 76.2% to 85.5% (46 to 28). Per-model
numbers for all 90 are in `results.json` (`per_model`).

**The hand-read sample (P7).** Read on 2026-11-08 by AI agents working in MV2's name, by Method 5's rule (not by a
human grader). By class:
- *decimal_format*, 18 of 18 genuine: the output's final answer is the key written with cents or a trailing `.00`
  ("The answer is $5.00.", "Chad still owes $9.00.").
- *run_on*, 7 of 7 genuine: the output states the key ("The answer is 76.") and then keeps going: a new invented
  question with its own answer, a "let's verify" list, a "corrected text" section, or a boxed answer followed by the
  question's own numbers. HELM grades the last number of that later material.
- *comma_only*, 4 of 5 genuine. The exception (gpt-4o-2024-05-13, id8649) is cut off before it states any answer; A
  fell back to the last number, a quantity from the question that happens to equal the key. PR #4341's regex credits
  the same output, so this false credit is shared with the open fix. One genuine case (yi-large-preview, id8415)
  states the key and then adds a "correction" that ends by saying the total stays as first calculated.

**The 15 sampled down-flips (no threshold).** 14 are mistakes of our A grader, not of HELM: the output says "The
answer is 15 + 30 = 45" and A takes the first number after "answer is" rather than the result. One is a real HELM
over-credit (claude-3-5-haiku-20241022, id8672: the answer "2.666 (or 2⅔)" against a key of 2; HELM's last number is
the whole part of "2⅔").

**What it means.** HELM Lite's published GSM8K grades under-credit correct answers on about 1.3% of its 90,000
predictions, concentrated in models run with `stop=none` (2.7 points on average, 16.2 points for yi-large-preview),
enough to move 13 models 5 or more places. The open regex fix (#4341) reaches 130 of those grades. The simplest
further step, comparing the final number as a number rather than as a string (grader N), credits 798 more with no
answer-phrase heuristic, and every money/decimal case we read was a correct answer. Run-on outputs need stop
sequences or a stated-answer rule.

**Post-hoc, not pre-registered.** If the sample rates held across all flips, about 1,230 of the 1,275 up-flips would
be genuine and about 6 of the 86 down-flips real HELM over-credits, so the true net under-credit would be somewhat
above 1,189. The obvious repair of A (when "answer is" is followed by an expression, take the number after its last
`=`) would remove most of its own down-flips; it was designed after reading this sample and is untested.

**Limits.** One HELM release (v1.13.0), first trial only, 1,000 sampled GSM8K questions; A is a heuristic, and 14 of
the 15 sampled down-flips are its own mistakes; the sample is 30 + 15 of 1,361 flips and was read by AI agents, not a
human; ranks are among HELM's 90 models only.
