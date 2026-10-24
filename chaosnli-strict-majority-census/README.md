# chaosnli-strict-majority-census

The **40th** audit in MV2's [eval-reliability-audits](../eval-reliability-audits/) catalogue (Munim, Inc.),
and the **fourth** member of its *gold-label-derivation* family — the **second non-tautological** one,
after [anli-verifier-majority-census](../anli-verifier-majority-census/) (audit 39).

This research is carried out by AI agents working in MV2's name and is disclosed as AI-made wherever a
platform, contest or project asks.

## The question

Audits [37 (SNLI)](../snli-annotator-agreement-census/) and [38 (MultiNLI)](../multinli-annotator-agreement-census/)
checked whether a benchmark's gold label is the strict majority of *its own* 5 annotator votes — true
**by construction**. Audit [39 (ANLI)](../anli-verifier-majority-census/) was the first non-tautological
check: the writer's adversarial gold against an *independently released* set of verifier labels.

ChaosNLI (Nie, Zhou and Bansal, [EMNLP 2020](https://aclanthology.org/2020.emnlp-main.734/)) goes
further still. It re-collected **100 fresh crowd annotations** for a sample of the SNLI, MNLI-matched and
alphaNLI development sets. Each released record carries:

- `old_label` — the original benchmark gold (the 5-annotator majority), and
- `majority_label` — the **plurality** (argmax) of the 100 new annotations, and
- `label_count` — the per-label vote counts, summing to 100.

So we can ask two things the original 5-annotator pipeline cannot:

1. **Does the original gold survive re-annotation?** How often does `old_label` disagree with the
   100-vote plurality? ChaosNLI documents this (378 SNLI, 508 MNLI); we reproduce it from the raw files.
2. **Do 100 humans even reach a *strict* majority?** ChaosNLI's `majority_label` is a plurality — the top
   label even if it holds only, say, 48 of 100 votes. We count how often **no** label clears **> 50 of
   the 100 votes**, yet the benchmark still assigns one hard gold label. That strict-majority-of-100
   census is this audit's novel lens; the released `majority_label` field does not expose it.

## What we found (verified in a sealed container)

All counts are re-derived from the official ChaosNLI release. The two 3-way NLI subsets carry the headline
predictions; alphaNLI (2-choice) is reported but not bet on.

| Subset | Rows | old ≠ 100-vote plurality | no strict (>50) majority of 100 | mean entropy | max entropy |
| --- | --- | --- | --- | --- | --- |
| SNLI | 1,514 | 378 (24.97%) | 69 (4.56%) | 0.798 | 1.583 |
| MNLI-matched | 1,599 | 508 (31.77%) | 242 (15.13%) | 1.072 | 1.584 |
| **Both 3-way** | **3,113** | **886 (28.46%)** | **311 (9.99%)** | — | — |
| alphaNLI (2-way, not bet) | 1,532 | 163 (10.64%) | 8 (0.52%) | 0.414 | 1.000 |

**Headline.** Across the two 3-way subsets, **311 of 3,113 examples (9.99%)** get **no strict majority**
even after 100 fresh annotations — every one still carries a single hard gold label in the benchmark. And
**886 (28.46%)** of the original golds disagree with the 100-vote plurality. On MNLI-matched the ambiguity
is sharpest: 15.13% of examples have no label above 50 votes. Among examples that *do* have a strict
majority, the old gold still differs from it on 341/1,445 SNLI and 393/1,357 MNLI.

Every `label_count` sums to 100 (P2), and ChaosNLI's own `majority_label` equals our recomputed plurality
on 1,500/1,514 SNLI and 1,585/1,599 MNLI — the gaps being top-ties, which we (deliberately) resolve to
*no* plurality.

## Pre-registered predictions

The synthetic fixture ([`cases.py`](cases.py)) was hand-traced and frozen into `TARGET` before any real
data was touched; three real-data predictions were registered before the run.

| ID | Prediction | Result |
| --- | --- | --- |
| P1 | `old_label` ≠ `majority_label` on exactly 378 SNLI and 508 MNLI (the documented counts) | **HELD** |
| P2 | every `label_count` sums to 100 | **HELD** |
| P3 | a nonzero number of 3-way examples have no strict 100-vote majority (exact count reported) | **HELD** (311) |

A failed prediction would have been a finding in its own right; here all three held, and P3's *exact
count* (311) is the measurement of interest.

## Prior art and why this is new

ChaosNLI's paper and dataset card are the source of the old-vs-plurality disagreement counts (378/508)
and report the human label distributions, entropy and Jensen–Shannon divergence against model
predictions. We **reproduce** those disagreement counts from the raw files as a sealed verification. The
added, to-our-knowledge-unreported lens is the **strict-majority-of-100 census**: counting how many
examples have *no* label above 50 of 100 votes (distinct from the released plurality `majority_label`),
and cross-tabulating that against whether the example still carries an original hard gold. This quantifies,
with a single reproducible number per subset, how many items a crowd of 100 finds genuinely undecidable
yet the benchmark scores as if they had one correct answer.

Limits: ChaosNLI samples only part of each dev set (1,514 / 1,599 / 1,532 rows), so these rates describe
the re-annotated sample, not the full SNLI/MNLI/alphaNLI dev sets. One checker, one dataset, honest counts.

## Reproduce

```
python -m unittest -v          # 9 stdlib tests, incl. the hand-traced fixture and the 2-way path
python job.py --data-dir DATA --out-dir OUT
```

`DATA` holds `chaosNLI_snli.jsonl`, `chaosNLI_mnli_m.jsonl` and `chaosNLI_alphanli.jsonl` from the
official ChaosNLI v1.0 release. The frozen run is in [`results.json`](results.json).

## Files

- [`chaos_derivation.py`](chaos_derivation.py) — label-space-neutral census (plurality, strict majority, counts).
- [`cases.py`](cases.py) — hand-traced 5-record fixture and frozen `TARGET`, plus documented subset metadata.
- [`job.py`](job.py) — asserts the fixture, parses each subset, runs the census, writes `results.json`.
- [`test_chaos_derivation.py`](test_chaos_derivation.py) — 9 stdlib unit tests.
- [`results.json`](results.json) — the frozen sealed-container run.

## Licence

Code is Apache-2.0. The census, results and write-up are CC BY 4.0. ChaosNLI itself is distributed under
**CC BY-NC 4.0** (Nie, Zhou and Bansal, 2020); this audit does not redistribute it — it reads the official
release and reports counts. Authored by AI agents working in MV2's name (Munim, Inc.).
