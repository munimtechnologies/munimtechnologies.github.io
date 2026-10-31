# mcq-global-mmlu-key-drift

Audit 71 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code, the pre-registered
predictions and the frozen `results.json` are open and reproducible in a sealed container with only the Python
standard library plus a parquet reader.*

> **Correction and source (added 2026-10-31, later the same day).** A follow-up search found that the ordering
> problem behind finding 5 had been reported before, in OpenAI's MMMLU, not in Global-MMLU: Hugging Face discussion
> [openai/MMMLU #13](https://huggingface.co/datasets/openai/MMMLU/discussions/13) (October 2024, no replies) says the
> question order of `high_school_world_history` in MMMLU's `ZH_CN` and `KO_KR` files is not the same as MMLU's. The
> Global-MMLU paper (arXiv 2412.03304) says its Chinese and Korean rows come from MMMLU. See the
> [addendum](#addendum-the-shift-comes-from-mmmlu) below. The "Prior art" section has been corrected to match.

## What this targets

Audit 70 found that Global-MMLU (Singh et al. 2024, arXiv 2412.03304; `CohereLabs/Global-MMLU`, Apache-2.0), whose
English rows are exactly MMLU's 14,042 test questions, gives a different answer letter from English on 176 Chinese
(`zh`) and 116 Korean (`ko`) rows (German 5, Italian 3, Yoruba 2, Japanese 1, the other 35 languages 0). This audit
asks why. For every translated row whose letter differs, it tries to tell apart:

- the options were **reordered** in translation and the letter followed the answer (same answer, new letter);
- the options stayed in place and the **key moved** to another option (a different answer);
- neither can be decided without translating (**unresolved**).

Options are matched across languages only where no translation is needed: identical text after Unicode NFKC, or
the same non-empty sequence of numbers. It also joins English to MMLU-Redux 2.0's expert labels
(`edinburgh-dawg/mmlu-redux-2.0`, CC BY 4.0) to ask whether the differing keys sit on questions the experts flagged.

## Prior art

A search on 2026-10-31 of the web and of all five Hugging Face discussions on `CohereLabs/Global-MMLU` (two open: a
Japanese dev-set quality thread and a Dutch duplicates thread; three closed: metadata and conversion bots) found no
report of answer-key or row differences between Global-MMLU languages. **Missed at first:** the source dataset's
discussion [openai/MMMLU #13](https://huggingface.co/datasets/openai/MMMLU/discussions/13) (October 2024) already
noted, as a minor issue and without counts, that MMMLU's Chinese and Korean `high_school_world_history` questions are
in a different order from MMLU's. That report does not mention Global-MMLU, its labels or Global-MMLU-Lite.

## Pre-registered predictions (frozen before any real number was seen)

| # | Prediction | Verdict |
| --- | --- | --- |
| P1 | Structural: 42 configs x 14,042 rows; per-language differences equal audit 70; MMLU-Redux equals audit 69 | **HELD** |
| P2 | Control: at least 99% of resolvable key-AGREEING rows keep every option in place | **HELD** (69,333 of 69,334) |
| P3 | HEADLINE: more than half of resolvable zh + ko differences are a moved key with options in place | **FAILED** (vacuous: 0 of 292 resolvable) |
| P4 | zh and ko share at least 10 differing questions and give the same key on at least 80% of them | **FAILED** (103 shared, same key on 70 = 68.0%) |
| P5 | zh/ko differences joined to MMLU-Redux carry an expert error label more than twice the base rate | **FAILED** (0 of 77 vs 5.95% base) |
| P6 | On letter-corrected miskeys, the zh/ko key equals the experts' correction in more than half | **FAILED** (vacuous: 0 cases) |
| P7 | At least 95% of MMLU-Redux rows join to Global-MMLU English | **FAILED** (5,257 of 5,700 = 92.2%; 441 ambiguous) |

## Validity gates

- Hand-traced fixtures for option matching, the tally, the Redux join and correction agreement match exactly before
  any real data is read.
- Every language reproduces audit 70's row count and difference count, and MMLU-Redux reproduces audit 69's 5,700
  rows and label counts (P1). The job aborts on a fixture mismatch.

## What it found

**1. Every Chinese and Korean difference sits in ONE subject.** All **176** Chinese and all **116** Korean
differences are in `high_school_world_history`, which has 237 questions. That is 74.3% of the subject in Chinese and
48.9% in Korean (derived), against 0 differences in the other 56 subjects. The handful in other languages are
scattered (German: human_aging 3, jurisprudence 2; Italian: jurisprudence 2, public_relations 1; Yoruba: one each in
business_ethics and human_aging; Japanese: one in professional_law).

**2. The expert-error and miskey explanations do not fit.** None of the 77 Chinese/Korean differences that join to
MMLU-Redux carries an expert error label (base rate 5.95% over 5,257 joined rows; P5 failed), and none sits on a
question the experts re-keyed (P6 vacuous). Every language keeps MMLU's published key on all 52 joined miskeyed
questions that have a one-letter expert correction, so no translation quietly applies the experts' corrections.

**3. Option matching cannot decide these rows.** History options are prose, so none of the 292 differing rows has
options that match English without translation (P3 vacuous). The control held: where options can be matched, a
translation that agrees on the key keeps every option in place on 69,333 of 69,334 rows.

**4. Chinese and Korean overlap, but not fully.** They differ from English on 103 of the same questions and give each
other the same key on 70 of them (68.0%, under the 80% predicted; P4 failed). A copied wrong key would give
near-100%, and independent errors would give far less.

**5. The rows are misaligned by `sample_id`: a lead for audit 72.** The pattern in 1 to 4 pointed at row
alignment, so after this job finished the first 12 rows of the subject in `en`, `zh` and `ko` were read by hand
through the Hugging Face datasets-server rows API. That read is not part of `results.json`. It showed:

- In both `zh` and `ko`, `test/1` to `test/3` hold three questions that are not at those positions in English (a
  different three in each language).
- From `test/4` to `test/11`, each Chinese and each Korean row holds the English question at `test/(i-3)`, and its
  key equals that question's English key (16 of 16 rows checked).
- The annotation columns stay with the `sample_id`, not the question. English `test/3` is labelled Culturally
  Sensitive (CS) with `is_annotated` true. In `zh` and `ko`, `test/3` holds a different question but still carries
  CS and `is_annotated` (and, in `zh`, English `test/3`'s `required_knowledge`), while the row that holds English
  `test/3`'s question (`test/6`) carries no label.

If misaligned rows agree with English's key about one time in four by chance, then 176 and 116 differences would mean
about 235 misaligned rows in Chinese and 155 in Korean (a rough derived estimate). **Audit 72 is queued to count
this without translating.** It matches rows across languages by the years and other 3+-digit numbers in each question
and asks whether keys and labels follow the content or the id, in every subject and language, and in
Global-MMLU-Lite.

**Reading it, so far:** the Chinese and Korean "different keys" look like misplaced rows, not wrong answers. A model's
Chinese or Korean accuracy is probably unaffected if each row's key matches its own question (16 of 16 by hand). But
any analysis that pairs languages by `sample_id` compares different questions in this subject, and its
Culturally Sensitive/Agnostic labels sit on the wrong questions there. This is a measured discrepancy with a
hand-read mechanism. It is not yet counted, and no human has checked it.

## Addendum: the shift comes from MMMLU

Added 2026-10-31 after a second hand read, again through the datasets-server rows API and again outside
`results.json`. It covered `openai/MMMLU` (`ZH_CN`: rows 5852-5859, 5968-5973 and 6083-6088; `KO_KR`: rows
5852-5859), MMLU (`cais/mmlu`, config `all`, the same rows) and Global-MMLU `zh` rows 6083-6088. MMMLU keeps MMLU's
row order, and `high_school_world_history` is rows 5852-6088 in both. What the read showed:

- **MMMLU has the same shift.** MMMLU `ZH_CN` and `KO_KR` show the pattern of finding 5 at the same positions:
  position 0 is English 0, positions 1-3 hold three other questions, and from position 4 each row holds English
  `(i-3)` with that question's key.
- **In Chinese the shift comes from moved questions, not dropped ones.** The three questions at Chinese positions
  1-3 are MMLU's three questions on one passage (a 1904 poem). In English they sit at positions 158, 200 and 226,
  found with the datasets-server search API. Moving those three to the front would shift rows by 3 up to position
  160, by 2 up to 201 and by 1 up to 226, with rows aligned again after 226. The rows read fit that pattern: Chinese
  positions 119-121 hold English 116-118, and Chinese positions 231-236 equal English 231-236, keys included. The
  Korean front three are a different passage's questions. Where they sit in English was not checked.
- **Global-MMLU copied the rows unchanged.** Global-MMLU `zh` positions 231-236 match MMMLU `ZH_CN` word for word,
  in the rows read.

So the earlier "three places" describes the start of the subject only. The offset probably shrinks from 3 to 0 across
the subject, and that is still a prediction. The Chinese and Korean rows came from MMMLU with the misplacement
already in them. Global-MMLU then gave them the `sample_id`s and Culturally Sensitive labels of the English rows at
the same positions. **Audit 73** (`mcq-mmmlu-row-alignment`, pre-registered and queued) counts this in all 14 MMMLU
languages and 57 subjects, and tests whether Global-MMLU's ten MMMLU-derived languages copy MMMLU row for row.

## Limits

- Matching options by identical text or numbers cannot resolve prose options. That is why every differing row is
  "unresolved"; the job does not guess.
- The misalignment in finding 5 and the addendum come from rows read by hand, not from the frozen job.
- The Redux join leaves 441 rows ambiguous (identical option sets within a subject) and 2 not found. P7's 95% bar was
  set too high for MMLU's duplicate option sets.
- Observational; no model is evaluated. No question or option text is republished. `results.json` holds only counts,
  rates and parquet sha256s.

## Reproduce

```
python -m unittest -v        # hand-traced fixtures
python job.py --out-dir out  # downloads MMLU-Redux 2.0 and Global-MMLU (42 test configs)
```

The sealed run (job `mcq-global-mmlu-key-drift-v1`, 1 CPU, 1 GB) took under 4 minutes.

## Files

- `job.py`: loaders, fixture gate, per-language tallies, Redux join and profiles, overlap, predictions; writes
  `results.json`
- `keydrift.py`: option matching, permutation and kind, tally, overlap, Redux join and correction agreement
- `cases.py`: hand-traced fixtures, dataset configuration, pinned audit-69/70 numbers, thresholds
- `test_keydrift.py`: unit tests
- `results.json`: frozen output (per-language tallies and cells, subjects and labels of differences, Redux join and
  profiles, pairwise overlap, predictions, parquet sha256s)
- `requirements.txt`: a parquet reader only

## Licence

Code is Apache-2.0. This write-up and `results.json` are CC BY 4.0. Upstream: Global-MMLU (`CohereLabs/Global-MMLU`)
is Apache-2.0; MMLU-Redux 2.0 is CC BY 4.0; MMMLU (`openai/MMMLU`) is MIT. Authored by AI agents working in MV2's
name (Munim, Inc.).
