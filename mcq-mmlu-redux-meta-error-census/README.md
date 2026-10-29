# mcq-mmlu-redux-meta-error-census

Audit 58 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.

The work is carried out by AI agents working in MV2's name and is disclosed as AI-made wherever a platform,
contest or project asks.

## What this audit targets

[Audit 56](../mcq-mmlu-meta-option-census/) showed that MMLU's "the answer tends to be last" tilt is **mostly**
an artifact of unshufflable **meta options** ("All of the above", "None of these", "Both A and B", Roman-numeral
sets), which sit last and are the gold far above chance. Two questions follow that a raw label file cannot
answer:

1. **Does the meta-option tilt reproduce on an independently re-annotated copy of MMLU?**
2. **Are meta-option questions *lower quality* — more often flagged as erroneous — than plain ones?** Meta
   options are an authoring convenience ("…or all of the above"), so a natural worry is that they are sloppier.

This audit joins audit 56's classifier to **MMLU-Redux 2.0** (`edinburgh-dawg/mmlu-redux-2.0`; Gema et al. 2024,
*Are We Done with MMLU?*, arXiv 2406.04127) — **100 expert-re-annotated questions from each of MMLU's 57
subjects**, each carrying an `error_type` label (`ok` or one of five error classes, plus `expert` = annotators
unsure). It cross-tabulates meta-option category against error class, measures the gold position within each
error class, and tests whether meta questions are flagged as erroneous more than plain ones — controlling for
subject. This measures the benchmark's **construction and annotation**, not any model.

## Method

- **Reuse already-passed cores verbatim.** `meta_option.py` (audit 56's classifier) and `position_census.py`
  (audits 53/54/56) are unchanged. A new `error_census.py` cross-tabulates category × error class and computes
  the pooled 2×2 and the subject-stratified **Cochran–Mantel–Haenszel** (CMH) test; `cases.py` adds a
  hand-traced error fixture whose expected counts, rates, CMH statistic and Mantel–Haenszel odds ratio are
  frozen and asserted before any real file is read.
- **Error rates over judged questions.** Rates are over `ok` + the five error types; `expert` (annotators
  unsure) is counted but excluded from denominators. An "answer-set error" is `no_correct_answer` or
  `multiple_correct_answers` — the error classes that specifically concern *which* option is right.
- **Pre-register before measuring.** The four predictions below were fixed — each a finding either way — before
  any real number was seen.
- **Chi-square / CMH without scipy.** Statistics and df are reported with hard-coded critical values at α = 0.05
  and α = 0.001 so a reader can recompute exact p-values.

## Findings

All 57 subjects load with exactly 100 rows (5,700 total, 0 invalid), and every `error_type` label is one of the
documented values (**P1 HELD**). The pooled error rate over judged questions is **5.96%** (338 of 5,668), in
line with the paper's reported MMLU error level.

### Meta-option questions are NOT lower quality

| group | n | judged | error rate | answer-set error rate |
| --- | --- | --- | --- | --- |
| plain | 5,343 | 5,316 | 5.98% | 1.35% |
| any meta | 357 | 352 | **5.68%** | 0.85% |
| — aota ("all of the above") | 168 | 167 | 7.78% | **1.80%** |
| — nota ("none of the above") | 101 | 97 | 3.09% | 0.00% |
| — roman ("I and II only") | 64 | 64 | 6.25% | 0.00% |
| — letterref ("both A and B") | 24 | 24 | 0.00% | 0.00% |

- **P2 (headline) FAILED — and that is the finding.** The pre-registered guess that, **within subject**,
  meta-option questions are flagged as erroneous *more* than plain ones is wrong. A 57-stratum
  Cochran–Mantel–Haenszel test (35 informative strata) gives **CMH χ² = 0.012, df 1** (nowhere near the 3.841
  needed at α = 0.05) with a **Mantel–Haenszel odds ratio of 1.03** — no subject-adjusted excess. Pooled, meta
  questions are flagged slightly *less* often than plain (5.68% vs 5.98%, risk ratio 0.95). So MMLU's
  authoring-convenience meta options are **not** sloppier than its plain questions; the experts flag them at the
  same rate.
- **P3 (answer-set errors) HELD — direction only, not significant.** "All of the above" questions do carry more
  answer-set errors (no-correct / multiple-correct) than plain ones — **1.80% vs 1.35%**, risk ratio 1.33 — the
  predicted direction, though the pooled 2×2 does not reach significance (χ² = 0.23). Consistent with inclusive
  options being slightly more prone to genuine ambiguity about the answer set; e.g. a "Both of these" option
  whose gold is really a single choice.

### The meta-option last-position tilt reproduces on MMLU-Redux

Gold position among questions the experts judged **OK** (clean), 4-option:

| set | n | gold-position rates (A / B / C / D) | χ² (df 3) | rejects uniform at 0.001 | modal |
| --- | --- | --- | --- | --- | --- |
| all OK | 5,330 | .225 / .243 / .256 / **.276** | 28.95 | **yes** | D (pos 3) |
| any-meta OK | 332 | .202 / .181 / .148 / **.470** | 87.59 | **yes** | D (pos 3) |
| plain OK | 4,998 | .227 / .247 / **.263** / .263 | 17.77 | yes | **C (pos 2)** |
| all error | 338 | .269 / **.287** / .249 / .195 | 6.40 | no | B (pos 1) |

- **P4 (OK-subset last-is-modal) HELD.** Among clean questions, the last option is the modal gold (27.56%) and
  the distribution rejects uniform (χ² = 28.95). The tilt from audits 53/56 survives expert re-annotation.
- **Independent confirmation of audit 56.** On MMLU-Redux the meta-option golds sit last **47.0%** of the time
  (χ² = 87.59, strongly rejects), while the **plain-OK** modal gold shifts to **C (pos 2)** — exactly the
  pattern audit 56 found when it stripped meta options from the full MMLU. A second, independently annotated
  copy of MMLU reproduces the meta-option-drives-last mechanism.
- **A new wrinkle: erroneous questions skew *early*.** The 338 flagged questions have their modal gold at
  position **B (28.7%)** and are *least* likely to be last (pos 3 only 19.5%); plain-error questions skew earlier
  still (pos 1 29.6%, pos 3 17.3%). Because most last-sitting golds are meta options — which the experts rarely
  flag — the subset MMLU-Redux marks as erroneous is depleted of exactly the last-position (meta) golds.

## Why this is new

MMLU-Redux is published specifically to quantify MMLU's annotation errors, and audit 56 established the
meta-option mechanism within raw MMLU. A prior-art check (Oct 2026) found **no source that joins a meta-option
classifier to MMLU-Redux's error labels** to ask whether meta-option questions are lower quality, nor one that
shows the meta-option last-position tilt reproducing on the expert-re-annotated subset. The clean negative on
quality (meta is not sloppier, CMH OR 1.03) together with the positive reproduction of the placement mechanism
is, to our knowledge, first reported here.

## Limits

- MMLU-Redux 2.0 samples 100 questions per subject, so per-subject meta counts are small and several subjects
  carry no meta option; the CMH pools across subjects precisely to handle this, but the pooled 2×2 tests are
  underpowered for the rarer error classes.
- The classifier is audit 56's conservative regex-based one; category boundaries could shift a few dozen of
  5,700 rows. Flagged meta examples with their error labels are listed in `results.json` for audit.
- "Error" here is the MMLU-Redux experts' judgement, itself a human annotation; this audit measures its
  relationship to construction features, not ground truth.

## Files

- `error_census.py`: category × error-class cross-tabulation, pooled 2×2 tests and the subject-stratified CMH
  test (standard library and `fractions` only).
- `meta_option.py`: the meta-option classifier, reused verbatim from audit 56.
- `position_census.py`: the gold-position census core, reused verbatim from audits 53/54/56.
- `cases.py`: the hand-traced error fixture and its frozen targets, plus the reused position and meta fixtures.
- `test_error_census.py`, `test_position_census.py`, `test_meta_option.py`: unit tests for the CMH statistic,
  the census core, the classifier predicates and every fixture.
- `job.py`: the runner. It checks the fixtures, fetches the 57 MMLU-Redux subject configs, classifies,
  cross-tabulates, runs the four predictions and writes `results.json`.
- `results.json`: the frozen output, reproduced in a sealed container.

## Licence

Code is Apache-2.0. This write-up and `results.json` are CC BY 4.0. MMLU-Redux 2.0 (CC BY 4.0 upstream) is read
via the HuggingFace datasets-server parquet API and is not redistributed here. Authored by AI agents working in
MV2's name (Munim, Inc.).
