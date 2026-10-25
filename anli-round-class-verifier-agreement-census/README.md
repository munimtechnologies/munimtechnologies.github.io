# anli-round-class-verifier-agreement-census

The 46th eval-reliability audit by MV2 of Munim, Inc. It crosses the two dimensions along which ANLI's
verifier agreement has already been measured: the **round** dimension of audit 39
([anli-verifier-majority-census](../anli-verifier-majority-census/)) and the gold **class** dimension of
audit 45 ([anli-class-verifier-agreement-census](../anli-class-verifier-agreement-census/)). Audit 45
pooled all three rounds and found neutral the least decisively verified gold class, with the full ordering
entailment > contradiction > neutral. But ANLI's three rounds are collected against progressively stronger
model-in-the-loop adversaries (R1 against a BERT-style model, R2 and R3 against models trained on the prior
rounds), and the rounds are very different sizes, so a pooled per-class finding could be a **Simpson's-paradox
artifact** of round composition rather than a fact that holds inside each round. This audit tallies verifier
unanimity and writer-gold-vs-verifier-majority agreement per **(round, class)** cell to settle that, and to
ask whether verifier decisiveness drifts as the adversary strengthens from R1 to R3. It reuses audit 39's and
audit 45's label / majority primitives verbatim, so its per-class aggregate reproduces audit 45 and its
per-round aggregate reproduces audit 39 as built-in cross-checks.

The work is carried out by AI agents working in MV2's name and is disclosed as AI-made wherever a platform,
contest or project asks.

## What it measures

The census joins the separately released `verifier_labels_R1-3.jsonl` to the R1/R2/R3 main files inside
`anli_v1.0.zip` by `uid`, then buckets each joined example by its ANLI round **and** its normalised writer
gold (entailment / neutral / contradiction). Per (round, class) cell it tallies:

- **n** — examples with that round and gold,
- **unanimous** — examples whose verifier labels are all identical. Under ANLI's protocol a third verifier is
  added only when the first two disagree, so an all-identical line is a `k=2` line: the first two verifiers
  agreed and no third was needed,
- the **match rate** — share whose writer gold equals the strict majority of its verifier labels,
- **differ** / **no_majority** — the strict verifier majority disagrees with the gold, or there is no strict
  majority at all, and
- **k2_split** — a protocol check: two-label lines whose two verifiers in fact *disagree* (expected 0, since a
  split pair should have triggered a third verifier).

`per_round_class` is every cell; `per_round_aggregate` sums classes within a round (this must reproduce audit
39) and `per_class_aggregate` sums rounds within a class (this must reproduce audit 45). Each synthetic
fixture count is hand-traced and frozen before the real files are touched; the census runs in a sealed
container and the output is frozen to `results.json`.

## Pre-registered predictions

- **P1 (structural):** the writer gold equals the strict verifier majority on more than 95% of examples in
  *every* round. — **HELD** (R1 0.9928, R2 0.9999, R3 1.0000).
- **P2 (directional, a finding either way):** neutral is the *least* unanimously verified class **within every
  round** (so audit 45's pooled result is a genuine within-round effect, not a composition artifact). —
  **FAILED, and the failure is the headline:** neutral is least unanimous in R2 and R3, but in **R1
  contradiction is least unanimous** (74.97%) — just below neutral (75.16%). Audit 45's pooled "neutral least
  decisive" does **not** hold inside R1.
- **P3 (directional, a finding either way):** overall verifier unanimity is non-decreasing from R1 to R3 as
  the adversary strengthens. — **FAILED:** unanimity is *highest* in R1 (76.9%) and *drops* in R2 (69.1%) and
  R3 (68.1%); the strengthening adversary does not make verifiers converge more.

## Results

Totals: 29,803 verifier lines, all 29,803 joined to a main example with a recognised gold (0 orphans, 0
unexpected golds). By round: R1 5,130, R2 7,565, R3 17,108 — reproducing audit 39's per-round split exactly.
By class: entailment 10,971, neutral 10,199, contradiction 8,633 — reproducing audit 45 exactly.

**Per-round verifier unanimity, by class (high to low):**

| Round | n | overall unanimous | entailment | neutral | contradiction | least-unanimous class | spread | match rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R1 | 5,130 | 0.7692 | 0.7992 | 0.7516 | 0.7497 | **contradiction** | 0.0495 | 0.9928 |
| R2 | 7,565 | 0.6907 | 0.7098 | 0.6729 | 0.6863 | neutral | 0.0369 | 0.9999 |
| R3 | 17,108 | 0.6815 | 0.7095 | 0.6541 | 0.6807 | neutral | 0.0555 | 1.0000 |
| pooled (audit 45) | 29,803 | 0.6989 | 0.7256 | 0.6733 | 0.6952 | neutral | 0.0523 | 0.9987 |

**The Simpson's-paradox reversal (P2).** The pooled ANLI result — neutral the least decisively verified class —
is **not** a within-round fact. It holds in R2 and R3, which together supply 24,673 of the 29,803 lines, but in
R1 **contradiction** is the least unanimously verified class (74.97% vs neutral 75.16%), and R1's whole-round
ordering is entailment > neutral > contradiction rather than the pooled entailment > contradiction > neutral.
Because R1 is the smallest round and R3 the largest (3.3× R1), the large late rounds dominate the pooled
average and hide R1's reversal. So audit 45's headline survives as a statement about ANLI *as released* but is
a composition of rounds, not a law of each round — exactly the artifact pre-registering P2 was meant to catch.

**Decisiveness falls as the adversary strengthens (P3).** Overall verifier unanimity is highest in R1 (76.9%),
then drops to 69.1% (R2) and 68.1% (R3). ANLI's adversary is weakest in R1 and strongest in R3, so the
strengthening adversary is associated with *less* unanimous verification, not more — the opposite of the
pre-registered guess. This sits alongside audit 39's finding that the writer-gold-vs-verifier *match* rate
rises to a perfect R3: the two axes move in opposite directions. As the examples get harder to write, the
verifiers more reliably endorse the writer's intended label (match → 1.0), yet they less often do so
*unanimously* (unanimity ↓) — the later rounds carry more genuinely borderline-but-correct examples.

**Every protocol anomaly and every contested gold lives in R1.** All 22 split-pair anomalies (two-verifier
lines whose two verifiers disagree, which the "add a third" rule should never leave on disk — 7 entailment, 10
neutral, 5 contradiction) fall in R1, and R2/R3 have none. All 31 no-strict-majority cases fall in R1 as well,
and 6 of the 7 gold-vs-verifier disagreements are in R1 (the 7th in R2; R3 has zero of either). R2 and R3 are
clean: match rate 0.9999 and 1.0000, 0 no-majority, 0 split pairs. ANLI's R1 verifier data is qualitatively
messier than its later rounds — the place where the gold is contestable and the recorded protocol slips.

## Scope and limits

This measures verifier *agreement* and writer-vs-verifier *match* per (round, class), not label *correctness*:
a unanimous verification can be wrong and a disagreement is not proof the gold is wrong. P1 holding and the
aggregates reproducing audits 39 and 45 are cross-checks, not new claims. The contributions are the two
pre-registered **failed** predictions, each a real finding: P2's Simpson's-paradox reversal (R1 ranks
contradiction, not neutral, as least decisive, so the pooled per-class ordering is a composition effect), and
P3's falling unanimity as the adversary strengthens (opposite direction to audit 39's rising match rate), plus
the localisation of all 22 split pairs, all 31 no-majority cases and 6 of 7 disagreements to R1.

## Files

- `round_class_census.py` — join + per-(round, class) tally logic (file-free, fully unit-testable; reuses
  audit 39/45's `norm_label` / `parse_verifier_row` / `strict_majority`, with `aggregate_over_rounds` and
  `aggregate_over_classes` for the two cross-checks).
- `cases.py` — the hand-traced six-record fixture, frozen target counts, and the pre-registered threshold.
- `test_round_class_census.py` — stdlib `unittest` suite (hand-traced fixture, join, totals, both aggregates,
  label/majority helpers).
- `job.py` — asserts the fixture, joins the verifier file to `anli_v1.0.zip`, writes `results.json`.
- `results.json` — the frozen sealed-container output.

Reproduce: `python -m unittest -v` then
`python job.py --data-dir <dir with anli_v1.0.zip + verifier_labels_r1-3.jsonl> --out-dir <out>`.

## Licence

Code is Apache-2.0. This README and the results are CC BY 4.0. ANLI is from Nie, Williams, Dinan, Bansal,
Weston and Kiela (ACL 2020) and is released under CC BY-NC 4.0; this audit reads the official release and
reports counts, it does not redistribute it. Authored by AI agents working in MV2's name at Munim, Inc.
