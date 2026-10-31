# mcq-mmmlu-row-alignment

Audit 73 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-10-31, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library plus a parquet
reader.*

## Why

Audit 71 ([mcq-global-mmlu-key-drift](../mcq-global-mmlu-key-drift/)) found that all of Global-MMLU's 176 Chinese
and 116 Korean answer-key differences from English sit in one subject, `high_school_world_history`. A hand read
suggested misplaced rows, not wrong keys, and audit 72 (queued) counts that in Global-MMLU. But Global-MMLU (Singh
et al. 2024, arXiv 2412.03304) did not translate Chinese or Korean itself. It took them, and eight other languages,
from OpenAI's MMMLU (`openai/MMMLU`, MIT, revision `325a01dc`), the professional translation of MMLU's test set into
14 languages.

**Prior art.** Hugging Face discussion [openai/MMMLU #13](https://huggingface.co/datasets/openai/MMMLU/discussions/13)
(October 2024, no replies) noted, as a minor issue, that the question order of this subject in MMMLU's `ZH_CN` and
`KO_KR` files differs from MMLU's. It gave no counts. A search on 2026-10-31 of the web and of all eight open MMMLU
discussions found nothing that counts misplaced rows across MMMLU's languages and subjects, and nothing that
connects them to Global-MMLU. The other open discussions report a German key mismatch (#13), malformed subject names
in `SW_KE` and `YO_NG` (#15), and duplicated questions (#17, #18).

**Hand read before this job was written** (datasets-server rows and search APIs, not part of any results):

- MMMLU keeps MMLU's row order, and the subject is rows 5852-6088 in both.
- In MMMLU `ZH_CN` and `KO_KR`, position 0 holds MMLU's position 0, positions 1-3 hold three other questions, and
  from position 4 each row holds MMLU's question three places earlier, with that question's key. This is the same
  pattern audit 71 saw in Global-MMLU.
- The three Chinese front rows are MMLU's three questions on one passage, which sit at positions 158, 200 and 226 in
  MMLU. Chinese positions 119-121 hold MMLU's 116-118, and Chinese positions 231-236 equal MMLU's, keys included.
- Global-MMLU `zh` positions 231-236 match MMMLU `ZH_CN` word for word.

## Method

Every MMMLU row takes the positional id of the MMLU row at the same place (`subject/test/k`, counted within the
subject; the ids Global-MMLU uses). Rows are then matched to MMLU questions without translation, using
audit 72's language-independent fingerprint. A fingerprint is the set of 3+-digit
numbers (years, amounts) in the question and options. Matching keeps order within each fingerprint, and a row is
never matched when the counts differ. A matched row holding a different MMLU question is *misaligned*. For each one
the job checks whether its key is the key of the question it holds. Global-MMLU's ten MMMLU-derived languages
(`bn de id it ja ko pt sw yo zh`) are compared with MMMLU at the same `sample_id` in two ways: identical normalised
text and key, or the same fingerprint and key.

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: MMLU (`cais/mmlu`, `all`, test) has 14,042 rows with the subject at 5852-6088 (237 rows); all 14 MMMLU configs have 14,042 rows; each config's own `Subject` equals MMLU's subject at the same position on at least 99% of rows (malformed file-name subjects are read up to `_test`) |
| P2 | HEADLINE: in each of MMMLU `ZH_CN` and `KO_KR` `high_school_world_history`, at least 25% of the 237 rows are matched to a different MMLU question |
| P3 | Inside MMMLU, those misaligned rows carry the key of the question they hold on at least 95% (pooled; vacuous below 20) |
| P4 | Global-MMLU `zh` and `ko` rows on those positions have the same fingerprint and key as the MMMLU row on at least 95% (vacuous below 20) |
| P5 | The only MMMLU (language, subject) cells with 5 or more misaligned rows are `ZH_CN` and `KO_KR` `high_school_world_history`, including the four MMMLU languages Global-MMLU did not use (`AR_XY ES_LA FR_FR HI_IN`) |
| P6 | In each of the ten MMMLU-derived Global-MMLU languages, at least 95% of rows are identical (normalised text and key) to the MMMLU row at the same position |
| P7 | Shape (suggested by the hand read): in each of `ZH_CN` and `KO_KR`, at least 90% of misaligned rows sit 1, 2 or 3 places after the MMLU question they hold |

Descriptive outputs: per-language key agreement by position, fingerprint agreement, offsets, which MMLU positions
the focus positions 1-3 hold, Chinese-Korean content agreement, and Global-MMLU's key differences from MMLU English
(audit 71 found 176 for Chinese and 116 for Korean in the subject).

## What a result would mean

If P2-P4 hold, then MMMLU's own scoring is unaffected, because each row's key fits its own question. The rows only
fail to line up with MMLU. Global-MMLU inherited them and attached its English rows' `sample_id`s and Culturally
Sensitive/Agnostic labels to them. That affects any analysis that pairs languages question by question, both in
MMMLU and in Global-MMLU(-Lite).

## Validity gates

A hand-traced fixture (`cases73.py`) must match exactly before any real data is read (the job aborts otherwise), and
the unit tests (`test_mmmlu.py`) run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads MMLU, 14 MMMLU configs and 10 Global-MMLU configs (test splits)
```

## Files

- `job.py`: loaders, fixture gate, per-language comparison, Global-MMLU inheritance, predictions; writes
  `results.json`
- `mmmlu.py`: positional ids, subject canonicalisation, per-language comparison, inheritance test
- `align.py`: fingerprint matching and the per-subject report (from audit 72, logic unchanged)
- `cases73.py`: configuration, thresholds and the hand-traced fixture
- `test_mmmlu.py`: unit tests
- `requirements.txt`: a parquet reader only

## Licence

Code is Apache-2.0. This write-up and any results are CC BY 4.0. Upstream: MMMLU (`openai/MMMLU`) and MMLU
(`cais/mmlu`) are MIT; Global-MMLU (`CohereLabs/Global-MMLU`) is Apache-2.0. Only aggregates and sha256s are
published, never question or option text. Authored by AI agents working in MV2's name (Munim, Inc.).
