# helm-medec-scorer

Audit 112 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-12, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container.*

## Why

MedHELM (release v4.0.0, 13 models from GPT-4o and Claude 3.5 Sonnet to GPT-5, o3-mini and DeepSeek R1) includes
MEDEC (Ben Abacha et al., arXiv:2412.19260): 597 clinical notes (the MS test set), each either correct or holding one
medical error. The prompt asks for `CORRECT`, or for the sentence ID of the wrong sentence followed by a corrected
sentence. HELM's `MedecMetric` stores two numbers per answer, **error flag accuracy** (the leaderboard column
`MedecFlagAcc`) and **error sentence accuracy** (stored in `stats.json`, not shown on the leaderboard). Reading the
metric's code (`src/helm/benchmark/metrics/medec_metrics.py`, unchanged on HELM's main branch since 2025-08-22):

- **The gold sentence id is never read.** `MedecScenario` writes each error note's reference as
  `"<sentence id> <corrected sentence>"`. The metric removes every `.` and calls `int()` on the whole text;
  `int("7 The patient ...")` raises `ValueError`, and the code then sets the gold id to -1. A predicted id is a
  number from 0 up, or -2 for an unreadable answer, so it can never equal -1: **sentence accuracy can only credit notes
  without an error**, and on every note with an error it is 0, whatever the model answers.
- **Only the exact string `CORRECT` means "no error".** The answer is stripped and compared with `"CORRECT"`
  case-sensitively; otherwise a leading number is read as the sentence id. Anything else, such as `CORRECT.` (the
  prompt itself writes "return the following output: CORRECT."), `**7**`, `Sentence 7:`, prose or an **empty answer**,
  is read as "there is an error" with an invalid id. So an unreadable or empty answer earns flag credit on every note
  that has an error.

**Prior art, and what is new here.** HELM issues and PRs searched on 2026-11-12 for "medec": #3403 (MedHELM v1,
which added the metric), #3509 (stop sequences for MEDEC) and #3584 (Qwen3 thinking tokens); none is about how the
gold or the answer is parsed. The metric file has two commits (#3403, and #3829, which added metadata). The MEDEC
paper scores sentence detection with its own scripts; on the MS test set it reports Claude 3.5 Sonnet at 0.6750 flag
accuracy and 0.6348 sentence accuracy (Table 3, with its own prompts), while HELM stores 0.521 and 0.013 for the same
model. A web search found no report of either parsing problem and no count of their effect.

**What we saw before freezing.** The scenario, run spec and metric code; the release's run list (13 `medec` runs, all
v4.0.0); the group page's `MedecFlagAcc` column for all 13 models (o3-mini 0.687 first, o4-mini 0.667, Claude 3.7
Sonnet 0.628; Claude 3.5 Sonnet 0.521 last); `stats.json` of all 13 runs (both means; the stored sentence accuracy runs
from 0.010, Gemini 1.5 Pro, to 0.231, Claude 3.7 Sonnet); the first 234 answers of GPT-4o (54 exactly `CORRECT`, 3
empty, the rest starting with a digit) and the first 135 of DeepSeek R1 (11 exactly `CORRECT`, 119 starting with a
digit, 4 empty, 1 `CORRECT.`); and the first 94 references of GPT-4o's `instances.json` (46 `CORRECT`, 48 with a
sentence id). From the code, the stored sentence accuracy should equal the share of notes without an error that the
model answered exactly `CORRECT`; that is checked below, not predicted.

## Method

1. **Data.** MedHELM release v4.0.0: `runs_to_run_suites.json`, the group page `groups/medec.json`, and for each listed
   `medec:` run `instances.json`, `display_predictions.json` and `stats.json`.
2. **HELM's scores (gate).** `MedecMetric.evaluate_generation` is transcribed (`grade112.py`): the gold with the bug
   kept, the answer read as HELM reads it, both stats. A run is **included** if it downloads, its test ids and
   references equal the first run's, every stored per-record flag and sentence accuracy equals ours, the record count
   equals `num_instances`, and both run means equal `stats.json` within 1e-9. Published cells are matched by value
   (within 1e-6) to the group page's `MedecFlagAcc` column.
3. **Check C1 (not a prediction).** In every included run no note with an error has a stored sentence accuracy above 0,
   and the stored sentence accuracy equals the share of error-free notes answered exactly `CORRECT`.
4. **Re-scores**, all with the gold id read as the leading number of the reference:
   - `fixed_sent`: HELM's reading of the answer, fixed gold id (flag accuracy unchanged);
   - `noinv`: as `fixed`, but an answer HELM marks invalid (neither exactly `CORRECT` nor starting with a digit)
     counts as no answer, 0 for flag and sentence;
   - `len` (lenient): `correct_variant` answers read as `CORRECT`, `id_variant` answers read as their id, `empty` and
     `other` count as no answer.
5. **Answer classes.** `exact` (`CORRECT`), `digit` (starts with a digit), and the four HELM marks invalid:
   `correct_variant` (the first non-empty line starts, after markdown or quote marks, with the word "correct" in any
   case and holds no digit), `id_variant` (the first non-empty line starts with a sentence id behind markdown or a label:
   `**7**`, `Sentence 7:`, `ID: 7`, `(7)`), `empty`, `other`.
6. **Cells and ranks.** One cell per run, exact fractions. Ranks: higher is better, 1 + the number of runs strictly
   higher. Also reported: the number of error notes, the always-"error" baseline (error notes / 597) and the runs whose
   published cell is within 0.03 of it.
7. **Hand-read** (next run): up to 8 answers per invalid class, one per run, spread by a stable hash, and four gold
   references, printed in the job log only; texts are never published.

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: the unit tests pass; 597 test ids; at least 13 runs listed; at least 12 included; at least 90% of included runs' cells match a published `MedecFlagAcc` cell |
| P2 | With the gold id fixed, sentence accuracy rises by at least **0.10** in at least **8** included runs |
| P3 | The highest fixed sentence accuracy of any run is at least **0.40** |
| P4 | Pooled over included runs, answers HELM marks invalid are at least **5%** of records |
| P5 | In at least one run, at least **20%** of answers are ones HELM marks invalid |
| P6 | Counting HELM-invalid answers as no answer lowers at least one run's flag accuracy by at least **0.05** |
| P7 | Under the lenient reading at least one model moves **3 or more places** in flag accuracy |
| P8 | The published leader (o3-mini) is still first under the lenient reading |

Reasoning: many answers start with a sentence id, and the MEDEC paper's models find the right sentence on most notes
they flag, so once the gold id is read, sentence accuracy should rise by 0.10 or more in most runs (P2) and reach 0.40
for the best (P3). Claude 3.5 Sonnet, Gemini 1.5 Pro and 2.5 Pro and Llama 3.3 have stored sentence accuracies of 0.03
or less, so they almost never answered exactly `CORRECT`; we expect that many of their answers are unreadable to HELM
(long answers, `CORRECT.` or markdown), enough for 5% pooled (P4) and 20% in one run (P5), and that removing the flag
credit those answers get on error notes moves some cell by 0.05 (P6). The lenient reading should lift those models
above several others (P7), but not above o3-mini, which leads by 0.02 (P8).

## What a result would mean

C1 says whether HELM's stored sentence accuracy measures anything beyond "answered `CORRECT` on a correct note". P2
and P3 say how far it is from what the models actually do. P4 to P8 say how much of the published `MedecFlagAcc`
column comes from reading unreadable or slightly mis-formatted answers as error reports, and whether fixing that
reorders the table. If P4 to P7 fail, the format problem is real in the code but small in this release.

## Validity gates

The unit tests (`test_grade112.py`, standard library only, traced by hand) cover the transcribed gold parsing with the
bug, the fixed gold, HELM's answer reading, scoring, an end-to-end case of the bug, every answer class (including
`Correction: 5`, `The text is correct.` and `Identified error in sentence 3`, which stay `other`), that the four
invalid classes are exactly what HELM marks invalid, a 6,000-digit answer, a run census with a perturbed record, a
non-test record, a duplicate, stored-score mismatches and missing stats, two trials, the release helpers, ranks,
Kendall tau-b with ties, the group column, cell matching and the verdicts on, past and without every boundary. The
unit tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads the release index, the group page and 13 runs (about 15 MB)
```

## Files

- `grade112.py`: HELM's parsing and scoring (transcribed), the fixed gold, classes, census, cells, ranks, Kendall
  tau-b and verdicts (standard library)
- `job.py`: downloads, gates, re-scores, cells, ranks; writes `results.json`
- `test_grade112.py`: unit tests with the hand traces

## Licence

Code is Apache-2.0 (`MedecMetric`'s parsing and scoring are transcribed from stanford-crfm/helm, Apache-2.0). This
write-up and any results are CC BY 4.0. MedHELM's outputs are published by Stanford CRFM; MEDEC is by Ben Abacha et
al. Only run names, model names, HELM instance ids, classes and counts are published, never notes, references or model
text. Authored by AI agents working in MV2's name (Munim, Inc.).
