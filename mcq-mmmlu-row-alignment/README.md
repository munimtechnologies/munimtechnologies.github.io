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

## Results

*Added 2026-11-01, after the sealed run (started 06:21 UTC, 203 s; fixture gate and unit tests passed). Everything
above this heading is unchanged from the pre-registration. Frozen output: `results.json`.*

**Status: results in. 6 of 7 predictions held; P5 failed because of the matcher, not because of the data (see
below).**

| # | Result |
| --- | --- |
| P1 | **HELD.** MMLU has 14,042 rows with the subject at 5852-6088. All 14 MMMLU configs have 14,042 rows, and each config's `Subject` matches MMLU's at the same position on 14,042 of 14,042 rows (345 malformed names in `SW_KE` and 100 in `YO_NG` read correctly up to `_test`) |
| P2 | **HELD.** Rows matched to a different MMLU question: `ZH_CN` **180 of 237 (75.9%)**, `KO_KR` **113 of 237 (47.7%)**. These are the same counts audit 72 found in Global-MMLU |
| P3 | **HELD.** 293 of 293 misaligned rows carry the key of the question they hold (100%). Only 42 of 180 (zh) and 24 of 113 (ko) carry the key of the MMLU question at their own position |
| P4 | **HELD.** Global-MMLU `zh` and `ko` rows on those 293 positions have the same fingerprint and key as MMMLU on 293 of 293, and are identical in normalised text and key on 293 of 293 |
| P5 | **FAILED.** Three more cells were flagged: `JA_JP moral_scenarios` (353), `JA_JP professional_law` (105) and `IT_IT professional_law` (18). None of the four languages Global-MMLU did not use was flagged (`AR_XY` 3 misaligned rows in total, `FR_FR` 5 spread over two subjects, `ES_LA` 0, `HI_IN` 0) |
| P6 | **HELD.** All ten MMMLU-derived Global-MMLU languages are identical to MMMLU on 14,042 of 14,042 rows (100%) |
| P7 | **HELD.** Offsets of −3 / −2 / −1: `ZH_CN` 125 / 30 / 22 = 177 of 180 (98.3%); `KO_KR` 50 / 37 / 23 = 110 of 113 (97.3%). The other three in each language are positions 1-3 |

**Positions 1-3** hold MMLU positions 158, 200 and 226 in `ZH_CN`, as in the hand read, and 67, 123 and 150 in
`KO_KR` (these Korean positions are new). Chinese and Korean are shifted differently: of the 98 positions misaligned in
both, 45 hold the same MMLU question.

**MMMLU's own key differences from MMLU** at the same position are `ZH_CN` 176, `KO_KR` 116, `DE_DE` 5, `IT_IT` 3,
`YO_NG` 2, `JA_JP` 1 and 0 in the other eight configs. These match audit 70's Global-MMLU counts language for
language, so every answer-key difference audit 70 found between Global-MMLU and English is already present in MMMLU.
In `ZH_CN`, 138 of the 176 key differences fall on misaligned rows and 38 on rows the fingerprint could not match
(`KO_KR`: 89 and 27). None falls on an aligned row. The handful in German, Italian, Yoruba and Japanese all sit on
unmatched rows, and this audit does not test their cause.

**Why P5 failed (post-hoc reading, not pre-registered).** In each of the three extra cells, every "misaligned" row
carries the key of the MMLU question at its own position (18 of 18, 353 of 353, 105 of 105). Only 39%, 31% and 29%
carry the key of the question the matcher paired them with. In Chinese and Korean world history it is the other way
round (100% versus 23% and 21%). Same-position fingerprints agree on 94-99% of rows in the extra cells, against 5%
(zh) and 35% (ko) in world history. MMLU's moral-scenarios questions share a template sentence containing "as of
2020", so almost all of them share one fingerprint. Inside such a group, order-preserving matching shifts by one place
wherever a translation adds or drops a number (`JA_JP` offsets are only −1 and +1). Law questions that share amounts
behave the same way. So these rows look like artifacts of the matcher, not misplaced rows. Audit 74 (pre-registered,
queued) tests that reading with a matcher that leaves very large fingerprint groups unmatched.

**What it means.** The prior report in MMMLU discussion #13 is right, and it can now be quantified: 180 Chinese and
113 Korean rows of `high_school_world_history` hold a different MMLU question from the one at their position (lower
bounds; 49 and 58 rows could not be matched). Each keeps its own question's key, so MMMLU and Global-MMLU accuracy are
unaffected. Question-by-question pairing across languages is affected in both datasets, and so are Global-MMLU's
cultural-sensitivity labels on those rows (audit 72: 98 rows carry another question's label). Global-MMLU copied all
ten MMMLU languages unchanged, including this misplacement.
