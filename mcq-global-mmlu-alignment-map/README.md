# mcq-global-mmlu-alignment-map

Audit 74 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-01, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library plus a parquet
reader.*

## Why

Audits 72 ([mcq-global-mmlu-row-alignment](../mcq-global-mmlu-row-alignment/)) and 73
([mcq-mmmlu-row-alignment](../mcq-mmmlu-row-alignment/)) matched translated rows to English by a digit fingerprint
(the set of 3+-digit numbers in a question and its options). They found 180 Chinese and 113 Korean rows of
`high_school_world_history` that hold a different English question, in Global-MMLU and in its source, MMMLU. Two
questions remain.

1. **Are the other flagged cells real?** Both audits' "confined to world history" prediction failed. Eight more
   Global-MMLU cells were flagged: Japanese `moral_scenarios` and `professional_law` in `ig it ja ny sn so tr`. In
   all of them, every "misaligned" row carries the key of its own position's English question. Our post-hoc reading
   is a matcher artifact. Every moral-scenarios question contains "as of 2020", so hundreds of rows share one
   fingerprint, and order-preserving matching inside a huge group shifts by one place wherever a translation adds or
   drops a number. That reading has not been tested yet.
2. **Which rows hold which question?** Audits 72/73 published counts. Anyone who wants to repair the pairing, or move
   the cultural-sensitivity labels to the right rows, needs a per-position map. That includes the 49 Chinese and 58
   Korean rows the fingerprint could not match.

## Method

- Data: `CohereLabs/Global-MMLU` (all 42 configs, test) and `CohereLabs/Global-MMLU-Lite` (`zh`, `ko`), Apache-2.0,
  from the Hugging Face parquet API.
- **Original matcher** (audit 72's `align.py`, unchanged), rerun as a gate.
- **Capped matcher** (`amap.capped_align`): the same matcher, except that a fingerprint group with more than **8** rows
  on either side stays unmatched. Questions on one world-history passage give small groups; a shared template gives
  huge ones.
- **Neighbour inference** (`amap.infer`), for Chinese and Korean world history only. A row the fingerprint left
  unmatched is taken to hold position `j+d` when the nearest matched rows before and after it both have offset `d`,
  `j+d` exists, and no other row holds it. Otherwise the row stays unresolved.
- **Checks on the inference.** Leave-one-out hides each fingerprint-matched row in turn and infers it from the
  others. Separately, the answer keys are tested: a row's key should fit the question it is inferred to hold.
- **Map** (`alignment_map.json`): one record per Chinese and Korean world-history row. Each record gives its
  `sample_id`, the position of the English question it holds (or null), how that was found, whether its key fits
  that question and whether it fits its own position's question, its own cultural-sensitivity label, and the label
  of the question it holds. There is no question or option text.

## Pre-registered predictions

Audit 72's numbers were known when these were written and are pinned in P1 as a gate. P2-P7 are new.

| # | Prediction |
| --- | --- |
| P1 | Structural: 42 configs × 14,042 rows; English world-history positions are exactly 0-236; same-id key differences equal audit 70 per language; the original matcher reproduces audit 72 exactly (zh 180 and ko 113 misaligned world-history rows; the same 10 flagged cells) |
| P2 | HEADLINE: with the capped matcher, the only (language, subject) cells across all 41 translations with 5 or more misaligned rows are `zh` and `ko` `high_school_world_history` |
| P3 | The capped matcher keeps at least 90% of audit 72's misaligned world-history rows in each language (zh ≥ 162, ko ≥ 102) |
| P4 | Capped misaligned zh+ko world-history rows carry the key of the question they hold on at least 95% (vacuous below 20) |
| P5 | Neighbour inference resolves at least 50% of the zh+ko world-history rows the fingerprint left unmatched (pooled) |
| P6 | Leave-one-out: where an inference is made for a fingerprint-matched row, it equals the fingerprint match on at least 90% (pooled zh+ko; vacuous below 50 inferences) |
| P7 | Rows that inference places on another question carry that question's key on at least 90% (pooled; vacuous below 20) |

## What a result would mean

If P2-P4 hold, the misplacement in Global-MMLU (and MMMLU, which it copies) is confined to Chinese and Korean world
history, and the other flags were artifacts of the instrument. If P5-P7 hold, the map covers most of the subject with a
rule that is checked twice, once by leave-one-out and once by answer keys that the inference never reads. Then the
map can serve as a repair table. If any of them fail, the map is still published with every record's `how` field, and
the failure is reported.

## Validity gates

Audit 72's hand-traced fixture (`cases.py`) and audit 74's (`cases74.py`) must match exactly before any real data is
read (`gate.py`; the job aborts otherwise), and the unit tests (`test_amap.py`) run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads Global-MMLU (42 configs) and Global-MMLU-Lite zh/ko (test splits)
```

## Files

- `align.py`: audit 72's fingerprint matcher (unchanged)
- `amap.py`: capped matcher, key report, neighbour inference, leave-one-out, per-position map
- `cases.py`: audit 72's configuration and fixture (unchanged); `cases74.py`: pinned numbers, thresholds, fixtures
- `gate.py`: both fixture gates; `job.py`: loaders, gates, predictions; writes `results.json` and `alignment_map.json`
- `test_amap.py`: unit tests; `requirements.txt`: a parquet reader only

## Licence

Code is Apache-2.0. This write-up and any results are CC BY 4.0. Upstream: Global-MMLU and Global-MMLU-Lite are
Apache-2.0. Only aggregates, `sample_id` positions and sha256s are published, never question or option text.
Authored by AI agents working in MV2's name (Munim, Inc.).
