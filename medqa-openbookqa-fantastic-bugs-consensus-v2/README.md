# medqa-openbookqa-fantastic-bugs-consensus-v2

Audit 89, second run, in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered amendment, results pending.** This page and its code were frozen on 2026-11-08, before the
v2 sealed job ran. The results will be added below, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library plus a parquet
reader.*

## Why a second run

[Audit 89](../medqa-openbookqa-fantastic-bugs-consensus/) asked whether audit 77's answer-level consensus flag
separates the MedQA and OpenBookQA items that Fantastic Bugs' expert reviewers (Truong et al., arXiv 2511.16842;
`stair-lab/fantastic-bugs`, MIT) judged invalid from those they judged valid. Its pre-registered structural check P1
**failed**, and the MedQA half of the question was never tested. The cause was two mistakes in our code, not anything
in the data:

1. **Wrong score field.** The inclusion gate compares our correct count with HELM's own per-item `exact_match`. HELM
   Lite records `med_qa` under `quasi_exact_match` only, so our count of HELM-correct items was 0 for every model and
   all 91 MedQA runs failed the gate. With no included models, no MedQA panel existed and no flag could fire.
2. **Wrong split.** Our parser keeps HELM instances whose split is `test`. HELM Lite's `med_qa` runs evaluate
   questions from both MedQA's `valid` and `test` splits (about half each), and Fantastic Bugs' reviewed rows come
   from both. Only 27 of the 49 MedQA rows were placed (P1 needed 45).

OpenBookQA was unaffected: all 91 runs were included and all 50 rows were placed.

## Amendment (the only changes from v1)

- The `med_qa` universe holds every question HELM Lite's oldest `med_qa` suite evaluates in the `valid` and `test`
  splits. OpenBookQA keeps `test` only, exactly as in v1.
- The inclusion gate reads an item's `exact_match` and, only when the item has none, its `quasi_exact_match`.
  `em_from_quasi_items` in the results says how many items were scored that way.

Everything else is unchanged and copied from v1: the categories, placement, panel, flag, margin, the thresholds and
P1-P6 word for word (below). Two outputs are added: `helm_split` per placed row (`test` or `other`, which for MedQA
means `valid`) and a check that OpenBookQA reproduces v1's numbers exactly (universe 500, 91 included, 6 flags in the
universe, flag on 4 of 48 valid and 2 of 2 invalid rows).

**What we saw before freezing v2.** From v1's output: MedQA placement (27 rows placed, 15 reviewed invalid and 12
valid, Fantastic Bugs' key equal to HELM's gold on all 27) and every OpenBookQA number. No MedQA model answer was
compared with any key in v1, because the panel was empty. To find the two causes we read the `stats` field of the
first three items of one HELM `med_qa` run (gpt-4-0613, v1.0.0; only `quasi_exact_match` is present) and the split
labels of the first 74 instances of the same suite (36 `valid`, 38 `test`). We did not look at any answer for a
Fantastic Bugs row.

**How v1 and v2 are reported.** v1's verdicts stand as published (P1 failed; P2, P3 and P6 failed, and P4 held
only because no flag could fire without a panel; P5 held on OpenBookQA). v2 is the test of the MedQA predictions. P1 is judged
again for v2 with the same thresholds.

## Method (as v1, with the amendment)

1. **HELM Lite.** Release v1.13.0: per benchmark (`med_qa`; `commonsense:dataset=openbookqa`,
   `multiple_choice_joint`), one run per model (newest suite). The question universe comes from the oldest suite's
   `instances.json` (MedQA: valid and test; OpenBookQA: test; one gold), and each run's `display_predictions.json`
   is mapped to it through its own suite's instances. A model is included when it answers at least 99% of the
   universe, its predicted letter agrees with HELM's mapped output on at least 99% of answers, and our correct count
   is within 0.5% of HELM's own exact_match (quasi_exact_match where exact_match is absent). The panel is the 10 most
   accurate included models of that benchmark; the flag is audit 77's rule, unchanged.
2. **Categories (frozen, `fb89.fb_category`).** MedQA: first word "valid" -> *valid*, "invalid" -> *invalid*.
   OpenBookQA: "correct" -> *valid*, "incorrect" -> *invalid*. Anything else -> *unclear* (left out).
3. **Placement.** As in audit 88: normalised question and options, then Mac Roman repair, then question text alone
   if it matches exactly one universe question. A second row on a placed question is dropped. Fantastic Bugs' tagged
   key must equal HELM's gold.
4. **Per item:** the flag, the consensus option, the top-10 votes and margin (most-picked non-key option's votes
   minus the key's), whether all 10 agree, and whether no included model picks the key.

## Pre-registered predictions (unchanged from v1)

| # | Prediction |
| --- | --- |
| P1 | Structural: fixtures match; the splits have 49 and 50 rows; at least 50 included models in each benchmark; at least 45 rows placed in each split; Fantastic Bugs' key equals HELM's gold on at least 95% of placed rows in each |
| P2 | HEADLINE (MedQA): the flag fires on a larger share of *invalid* items than of *valid* items |
| P3 | MedQA: the margin separates *invalid* from *valid* items with AUC at least 0.60 |
| P4 | MedQA: the flag fires on at most a quarter of *valid* items |
| P5 | OpenBookQA: the flag fires on at most a quarter of *valid* items |
| P6 | MedQA: the flag fires on at least a third of *invalid* items |

A comparison with a group under 5 items (10 for P4 and P5) is reported as undecidable and counts as not held.

v1's reasoning still applies: in audit 88 the flag rarely fired on questions medical reviewers accepted and often on
questions they faulted, so P2-P4 should hold; against them, every item was chosen because strong models answer it
worse than weak ones, and "invalid" in MedQA covers missing information and ambiguity as well as wrong keys. P6 is the
least certain.

## Validity gates

Hand-traced fixtures (`cases89.py`, traced in the docstring of `test_fb89.py`, now with the two-split universe and
the quasi_exact_match fallback) must match before any data is read. At least 20 rows per split must be placed, or the
job writes its diagnostics and stops. The unit tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads HELM Lite v1.13.0 med_qa and openbookqa run files and Fantastic Bugs'
                              # med_qa and openbookqa viewer splits
```

## Files

- `base89.py`: v1's copied functions, with the two amended ones (`parse_instances` splits, `map_predictions` score
  field)
- `fb89.py`: the review categories, the suggested option and the verdicts (unchanged)
- `cases89.py`: the frozen settings, gates, data sources and fixtures (v2: per-benchmark splits, v2 fixtures)
- `job.py`: downloads, model inclusion, the panel and flag per benchmark, placement, the comparison and the v1
  reproduction check; writes `results.json` and `rows.json`
- `test_fb89.py`: unit tests; `requirements.txt`: a parquet reader only

## Licence

Code is Apache-2.0. This write-up and any results are CC BY 4.0. Upstream: HELM (Stanford CRFM) is Apache-2.0 and its
published run outputs keep their own terms; Fantastic Bugs' data is MIT; MedQA is MIT; OpenBookQA is Apache-2.0. Only
split names, row numbers, ids, positions, letters, our categories, votes and counts are published, never question,
option, review or model text. Authored by AI agents working in MV2's name (Munim, Inc.).
