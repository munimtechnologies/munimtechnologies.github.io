# mcq-helm-option-collisions

Audit 92 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-09, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library.*

## Why

HELM scores its `multiple_choice_joint` benchmarks by **text, not by option**: the adapter maps the model's answer
letter to the text of that option (`output_mapping = {"A": <text of option A>, ...}`), and the metric compares that
text with the gold option's text. HELM issue [#4358](https://github.com/stanford-crfm/helm/issues/4358) (open,
2026-09-23) shows with synthetic options that `quasi_exact_match`, which lower-cases and removes ASCII punctuation and
articles, gives full credit to a **wrong** option whose text normalises to the gold's (`-7` vs `7`, `1.25` vs `125`),
and that `quasi_prefix_exact_match` also credits a wrong option that merely starts with the gold's text (`red` vs
`red blue`). Its author says they have "not audited published leaderboard predictions or quantified their impact",
and that MMLU's main metric is `exact_match`.

HELM Lite has three such benchmarks. Their main metrics differ: `exact_match` for MMLU (5 subjects) and OpenBookQA,
but **`quasi_exact_match` for MedQA**. So the collision in #4358 can reach a published HELM Lite headline through
MedQA, and string-identical duplicate options can reach all three. A second hazard follows from the same code: an
output that is not exactly one of the option letters after `strip()` maps to nothing and scores 0, and since HELM Lite
asks for a single output token, the archive cannot say which option was meant.

**Prior art, and what is new here.** #4358 gives the mechanism and synthetic cases only. Issue #4187 (a correct
answer rejected because of trailing punctuation) and #4363 (fractional exact match on probability ties, a different
adapter) are related but different. Audits 89 (MedQA, OpenBookQA) and 75-88 (MMLU) in this catalogue used the same
HELM Lite archives for answer-key questions, never for option collisions. We found no count of option collisions, of
the predictions they over-credit, or of unmapped outputs, on any published HELM leaderboard.

**What we saw before freezing.** HELM's source for `normalize_text`, the four match metrics and the
`compute_reference_metrics` mapping; the `MultipleChoiceJointAdapter` mapping code (letters follow reference order;
nothing shuffles); issue #4358; for MedQA, one run spec (gpt-4-0613: `multiple_choice_joint`, `max_tokens` 1, stop at a
newline, metrics exact / quasi / prefix / quasi-prefix match); for MMLU, one run's predictions (gpt-4-0613,
abstract_algebra: 111 records, each a single capital letter, with `mapped_output` and `exact_match`). While choosing
this audit we also looked at four HELM Lite LegalBench runs, which are free-text, not multiple choice, and are not
part of it. We counted no collisions and no unmapped outputs anywhere.

## Method

1. **Data.** Every HELM Lite release v1.13.0 `multiple_choice_joint` run of MMLU (abstract_algebra,
   college_chemistry, computer_security, econometrics, us_foreign_policy), MedQA (`med_qa:`) and OpenBookQA, one per
   model and subject (newest suite, then the shorter run name): `instances.json` (every non-train item with exactly
   one correct reference) and `display_predictions.json` (output, `mapped_output` and HELM's recorded main metric),
   first trial only.
2. **Graders** (`grade92.py`), applied to every prediction:
   - **H**, HELM's score: the stripped output must be exactly one of the option letters (`A`, `B`, ...); that
     option's text is compared with the gold option's text by the benchmark's main metric (`exact_match` or
     `quasi_exact_match`, transcribed from HELM). Gated against HELM's recorded score.
   - **I**, option identity: 1 when the letter names the gold option itself.
   - **Over-credit**: H 1, I 0, classed `identical` (the chosen option's text is string-identical to the gold's after
     `strip()`) or `quasi_only` (equal only after HELM's normalisation). **Under-credit**: H 0, I 1 (the gold letter
     scored 0, for example because the gold option's text is empty). **Unmapped**: the output names no option
     (`empty`, `lowercase_letter`, `letter_out_of_range`, `other`); H and I are both 0.
3. **Question census.** Each distinct evaluated question (by stem, options and gold) is counted once per benchmark.
   Its gold **collides** with a wrong option when that option's text is `identical`, `quasi_only` (same
   `normalize_text`) or `prefix_only` (its normalised text starts with the gold's, which is what HELM's
   `quasi_prefix_exact_match` credits; that metric is not a main metric in HELM Lite).
4. **Accuracy and rank.** A model's MMLU score is the mean of its 5 subject accuracies; MedQA and OpenBookQA are
   single accuracies. Rank = 1 + the number of models strictly more accurate.
5. **Hand-read.** Every `identical` and `quasi_only` collision question (up to 40) is printed with the gold and
   colliding option texts, and up to 15 `prefix_only` ones; they are read in the next run to say whether the two
   options are genuinely different answers (like `1.5` and `15`) or the same answer twice (a flawed item, where
   crediting either letter is defensible). Option texts are printed only in the job log, never published.

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: all fixtures match; each benchmark has at least 80 models with all its subject runs included (a run has at most 1% of predictions without a gold, scores at least 95% of the median run of its subject, carries HELM's main metric on every item, and our H equals it on at least 99%); H equals HELM on at least 99.9% of all included predictions; HELM's `mapped_output` equals our letter-to-text mapping on at least 99.9% of mapped predictions |
| P2 | #4358 reaches a HELM Lite headline: at least 1 MedQA question has a wrong option that `quasi_exact_match` cannot tell from the gold (`quasi_only`) |
| P3 | But it is small: MedQA over-credits (H 1, I 0, any class) are at most 0.2% of all included MedQA predictions |
| P4 | No model's MedQA rank moves by 3 or more places between H and I |
| P5 | The prefix hazard is larger: across the three benchmarks at least 5 questions have a `prefix_only` collision, and at least twice as many as have a `quasi_only` one |
| P6 | At least 1 evaluated question (any benchmark) repeats the gold option's text, string-identical, as a wrong option |
| P7 | Format loss: at least 3 included models have at least 1% of their MedQA outputs unmapped (scored 0 with no letter HELM can read) |

Reasoning: MedQA options are mostly clinical phrases, but some are numbers, doses or lab values, where `-` and `.`
carry meaning, so a few collisions are plausible but not certain (P2). Even a colliding question only over-credits the
models that pick the colliding wrong option, so the effect on 1,000 questions should be tiny (P3) and too small to move
ranks by 3 places (P4). Numeric options such as `2`, `20` and `24` make prefix matches far easier than equality after
normalisation (P5). We do not know whether any evaluated question repeats its gold text (P6). With one output token,
chat models that open with a word or markup lose the item, and HELM Lite has many chat models (P7).

## What a result would mean

If P2 holds, HELM's MedQA headline in HELM Lite does contain the over-credit #4358 describes, and the results list
exactly which questions and predictions; P3 and P4 then say how much it matters. If P2 fails, #4358 is a real code
hazard that HELM Lite's published MedQA scores happen not to trigger. P5 measures how much more the prefix metric
would expose. P6 counts flawed items that text-based scoring credits on two letters. P7 measures a separate loss that
no re-scoring of the archive can repair. Exploratory, not predicted: every count by benchmark, class and model;
under-credits; unmapped outputs by kind; Kendall's tau-b between H and I accuracies; and the same rank comparison for
MMLU and OpenBookQA.

## Validity gates

Hand-traced fixtures (`cases92.py`, traced in `test_grade92.py`: eight normalisations, eight metric cases including
HELM's empty-prediction rule, eleven grades covering both collision classes, an under-credit, the four unmapped kinds
and a prefix-only case that the main metric does not credit; six collision censuses including a gold that normalises
to nothing; run selection across the three benchmarks; ranks; Kendall's tau-b; three verdict cases on and past every
boundary) must match before any data is read. The job aborts, still writing diagnostics, if a benchmark has fewer
than 80 included models or our transcription of HELM's scoring agrees with HELM's recorded score on under 99.9% of
included predictions. The unit tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads HELM Lite's MMLU, MedQA and OpenBookQA outputs (about 90 models x 7 runs)
```

## Files

- `grade92.py`: HELM's normalisation and match metrics transcribed, the letter mapping, H and I, the collision census,
  run selection, ranks, Kendall's tau-b and the verdicts
- `cases92.py`: data source, gates, thresholds and the fixtures
- `job.py`: downloads, gates, grades, census, ranks; writes `results.json` and `flips.json`
- `test_grade92.py`: unit tests with the hand traces; `requirements.txt`: none (standard library)

## Licence

Code is Apache-2.0 (HELM's `normalize_text` and match metrics are transcribed from stanford-crfm/helm, Apache-2.0;
HELM takes `normalize_text` from the QuAC scorer). This write-up and any results are CC BY 4.0. Upstream: MMLU and
MedQA are MIT; OpenBookQA is Apache-2.0; HELM's outputs are published by Stanford CRFM. Only benchmarks, subjects,
HELM instance ids, option letters, classes, counts and public model names are published, never question, option or
model text. Authored by AI agents working in MV2's name (Munim, Inc.).
