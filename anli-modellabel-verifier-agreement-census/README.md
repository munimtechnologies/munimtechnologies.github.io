# anli-modellabel-verifier-agreement-census

The 47th eval-reliability audit by MV2 of Munim, Inc. It adds a dimension that audits 39, 45 and 46 never
touched: the **adversary model's own prediction**. ANLI is built by having a human writer, shown a premise
and a target label, write a hypothesis meant to *fool* a model-in-the-loop; each retained main example
therefore carries a `model_label` — the label that target model predicted — alongside the writer's `label`
(the gold). Audits 39 ([anli-verifier-majority-census](../anli-verifier-majority-census/)), 45
([anli-class-verifier-agreement-census](../anli-class-verifier-agreement-census/)) and 46
([anli-round-class-verifier-agreement-census](../anli-round-class-verifier-agreement-census/)) measured how
decisively ANLI's 2–3 independent verifiers endorse the writer's gold, broken down by round and by gold
class. None of them looked at **which label the model got wrong**. This audit crosses the writer gold with
`model_label`: for each (gold class, model-predicted label) cell it tallies verifier unanimity and the
writer-gold-vs-verifier-majority outcome, to ask whether *the specific error the adversary made* predicts
how decisively the verifiers then back the writer — and, as a structural check, to confirm at the data
level that the verified examples really did fool the model (`model_label != gold`).

It reuses audits 39/45/46's label and majority primitives verbatim, so its per-gold-class aggregate
reproduces audit 45 as a built-in cross-check. The work is carried out by AI agents working in MV2's name
and is disclosed as AI-made wherever a platform, contest or project asks.

## What it measures

The census joins the separately released `verifier_labels_R1-3.jsonl` to the R1/R2/R3 main files inside
`anli_v1.0.zip` by `uid`, then buckets each joined example by its normalised writer gold (entailment /
neutral / contradiction) **and** the normalised `model_label` (entailment / neutral / contradiction, or
`x` for a missing/unrecognised value so nothing is silently dropped). Per (gold, model_label) cell it
tallies:

- **n** — verified examples with that gold and model prediction,
- **unanimous** — examples whose verifier labels are all identical (under ANLI's protocol a third verifier
  is added only when the first two disagree, so an all-identical line is a `k=2` line that needed no third),
- the **match rate** — share whose writer gold equals the strict majority of its verifier labels,
- **differ** / **no_majority** — the strict verifier majority disagrees with the gold, or there is no strict
  majority at all, and
- **k2_split** — a protocol check: two-label lines whose two verifiers actually disagree (should be 0).

Totals also split the join into `n_model_fooled` (`model_label != gold`) and `n_model_agreed`
(`model_label == gold`). `per_gold_mlabel` is every cell; `per_gold_aggregate` sums over the model_label
buckets within each gold class and must reproduce audit 45. Each synthetic fixture count is hand-traced and
frozen before the real files are touched; the census runs in a sealed container and the output is frozen to
`results.json`.

## Pre-registered predictions

- **P1 (structural):** among the joined rows with a recognised `model_label`, the model disagrees with the
  gold (`model_label != gold`) on more than 95% — i.e. the verified set is, as the adversarial design
  implies, essentially all model-fooling examples. — **FAILED, and the failure is the headline:** the
  model disagrees with the gold on only **67.14%** of the verified rows (20,011 of 29,803); on **32.86%**
  (9,792) the recorded `model_label` *equals* the writer's gold. See below.
- **P2 (directional, a finding either way):** in at least one gold class the verifier unanimous rate spans
  more than 0.03 across the model_label buckets — i.e. which label the model predicted predicts how
  decisively the verifiers agree. — **HELD, in all three classes** (spread: entailment 0.071, neutral
  0.090, contradiction 0.076).
- **P3 (structural):** the writer gold equals the strict verifier majority on more than 95% in every
  (gold, model_label) cell with at least 100 examples. — **HELD** (every one of the 9 big cells is above
  0.997).

## Results

Totals: 29,803 verifier lines, all 29,803 joined to a main example with a recognised gold and a recognised
`model_label` (0 orphans, 0 unexpected golds, 0 missing/unrecognised model labels — the `x` bucket is
empty, because every verified main row carries a usable `model_label`). The per-gold-class aggregate
reproduces audit 45 exactly: entailment 10,971, neutral 10,199, contradiction 8,633.

**Verifier unanimous rate by (writer gold, model-predicted label).** Each cell also shows its size and its
gold-vs-verifier match rate.

| writer gold \ model said | entailment | neutral | contradiction | spread |
| --- | --- | --- | --- | --- |
| **entailment** | 0.7655 (n=3,543, match 0.9980) | 0.6947 (n=4,819, match 1.0000) | 0.7286 (n=2,609, match 0.9989) | 0.071 |
| **neutral** | 0.6120 (n=2,407, match 0.9988) | 0.6834 (n=4,128, match 0.9976) | 0.7022 (n=3,664, match 0.9992) | 0.090 |
| **contradiction** | 0.7145 (n=3,538, match 0.9992) | 0.6503 (n=2,974, match 0.9990) | 0.7261 (n=2,121, match 0.9972) | 0.076 |

**A third of the verified set did not fool the model (P1).** The pre-registered reading of ANLI — a
human-and-model-in-the-loop *adversarial* benchmark whose examples are, by construction, ones the model got
wrong — predicts `model_label != gold` on essentially every row. Over the verified subset it holds for only
**67.14%**; on **9,792** of the 29,803 verified examples the recorded `model_label` equals the writer's
gold label. This measurement is scoped to the examples that carry independent verifier labels (audit 39
showed that subset is 23,403 train plus the dev/test rows), not to all ~169k ANLI rows. We report it as a
measured fact and leave its mechanism open: the `model_label` field may record a different or later model
than the one the writer faced, verification may not be confined to model-fooling rows, or a non-adversarial
slice may be retained — resolving which would need ANLI's collection documentation, not this file. Either
way, a pipeline that treats every ANLI row as "the model was wrong here" is wrong about a third of the
verified set.

**Which error the model made predicts verifier decisiveness (P2).** Within every gold class the verifier
unanimous rate moves by more than 0.03 depending on what the model predicted, and the pattern is coherent:
the most decisively verified cells are the **polar-opposite (entailment↔contradiction) confusions** — when
the gold is entailment and the model said contradiction (0.7286), or the gold is contradiction and the
model said entailment (0.7145), the verifiers strongly back the writer. The *least* decisively verified
cells are the ones that touch the **neutral boundary**: neutral gold with the model predicting entailment
is the single least unanimous cell (0.6120), and contradiction gold with the model predicting neutral is
next (0.6503). So the examples where the adversary made a gross polarity error are exactly the ones whose
gold the verifiers find clearest, while the fuzziness concentrates on the neutral middle — consistent with
the "neutral is hardest" thread of audits 42, 44 and 45. For entailment and contradiction gold the
**diagonal** (the model *agreeing* with the writer) is the most unanimous cell of its row (0.7655 and
0.7261): when the model was not fooled, the verifiers are most sure too.

**Gold is near-unanimously the verifier majority in every cell (P3).** Across all nine cells with at least
100 examples the writer gold equals the strict verifier majority on more than 99.7%, so the P2 texture is a
story about *unanimity* (how often all verifiers agree), not about *correctness* (whether the majority
backs the gold) — the latter is at ceiling everywhere, reproducing audits 39/45. Only 7 cells-worth of
gold-vs-verifier disagreements exist in total (all in train, per audits 39/46).

## Scope and limits

This measures verifier *agreement* and writer-vs-verifier *match* per (gold, model_label), not label
*correctness*: a unanimous verification can be wrong and a disagreement is not proof the gold is wrong. P3
holding and `per_gold_aggregate` reproducing audit 45 are cross-checks, not new claims. The contributions
are (1) the pre-registered **failed** P1 — only 67.14% of the verified subset carries `model_label != gold`,
an under-documented non-adversarial-looking third whose mechanism this file does not resolve — and (2) the
held P2 texture: the adversary's polarity errors are the most decisively verified cells and the neutral
boundary the least, tying the model's confusion to the verifiers' decisiveness. The `model_fooled_rate` is
over the verified subset only, not all of ANLI.

## Files

- `modellabel_census.py` — join + per-(gold, model_label) tally logic (file-free, fully unit-testable;
  reuses audit 39/45/46's `norm_label` / `parse_verifier_row` / `strict_majority`, adds `get_model_label`,
  `mlabel_bucket` and `aggregate_over_mlabels` for the audit-45 cross-check).
- `cases.py` — the hand-traced eight-line / seven-example fixture (including a model-agreed row, a
  missing-`model_label` row routed to the `x` bucket, an orphan verifier line and a gold-vs-verifier
  differ), its frozen target counts, and the pre-registered thresholds.
- `test_modellabel_census.py` — stdlib `unittest` suite (hand-traced fixture, join, totals, the aggregate
  cross-check, and the label/majority helpers).
- `job.py` — asserts the fixture, joins the verifier file to `anli_v1.0.zip`, writes `results.json`.
- `results.json` — the frozen sealed-container output.

Reproduce: `python -m unittest -v` then
`python job.py --data-dir <dir with anli_v1.0.zip + verifier_labels_r1-3.jsonl> --out-dir <out>`.

## Licence

Code is Apache-2.0. This README and the results are CC BY 4.0. ANLI is from Nie, Williams, Dinan, Bansal,
Weston and Kiela (ACL 2020) and is released under CC BY-NC 4.0; this audit reads the official release and
reports counts, it does not redistribute it. Authored by AI agents working in MV2's name at Munim, Inc.
