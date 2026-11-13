# helm-mimic-billing-icd-regex (audit 114)

**Status: desk check, 2026-11-13. Code-certain, not pre-registered, and not measured on the published runs, because
HELM's public archive redacts both the gold codes and the model outputs of this benchmark.**

MedHELM v4.0.0's "MIMIC-IV Billing Code" column asks 13 models for "all relevant ICD-10 codes" in 1,000 discharge
notes and publishes a micro F1 (`MIMICBillingF1`, from 0.186 for Gemini 1.5 Pro (001) to 0.429 for GPT-5
(2025-08-07)). Both sides of that F1 go through one regular expression,

```
\b[A-Z]\d{1,3}(?:\.\d{1,4})?\.?\b
```

in `MIMICIVBillingCodeMetric.extract_icd_codes` (`src/helm/benchmark/metrics/mimiciv_billing_code_metrics.py`,
unchanged since commit 859a823, 2025-08-22). It allows only digits after the first letter and only digits after
the period. The gold list does not have that shape.

The work was carried out by AI agents working in MV2's name (MV2 of Munim, Inc.).

## Where the gold comes from

HELM's scenario reads `mimiciv_icd10.feather` and builds the reference as `",".join(codes)` of its `target` column.
HELM's maintainers say the file was generated with
[JoakimEdin/medical-coding-reproducibility](https://github.com/JoakimEdin/medical-coding-reproducibility)
([HELM issue #3689](https://github.com/stanford-crfm/helm/issues/3689)). In that repository's
`prepare_data/prepare_mimiciv.py` and `prepare_data/utils.py` (commit 1087eac):

- the target is the admission's ICD-10-PCS **procedure** codes plus its ICD-10-CM **diagnosis** codes;
- diagnosis codes get a period after the third character (always, so a three-character code ends in a period);
- procedure codes keep no period (seven characters, letters and digits).

The paper behind that repository (Edin et al., SIGIR 2023, [arXiv 2304.10909](https://arxiv.org/abs/2304.10909))
reports 7,942 unique codes in the MIMIC-IV ICD-10 set and 5,794 unique diagnosis codes, so by subtraction about
2,148 unique codes (27.0% of the label set) are procedure codes. These are counts of distinct codes, not of
occurrences in the 1,000 notes HELM uses.

## What the extraction keeps (code-certain)

`icd_regex_check.py` transcribes HELM's function and applies it to the dataset's format. Every code below is a
format example from the public ICD-10-CM / ICD-10-PCS code sets, not a value from MIMIC-IV.

| Gold format | Example in the gold list | HELM extracts | Verdict |
| --- | --- | --- | --- |
| three characters | `I10.` | `I10` | intact |
| digits after the period | `E11.9`, `I50.23` | the same | intact |
| a letter after the period (seventh-character extensions, `X` placeholders: injuries, poisonings, adverse effects, external causes) | `S72.001A`, `T38.0X5A`, `W19.XXXA` | `S72`, `T38`, `W19` | **truncated to the three-character category** |
| a letter in the third place (`C4A`, `C7A`, `C7B`, `D3A`, `M1A`, `O9A`, `Z3A`) | `Z3A.38`, `C7A.00` | nothing | **dropped** |
| ICD-10-PCS procedure (seven characters, no period) | `0DTJ4ZZ`, `5A1955Z`, `BW03ZZZ`, `XW033E5` | nothing | **dropped** |

No ICD-10-PCS code can ever match: the pattern covers at most four characters before an optional period, and a
seven-character run of letters and digits has no word boundary inside it. The same function reads the model's
answer, so the three defects act on both sides:

- **Procedures are never scored.** A note's procedure codes vanish from the gold; a model that lists them, or
  misses them, gets the same F1. The column measures diagnosis coding only, while the gold and the prompt
  ("ICD-10 codes") include procedures.
- **Extensions are not checked.** `S72.001A` (gold) and `S72.92XA` (a different fracture, other side) both become
  `S72` and score as an exact match; two gold codes in one category collapse into one.
- **Some diagnosis categories are invisible.** `Z3A` (weeks of gestation), `C7A` / `C7B` (neuroendocrine tumours),
  `M1A` (chronic gout) and the others above are dropped from the gold and from every answer.

Instance-level examples (from the unit tests; "full code" compares every gold code in full, periods removed):

| Example | Gold | Answer | HELM F1 | Full-code F1 |
| --- | --- | --- | --- | --- |
| procedure never scored | `0DTJ4ZZ,E11.9,I10.` | `E11.9, I10` | 1.0 | 0.8 |
| wrong extension credited | `S72.001A` | `S72.92XA` | 1.0 | 0.0 |
| two codes collapse | `S72.001A,S72.002A` | `S72.001A` | 1.0 | 0.667 |
| gestation code dropped | `Z3A.38,O80.` | `O80` | 1.0 | 0.667 |

Smaller points, also code-certain: lower-case codes (`e11.9`) are not read, and a code written without its period
(`I5023`) is not read either.

## Limits

- **No published number is re-computed.** In the public archive (`medhelm/benchmark_output/runs/v4.0.0/`), the
  inputs, references and `predicted_text` of `mimiciv_billing_code` read `[redacted]` (checked in the first half of
  the GPT-4o mini run's `instances.json` and `display_predictions.json`, several hundred instances each; MIMIC-IV is
  credentialed data). The published per-instance F1 values are public. So how many gold codes per note are dropped or truncated, and how the 13
  cells would change, cannot be measured here. It needs MIMIC-IV access.
- The gold format rests on two facts: HELM's maintainers name the Edin et al. repository as the source, and its
  code formats codes as described above. If HELM's file was later re-formatted, the code-level verdicts still hold
  for whatever codes have these shapes.
- Not every effect lowers a score. Dropping procedures can raise F1 (a model's missed procedures stop counting) or
  lower it (a note whose gold codes are all procedures has an empty reference, so no answer can score); truncation
  credits wrong extensions, but because it also merges codes it can move an F1 either way (gold `S72.001A`,
  `S72.002A`, `E11.9` and answer `S72.001A`, `S72.002A`, `I10` score 0.667 in full and 0.5 truncated).

## Suggested fix

Split the gold on the commas the scenario joins it with (no regular expression on the gold side), compare codes with
periods removed and in upper case, and read answers with a pattern that allows a letter in the third place and after
the period, plus seven-character ICD-10-PCS codes; or, if the column is meant to cover diagnoses only, say so in the
prompt and remove procedure codes from the gold.

## Reproduce

```
python -m unittest -v test_icd_regex_check.py
python icd_regex_check.py
```

Standard library only.

## Prior art

HELM's issues and pull requests mention this benchmark only for data access (#3564, #3689) and its addition
(#3403, #3459, #3508); none mentions the extraction pattern or procedure codes. A web search found no report of
it. The MedHELM paper ([arXiv 2505.23802](https://arxiv.org/abs/2505.23802)) describes the metric as F1 on
extracted ICD-10 codes without the pattern.

## Licence

Code is Apache-2.0; the transcribed HELM function keeps HELM's Apache-2.0 licence. This write-up is CC BY 4.0.
Made with AI agents working in MV2's name (Munim, Inc.).
