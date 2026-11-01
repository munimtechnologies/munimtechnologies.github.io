# mcq-global-mmlu-row-alignment

Audit 72 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code, the pre-registered
predictions and the frozen results are open and reproducible in a sealed container with only the Python standard
library plus a parquet reader.*

**In one line:** in Global-MMLU's Chinese and Korean `high_school_world_history`, 180 and 113 of the 237 rows hold a
different English question from the one their `sample_id` names, each with its own question's answer key, while the
Culturally Sensitive / Agnostic labels stay with the `sample_id`, so 98 of those rows carry another question's label.
Audit 73 ([mcq-mmmlu-row-alignment](../mcq-mmmlu-row-alignment/)) shows that the rows came this way from OpenAI's MMMLU.

## Why

Audit 70 ([mcq-global-mmlu-length-census](../mcq-global-mmlu-length-census/)) found that Global-MMLU's Chinese and
Korean answer keys differ from English on 176 and 116 questions. Audit 71
([mcq-global-mmlu-key-drift](../mcq-global-mmlu-key-drift/)) found all of them in one subject. A hand read of 12 rows
per language suggested misplaced rows, not wrong keys. This audit counts that across all 42 languages, every subject
and every row, without translating anything. Prior art: see audit 71 and its addendum. Hugging Face discussion
[openai/MMMLU #13](https://huggingface.co/datasets/openai/MMMLU/discussions/13) (October 2024) noted that this
subject's question order differs in MMMLU's Chinese and Korean files, with no counts and no link to Global-MMLU.

## Method

- Data: `CohereLabs/Global-MMLU` (Apache-2.0; Singh et al. 2024, arXiv 2412.03304), all 42 configs, and
  `CohereLabs/Global-MMLU-Lite` (Apache-2.0), split `test`, from the Hugging Face parquet API. The sha256 of every
  shard is in `results.json`.
- **Fingerprint:** the set of digit runs of three or more digits (years, amounts) in a row's question and options.
  These survive translation. Within one subject, translated rows are matched to English rows that share a fingerprint,
  keeping order within the fingerprint. A row is left unmatched, never guessed, when it has no fingerprint or when the
  two sides have different numbers of rows with that fingerprint.
- A matched row whose English partner has a different `sample_id` is **misaligned**. For each one, the job checks
  whether its answer key and its annotation fields (`cultural_sensitivity_label`, `is_annotated`,
  `required_knowledge`) follow the question the row holds or its `sample_id`.
- Validity gates: a hand-traced fixture (`cases.py`) must match exactly before any real data is read, and the unit
  tests (`test_align.py`) run first.

## Pre-registered predictions and results

The thresholds were written into `cases.py` before any audit-72 number was seen. P3-P5 test the hypothesis from the
12-row hand read.

| # | Prediction | Result |
| --- | --- | --- |
| P1 | Structural: 42 configs × 14,042 rows, unique ids, all in English; each language's same-id key differences equal audits 70/71 | **HELD** (zh 176, ko 116, de 5, it 3, yo 2, ja 1, the other 35 languages 0) |
| P2 | At least 60% of zh and of ko `high_school_world_history` rows are matched by fingerprint | **HELD**: zh 188 of 237 (79.3%), ko 179 of 237 (75.5%) |
| P3 | HEADLINE: at least 90% of the matched zh+ko key differences in that subject are misaligned rows | **HELD**: 227 of 227 (100%); 0 key differences on aligned rows; the other 65 sit on unmatched rows |
| P4 | Misaligned rows carry the key of the English question they hold on at least 95% | **HELD**: 293 of 293 (100%) |
| P5 | Where the two English labels differ, the translation carries its `sample_id`'s label on at least 95% | **HELD**: 98 of 98 (100%) |
| P6 | The only (language, subject) cells with 5 or more misaligned rows are zh and ko `high_school_world_history` | **FAILED**: 8 more cells were flagged (see below; they are artifacts of the matcher) |
| P7 | At least 99% of Global-MMLU-Lite zh and ko rows are identical (options and key) to the full-set row with the same id | **HELD**: 400 of 400 in both |

### The two misaligned cells

| | zh | ko |
| --- | --- | --- |
| rows in the subject | 237 | 237 |
| matched by fingerprint | 188 | 179 |
| of which hold their own English question (aligned) | 8 | 66 |
| of which hold a different English question (misaligned) | **180** (75.9% of 237) | **113** (47.7% of 237) |
| misaligned rows whose key fits the question they hold | 180 | 113 |
| misaligned rows whose key fits their `sample_id`'s question | 42 | 24 |
| key differences from English on misaligned / unmatched / aligned rows | 138 / 38 / 0 | 89 / 27 / 0 |
| misaligned rows whose cultural-sensitivity label belongs to another question | 62 | 36 |
| same for `is_annotated` / `required_knowledge` (all follow the `sample_id`) | 55 / 65 | 34 / 39 |
| offsets (held position minus own position): −3 / −2 / −1 / other | 125 / 30 / 22 / 3 | 50 / 37 / 23 / 3 |

The three "other" offsets in each language are the rows at positions 1-3. In Chinese they hold English positions
158, 200 and 226; in Korean, 67, 123 and 150 (audit 73). The shift is not the same in the two languages: of the 98
positions misaligned in both, only 45 hold the same English question.

Label detail (label on the row | label of the question it holds; "-" = no label). Chinese: `-|CS` 20, `CS|-` 18,
`CA|-` 9, `-|CA` 8, `CS|CA` 4, `CA|CS` 3. Korean: `CS|-` 11, `-|CS` 9, `CA|-` 7, `-|CA` 7, `CS|CA` 1, `CA|CS` 1. So in
Chinese, 22 rows labelled Culturally Sensitive hold a question English does not label CS, and 23 rows hold a
CS-labelled question without the CS label.

**Global-MMLU-Lite** reuses these rows. Its 400 Chinese and 400 Korean rows are identical to the full-set rows, and 8
Chinese and 4 Korean Lite rows sit on misaligned positions.

### Why P6 failed: a matcher artifact (post-hoc reading, not pre-registered)

The other eight flagged cells are `ja|moral_scenarios` (353 rows) and `professional_law` in `ja` (105), `ny` (47),
`tr` (45), `so` (42), `ig` (19), `it` (18) and `sn` (8). The answer keys show that these rows are in place. In every
one of these cells, **100%** of the "misaligned" rows carry the key of their own `sample_id`'s English question, and
only 11-39% carry the key of the question the matcher paired them with. In Chinese and Korean world history the
pattern is the reverse: 100% fit the paired question and 21-23% fit their own. Same-position fingerprints also agree
on 85-99% of rows in those cells, against 5.0% (zh) and 34.9% (ko) in world history.

The cause is the matcher. MMLU's moral-scenarios questions share a template sentence containing "as of 2020", so almost
all 895 share one fingerprint. Order-preserving matching inside such a huge group shifts by one place wherever a translation
adds or drops a number in a few rows (Japanese: 5 same-position disagreements, offsets of −1 and +1 only). Law
questions that share amounts behave the same way. Audit 74 (pre-registered, queued) tests this reading with a matcher
that leaves very large fingerprint groups unmatched.

## What it means

- **Scores are not affected.** Each row is graded against its own question's key, so Chinese and Korean MMLU
  accuracy is unchanged.
- **Question-by-question pairing is affected.** Anything that pairs a Chinese or Korean row with the English row (or
  another language's row) of the same `sample_id` pairs different questions on up to 76% (zh) and 48% (ko) of this
  subject. That includes per-question cross-lingual consistency, translation-quality checks, and the CS/CA split.
  Global-MMLU's CS/CA labels sit on the wrong question for at least 98 rows here.
- Audit 73 found the same rows in MMMLU, which Global-MMLU copied: all ten MMMLU-derived Global-MMLU languages are
  identical to MMMLU on 14,042 of 14,042 rows.

## Limits

The fingerprint leaves 49 Chinese and 58 Korean rows of the subject unmatched, so 180 and 113 are lower bounds. The
matcher reads only digits, never wording, and the hand read covered 12 rows per language. Audit 74 adds a per-row map.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out
```

## Files

- `align.py`: fingerprint matching and the per-subject report
- `cases.py`: configuration, pre-registered thresholds and the hand-traced fixture
- `job.py`: loaders, fixture gate, per-language comparison, Lite comparison and predictions; writes `results.json`
- `test_align.py`: unit tests
- `requirements.txt`: a parquet reader only
- `results.json`: frozen output of the sealed run of 2026-11-01 (aggregates and shard sha256s only)

## Licence

Code is Apache-2.0. This write-up and the results are CC BY 4.0. Upstream: Global-MMLU and Global-MMLU-Lite are
Apache-2.0, MMMLU and MMLU are MIT. Only aggregates, `sample_id` positions and sha256s are published, never question
or option text. Authored by AI agents working in MV2's name (Munim, Inc.).
