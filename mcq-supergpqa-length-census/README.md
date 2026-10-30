# mcq-supergpqa-length-census

Audit 64 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code, the pre-registered
predictions and the frozen `results.json` are open and reproducible in a sealed container with only the Python
standard library plus a parquet reader.*

## What this targets

Audits 61 to 63 found that MMLU-Pro, a 10-option benchmark with LLM-assisted distractors, carries a strong
"pick the longest option" shortcut: 18.4% against 11.1% chance pooled, and about 67% on its STEM-website biology
and psychology questions. SuperGPQA (m-a-p/SuperGPQA, 26,529 graduate-level questions in 13 disciplines, mostly
10 options) was built later with a stated rule that confusing options should be of similar length. Its paper reports
only mean token lengths (answers 12.86 vs options 12.64).

This audit runs the same tie-aware length census on all of SuperGPQA, by discipline, difficulty, calculation flag
and option count, and adds three data-quality checks: answer letter vs answer text, duplicated options, and the
gold-position distribution of the 10-option questions. Lengths are characters after `str.strip()`, with whitespace
tokens alongside. This measures **agreement with a length heuristic**, a property of the options, not the
correctness of any model.

## Prior art

The SuperGPQA paper (arXiv 2502.14739) describes the similar-length rule and reports mean lengths only. A search on
2026-10-30 found no pick-longest, choices-only or gold-position result for SuperGPQA. Related length work:
Balepur et al. (arXiv 2402.12483, choices-only MCQ) and FormationEval (arXiv 2601.02158).

## Pre-registered predictions (frozen before any real number)

| # | Prediction | Verdict |
| --- | --- | --- |
| P1 | Pooled pick-longest scores under 1.5× chance (MMLU-Pro: 1.66×) | **HELD** (1.23×) |
| P2 | A residual cue remains: pooled lift at least +1 point | **HELD** (+2.43 pts) |
| P3 | Text questions carry a larger lift than calculation questions | **HELD** (+2.67 vs +2.09) |
| P4 | Easy questions carry a larger lift than hard ones | **HELD** (+1.96 vs +1.64) |
| P5 | Mean gold length exceeds mean distractor length (characters) | **HELD** (34.90 vs 34.23) |
| P6 | The gold is the unique longest option more often than the unique shortest | **HELD** (2,109 vs 1,814) |
| P7 | Gold positions of the 10-option questions are uniform (χ² df 9 < 27.877) | **HELD** (χ² = 14.98) |
| P8 | Pick-longest beats chance in a strict majority of disciplines with n ≥ 100 | **HELD** (12 of 13) |
| P9 | The answer text equals the option named by the answer letter in every question | **HELD** (0 mismatches) |

All nine held. Each would have been a finding either way.

## Validity gate

The same pipeline first re-reads MMLU-Pro and must reproduce audit 61 exactly: 12,032 valid questions, 1,655 gold
unique-longest, pick-longest 0.18376805…, 0 bad keys, 0 degenerate rows. It did. SuperGPQA's row count matches the
paper (26,529).

## What it found

**SuperGPQA's similar-length rule mostly works.** Its length cue is about a third of MMLU-Pro's and has no
pocket anywhere near MMLU-Pro's 67%.

| benchmark | n | chance | pick-longest | lift (pts) | × chance | gold unique-longest | gold unique-shortest | mean gold / distractor (chars) | pick-longest, tokens |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SuperGPQA | 26,529 | .1059 | .1301 | +2.43 | 1.23 | .0795 | .0684 | 34.90 / 34.23 | .1337 |
| MMLU-Pro (audit 61) | 12,032 | .1109 | .1838 | +7.29 | 1.66 | .1375 | .0616 | 43.24 / 36.10 | .1676 |

- **A small residual cue remains.** Pick-longest beats chance by 2.43 points and the gold is a little longer on
  average. The token view agrees (0.1337).
- **The gold also leans short.** Unlike MMLU-Pro, a "pick the shortest option" heuristic also beats chance on
  SuperGPQA (0.1229 vs 0.1059 by characters, 0.1166 by tokens). The gold is a little more often at either length
  extreme than a random option would be. On MMLU-Pro pick-shortest is below chance (0.1054 vs 0.1109).
- **Clean data.** 0 unparseable letters, 0 letters out of range, 0 letter/text mismatches and 0 questions with
  duplicated option texts across all 26,529 rows.
- **No position cue.** Among the 23,158 ten-option questions the gold position is consistent with uniform
  (counts A–J 2,374 / 2,250 / 2,297 / 2,253 / 2,311 / 2,340 / 2,253 / 2,278 / 2,434 / 2,368; χ² = 14.98, df 9).

**By discipline** (13 disciplines, all with n ≥ 100):

| discipline | n | chance | pick-longest | lift (pts) | gold unique-longest | gold unique-shortest | mean gold / distractor (chars) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Management | 501 | .1044 | .1906 | +8.62 | .1617 | .0818 | 36.1 / 30.5 |
| Economics | 873 | .1022 | .1720 | +6.99 | .1386 | .0745 | 37.8 / 34.7 |
| Philosophy | 347 | .1067 | .1759 | +6.93 | .1585 | .1095 | 44.9 / 42.8 |
| Education | 484 | .1035 | .1695 | +6.60 | .1405 | .0971 | 31.1 / 29.5 |
| Law | 656 | .1050 | .1619 | +5.69 | .1433 | .1174 | 61.2 / 57.9 |
| Engineering | 7,892 | .1039 | .1293 | +2.54 | .0698 | .0521 | 34.1 / 33.5 |
| Military Science | 205 | .1157 | .1398 | +2.41 | .1073 | .0878 | 33.6 / 31.7 |
| Agronomy | 485 | .1016 | .1214 | +1.98 | .0969 | .0866 | 22.4 / 22.2 |
| Science | 9,838 | .1045 | .1231 | +1.86 | .0615 | .0579 | 38.0 / 37.5 |
| Literature and Arts | 1,676 | .1278 | .1388 | +1.10 | .0996 | .1044 | 23.5 / 22.9 |
| Medicine | 2,755 | .1051 | .1158 | +1.07 | .0915 | .0926 | 30.8 / 30.9 |
| History | 674 | .1064 | .1089 | +0.25 | .0564 | .0920 | 19.4 / 20.4 |
| Sociology | 143 | .1022 | .0923 | −0.98 | .0559 | .0909 | 37.9 / 36.0 |

The cue is largest in the social-science and humanities disciplines with prose answers (management, economics,
philosophy, education, law; +5.7 to +8.6 points), the same kind of subject where MMLU-Pro's cue peaked, but well
below MMLU-Pro's category peaks (biology +33.5, psychology +22.2; audit 61). The two big disciplines, Science and Engineering (17,730
questions, 67% of the benchmark), sit at +1.9 and +2.5. Medicine (2,755 questions) is at +1.1.

**By difficulty and calculation flag:**

| slice | n | chance | pick-longest | lift (pts) |
| --- | --- | --- | --- | --- |
| easy | 7,731 | .1068 | .1264 | +1.96 |
| middle | 11,748 | .1064 | .1385 | +3.21 |
| hard | 7,050 | .1040 | .1204 | +1.64 |
| text | 15,300 | .1078 | .1345 | +2.67 |
| calculation | 11,229 | .1032 | .1242 | +2.09 |
| middle × text | 7,303 | .1083 | .1437 | +3.54 |

P4 held (easy above hard) but the middle tier carries the largest lift, so the cue does not fall steadily with
difficulty. Questions with 4, 5, 6 or 8 options (1,605 questions) sit slightly below chance; 7-, 9- and 10-option
questions sit above it.

**Reading it:** a closed-book SuperGPQA score has a length-only floor of about 13% against 10.6% chance, and about
17–19% in management, economics, philosophy and education. That is a small cue next to MMLU-Pro's ~18% pooled and
~67% on its STEM-website biology and psychology questions. A stated similar-length rule, applied when the
distractors are written, appears to do what it says.

## Limits

- SuperGPQA is released as a single `train` split; this audit reads all of it.
- Length is measured on raw option text; LaTeX, units and numerals lengthen an option without changing its content.
- The pick-shortest observation was not pre-registered; it is read from the same frozen census.
- This is a property of the answer options. It does not show that any model exploits it.

## Reproduce

```
python -m unittest -v        # hand-traced fixtures for the census core, keys, quality counts and chi-square
python job.py --out-dir out  # downloads SuperGPQA and the MMLU-Pro test parquet, writes out/results.json
```

`job.py` reads `m-a-p/SuperGPQA` (`default`, `train`) and `TIGER-Lab/MMLU-Pro` (`default`, `test`) from the
HuggingFace auto-converted parquet via the datasets-server parquet API. The run aborts unless the fixtures match and
the MMLU-Pro numbers reproduce audit 61 exactly. Accumulation is exact (`fractions.Fraction`) and standard library
only.

## Files

- `job.py`: loader, census under every key, quality counts, position test, gate and predictions; writes `results.json`
- `supergpqa.py`: row conversion, quality counts, chi-square, the structural gate and the pre-registered predictions
- `gold_length.py`: length / unique-longest / pick-longest logic (verbatim from audits 51, 52 and 60 to 63)
- `cases.py`: hand-traced synthetic fixtures, real-data config, pinned audit-61 reference numbers
- `test_supergpqa.py`: unit tests
- `results.json`: frozen output (pooled, MMLU-Pro reference, by difficulty, calculation, option count, discipline,
  field, quality, position, predictions)
- `requirements.txt`: a parquet reader only

## Licence

Code is Apache-2.0. This write-up and `results.json` are CC BY 4.0. Upstream: SuperGPQA (`m-a-p/SuperGPQA`) is
ODC-BY; MMLU-Pro (`TIGER-Lab/MMLU-Pro`) is MIT-licensed. Authored by AI agents working in MV2's name (Munim, Inc.).
