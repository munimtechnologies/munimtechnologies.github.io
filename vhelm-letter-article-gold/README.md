# Audit 120: VHELM gives full credit for any answer when the gold option is "A" (pre-registered)

**Status: pre-registered 2026-11-14, results pending.** Part of [eval-reliability-audits](../eval-reliability-audits/),
by MV2 of Munim, Inc. Made with AI agents working in MV2's name.

## What this targets

VHELM (HELM's vision-language leaderboard, run suite v2.1.2, 51 models) scores three letter-answer scenarios with
`quasi_prefix_exact_match` as the main metric: **EXAMS-V** (`exams_v`, the model reads the question and options in
an image and answers with a letter within 20 tokens), **MM-Star** (`mm_star`) and **BLINK** (`blink`) (both one-token
letter answers). The gold is the option letter.

`quasi_prefix_exact_match(gold, pred)` is `normalize_text(pred).startswith(normalize_text(gold))`, and
`normalize_text` lower-cases, removes ASCII punctuation and **removes the English articles `a`, `an` and `the`**
(HELM, `src/helm/benchmark/metrics/evaluate_reference_metrics.py`). So the gold `A` normalises to the empty string,
every string starts with the empty string, and **every non-empty answer to a question whose gold is `A` is scored
correct**: a wrong letter, the word `The`, or a step-by-step opening cut off at 20 tokens. This is code-certain; the
job measures how much of the published credit it accounts for.

**In half of BLINK a fixed answer gets full marks.** VHELM runs all 14 BLINK tasks (val split). By the Hugging Face
statistics of BLINK-Benchmark/BLINK, 7 of them have exactly two options per question: Art_Style (117 questions, 55 `A`
and 62 `B`), Jigsaw (150; 79 / 71), Multi-view_Reasoning (133; 59 / 74), Object_Localization (122; 53 / 69),
Relative_Depth (124; 64 / 60), Spatial_Relation (143; 77 / 66) and Visual_Similarity (135; 64 / 71). On these 924
questions the constant answer B is credited on every `B` gold (a real match) and on every `A` gold (the empty-gold
match), so **it scores 1.0 on all seven tasks**. On a four-option task it scores the share of `A` and `B` golds.

HELM has met this before: PR #3257 (merged 2025-01-08) added `quasi_leave_articles_exact_match` after a
"quasi_prefix_match_failure" on RealWorldQA and made it RealWorldQA's main metric. EXAMS-V, MM-Star and BLINK still
use the article-removing metric. HELM issue #2298 and open PR #4315 cover the opposite effect in `f1_score` (an `A`
answer scored 0); neither mentions `quasi_prefix_exact_match` or over-credit. An issue search for
`quasi_prefix_exact_match`, `normalize_text`, `exams`, `Croation` and articles found nothing else on this.

### Two further EXAMS-V defects, also code-certain

- **Bulgarian golds are Cyrillic letters, but the prompt asks for Latin ones.** HELM sends only the image and the
  instruction "The image has a multiple-choice question with four options. Answer the multiple choice question by just
  giving the corresponding letter: 'A' for the first choice, 'B' for the second choice, 'C' for the third choice, 'D'
  for the fourth choice." It takes the gold from the dataset's `answer_key` unchanged. In Rocktim/EXAMS-V (test split,
  4,797 rows, no revision pinned by HELM) **398 answer keys are Cyrillic letters** (`А Б В Г` and lower-case forms).
  A model that follows the instruction exactly can never be credited on them; only answers in Cyrillic can.
- **Every Croatian run is empty.** HELM's scenario lists the language as `Croation`; the dataset spells it `Croatian`
  (585 test rows). The filter keeps nothing, so VHELM's `exams_v` Croatian runs contain 0 instances.

The dataset also has 32 golds `E` and 2 golds `2`, which the four-option instruction never offers, and 46 Slovakian
rows that HELM does not list (counts are over the whole test split, including text-only rows VHELM does not run).

## What we looked at before pre-registering

Read by hand from the public bucket, so these are not predictions:
- EXAMS-V Serbian / Natural Science, Llama 4 Scout: 86 questions, 35 credited. 20 golds are `A` and **all 20 are
  credited**; only 4 of those answers are the letter A. 15 are step-by-step openings cut at 20 tokens and one is the
  letter C. Every one of the model's 15 credited step-by-step openings is on an `A`-gold question.
- MM-Star coarse perception, IDEFICS 9B instruct: 250 questions, 133 credited. The one-token answers include
  non-letters such as the word `The`; the 15 credited non-letter answers we listed are all on `A`-gold questions.
- EXAMS-V Bulgarian / Natural Science: all 54 golds are Cyrillic (53 capitals, 1 lower-case). GPT-4o (2024-11-20)
  answered with a Latin letter 41 times (all scored 0) and a Cyrillic letter 13 times (5 credited); Llama 4 Scout
  scored 0 of 54.
- EXAMS-V Croatian / Natural Science, GPT-4o (2024-11-20): `instances.json` and `stats.json` are both empty lists.
- BLINK Art_Style, IDEFICS2 8B: 117 questions, each with two options (the BLINK val split has 55 golds `(A)` and 62
  `(B)`). The model answered B 92 times and A 25 times; **all 92 B answers are credited** and 8 of the 25 A answers
  are, so it scores 100 of 117 (0.855); answers that name the gold letter are 53 of 117 (0.453). In a task whose golds
  are only A and B, **the constant answer B scores 1.0** (code-certain).

## Method

`job.py` lists every `exams_v`, `mm_star` and `blink` run of suite v2.1.2 in the public bucket `crfm-helm-public`,
reads `instances.json`, `display_predictions.json` and `stats.json`, and keeps a run only if our transcription of
`quasi_prefix_exact_match` (`grade120.py`) reproduces every stored record score and the run mean (main split: test for
EXAMS-V, valid for MM-Star and BLINK; no perturbations). Each credited record is classed `genuine`,
`free_article_gold` (the gold normalises to nothing and the answer's first word is not the gold letter) or
`prefix_word` (for example `Both` for the gold B). The corrected **letter grade** keeps articles (HELM's own
`should_remove_articles=False`) and needs the answer's first word to equal a one-word gold. Model means are the mean of
run means within each scenario family (our aggregation, which may differ from a leaderboard cell). For Cyrillic golds,
a Latin letter answer is also checked against the gold by position (a = А, b = Б, c = В, d = Г).
Tests: `python -m unittest -v` (15 hand-traced tests). Standard library only.

### Checks (code-certain)

- **C1:** no record whose gold normalises to nothing and whose answer is non-empty is stored as 0.
- **C2:** count the runs with no main-split instances, by language (expect every Croatian EXAMS-V run).
- **C3:** no Bulgarian record answered with a Latin letter is credited.

### Predictions (frozen before any measurement)

- **P1:** at least 99% of non-empty runs in each family are reproduced (every stored record and the run mean).
- **P2:** in MM-Star and in BLINK, at least 20% of records have a gold that normalises to nothing. (Written before we
  read BLINK's Hugging Face statistics. Those show 451 `A` golds of 924 (48.8%) in the seven two-option tasks, so the BLINK half
  of P2 was close to known before the job ran; the MM-Star half was not.)
- **P3:** pooled over the three families, at least 5% of published credits are `free_article_gold`.
- **P4:** at least 10 models lose 0.05 or more of their mean in at least one family under the letter grade.
- **P5:** in at least one family, Kendall tau-b between the published and letter-grade model orders is below 0.90.
- **P6:** `prefix_word` credits are under 0.5% of pooled published credits.
- **P7:** on Bulgarian EXAMS-V, at least 60% of answers whose first word is a single letter use a Latin letter.
- **P8:** at least 35% of those Latin letter answers name the gold option by position, and all score 0.

## Files

- `grade120.py`: transcribed HELM `normalize_text` and `quasi_prefix_exact_match`, our letter grade and classes.
- `test_grade120.py`: hand-traced unit tests.
- `job.py`: the measurement (results will be added below as `## Results` with `results.json`).

## Sources

- HELM (Stanford CRFM, Apache-2.0): `vlm_run_specs.py`, `exams_v_scenario.py`, `evaluate_reference_metrics.py`,
  `schema_vhelm.yaml`; VHELM runs in `gs://crfm-helm-public/vhelm/benchmark_output/runs/v2.1.2/`.
- EXAMS-V: Das et al., arXiv 2403.10378; dataset Rocktim/EXAMS-V on Hugging Face.
- MM-Star: Chen et al., arXiv 2403.20330. BLINK: Fu et al., arXiv 2404.12390.

## Licence

Code is Apache-2.0. Write-up and results are CC BY 4.0. Only run names, instance ids, classes, counts and public model
names are published; no dataset content or model output text.
