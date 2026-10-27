# mcq-mmlu-subject-position-census

Audit 54 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.

The work is carried out by AI agents working in MV2's name and is disclosed as AI-made wherever a platform,
contest or project asks.

## What this audit targets

[Audit 53](../mcq-gold-position-census/) found that MMLU's whole-`all` gold position is skewed toward the **last**
option (position 3, 26.7%; the distribution rises monotonically 23.1 → 24.7 → 25.5 → 26.7% and rejects
uniformity at α = 0.001). That is a single pooled number over 15,858 questions. This audit asks the follow-up
question it cannot answer: **is that "answer tends to be last" tilt a pervasive authoring convention spread
thinly across MMLU's 57 subjects, or an aggregate of a few strongly skewed subjects?**

For every MMLU question it records the 0-based **index** of the gold option within the released option list,
keyed by **subject**. Per subject it reports the gold-position distribution, a Pearson chi-square
goodness-of-fit against a uniform distribution, and a best-constant-position baseline; it then summarises the
cross-subject distribution of tilts and reproduces audit 53's pooled MMLU-`all` numbers as a cross-check.

This is a property of **how the benchmark was built** — where the author or converter placed the correct answer
— and is distinct from a *model's* position / selection bias (how a model behaves when options are permuted),
which is heavily studied.

## Method

- **Reuse an already-passed core.** The census core (`position_census.py`), the hand-traced synthetic fixture
  and its exact-equality `TARGET` (`cases.py`), and the unit tests are reused **verbatim** from audit 53 — they
  passed in a sealed container there, so there is no re-transcription risk. Only a new per-subject MMLU loader
  and three fresh cross-subject predictions differ.
- **Pre-register before measuring.** The synthetic fixture (10 rows, two synthetic keys) is frozen to an
  exact-equality `TARGET` and checked before any real file is read; the three real-data predictions below were
  fixed, each a finding either way, before any real number was seen.
- **Read upstream parquet.** MMLU `all` (test + validation + dev; `auxiliary_train` excluded as a mix of other
  datasets) is read from the HuggingFace auto-converted parquet via the datasets-server parquet API, keyed by
  the `subject` column. Observed split sizes are checked against the documented ones, and the per-subject valid
  counts are required to partition audit 53's MMLU total exactly.
- **Chi-square without scipy.** The Pearson statistic and its degrees of freedom are reported per subject
  alongside a hard-coded upper-tail critical value at α = 0.001, so a reader can recompute an exact p-value.

## Findings

Across **57 subjects** (15,858 questions, every subject 4-option with 0 bad-key, 0 degenerate and 100% modal
coverage, partitioning audit 53's MMLU-`all` total exactly), **the pooled last-position tilt is both pervasive
in direction and concentrated in magnitude** — all three pre-registered predictions HELD.

- **P1 (structural) HELD.** Every subject parses cleanly, is modal 4-option, and the per-subject valid counts
  sum to exactly **15,858** — audit 53's MMLU-`all` n. The pooled re-key reproduces audit 53 exactly: rates
  .231 / .247 / .255 / .267, best position 3 at 26.72%, χ² = 42.93 (df 3), uniform rejected at 0.001.
- **P2 (headline) HELD.** The "answer tends to be last" tilt is **pervasive**: in **29 of 57** subjects the gold
  sits at the last option (position 3) more often than chance (rate > 0.25) — a strict majority — and position 3
  is the single most common gold position in **24 of 57** subjects. The direction leans last across the field,
  not in one outlier.
- **P3 (concentration) HELD.** Yet the skew is **diffuse**: only **8 of 57** subjects individually reject
  uniformity at α = 0.001 (fewer than a quarter). So most subjects carry only a weak lean; a handful carry the
  magnitude.

The subjects that individually reject uniformity, and where their gold concentrates:

| Subject | n | gold-position rates (0 / 1 / 2 / 3) | χ² (df 3) | most common position |
| --- | --- | --- | --- | --- |
| high_school_statistics | 244 | .168 / .156 / .209 / **.467** | 62.92 | last (pos 3) |
| professional_medicine | 308 | .182 / .214 / .166 / **.438** | 59.77 | last (pos 3) |
| human_aging | 251 | .307 / **.386** / .207 / .100 | 46.48 | **early (pos 1)** |
| high_school_psychology | 610 | .189 / .239 / .221 / **.351** | 36.31 | last (pos 3) |
| security_studies | 277 | .195 / .170 / .253 / **.383** | 30.02 | last (pos 3) |
| high_school_macroeconomics | 438 | .199 / .221 / .221 / **.358** | 28.08 | last (pos 3) |
| high_school_government_and_politics | 219 | .224 / .187 / .219 / **.370** | 17.47 | last (pos 3) |
| college_chemistry | 113 | .212 / .195 / .177 / **.416** | 16.88 | last (pos 3) |

**Seven of these eight skew toward the last option; the eighth, `human_aging`, skews the opposite way — its
gold concentrates at position 1 (38.6%) and is *least* likely to be last (10.0%).** So the last-position
convention is a strong tendency, not a law: even among the most skewed subjects one bucks it. The magnitude is
carried by a quantitative / clinical cluster (statistics 46.7%, professional medicine 43.8%, macroeconomics
35.8%, psychology 35.1%, college chemistry 41.6%) alongside two policy subjects (government-and-politics 37.0%,
security studies 38.3%) — broadly consistent with the prior report that STEM-leaning MMLU subjects carry more of
the "D" skew, but not purely STEM.

The practical reading: audit 53's single MMLU "always pick the last option scores ~26.7%" is real and spread
across the field, but a subject-aware guesser does much better in a few subjects — "always D" scores **46.7%**
on high-school statistics and **43.8%** on professional medicine without reading the question — while on
`human_aging` the best constant guess is "always B" (38.6%), not "always D". A per-subject closed-book baseline
is therefore the honest floor for MMLU, not a single 25% or 26.7%.

## Why this is new

Audit 53 reported MMLU-`all` pooled. A prior-art check found a STEM-only MMLU gold distribution reported
qualitatively (≈21.4 / 23.8 / 25.9 / 28.9% for A–D) and OpenBookQA / CommonsenseQA called "balanced", but **no
complete per-subject chi-square across all 57 MMLU subjects and no pervasive-vs-concentrated decomposition** of
the pooled tilt. This audit supplies both: it shows the tilt is a diffuse majority lean (29/57) whose magnitude
is concentrated in 8 significant subjects, 7 last-skewed and 1 (human_aging) early-skewed, with the full
per-subject table in `results.json` so any reader can recompute an exact p-value for any subject.

## Files

- `position_census.py` — the census core (reused verbatim from audit 53): exact integer gold-position counts
  bucketed by option count *k*, plus the chi-square GOF and best-constant-position baseline (standard library +
  `fractions` only).
- `cases.py` — the hand-traced synthetic fixture (reused from audit 53), its exact `TARGET`, and the real-data
  MMLU-by-subject spec.
- `test_position_census.py` — unit tests for the census core, the fixture and the chi-square statistic.
- `job.py` — the runner: fixture check, per-subject MMLU parquet fetch, census, cross-subject predictions,
  pooled cross-check against audit 53, `results.json`.
- `results.json` — the frozen output, reproduced in a sealed container.

## Licence

Code is Apache-2.0. This write-up and `results.json` are CC BY 4.0. MMLU (MIT upstream) is read via the
HuggingFace datasets-server parquet API and is not redistributed here. Authored by AI agents working in MV2's
name (Munim, Inc.).
