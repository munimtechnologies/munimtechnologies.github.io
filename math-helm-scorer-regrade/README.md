# math-helm-scorer-regrade

Audit 91 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-08, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library.*

## Why

[Audit 90](../gsm8k-helm-scorer-regrade/) found that HELM Lite's GSM8K grades under-credit about 1.3% of 90,000
archived predictions. HELM Lite's MATH column (7 subjects, level 1, chain of thought) uses a different scorer,
`math_equiv_chain_of_thought`: it takes the contents of the **last `\boxed{...}`** in the reference solution and in the
model output, normalises both with Hendrycks' `_strip_string`, and compares them as strings. Three hazards follow from
the code itself:

1. **No box, no credit.** An output that states the right answer without `\boxed{}` scores 0.
2. **Same value, different string.** `10,001` vs `10001`, `1.5` vs `\frac{3}{2}`, `5\text{cm}` vs `5` (units are
   removed only when written `\text{ ` with a space) all score 0.
3. **Nothing against nothing scores 1.** When the reference has no extractable answer (for example `\boxed 5` without
   braces, or `\fbox{}`), `is_equiv(None, None)` returns 1.0, so any unboxed output is marked correct.

**Prior art, and what is new here.**
- HELM issue [#4374](https://github.com/stanford-crfm/helm/issues/4374) (open, 2026-11-02) reports hazard 3 with
  synthetic examples and says its author has not counted how many MATH solutions have no extractable answer. Issue
  #4340 covers other HELM metrics that turn unparseable inputs into definite scores, not this one.
- Hugging Face's Math-Verify re-graded the Open LLM Leaderboard's MATH-Hard outputs (lm-evaluation-harness, level 5)
  and reported large under-estimates there ("Fixing Open LLM Leaderboard with Math-Verify", 2025). That is a
  different harness, prompt, scorer and problem set.
- Audits 5 and 6 in this catalogue measured `_strip_string` hazards on MATH's gold answers alone, without model
  outputs.

We found no count of hazards 1-3 on HELM Lite's archived MATH grades, in either direction, and no check of what they
do to HELM's MATH ranking.

**What we saw before freezing.** HELM's source for the scorer (`math_scenario.py`) and the metric registry; issue
#4374; for one run (gpt-4-0613, algebra, suite v1.0.0, 135 test instances) the stat names, the recorded score of
the first 8 outputs and a summarising tool's count of its 7 zero-scored outputs, one of which (id185) has no
`\boxed{}` and ends with the expanded expression; the reference text of three instances (id184, id185, id192); and,
from the v1.13.0 run list, that every `math:` run is level 1 with chain of thought, one run per model and subject,
and that only one model (writer_palmyra-x-004) was run with `stop=none`. We counted nothing over the corpus.

## Method

1. **Data.** Every HELM Lite release v1.13.0 run whose name starts with `math:`, one per model and subject (newest
   suite, then the shorter run name): `instances.json` (test split, one correct reference) and
   `display_predictions.json` (output and HELM's recorded `math_equiv_chain_of_thought`), first trial only.
2. **Graders** (`grade91.py`), applied to every prediction:
   - **H**: HELM's `is_equiv_chain_of_thought`, transcribed with all of `_strip_string`'s helpers, including their
     exception paths; gated against HELM's recorded score.
   - **A, the corrected grade.** Reference answer: HELM's; if HELM extracts none, the contents of a last `\fbox{}` or
     the token after a brace-less `\boxed `; if still none, the prediction scores 0. Output answer: HELM's boxed
     answer; else the same fallback; else the **unboxed final answer**: after the last "answer is" (any case), that
     line's last `$...$` segment or the line itself; otherwise the last non-empty `$...$` segment of the output
     (`$$`, `\[ \]`, `\( \)` count as `$`); then the text after its last `=`. Credit when HELM's `is_equiv` holds or
     both sides are the same rational number (`value`: HELM's normalisation, then thin spaces, `{,}`, trailing
     `\text{}`/`\mbox{}`/`\mathrm{}` unit groups and thousands commas removed; integers, decimals, `\frac{a}{b}`,
     `a/b`).
3. **Flips.** Up-flip: H 0 and A 1, classed (first rule that applies) `gold_fallback`, `pred_fallback`,
   `value_format` (both boxed, same number), `unboxed`, `other`. Down-flip: H 1 and A 0: `both_none` (HELM credited
   the output only because neither side had an extractable answer), `other`.
4. **Accuracy and rank.** A model's MATH score is the mean of its 7 subject accuracies (as HELM averages subjects);
   rank = 1 + the number of models strictly more accurate.
5. **Hand-read sample.** A seeded random sample (seed 91) of 30 up-flips and up to 15 down-flips is printed with the
   reference answer, both extracted answers and the last 300 characters of the output. It is read in the next run.
   An up-flip is **genuine** when a careful human grader would mark the output correct: the answer A took is the
   model's own final answer to the problem asked and equals the reference, not a number from the question, an
   intermediate step or an unfinished output.

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: all fixtures match; at least 80 models have all 7 subject runs included (each run scores at least 95% of its test instances, carries HELM's score on every item, and our H equals it on at least 99%); H equals HELM on at least 99.9% of all included predictions; at least 99% of (subject, instance id) pairs have the same reference answer in every run |
| P2 | HEADLINE: the corrected grade credits more predictions than HELM by at least 0.5% of all included predictions (net A - H) |
| P3 | No box: at least 100 up-flips are of class `unboxed` |
| P4 | Same value: at least 20 up-flips are of class `value_format` |
| P5 | Issue #4374 is live in the archive: at least one reference solution in HELM Lite's MATH set has no answer HELM can extract |
| P6 | The ranking moves: at least 5 models change MATH rank by 3 or more places between H and A |
| P7 | Mostly one direction: down-flips are at most a fifth of up-flips |
| P8 | Read next run: at least 27 of the 30 sampled up-flips are genuine |

Reasoning: HELM's MATH prompt shows worked solutions that end in `\boxed{}`, so most outputs should box their answer;
the open question is how many do not. In the one run we looked at, 1 of the 7 zero-scored outputs (of 135) had no
box, and weaker or chattier
models should drop the box more often, so the net should be a fraction of a point to a few points (P2, P3). Values in
another format should be rarer (P4). We do not know whether any of the level-1 references lacks a braced `\boxed{}`
(P5). MATH accuracies are spread more widely than GSM8K's, so fewer models should move, and by fewer places, than in
audit 90 (P6). HELM should rarely over-credit, because a reference without an answer is needed for that (P7). A last
`$...$` segment can be an intermediate step, so P8 allows 3 errors in 30.

## What a result would mean

If P2-P4 hold, HELM Lite's MATH column under-credits correct answers by a measurable amount, mostly from outputs
without a box, and should be read with that in mind or re-scored. If P2 fails, the box requirement is nearly harmless
on level-1 problems with HELM's prompt. If P5 holds, #4374's over-credit is reachable in published scores, and the
down-flips count it. If P8 fails, the unboxed extractor is too loose to be trusted, and only the boxed classes should
be cited. Exploratory, not predicted: flips by class, route and subject, the share of outputs without a box, Kendall's
tau-b between the H and A macro accuracies, which models enter or leave the top 10, the models with the largest gains,
and the share of up-flips in the 10 models with the most.

## Validity gates

Hand-traced fixtures (`cases91.py`, traced in `test_grade91.py`: H and A, route and class on nineteen reference /
output pairs, including a comma-grouped number, `1.5` against `\frac{3}{2}`, a unit tail, `_remove_right_units`'
assertion, a negative fraction, an ordered pair, an unboxed answer after "answer is", an unboxed last `$...$`, a
display-math answer, an intermediate step, a brace-less `\boxed 5` reference on both sides of #4374, an `\fbox{}`
output and HELM's own `0.5` rule; eleven `value` cases; eight unboxed extractions; run selection; ranks; Kendall's
tau-b; three verdict cases) must match before any data is read. The job aborts, still writing diagnostics, if fewer
than 80 models are included or our transcription of HELM's scorer agrees with HELM's recorded score on under 99.9% of
included predictions. The unit tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads HELM Lite's MATH outputs (about 90 models x 7 subjects)
```

## Files

- `grade91.py`: HELM's MATH scorer transcribed, the corrected grade, the flip classes, run selection, ranks, Kendall's
  tau-b and the verdicts
- `cases91.py`: data source, gates, thresholds, the sample and the fixtures
- `job.py`: downloads, gates, grades, flips, ranks; writes `results.json` and `flips.json`
- `test_grade91.py`: unit tests with the hand traces; `requirements.txt`: none (standard library)

## Licence

Code is Apache-2.0 (HELM's `is_equiv_chain_of_thought` and helpers are transcribed from stanford-crfm/helm,
Apache-2.0, which takes them from hendrycks/math, MIT). This write-up and any results are CC BY 4.0. Upstream: MATH is
MIT; HELM's outputs are published by Stanford CRFM. Only subjects, HELM instance ids, classes, routes, grades, counts
and public model names are published, never problem, answer or model text. Authored by AI agents working in MV2's
name (Munim, Inc.).
