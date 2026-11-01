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

## Results

*Added 2026-11-01, after the sealed run (started 13:02 UTC, 247 s; unit tests and both fixture gates passed).
Everything above this heading is unchanged from the pre-registration. Frozen output: `results.json` and
`alignment_map.json`.*

**Status: results in. 6 of 7 predictions held. The headline P2 failed: one extra cell, Shona `professional_law`,
still shows 8 misaligned rows under the capped matcher.**

| # | Result |
| --- | --- |
| P1 | **HELD.** 42 configs × 14,042 rows; English world-history positions are exactly 0-236; same-id key differences equal audit 70 in every language (zh 176, ko 116, de 5, it 3, yo 2, ja 1, the other 35 languages 0); the original matcher again gives zh 180 and ko 113 misaligned world-history rows and the same 10 flagged cells |
| P2 | **FAILED.** Capped flagged cells: `zh` and `ko` `high_school_world_history`, plus `sn professional_law` (8 misaligned rows). The other seven extra cells drop to 0 (see below) |
| P3 | **HELD.** The capped matcher keeps zh **172** of 180 (95.6%) and ko **106** of 113 (93.8%); 9 rows in each language sit in fingerprint groups above the cap |
| P4 | **HELD.** 278 of 278 capped misaligned zh+ko world-history rows carry the key of the question they hold (100%) |
| P5 | **HELD.** Neighbour inference resolves **101 of 107** rows the fingerprint left unmatched (94.4%): zh 44 of 49, ko 57 of 58 |
| P6 | **HELD.** Leave-one-out made an inference for 343 of 367 fingerprint-matched rows, and all **343 of 343** equal the fingerprint match (100%) |
| P7 | **HELD.** **79 of 79** rows that inference places on another question carry that question's key (zh 42, ko 37) |

**The extra flags.** Under the capped matcher, six of the seven `professional_law` cells flagged in audit 72 (`ig
it ja ny so tr`) map 178 to 227 rows each, and every mapped row holds its own position's question (0 misaligned).
Japanese `moral_scenarios` drops to 0 for a different reason: 892 of its 895 rows share fingerprint groups above the
cap, so the capped matcher leaves them unmatched rather than proving them aligned. Shona `professional_law` is the
exception. Its groups are all within the cap (0 rows over it), and the same count of 8 misaligned rows remains.

**Why P2 failed (post-hoc reading, not pre-registered).** All 8 Shona rows carry the key of the English question at
their own position. Only 2 of 8 carry the key of the question the matcher paired them with, about what chance
agreement between 4-option keys gives. Across every capped "misaligned" row outside Chinese and Korean world history
(26 rows in 12 cells, none of the others with more than 4), 26 of 26 carry their own position's key and 8 of 26 the
paired question's. In Chinese and Korean world history it is the other way round: 278 of 278 carry the paired
question's key and 61 of 278 their own. So the Shona rows look like matcher errors on small groups, not misplaced rows.
This audit does not test why the matcher slips there; a translation that drops or reorders numbers inside a small
group of law questions would do it.

**The map** (`alignment_map.json`, 474 records):

| | Chinese (`zh`) | Korean (`ko`) |
| --- | --- | --- |
| Rows placed by fingerprint | 188 | 179 |
| Rows placed by neighbours | 44 | 57 |
| Unresolved | 5 | 1 |
| Rows holding a different English question | **222 of 237 (93.7%)** | **150 of 237 (63.3%)** |
| ... of which carry that question's key | 222 of 222 | 150 of 150 |
| ... of which carry a different cultural-sensitivity label (CS, CA or unannotated `-`) from the question they hold | 76 | 47 |
| Global-MMLU-Lite world-history rows holding a different question | 10 of 10 | 7 of 10 |

The map uses audit 72's original matcher for the fingerprint step, because in this subject its matches are the
ones the key test confirms (293 of 293 misaligned rows carry their held question's key). The capped matcher was used
only for P2-P4. A neighbour-placed row's key never feeds into its placement, and all 101 fit the question they were
placed on (P7 covers the 79 that moved; the other 22 were placed on their own position). Counted over the whole
map (post-hoc, from `alignment_map.json`), all 468 placed rows, 367 by fingerprint and 101 by neighbours, carry the
key of the question they are placed on.

**Every answer-key difference is accounted for (post-hoc arithmetic from the frozen outputs).** Audit 70 found 176
Chinese and 116 Korean rows whose key differs from English at the same `sample_id`. The map explains them: in
Chinese, 138 fingerprint-placed and 34 neighbour-placed rows hold another question with a different key, and the
remaining 4 are unresolved rows (positions 4, 5, 200 and 201); in Korean, 89 + 27 = 116, with none left over. No row
the map places on its own position has a different key.

Global-MMLU-Lite ids holding another question in `zh`: `high_school_world_history/test/` 33, 58, 67, 87, 93, 115,
145, 157, 187, 225; in `ko`: 33, 58, 67, 87, 93, 115, 145.

**What it means.** The misplacement audits 71-73 found is real and confined, as far as these instruments can see, to
Chinese and Korean `high_school_world_history`; the Japanese, Igbo, Italian, Chichewa, Somali, Turkish and Shona flags
come from the matcher, judged by their keys. Scoring is unaffected because every moved row keeps its own question's
key. What the map changes is coverage: audits 72/73 could place 180 Chinese and 113 Korean rows, and the map places
222 and 150, with only 6 rows unresolved. `alignment_map.json` can serve as a repair table: for each position it gives
the English position whose question the row holds, so cross-language pairs and the CS/CA labels can be moved to the
right rows. It applies equally to MMMLU `ZH_CN` and `KO_KR`, which audit 73 found identical on these rows. Limits: the
map is checked by answer keys and leave-one-out, not by reading translations, and a 4-option key matches by chance
about a quarter of the time, so a single row's placement is strongest where the fingerprint made it.
