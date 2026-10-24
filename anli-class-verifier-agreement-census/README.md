# anli-class-verifier-agreement-census

The 45th eval-reliability audit by MV2 of Munim, Inc., and the ANLI companion to the per-class decisiveness
studies on SNLI (audit 42) and MultiNLI (audit 44). Audit 39 verified, over all 29,803 released ANLI verifier
lines, that the adversarial writer's `gold_label` equals the strict majority of the independently released
verifier labels on 99.87% of examples — and found that the verifier file also covers **train**. Audits 42 and
44 broke SNLI and MultiNLI annotator agreement down by gold *class* and found the same strong ordering —
contradiction most decisive, neutral least. This audit asks whether that per-class pattern recurs on ANLI,
where the setting is different in two ways that matter: the gold is one adversarial *writer's* label (not a
crowd majority), and the "annotators" are 2–3 independent *verifiers* checking that writer's example rather
than labelling it from scratch. So the question is sharper: **does ANLI's writer-vs-verifier decisiveness
depend on gold class, and is neutral again the least decisive, even under an adversarial gold?** It reuses
audit 39's label / majority primitives verbatim in a new `class_census.py`, so the counts are directly
comparable to that audit's aggregate.

The work is carried out by AI agents working in MV2's name and is disclosed as AI-made wherever a platform,
contest or project asks.

## What it measures

The census joins `verifier_labels_R1-3.jsonl` (the separately released verifier labels) to the R1/R2/R3 main
files inside `anli_v1.0.zip` by `uid`, then buckets each joined example by its normalised writer gold
(entailment / neutral / contradiction) and, per class, tallies:

- **n** — examples with that gold,
- **unanimous** — examples whose verifier labels are all identical. Under ANLI's protocol a third verifier is
  added only when the first two disagree, so an all-identical line is a `k=2` line: the first two verifiers
  agreed and no third was needed,
- the **match rate** — share of examples whose writer gold equals the strict majority of its verifier labels
  (the per-class slice of audit 39's 99.87%),
- **differ** / **no_majority** — examples where the strict verifier majority disagrees with the gold, or where
  the verifiers reach no strict majority at all, and
- **k2_split** — a protocol check: two-label lines whose two verifiers in fact *disagree* (expected 0, since a
  split pair should have triggered a third verifier).

`per_class` is over all joined examples; `per_class_devtest` and `per_class_train` split it, because audit 39
showed the verifier file covers train too. Each synthetic fixture count is hand-traced and frozen before the
real files are touched; the census runs in a sealed container and the output is frozen to `results.json`.

## Pre-registered predictions

- **P1 (structural):** ANLI's adversarial gold equals the strict verifier majority on more than 95% of
  examples in *every* class. — **HELD** (match rate 0.9991 entailment, 0.9984 neutral, 0.9986 contradiction).
- **P2 (directional, a finding either way):** neutral is the *least* unanimously verified class, mirroring
  SNLI (audit 42) and MultiNLI (audit 44). — **HELD** (neutral unanimous 67.3%, the lowest of the three).
- **P3 (directional, a finding either way):** the per-class unanimous rates span more than 0.05. — **HELD**
  (spread 0.0523, from neutral 0.673 to entailment 0.726).

## Results

Totals: 29,803 verifier lines, all 29,803 joined to a main example with a recognised gold (0 orphans, 0
unexpected golds). Of these 6,400 are dev/test and 23,403 are train.

| Gold class | n | unanimous | unanimous rate | gold == verifier majority | match rate |
| --- | --- | --- | --- | --- | --- |
| entailment | 10,971 | 7,961 | 0.7256 | 10,961 / 10,971 | 0.9991 |
| contradiction | 8,633 | 6,002 | 0.6952 | 8,621 / 8,633 | 0.9986 |
| neutral | 10,199 | 6,867 | 0.6733 | 10,183 / 10,199 | 0.9984 |

**Neutral is again the least decisive class — but the rest of the ordering flips.** On SNLI and MultiNLI the
decisiveness ordering is contradiction > entailment > neutral. On ANLI it is **entailment > contradiction >
neutral**: neutral stays firmly at the bottom (as predicted), but entailment, not contradiction, is now the
*most* decisively verified class, and contradiction drops to the middle. This is the interesting cross-corpus
result. The "neutral is hardest" finding is robust across three independently built 3-way NLI corpora and two
very different annotation protocols (5 fresh annotators vs 2–3 adversarial-example verifiers); but *which* of
the two non-neutral relations is easiest is protocol-dependent, so the full c>e>n ordering of the
crowd-labelled corpora does **not** carry over to the adversarial-writer setting. The spread is also far
narrower here (0.052 vs SNLI 0.250 and MultiNLI 0.233): verifiers reviewing a pre-written adversarial example
converge more uniformly across classes than fresh annotators labelling from scratch, and the match rate sits
near the ceiling in every class.

**Where the gold loses.** All 7 writer-vs-verifier disagreements and all 31 no-majority cases fall in train
(dev/test match the gold on 100% of all three classes, with 0 no-majority), reinforcing audit 39: ANLI's
multi-annotator signal on *train* is where the gold is contestable, not on the evaluation splits.

**A latent protocol finding: 22 split pairs.** 22 of the 29,803 verifier lines (0.07%) are two-label lines
whose two verifiers disagree (7 entailment, 10 neutral, 5 contradiction) — a configuration ANLI's "add a third
verifier when the first two disagree" rule should never leave on disk. These are a small, latent inconsistency
in the released verifier file: lines recorded as a split pair with no third tie-breaking label. Reported, not
dressed up; they do not change any class's headline rate.

## Scope and limits

This checks verifier *agreement* and writer-vs-verifier *match* per class, not label *correctness*: a
unanimous verification can still be wrong, and a disagreement is not proof the gold is wrong. ANLI verifiers
are not the original annotators — they review one adversarial example rather than labelling freely — so a
different non-neutral ordering from SNLI/MultiNLI is expected and is itself the finding, not a contradiction of
those audits. P1 holding restates audit 39's aggregate at the per-class level; the contribution is the
per-class table, the pre-registered P2 result (neutral least decisive under an adversarial gold too), the
narrower spread, the train-only location of every disagreement, and the 22 split-pair anomalies.

## Files

- `class_census.py` — join + per-gold-class tally logic (file-free, fully unit-testable; reuses audit 39's
  `norm_label` / `parse_verifier_row` / `strict_majority`).
- `cases.py` — the hand-traced six-record fixture, frozen target counts, and the pre-registered thresholds.
- `test_class_census.py` — stdlib `unittest` suite (hand-traced fixture, join, totals, label/majority helpers).
- `job.py` — asserts the fixture, joins the verifier file to `anli_v1.0.zip`, writes `results.json`.
- `results.json` — the frozen sealed-container output.

Reproduce: `python -m unittest -v` then
`python job.py --data-dir <dir with anli_v1.0.zip + verifier_labels_r1-3.jsonl> --out-dir <out>`.

## Licence

Code is Apache-2.0. This README and the results are CC BY 4.0. ANLI is from Nie, Williams, Dinan, Bansal,
Weston and Kiela (ACL 2020) and is released under CC BY-NC 4.0; this audit reads the official release and
reports counts, it does not redistribute it. Authored by AI agents working in MV2's name at Munim, Inc.
</content>
</invoke>
