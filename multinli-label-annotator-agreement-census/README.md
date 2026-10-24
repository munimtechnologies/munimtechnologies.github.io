# multinli-label-annotator-agreement-census

The 44th eval-reliability audit by MV2 of Munim, Inc., and the direct MultiNLI companion to audit 42
(SNLI per-gold-class annotator agreement). Audit 38 verified, over all 412,702 raw MultiNLI rows, that the
shipped `gold_label` is the strict majority of the five `annotator_labels`; audit 41 broke MultiNLI
agreement down by *genre*; audit 42 broke SNLI agreement down by gold *class* and found a strong ordering —
contradiction most decisive, neutral least. This audit asks the one question that lets the two 3-way NLI
corpora be compared head-to-head: **does SNLI's per-class decisiveness ordering replicate on MultiNLI?** Over
MultiNLI's two validated five-vote dev splits it measures, for entailment, neutral and contradiction
separately, the unanimous rate and the individual-agreement rate. It reuses audit 42's census module
verbatim, so the two per-class tables are produced by identical code and are directly comparable.

The work is carried out by AI agents working in MV2's name and is disclosed as AI-made wherever a platform,
contest or project asks.

## What it measures

Over the two validated files inside `multinli_1.0.zip` (`multinli_1.0_dev_matched.jsonl` +
`multinli_1.0_dev_mismatched.jsonl`, 20,000 rows, five annotators each), each valid-gold row is bucketed by
its normalised gold (entailment / neutral / contradiction) and, per class, we tally:

- **n** — rows with that gold,
- **unanimous** — rows where all five annotators chose the gold,
- the **individual-agreement rate** — share of individual annotator labels equal to the gold (the MultiNLI
  paper's "agreement" statistic), and
- a by-construction check that the gold equals the strict majority of the five labels.

Rows whose gold is `-` (no majority) have no class to bucket by and are counted separately. MultiNLI train is
single-annotator single-label (audit 38), so it carries no per-class agreement signal and is out of scope.
Each synthetic fixture count is hand-traced and frozen before the real files are touched; the census logic
runs in a sealed container and the output is frozen to `results.json`.

## Pre-registered predictions

- **P1 (structural / by construction):** in every class the gold equals the strict majority of its five
  labels. — **HELD** (gold == majority on all 6,942 entailment, 6,252 neutral and 6,453 contradiction rows,
  0 exceptions).
- **P2 (directional, a finding either way):** neutral — the fuzzy middle of NLI — is *less* often unanimous
  than entailment, as it was on SNLI (audit 42). — **HELD** (neutral 45.8% vs entailment 63.6%).
- **P3 (directional, a finding either way):** the per-class unanimous rates span more than 0.05. — **HELD**
  (spread 0.233, from neutral 0.458 to contradiction 0.691).

## Results

Totals over 20,000 dev_matched+dev_mismatched rows: 19,647 valid-gold, 353 `-` (no majority). The gold equals
the strict majority on all 19,647 valid rows (0 exceptions). The aggregate individual-agreement rate is 88.9%
— reproducing the MultiNLI paper's reported 88.7%.

| Gold class | n | unanimous | unanimous rate | individual agreement | gold == majority |
| --- | --- | --- | --- | --- | --- |
| contradiction | 6,453 | 4,460 | 0.6912 | 0.9169 | 6,453 / 6,453 |
| entailment | 6,942 | 4,417 | 0.6363 | 0.8998 | 6,942 / 6,942 |
| neutral | 6,252 | 2,866 | 0.4584 | 0.8467 | 6,252 / 6,252 |

**The SNLI ordering replicates exactly.** On MultiNLI, as on SNLI (audit 42), decisiveness is strongly
class-dependent and runs **contradiction > entailment > neutral** on both statistics at once — the
unanimous-rate ranking and the individual-agreement ranking are identical, and identical to SNLI's. Neutral is
again the least decisive class by a wide margin (unanimous on fewer than half its rows), contradiction the
most. Two independently annotated 3-way NLI corpora, built years apart from different source text, agree that
*which relation* a gold label asserts predicts how decisively annotators converge on it. The magnitudes differ
in a sensible way: MultiNLI's spread (0.233) is a touch smaller than SNLI's (0.250) and its floor is higher
(neutral 45.8% vs 40.9%), consistent with MultiNLI's longer, more varied premises leaving a little less room
for unanimous agreement on the easy classes while lifting the hardest one slightly. The per-genre spread of
audit 41 (0.118) is only about half the per-class spread here, so on MultiNLI too *which label* a gold is
predicts its decisiveness more strongly than *which genre* the text came from.

## Scope and limits

This checks annotator *agreement* per class, not label *correctness*: a unanimous gold can still be wrong, and
a `-` row is not an error. It covers only the validated dev_matched + dev_mismatched splits (MultiNLI train is
single-annotator; see audit 38). P1 holding is by construction and not surprising — the contribution is the
per-class table, the aggregate agreement figure matching the paper, the pre-registered P2 result, and the
head-to-head replication of SNLI's class ordering on an independent corpus.

## Files

- `label_census.py` — per-gold-class tally logic (file-free, fully unit-testable; identical to audit 42's).
- `cases.py` — the hand-traced six-record fixture, frozen target counts, and the MultiNLI member names.
- `test_label_census.py` — stdlib `unittest` suite (hand-traced fixture, totals, label/majority/rate helpers).
- `job.py` — asserts the fixture, loads the two validated files from `multinli_1.0.zip`, writes `results.json`.
- `results.json` — the frozen sealed-container output.

Reproduce: `python -m unittest -v` then `python job.py --data-dir <dir with multinli_1.0.zip> --out-dir <out>`.

## Licence

Code is Apache-2.0. This README, the fixture corpus and the results are CC BY 4.0. MultiNLI 1.0 is from
Williams, Nangia and Bowman (NAACL 2018); this audit reads the official release and reports counts, it does
not redistribute it. Authored by AI agents working in MV2's name at Munim, Inc.
</content>
</invoke>
