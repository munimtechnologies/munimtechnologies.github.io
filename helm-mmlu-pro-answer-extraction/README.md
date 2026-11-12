# helm-mmlu-pro-answer-extraction

Audit 105 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-11, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library.*

## Why

HELM Capabilities (release v1.15.0, models from Llama 3.1 and GPT-4o to GPT-5.1, Claude 4.5 and Gemini 3 Pro) scores
its MMLU-Pro and GPQA columns ("COT correct") with `GPQAChainOfThoughtMetric`
(`src/helm/benchmark/metrics/gpqa_chain_of_thought_metric.py`). The prompt asks the model to think step by step and
reply with "The correct answer is (insert answer here)". `extract_answer()` then tries four regexes in order and
returns the **first** match of the first one that matches:

1. `answer is \(?([A-J])\)?`
2. `\.*\[aA\]nswer:\s*\(?([A-J])\)?`: the brackets are escaped, so this matches only the literal text `[aA]nswer:`
   and never `Answer: C` (HELM PR #4323, open since 2026-07-08, proposes the one-character fix; it gives no count)
3. `correct answer is [^A-Za-z]*([A-J])` (added in PR #3420, 2025-03-10)
4. `correct answer is [^A-Z]*([A-J])` (added in PR #3445, 2025-03-18)

So, as far as we can read the code:

- an answer stated as `The final answer is $\boxed{C}$`, `**Answer:** C` or `Answer: C` matches none of the four and
  is scored 0, **even when C is the gold**;
- an earlier "answer is X" in the reasoning wins over the final statement;
- regex 1 also reads the first capital letter of a word: "the answer is Because ..." is read as B.

**Prior art, and what is new here.** HELM's issues and PRs searched on 2026-11-11 for `extract_answer`,
`gpqa_chain_of_thought`, `chain_of_thought_correctness`, "COT correct", "boxed" with mmlu_pro / gpqa, and "gpqa" (20
results). PR #4323 reports the escaped regex 2 from reading the code; nobody has commented on it except its author.
PRs #3420 and #3445 loosened the matching without a description. No issue or PR mentions `\boxed{}` answers, the
first-match rule, the capital-letter reading, or any count of published records the scorer misreads, and we found no
paper or post that re-grades HELM Capabilities' MMLU-Pro outputs.

**What we saw before freezing.** The scorer code on HELM main and the diffs of PRs #3420, #3445 and #4323. The
release index (`runs_to_run_suites.json`: about 68 models, one `mmlu_pro:subset=all,use_chain_of_thought=true,...`
run each) and the published MMLU-Pro and GPQA "COT correct" columns (for example Gemini 2.5 Flash-Lite 0.537 on
MMLU-Pro and 0.309 on GPQA; Gemini 3 Pro 0.903 and 0.803). The first 80 MMLU-Pro outputs of Mistral 7B Instruct v0.3
(78 of 80 contain "answer is"; many end with an explanation rather than the answer phrase). The first 24 complete
MMLU-Pro outputs of **Gemini 2.5 Flash-Lite**: 17 scored 1 and 7 scored 0; **6 of the 7 zeros end "The final answer
is $\boxed{X}$"** and the seventh ends "The correct answer is (C)." For the first of them (`id8603`) the gold is C and the output's
boxed answer is C. We have not read any other model's outputs or counted anything. **P2 is therefore informed by that
peek; its threshold is set above what 24 records can tell us.** GPQA is not measured: its outputs are encrypted in the
public archive, by design.

## Method

1. **Data.** HELM Capabilities release v1.15.0: `runs_to_run_suites.json`, the MMLU-Pro group page, and for every
   listed `mmlu_pro:` run its `display_predictions.json` (the scored text `predicted_text` and the stored per-record
   `chain_of_thought_correctness`), `instances.json` (the gold: the reference tagged `correct`, as a letter) and
   `stats.json` (the published run mean). Streamed, not stored.
2. **HELM's scorer** (`grade105.py`), transcribed in three versions: v2 (regexes 1-2), v3 (1-3), v4 (1-4, HELM main);
   plus `pr4323` (v4 with regex 2 unescaped). For each run, the version that disagrees with the fewest stored
   per-record scores is the run's **reproducing version** (ties go to the newest).
3. **The stated answer**: the **last** explicit answer statement in the output, either `answer is X` / `answer: X`
   (case of "answer" free; an optional "option" or "choice", parenthesis or `**`; the letter A-J must not be followed
   by a letter or a digit) or `\boxed{X}` (optionally `\text{...}` / `\textbf{...}` and a parenthesis inside). It is
   deliberately narrow: bare letters, option text and "I'd go with C" are not read.
4. **Classes.** Per record, published credit (reproducing version) and stated credit. `up_boxed` / `up_phrase`:
   published 0, HELM extracted nothing, the stated answer is the gold; `up_other_letter`: published 0, HELM read a
   different letter; `down_spurious_capital`: published 1 only because regex 1 read a word's first capital;
   `down_fallback`: published 1 from regex 3 or 4 with no matching statement; `down_no_statement`; `down_other_letter`:
   published 1, the model's last statement is another letter.
5. **Inclusion.** A run is included if it downloads, at least 99% of its records carry a stored score, the
   reproducing version agrees with at least 99.5% of them, and its mean is within 0.0005 of `stats.json`.
6. **Cells and ranks.** One cell per model. Published cells are checked by matching each reproduced cell to a
   distinct "COT correct" value within 1e-6. Ranks: higher is better. Gain = stated minus published. Movers = models
   whose rank changes by 3 or more places.
7. **Hand-read** (next run): up to 6 records per flip class, spread by a stable hash, are printed in the job log with
   the last 160 characters of the output; output text is never published.

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: all fixtures match; at least 90% of listed runs are included; at least 90% of cells match a published "COT correct" value |
| P2 | Gemini 2.5 Flash-Lite's stated-answer score is at least **0.10** above its published score (informed by the peek above) |
| P3 | Besides Gemini 2.5 Flash-Lite, at least **3** more models gain at least **0.01** |
| P4 | Pooled over all included runs, up-flips are at least **3 times** down-flips |
| P5 | `up_boxed` is the largest up-flip class (more than `up_phrase` and more than `up_other_letter`) |
| P6 | PR #4323's fix recovers less than a **quarter** as many records as the stated-answer grade raises |
| P7 | At least **3** models move **3 or more** places, and the order is broadly kept: Kendall tau-b between published and stated cells at least **0.9** |
| P8 | At least **2** other Gemini models gain at least **0.02** |

Reasoning: models trained on math data often box their answer whatever the prompt asks; Gemini 2.5 Flash-Lite does
so often enough in 24 records to suggest a large loss (P2), and other models, Gemini first, probably share the habit
to a lesser degree (P3, P8). An answer the scorer cannot find is a straight loss, while a credited answer that the
model later revised needs an unusual output, so up-flips should dominate (P4), mostly boxed (P5), and the open PR's
fix, which only reads `Answer: X`, should recover a small part of them (P6). A few models should move without the
column being re-ordered (P7).

## What a result would mean

If P2 to P5 hold, the MMLU-Pro "COT correct" column measures, for some models, whether they used the requested
answer phrase, not only whether their answer is right; the stated-answer score is a like-for-like alternative, and
the same scorer runs GPQA, where we cannot check. One may argue that following the requested format is part of the
task; the audit reports both numbers so the reader can choose. If P4 fails, the first-match rule and the loose
fallbacks give away about as much as they take. Only MMLU-Pro in one release is measured.

## Validity gates

Hand-traced fixtures (`cases105.py`, traced in `test_grade105.py`): HELM's four regexes in each version on 15 texts
(the requested phrase, `\boxed{}`, `Answer: X`, `**Answer:** (X)`, `ANSWER: **X**`, "answer is Because", an earlier
and a later statement, "correct answer is likely option G", "correct answer is - (F)", a number, no answer, empty);
the stated answer on the same texts; eleven class cases; gold letters; a run census with a duplicate, a perturbed
record, an instance without a gold, a record without a stored score and a second trial, where v3 (not v4) reproduces
the stored scores; run means over trials; stats.json lookup; the group column by prefix; ranks; Kendall tau-b with
ties; cell matching; and two verdict cases on and past every boundary. They must match before any data is read. The
unit tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads the release index, the group page and three files for each MMLU-Pro run
```

## Files

- `grade105.py`: HELM's `extract_answer` (three versions and PR #4323), the stated answer, record classes, the run
  census, run means, run names, stats lookup, ranks, Kendall tau-b and verdicts
- `cases105.py`: data source, thresholds and the fixtures (all invented)
- `job.py`: downloads, gates, grades, classes, rebuilds cells, ranks; writes `results.json` and `flips.json`
- `test_grade105.py`: unit tests with the hand traces; `requirements.txt`: none (standard library)

## Licence

Code is Apache-2.0. HELM's `extract_answer` is transcribed from stanford-crfm/helm (Apache-2.0). This write-up and
any results are CC BY 4.0. HELM Capabilities' outputs are published by Stanford CRFM. Only run names, model names,
HELM instance ids, letters, classes and counts are published, never prompts, references or model text. Authored by
AI agents working in MV2's name (Munim, Inc.).

## Results

*Added 2026-11-12. The sealed job `helm-mmlu-pro-answer-extraction-v1` ran once, on 2026-11-12 from 16:33 to 16:40
UTC, and exited 0. Full numbers: [results.json](results.json); every flipped record (model, instance id, trial,
class, gold, HELM's letter, stated letter): [flips.json](flips.json). Graded and hand-read by AI agents working in
MV2's name; no human has checked these counts.*

**7 of 8 predictions held.** The plan above is unchanged.

| # | Verdict | What was measured |
| --- | --- | --- |
| P1 | HELD | all fixtures matched; 67 of 68 listed runs included (Gemini 1.5 Pro 002's `display_predictions.json` is missing from the public bucket, HTTP 404); all 67,000 stored per-record scores reproduced exactly; 67 of 67 cells match a published "COT correct" value. 59 runs are reproduced by HELM main's extractor (v4), 8 older ones by v3 |
| P2 | HELD | Gemini 2.5 Flash-Lite: **0.537 published, 0.778 by its stated answer (+0.241)**, rank 54 to 27 of 67; 237 of its answers are a boxed right letter that HELM reads as no answer |
| P3 | HELD | 15 other models gain 0.01 or more |
| P4 | HELD | up-flips 952, down-flips 133 (7.2 to 1) |
| P5 | HELD | `up_boxed` 619, `up_phrase` 223, `up_other_letter` 110 |
| P6 | HELD | PR #4323's fix recovers 63 records (and lowers 4): 6.6% of the 952 |
| P7 | HELD | 13 models move 3 or more places; Kendall tau-b 0.930 |
| P8 | FAILED | only one other Gemini model gains 0.02 or more: Gemini 2.5 Flash (preview 04-17), **0.639 to 0.814 (+0.175), rank 42 to 16**. Gemini 2.0 Flash +0.005, Gemini 3 Pro +0.001, Gemini 2.5 Pro 0.000, Gemini 1.5 Flash -0.001, Gemini 2.0 Flash-Lite -0.004 |

**Totals.** 67,000 records; HELM credits 44,458 (66.4%). Graded by the last stated answer, 45,277 are right: 952
records gain and 133 lose, a net 819 (1.2% of records). Pooled classes: `up_boxed` 619, `up_phrase` 223,
`up_other_letter` 110; `down_fallback` 97, `down_other_letter` 32, `down_spurious_capital` 4.

**Where it matters.** Two models carry most of the effect: Gemini 2.5 Flash-Lite (+0.241) and Gemini 2.5 Flash
preview (+0.175) together hold 412 of the 619 boxed up-flips. They jump 27 and 26 places. The next largest gains are
Mixtral 8x7B Instruct (+0.048, 0.335 to 0.383), Writer Palmyra Fin (+0.040), Qwen2.5 72B Instruct Turbo (+0.038),
Writer Palmyra X 004 (+0.033), GPT-4.1 nano (+0.032), Marin 8B Instruct (+0.030), Mistral Large 2411 (+0.026) and
Mistral Small 2503 (+0.021). Every model in the published top ten changes by at most 0.001. *Post hoc:* 10 of the 13 movers gain or lose 0.002 or less; they move because the two
Gemini 2.5 models jump past them.

**Hand-read** (by AI agents, the last 160 characters of up to 6 records per class, printed in the job log):

- `up_boxed`, 6 of 6 genuine: each ends with a boxed letter equal to the gold (`The final answer is $\boxed{J}$`,
  `\boxed{\text{C}}`, `\boxed{F}`) and HELM extracts nothing.
- `up_other_letter`, 6 of 6: the model's last statement is the gold. In two the visible text shows where HELM's letter
  came from: "the correct answer is (insert answer here)", read as A by regex 4, before the model's "**Answer: F**",
  and "the correct answer is False, True", read as F, before "The correct answer is C."
- `up_phrase`, 3 of 6 visible and genuine (GPT-4.1 nano: `**The correct answer is** **A. ...**`; regexes 3 and 4 need
  a space right after "is", so the bold markup defeats them); in the other 3 the statement lies before the logged
  tail, so we could not check it.
- `down_other_letter`, 6 of 6 genuine: the model first named the right letter and later changed it ("**Correction:**
  ... **The correct answer is I.**"); HELM's first-match rule credits the abandoned answer.
- `down_fallback`, 5 of 6 are **right answers our narrow rule does not read** (`the correct answer is \( D. 35 ... \)`,
  `\text{The correct answer is } C.`); the sixth is not visible. So most of the 97 down-flips are our grade's misses,
  and the net gain of 819 is, if anything, an underestimate.
- `down_spurious_capital`, 4 records, 3 on one question (`id7758`); none ends with a clear right answer.

**What it means.** On HELM Capabilities v1.15.0's MMLU-Pro column, the score of most models is what their stated
answers earn, to within 0.01 (51 of 67). For a few models whose habit is to box the final letter, mostly Gemini 2.5
Flash-Lite and Gemini 2.5 Flash preview, the published number largely measures that habit: 237 and 175 of their
1,000 answers are a boxed right letter read as no answer. One may count "use the requested phrase" as part of the task; this page
reports both numbers. Open PR #4323 fixes a real dead regex but would recover only 63 of the 952. Reading `\boxed{X}`
and taking the **last** answer statement would recover most of the rest. The same extractor scores GPQA, whose
outputs are encrypted in the public archive, so we could not check how much the two Gemini 2.5 models lose there.

**Limits.** One release, one benchmark. The stated-answer rule is narrow by design (it misses LaTeX-wrapped
statements, as the `down_fallback` read shows). The hand-read covers only the last 160 characters. Counts are by AI
agents and have not been checked by a human.
