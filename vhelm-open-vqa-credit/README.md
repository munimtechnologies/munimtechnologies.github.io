# Audit 122: how VHELM credits open-ended short answers in GQA, VQAv2 and VizWiz (pre-registered)

**Status: pre-registered 2026-11-15, results pending.** Part of [eval-reliability-audits](../eval-reliability-audits/),
by MV2 of Munim, Inc. Made with AI agents working in MV2's name.

## What this targets

VHELM, HELM's vision-language leaderboard (run suite v2.1.2), asks GQA, VQAv2 (`vqa_base`) and VizWiz questions for a
short free-text answer ("Answer the question using a single word", up to 20 tokens, no stop sequence). Its main metric
for all three is `quasi_prefix_exact_match`: an answer scores 1 when `normalize_text(answer)` **starts with**
`normalize_text(reference)` for **any** reference tagged correct (HELM takes the max over references).
`normalize_text` lower-cases and removes ASCII punctuation, the English articles `a`, `an` and `the`, and extra spaces.
How the references are built (from HELM's scenario code):

- **GQA:** two correct references, the short answer and the full-sentence answer.
- **VQAv2:** all 10 annotator answers, **not de-duplicated**. An answer that only one of ten annotators gave (for
  example `maybe` on a yes/no question, next to five `yes` and four `no`) is a full correct reference. The official VQA
  metric gives such an answer 0.3: `min(1, matches / 3)`, averaged over the ten sets of nine annotators.
- **VizWiz:** the distinct answers that annotators gave with confidence `yes`.

The prefix rule works on characters, not words. It credits a sentence that starts with the answer (`No, it is not`
for `no`), and also a different word that merely starts with the reference's letters (`carpet` for `car`; `none` for
`no`).

This audit re-grades every first-trial answer of every GQA, VQAv2 base and VizWiz run in the public bucket and
counts:

- **Credit classes:** `match` (the answer equals a reference after normalisation), `word_prefix` (it starts with a
  reference and then continues with a space), `mid_word` (it continues the reference's last word: `carpet` / `car`) and
  `empty_ref` (only a reference that normalises to nothing credits it).
- **VQAv2 consensus:** for each credited answer, `m`, the number of the ten annotators whose answer equals it after
  HELM's normalisation, and a VQA-style consensus accuracy **C** (leave-one-annotator-out mean of `min(1, m / 3)`).
  C uses HELM's `normalize_text`, **not** the official VQA answer processing (which also maps number words to digits
  and repairs contractions), so it is an approximation of the official metric, not a re-implementation.
- **Grounding markup:** answers that carry `<ref>` / `<box>` tags, as some Qwen-VL Chat outputs do.

## Prior art

- HELM issues and PRs searched for `vqa`, `viz_wiz`, `vizwiz`, `gqa`, `quasi_prefix_exact_match` and `article`
  (2026-11-15): only the scenario-adding issues and PRs (#1950, #1951, #1983) and unrelated items. Nothing on how the
  references are built or on prefix credit.
- The VHELM paper (Lee et al., [arXiv 2410.07112](https://arxiv.org/abs/2410.07112)) lists VQAv2 and VizWiz with
  "Exact Match" and gives no count of either effect.
- Ye et al., [arXiv 2607.10240](https://arxiv.org/abs/2607.10240) (July 2026), study the opposite direction: right
  answers that short-answer VQA scorers reject because of their surface form. They do not mention HELM, any-annotator
  credit or prefix credit.
- HELM [#4358](https://github.com/stanford-crfm/helm/issues/4358) and our audits 92 and 121 cover prefix collisions
  between **multiple-choice option texts**. Audit 120 covers letter golds that normalise to nothing. This audit covers
  free-text answers.

## What we looked at before pre-registering

These were read by hand from the public bucket, so they are not predictions:

- GQA `stats.json` means, H (`quasi_prefix_exact_match`) and Q (`quasi_exact_match`), for four models: PaliGemma 3B
  Mix 448 0.748 / 0.746; IDEFICS 9B Instruct 0.308 / 0.128; Claude 3 Opus 0.472 / 0.457; GPT-4o (2024-11-20)
  0.592 / 0.581. The GQA leaderboard table has 48 model rows; Qwen-VL Chat shows 0.0.
- GQA answers: the first 25 from IDEFICS 9B Instruct (mostly full sentences, a few bare `Answer:`), and about 300 from
  Qwen-VL Chat (most are grounding markup, `<ref>...</ref><box>(x,y),(x,y)</box>`). Of GPT-4o's first 39 GQA answers
  none was a prefix-only credit.
- VQAv2: the references of the first 10 questions (10 each, often split, e.g. 5 and 5, or 5, 4 and 1), and
  PaliGemma 3B Mix 448's means (H 0.838, Q 0.835).
- We computed no count over runs and no per-record class.

## Method

`job.py` lists every `gqa`, `vqa` (`groups=vqa_base`, no data augmentation) and `viz_wiz` run of suite v2.1.2 in
`crfm-helm-public` (51 + 51 + 51 listed on 2026-11-15) and reads `instances.json`, `display_predictions.json` and
`stats.json`. For every first-trial record it computes H (HELM's score, transcribed in `grade122.py`), Q, the credit
class, `m` and, on VQAv2, C. A run is kept only if:

- our H mean equals `stats.json`'s `quasi_prefix_exact_match` and our Q mean its `quasi_exact_match` (unperturbed,
  `valid` split, within 1e-9);
- our H equals the per-record `quasi_prefix_exact_match` stored in `display_predictions.json` on at least 99% of the
  records that carry one;
- no record lacks an instance or appears twice.

Model scores are run means (one run per model and scenario). Ranks (1 + the number of models scoring strictly higher)
are compared between H and Q, H and H without `mid_word` / `empty_ref` credits, and on VQAv2 between H and C. These are
our ranks over the included runs, which may include a few models that the leaderboard table leaves out.
Tests: `python -m unittest -v` (14 hand-traced tests). Standard library only.

### Predictions (frozen before any measurement)

- **P1:** at least 99% of listed runs in each scenario (GQA, VQAv2 base, VizWiz) pass every reproduction gate.
- **P2:** pooled over VQAv2 base, at least 2% of HELM's credits go to answers that only 1 or 2 of the 10 annotators
  gave (`m` = 1 or 2).
- **P3:** on VQAv2 base, the median model's H - C is at least 0.03.
- **P4:** on VQAv2 base, at least one model moves 3 or more places between H and C.
- **P5:** pooled over GQA, `mid_word` credits are under 1% of HELM's credits.
- **P6:** on GQA, at least 3 models get 5% or more of their credits from `word_prefix` answers.
- **P7:** Qwen-VL Chat has grounding markup in at least 90% of its answers in both VQAv2 base and VizWiz (its GQA
  share is reported as a check, since we have seen it).
- **P8:** pooled over VQAv2 base, credits where no annotator gave the answer (`m` = 0, prefix-only) are under 1% of
  HELM's credits.

## Files

- `grade122.py`: transcribed HELM `normalize_text`, `quasi_exact_match` and `quasi_prefix_exact_match`, the credit
  classes, `m`, C, markup detection, run-file readers, ranks and verdicts.
- `test_grade122.py`: hand-traced unit tests.
- `job.py`: the measurement (results will be added below as `## Results` with `results.json`).

## Sources

- HELM (Stanford CRFM, Apache-2.0): `gqa_scenario.py`, `vqa_scenario.py`, `viz_wiz_scenario.py`, `vlm_run_specs.py`,
  `evaluate_reference_metrics.py`, `schema_vhelm.yaml`, `qwen_vlm_client.py`; VHELM runs in
  `gs://crfm-helm-public/vhelm/benchmark_output/runs/v2.1.2/`.
- GQA: Hudson and Manning, [arXiv 1902.09506](https://arxiv.org/abs/1902.09506). VQAv2: Goyal et al.,
  [arXiv 1612.00837](https://arxiv.org/abs/1612.00837); the VQA accuracy metric and answer processing:
  https://visualqa.org/evaluation.html. VizWiz: Gurari et al., [arXiv 1802.08218](https://arxiv.org/abs/1802.08218).

## Licence

Code is Apache-2.0. Write-up and results are CC BY 4.0. Only run names, instance ids, classes, counts and public model
names are published; no dataset content or model output text.
