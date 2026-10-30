# mcq-mmlu-pro-source-length-census

Audit 63 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code, the pre-registered
predictions and the frozen `results.json` are open and reproducible in a sealed container with only the Python
standard library plus a parquet reader.*

## What this targets

Audit 61 ([mcq-mmlu-pro-length-census](../mcq-mmlu-pro-length-census/)) found that MMLU-Pro's 10-option expansion
**more than doubles** MMLU's answer-length shortcut: a tie-aware "pick the longest option" heuristic scores
0.1838 against a 0.1109 chance baseline (1.66× chance), reaching 44.6% in biology and 33.0% in psychology.
Audit 62 ([mcq-mmlu-pro-added-distractor-census](../mcq-mmlu-pro-added-distractor-census/)) traced that to
MMLU-Pro's **new** questions rather than the options added to MMLU's questions, and inferred *by subtraction* that
the new-source biology and psychology questions must score about 56% and 61%.

This audit measures it directly. It keys the same length census by MMLU-Pro's `src` field: by **source family**
(the prefix before the first `-`: `ori_mmlu`, `stemez`, `theoremQA`, `scibench`), by (category, provenance), by
(category, family) and by every individual `src` value. Lengths are characters after `str.strip()`, with
whitespace tokens alongside. This measures **agreement with a length heuristic**, a construction property of the
options, not the correctness of any model.

## Prior art

The MMLU-Pro paper (Wang et al., NeurIPS 2024 Datasets and Benchmarks, arXiv 2406.01574) lists the new sources
(a STEM problem website, TheoremQA, SciBench) and describes the GPT-4-Turbo distractor generation; it reports no
length analysis. MMLU-Pro+ (arXiv 2409.02257) studies "both X and Y" shortcuts; ABCD (arXiv 2602.17445) studies
answer position. A search on 2026-10-30 found no study other than audits 61 and 62 in this catalogue that measures a
length shortcut on MMLU-Pro, and none that breaks it down by source family or `src`.

## Pre-registered predictions (frozen before any real number)

| # | Prediction | Verdict |
| --- | --- | --- |
| P1 | New-source biology questions score at least 50% for pick-longest (audit 62 implied ~56%) | **HELD** (0.5660, n 498) |
| P2 | New-source psychology questions score at least 50% (audit 62 implied ~61%) | **HELD** (0.6701, n 305) |
| P3 | Every new-source family (n ≥ 100) has a larger pick-longest lift than the MMLU-derived questions | **FAILED** (TheoremQA −0.44 pts vs +1.44) |
| P4 | The STEM-website family (`stemez`) has the largest lift of the new-source families | **HELD** (+18.43 pts) |
| P5 | In a strict majority of categories with ≥ 50 questions of both provenances, the new-source lift is larger | **HELD** (9 of 9) |
| P6 | In every new-source family (n ≥ 100) the gold is the unique shortest option in under 5% of questions | **FAILED** (SciBench 6.47%) |

Each is a finding either way.

## Validity gate (must match audits 61 and 62 exactly)

| quantity | this audit | earlier audit | match |
| --- | --- | --- | --- |
| valid MMLU-Pro questions | 12,032 | 12,032 (61) | ✓ |
| pooled gold unique-longest count | 1,655 | 1,655 (61) | ✓ |
| pooled pick-longest accuracy | 0.18376805… | 0.18376805… (61) | ✓ |
| `ori_mmlu` n / pick-longest | 6,810 / 0.13011671… | 6,810 / 0.13011671… (62) | ✓ |
| new-source n / pick-longest | 5,222 / 0.25373465… | 5,222 / 0.25373465… (62) | ✓ |
| biology n / pick-longest | 717 / 0.44608044… | 717 / 0.44608044… (61) | ✓ |
| psychology n / pick-longest | 798 / 0.32999661… | 798 / 0.32999661… (61) | ✓ |
| bad_key / degenerate | 0 / 0 | 0 / 0 | ✓ |

## What it found

**MMLU-Pro's length shortcut is a STEM-website effect.** The `stemez` questions are 33.9% of MMLU-Pro but carry
85.8% of the pooled pick-longest excess. TheoremQA questions carry none, and SciBench's small edge disappears when
length is counted in tokens.

| source family | n | chance | pick-longest | lift (pts) | × chance | gold unique-longest | gold unique-shortest | mean gold / distractor (chars) | pick-longest, tokens | share of pooled excess |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ori_mmlu` (from MMLU) | 6,810 | .1157 | .1301 | +1.44 | 1.12 | .1040 | .0968 | 43.97 / 40.24 | .1364 | 11.2% |
| `stemez` (STEM website) | 4,083 | .1055 | .2897 | +18.43 | 2.75 | .2221 | .0100 | 50.86 / 36.69 | .2397 | 85.8% |
| `scibench` | 541 | .1018 | .1562 | +5.43 | 1.53 | .0573 | .0647 | 19.15 / 17.93 | .0997 | 3.4% |
| `theoremQA` | 598 | .1007 | .0963 | −0.44 | 0.96 | .0151 | .0100 | 4.71 / 5.24 | .0917 | −0.3% |

The share column is derived: n × lift per family (752.3, 98.0, 29.4 and −2.6 question-equivalents), divided by the
pooled 877.0 from audit 62.

- **STEM website, biology and psychology:** on `stemez-Biology` (351 questions) the gold is the unique longest of up
  to ten options **65.8%** of the time and pick-longest scores **66.7%** (chance 10.3%; gold 139.4 vs distractor
  74.5 chars). On `stemez-Psychology` (305) it is **66.2%** and **67.0%** (chance 10.6%; 138.2 vs 81.3 chars). The
  token view agrees (66.0% and 67.1%). Two of every three of these questions can be answered by picking the
  longest option without reading the question.
- Other strong `src` values: `stemez-ComputerScience` 51.1% (n 60), `stemez-Economics` 39.1% (n 400),
  `stemez-Genetics` 32.5% (n 147).
- **TheoremQA has no length cue at all.** Its answers are short numbers (mean gold 4.7 characters) and
  pick-longest sits slightly below chance (0.0963 vs 0.1007). This is why P3 failed: not every new source carries
  the cue.
- **SciBench's edge is a character effect.** By characters pick-longest is 0.1562 (chance 0.1018), but by tokens
  it is 0.0997, below chance, and the gold is the unique *shortest* option more often than the unique longest
  (6.47% vs 5.73%). This is why P6 failed.

**Inside each category, the new questions are where the cue lives (P5 HELD 9 of 9):**

| category | MMLU-derived n | pick-longest (chance) | lift (pts) | new-source n | pick-longest (chance) | lift (pts) |
| --- | --- | --- | --- | --- | --- | --- |
| psychology | 493 | .1196 (.1101) | +0.95 | 305 | .6701 (.1058) | +56.42 |
| biology | 219 | .1735 (.1302) | +4.33 | 498 | .5660 (.1022) | +46.37 |
| economics | 444 | .1118 (.1215) | −0.97 | 400 | .3907 (.1185) | +27.23 |
| computer science | 274 | .1023 (.1251) | −2.29 | 136 | .2564 (.1018) | +15.45 |
| engineering | 67 | .1197 (.1228) | −0.31 | 902 | .2267 (.1090) | +11.77 |
| physics | 411 | .0893 (.1041) | −1.49 | 888 | .1609 (.1005) | +6.05 |
| chemistry | 178 | .1079 (.1082) | −0.03 | 954 | .1544 (.1032) | +5.12 |
| business | 155 | .0945 (.1050) | −1.05 | 634 | .1351 (.1019) | +3.32 |
| math | 846 | .0908 (.1063) | −1.56 | 505 | .1330 (.1007) | +3.23 |

Health, history, law, other and philosophy have only MMLU-derived questions. On the MMLU-derived side, 7 of these
9 categories are at or below chance; only biology (+4.33) and psychology (+0.95) are above it.

**Audit 62's derivation, checked.** Audit 62 inferred about 56% for biology's non-intact-or-new remainder (505
questions) and about 61% for psychology's (358). Measured on the new-source questions alone: biology 56.6% (498),
psychology 67.0% (305). Biology matches. Psychology is higher than the derived figure because audit 62's remainder
also held the 53 MMLU-derived psychology questions outside its intact set (493 − 440), and those pull the
average down (biology's remainder held only 7 such questions: 505 = 498 + 7). Both derived figures were in the right direction and above 50%.

**Reading it:** a closed-book MMLU-Pro score should be read against a length-only floor that depends on where the
question came from: about 13% on MMLU-derived questions (chance 11.6%), about 29% on STEM-website questions
(chance 10.5%), about 67% on STEM-website biology and psychology, and chance on TheoremQA. Reporting MMLU-Pro by
`src`, not just by category, separates these.

## Limits

- The family is the `src` prefix. `stemez` is read as the "STEM website" source the MMLU-Pro paper names; this
  audit does not inspect the website.
- Length is measured on raw option text; LaTeX, units and numerals lengthen an option without changing its content.
  The token view is given alongside and agrees for `stemez`, not for `scibench`.
- The share-of-excess column and the `stemez-Biology` + `stemez-Psychology` reading are arithmetic on the frozen
  results, not separate measurements.
- This is a property of the answer options. It does not show that any model exploits it.

## Reproduce

```
python -m unittest -v        # hand-traced fixtures for the census core and the source keys
python job.py --out-dir out  # downloads the MMLU-Pro test parquet, writes out/results.json
```

`job.py` reads `TIGER-Lab/MMLU-Pro` (`default`, `test`) from the HuggingFace auto-converted parquet via the
datasets-server parquet API. The run aborts unless the fixtures match exactly and the pooled, provenance, biology
and psychology numbers match audits 61 and 62 exactly. Accumulation is exact (`fractions.Fraction`) and standard
library only.

## Files

- `job.py`: loader, census under every key, structural gate, predictions; writes `results.json`
- `source.py`: source family / provenance keys, the structural gate and the pre-registered predictions
- `gold_length.py`: length / unique-longest / pick-longest logic (verbatim from audits 51, 52, 60, 61 and 62)
- `cases.py`: hand-traced synthetic fixtures, real-data config, pinned audit-61/62 reference numbers
- `test_source_length.py`: unit tests
- `results.json`: frozen output (pooled, by provenance, category, family, category × provenance, category × family,
  every `src`, predictions)
- `requirements.txt`: a parquet reader only

## Licence

Code is Apache-2.0. This write-up and `results.json` are CC BY 4.0. Upstream: MMLU-Pro (`TIGER-Lab/MMLU-Pro`) is
MIT-licensed. Authored by AI agents working in MV2's name (Munim, Inc.).
