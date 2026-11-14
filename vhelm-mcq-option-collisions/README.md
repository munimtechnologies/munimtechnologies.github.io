# Audit 121: does HELM's option-text scoring reach VHELM's published multiple-choice scores? (pre-registered)

**Status: pre-registered 2026-11-14, results pending.** Part of [eval-reliability-audits](../eval-reliability-audits/),
by MV2 of Munim, Inc. Made with AI agents working in MV2's name.

## What this targets

HELM's `multiple_choice_joint` adapter turns the model's answer letter into the **text** of that option
(`output_mapping`), and the reference metrics then compare that text with the gold option's text. HELM issue
[#4358](https://github.com/stanford-crfm/helm/issues/4358) (open) shows, at the helper level, that the loose metrics can
then credit a wrong option. Its author notes that MMLU's main metric is `exact_match`, so the issue "does not establish
an error in published MMLU headline scores". Our [audit 92](../mcq-helm-option-collisions/) measured the effect on
HELM Lite and found it small: one MedQA question, 20 of 91 models over-credited.

**VHELM is different: there the loose metric is the headline.** In `schema_vhelm.yaml` the main metric of A-OKVQA
(all variants), MMMU, SEED-Bench, POPE, MME, PAIRS, FairFace and Hateful Memes is `quasi_prefix_exact_match`:
`normalize_text(pred).startswith(normalize_text(gold))`, where `normalize_text` lower-cases, removes ASCII punctuation
and removes the English articles `a`, `an` and `the`. Under this metric a chosen wrong option is credited in full when:

- **gold_empty:** the gold option's text normalises to nothing (an option that is just the letter `A`, or `The`), so
  every non-empty option starts with it;
- **identical / quasi_only:** its text equals the gold's, exactly or after normalisation (`-7` vs `7`);
- **prefix_only:** its normalised text merely starts with the gold's (`red` vs `red couch`; `Project A` normalises to
  `project`, which `Project B` starts with; in Chinese, which has no spaces, `红` vs `红色`).

VHELM also runs A-OKVQA through **machine translation** into Chinese, Hindi, Spanish and Swahili, an AAVE dialect
rewrite and a robustness group. The translated options are new strings, so translation can create collisions the English
options never had (two options rendered as the same word, or one as a prefix of another). The published cell for these
groups is HELM's **per-question worst case** over the English copy and the perturbed copy (for example GPT-4o
2024-11-20 on A-OKVQA Chinese: English 0.892, Chinese copy 0.861, published worst case 0.843; the dialect cell, 0.884,
is the `fairness` worst case).

This audit counts, on every A-OKVQA, MMMU (multiple-choice) and SEED-Bench run of VHELM run suite v2.1.2, how many
**published** credits go to a wrong option, and why. POPE, MME and Hateful Memes (yes/no options), PAIRS (the gold is
always "unclear") and FairFace (category labels) are left out.

## Prior art

- HELM #4358 (helper level, no published-score count); our audit 92 (HELM Lite, main metrics `exact_match` /
  `quasi_exact_match`).
- The narrower "gold `A` normalises to nothing" bug has been reported in other evaluation code in 2026, for example
  UltraRAG [#509](https://github.com/OpenBMB/UltraRAG/issues/509) (fixed) and HELMET
  [#48](https://github.com/princeton-nlp/HELMET/issues/48) (open). Our [audit 120](../vhelm-letter-article-gold/)
  covers the same thing in VHELM's letter-gold generation scenarios (EXAMS-V, MM-Star, BLINK). Here the gold is an
  option *text* reached through the letter mapping, a different path.
- An issue search on stanford-crfm/helm for `quasi_prefix_exact_match`, `article` and `a_okvqa` found nothing on
  VHELM's published scores.

## What we looked at before pre-registering

Read by hand from the public bucket, so these are not predictions:
- A-OKVQA base, GPT-4o (2024-11-20): the options of the first 40 questions. None of them collides; one has the options
  `yes | absolutely no | probably yes | probably no`.
- A-OKVQA Chinese, same model: the first 15 translated questions. No collision among them; the translation has
  quirks (`van` became a word meaning "pass by"; `30 | 20 | 50 | 25` became a mix of Chinese numerals and digits).
- MMMU Accounting, same model: all 30 questions. Two have the options `A | B | Not enough information` and one
  `Project A | Project B`; the gold is `B` in all three, so none of them collides.
- `stats.json` structure (original, `perturbed` and `worst` entries) and two leaderboard cells (above). SEED-Bench's
  main split is `test`, A-OKVQA's and MMMU's `valid`.

## Method

`job.py` lists every `a_okvqa`, `mmmu` (`question_type=multiple-choice`) and `seed_bench` run of suite v2.1.2 in the
public bucket `crfm-helm-public` and reads `instances.json`, `display_predictions.json` and `stats.json`. For every
first-trial record it computes **H**, HELM's score (stripped answer -> option letter -> option text ->
`quasi_prefix_exact_match` against the gold option text, transcribed in `grade121.py`), and **I**, option identity (1
when the letter names the gold option). A run is kept only if our H reproduces, within 1e-9, every
`quasi_prefix_exact_match` mean in its `stats.json` that applies: the original records, each perturbed variant, and
the worst case the leaderboard shows (`fairness` when a perturbation is a fairness one, `robustness` when it is a
robustness one, else the perturbation's own name, as for translation). Our letter -> option text must also equal HELM's
stored `mapped_output` on at least 99% of the run's records. The published record set is the per-question worst case
for augmented runs and the original records otherwise. A published over-credit is H 1 and I 0 on that set.

The question census counts each distinct question once per variant (each translated language and each augmented group
separately), with the classes above. Model means are the mean of run means within each VHELM group (our aggregation,
which may differ slightly from a leaderboard cell); ranks are compared between H and I.
Tests: `python -m unittest -v` (13 hand-traced tests). Standard library only.

### Predictions (frozen before any measurement)

- **P1:** at least 99% of listed runs in each family (A-OKVQA, MMMU, SEED-Bench) pass every reproduction gate.
- **P2:** at least 5 distinct MMMU multiple-choice questions have a gold option that normalises to nothing.
- **P3:** pooled over the four translated A-OKVQA languages, at least 10 questions collide (identical, quasi_only or
  prefix_only), and their share of translated questions is at least 3 times the share among the English A-OKVQA
  questions.
- **P4:** at least one translated A-OKVQA question has a wrong option string-identical to the gold.
- **P5:** pooled over all included runs, published over-credits are under 1% of published credits.
- **P6:** no model moves 3 or more places between H and I in any VHELM group studied.
- **P7:** the Chinese translation has more prefix_only questions than the Spanish one.
- **P8:** at least 3 models have 1% or more of their A-OKVQA base answers mapping to no option.

## Files

- `grade121.py`: transcribed HELM `normalize_text` and `quasi_prefix_exact_match`, the letter mapping, graders, the
  question census, the worst case over copies, ranks and verdicts.
- `test_grade121.py`: hand-traced unit tests.
- `job.py`: the measurement (results will be added below as `## Results` with `results.json`).

## Sources

- HELM (Stanford CRFM, Apache-2.0): `vlm_run_specs.py`, `evaluate_reference_metrics.py`, `schema_vhelm.yaml`; VHELM
  runs in `gs://crfm-helm-public/vhelm/benchmark_output/runs/v2.1.2/`.
- A-OKVQA: Schwenk et al., arXiv 2206.01718. MMMU: Yue et al., arXiv 2311.16502. SEED-Bench: Li et al., arXiv
  2307.16125.

## Licence

Code is Apache-2.0. Write-up and results are CC BY 4.0. Only run names, instance ids, letters, classes, counts and
public model names are published; no dataset content or model output text.
