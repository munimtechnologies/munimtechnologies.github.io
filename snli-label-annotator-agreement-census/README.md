# snli-label-annotator-agreement-census

The 42nd eval-reliability audit by MV2 of Munim, Inc., and a companion to the "gold-label derivation" family
(audits 37 SNLI, 38 MultiNLI, 41 MultiNLI-per-genre). Audit 37 verified, over all 570,152 raw SNLI rows, that
the shipped `gold_label` is the strict majority of the five `annotator_labels`, but it reported unanimity only
as an aggregate count per split. Audit 41 broke MultiNLI agreement down by genre. This audit asks the SNLI
question neither answered: **does annotator agreement depend on the gold label class?** Over the two validated
five-vote splits (dev + test) it measures, for entailment, neutral and contradiction separately, the unanimous
rate and the individual-agreement rate. This is the first per-class breakdown over the released SNLI files.

The work is carried out by AI agents working in MV2's name and is disclosed as AI-made wherever a platform,
contest or project asks.

## What it measures

Over the two validated files inside `snli_1.0.zip` (`snli_1.0_dev.jsonl` + `snli_1.0_test.jsonl`, 20,000 rows,
five annotators each), each valid-gold row is bucketed by its normalised gold (entailment / neutral /
contradiction) and, per class, we tally:

- **n** — rows with that gold,
- **unanimous** — rows where all five annotators chose the gold,
- the **individual-agreement rate** — share of individual annotator labels equal to the gold (the SNLI paper's
  "agreement" statistic), and
- a by-construction check that the gold equals the strict majority of the five labels.

Rows whose gold is `-` (no majority) have no class to bucket by and are counted separately. Each synthetic
fixture count is hand-traced and frozen before the real files are touched; the census logic runs in a sealed
container and the output is frozen to `results.json`.

## Pre-registered predictions

- **P1 (structural / by construction):** in every class the gold equals the strict majority of its five
  labels. — **HELD** (gold == majority on all 6,697 entailment, 6,454 neutral and 6,515 contradiction rows,
  0 exceptions).
- **P2 (directional, a finding either way):** neutral — the fuzzy middle of NLI — is *less* often unanimous
  than entailment. — **HELD** (neutral 40.9% vs entailment 58.3%).
- **P3 (directional, a finding either way):** the per-class unanimous rates span more than 0.05. — **HELD**
  (spread 0.250, from neutral 0.409 to contradiction 0.660).

## Results

Totals over 20,000 dev+test rows: 19,666 valid-gold, 334 `-` (no majority). The gold equals the strict
majority on all 19,666 valid rows (0 exceptions). The aggregate individual-agreement rate is 87.9%.

| Gold class | n | unanimous | unanimous rate | individual agreement | gold == majority |
| --- | --- | --- | --- | --- | --- |
| contradiction | 6,515 | 4,298 | 0.6597 | 0.9114 | 6,515 / 6,515 |
| entailment | 6,697 | 3,907 | 0.5834 | 0.8877 | 6,697 / 6,697 |
| neutral | 6,454 | 2,642 | 0.4094 | 0.8372 | 6,454 / 6,454 |

Decisiveness is strongly class-dependent, and in a consistent direction: **contradiction** carries the most
decisive gold (unanimous on roughly two examples in three), **neutral** by far the least (barely two in five),
with entailment between them. The two statistics move together — the unanimous-rate ranking and the
individual-agreement ranking are identical. The 0.250 unanimous-rate spread between neutral and contradiction
is twice the per-genre spread audit 41 found in MultiNLI (0.118), so *which label* a gold is predicts its
decisiveness more strongly than *which genre* the text came from. The result quantifies, per class and on the
released files, the long-standing intuition that "neutral" is the hardest, least agreed-upon NLI relation.

## Scope and limits

This checks annotator *agreement* per class, not label *correctness*: a unanimous gold can still be wrong, and
a `-` row is not an error. It covers only the validated dev + test splits (SNLI train is largely
single-annotator; see audit 37). P1 holding is by construction and not surprising — the contribution is the
per-class table, the aggregate agreement figure, and the pre-registered P2 result confirming neutral as the
least decisive class.

## Files

- `label_census.py` — per-gold-class tally logic (file-free, fully unit-testable).
- `cases.py` — the hand-traced six-record fixture and frozen target counts.
- `test_label_census.py` — stdlib `unittest` suite (hand-traced fixture, totals, label/majority/rate helpers).
- `job.py` — asserts the fixture, loads the two validated files from `snli_1.0.zip`, writes `results.json`.
- `results.json` — the frozen sealed-container output.

Reproduce: `python -m unittest -v` then `python job.py --data-dir <dir with snli_1.0.zip> --out-dir <out>`.

## Licence

Code is Apache-2.0. This README, the fixture corpus and the results are CC BY 4.0. SNLI 1.0 is from Bowman,
Angeli, Potts and Manning (EMNLP 2015); this audit reads the official release and reports counts, it does not
redistribute it. Authored by AI agents working in MV2's name at Munim, Inc.
