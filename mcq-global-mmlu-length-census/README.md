# mcq-global-mmlu-length-census

Audit 70 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code, the pre-registered
predictions and the frozen `results.json` are open and reproducible in a sealed container with only the Python
standard library plus a parquet reader.*

## What this targets

Audits 52 and 60 found that MMLU carries a small question-free "pick the longest option" shortcut (28.05% against
25% chance), concentrated in law, clinical and social subjects. Global-MMLU (Singh et al. 2024, arXiv 2412.03304;
`CohereLabs/Global-MMLU`, Apache-2.0) translates MMLU's 14,042 test questions into 42 languages and labels 2,850 of
them Culturally Sensitive (CS, 792) or Culturally Agnostic (CA, 2,058). Its paper reports no answer-length analysis.

This audit asks:

1. **Are Global-MMLU's English rows MMLU's test rows?** Joined by `sample_id` to `cais/mmlu`.
2. **Do CS and CA questions carry different length floors?** Raw, and within subject.
3. **What happens to the floor in each of the 41 translations**, and do the translations keep English's answer
   keys and English's longest option?

## Prior art

A search on 2026-10-30 found no length analysis of Global-MMLU or of its CS/CA split. Audit 67 in this catalogue
measured the same cue across MMLU-ProX's 29 languages (it kept 0.941-1.068 of the English lift). A search on
2026-10-31 of the web and of the dataset's Hugging Face discussions (5 threads) found no report that some
translations carry a different answer key from English.

## Pre-registered predictions (frozen before any real number was seen)

| # | Prediction | Verdict |
| --- | --- | --- |
| P1 | Structural: 42 configs x 14,042 test rows; English has 792 CS, 2,058 CA, 0 invalid | **HELD** |
| P2 | MMLU `all` (test + validation + dev) reproduces audit 60: n 15,858, pick-longest 0.2805 | **HELD** |
| P3 | At least 99% of English rows are identical to MMLU test (all four options and the key) | **HELD** (14,042 of 14,042) |
| P4 | HEADLINE: in English, CS questions carry a larger pick-longest lift than CA questions | **FAILED** (+2.73 vs +3.41 pts) |
| P5 | Stratifying by subject shrinks the CS - CA difference | **FAILED** (-0.68 raw, +1.74 within subject) |
| P6 | Every language keeps 0.80-1.25 of the English lift | **FAILED** (Ukrainian 0.775; the other 40 held) |
| P7 | Every language beats chance with z > 3.29 | **HELD** (lowest z 7.12) |
| P8 | Every language has English's answer key on every row | **FAILED** (Chinese 176, Korean 116, German 5, Italian 3, Yoruba 2, Japanese 1) |
| P9 | The CS - CA difference keeps English's sign in at least 38 of 41 languages | **FAILED** (31 of 41) |

## Validity gates

- Hand-traced fixtures for tie-aware credit, the CS/CA difference, the within-subject estimate, the comparison with
  English and the MMLU join match exactly before any real data is read.
- MMLU `all` reproduces audit 60 (P2), and the English floor matches the released
  [mcq-length-floor](https://github.com/munimtechnologies/mcq-length-floor) 0.1.0 to every digit. The job aborts on
  any mismatch.
- Every language has 14,042 rows and the same 14,042 `sample_id`s as English (0 missing either way).

## What it found

**1. Global-MMLU's English is exactly MMLU's test set.** All 14,042 English rows join to `cais/mmlu` test by
`sample_id` with identical options and key. English pick-longest is **28.22%** against 25% chance (+3.22 pts, z 9.09).

**2. No CS/CA difference is visible.** On English, CS questions score 27.73% (+2.73 pts, n 792) and CA questions
28.41% (+3.41 pts, n 2,058): a difference of **-0.68 pts (se 1.75, z -0.39)**. Within subject (43 subjects with both
labels) the estimate flips to **+1.74 pts (se 2.37, z 0.73)**. Neither is distinguishable from zero, so both
direction predictions (P4, P5) failed on noise, not on a measured opposite effect. The two labels sit in different
subjects (CS is 56% humanities, CA 45% STEM; derived from `results.json`), which is why the raw and within-subject
estimates differ. Across the 41 translations no CS - CA difference reaches |z| 1.7, and its sign matches English in
31 of 41 (P9 failed), as expected when the true difference is about zero.

**3. Translation keeps most of the cue.** Every language beats chance by at least 7 standard errors (P7). The
translations keep **0.775 (Ukrainian) to 1.054 (Romanian)** of the English lift, median 0.907 (derived); only
Ukrainian falls below the pre-registered 0.80, so P6 failed by one language. That is a little more loss than
MMLU-ProX showed for MMLU-Pro (audit 67, 0.941-1.068). English's unique longest option stays the unique longest in
**59.4% (Chinese) to 78.0% (Filipino)** of questions, yet the floor barely moves: the gold's length advantage
survives translation even when the longest option itself changes.

**4. Chinese and Korean carry different answer keys from English on 176 and 116 questions.** The pre-registered
check that every translation keeps English's answer letter (P8) failed: Chinese (`zh`) differs on **176** of 14,042
rows, Korean (`ko`) on **116**, German on 5, Italian on 3, Yoruba on 2, Japanese on 1, and the other 35 languages on
0. Since English is MMLU's test set exactly, a model scored on Chinese or Korean Global-MMLU is graded against a
different key on about 1% of questions. This audit cannot tell whether the options were reordered in translation
(same answer, new letter) or the key itself was changed (a correction or an error); audit 71 is queued to tell those
apart. Until then this is a measured discrepancy, not a claim of error.

| lang | pick-longest | lift (pts) | z | ratio to en | CS - CA (pts) | same unique longest | key ≠ en |
| --- | --- | --- | --- | --- | --- | --- | --- |
| en | .2822 | +3.22 | 9.09 | 1.000 | -0.68 | - | - |
| am | .2805 | +3.05 | 8.62 | 0.949 | -1.94 | .681 | 0 |
| ar | .2759 | +2.59 | 7.39 | 0.804 | +0.95 | .670 | 0 |
| bn | .2822 | +3.22 | 9.05 | 1.002 | +1.70 | .722 | 0 |
| cs | .2770 | +2.70 | 7.65 | 0.840 | -0.12 | .753 | 0 |
| de | .2825 | +3.25 | 9.13 | 1.012 | -1.10 | .741 | 5 |
| el | .2808 | +3.08 | 8.66 | 0.958 | -0.50 | .736 | 0 |
| es | .2816 | +3.16 | 8.88 | 0.982 | -0.87 | .767 | 0 |
| fa | .2780 | +2.80 | 7.91 | 0.871 | -2.31 | .686 | 0 |
| fil | .2818 | +3.18 | 8.90 | 0.987 | -1.13 | .780 | 0 |
| fr | .2798 | +2.98 | 8.40 | 0.926 | -0.91 | .754 | 0 |
| ha | .2787 | +2.87 | 8.08 | 0.894 | -0.06 | .630 | 0 |
| he | .2766 | +2.66 | 7.82 | 0.825 | -0.76 | .626 | 0 |
| hi | .2787 | +2.87 | 8.10 | 0.893 | -0.07 | .706 | 0 |
| id | .2819 | +3.19 | 9.04 | 0.993 | +0.60 | .743 | 0 |
| ig | .2780 | +2.80 | 7.87 | 0.870 | -2.92 | .709 | 0 |
| it | .2782 | +2.82 | 7.94 | 0.875 | -1.59 | .767 | 3 |
| ja | .2787 | +2.87 | 8.42 | 0.891 | -1.47 | .616 | 1 |
| ko | .2821 | +3.21 | 9.38 | 0.999 | -0.60 | .641 | 116 |
| ky | .2792 | +2.92 | 8.46 | 0.907 | +0.06 | .658 | 0 |
| lt | .2810 | +3.10 | 8.69 | 0.963 | +0.14 | .669 | 0 |
| mg | .2824 | +3.24 | 9.04 | 1.006 | -1.13 | .721 | 0 |
| ms | .2785 | +2.85 | 8.05 | 0.885 | -2.35 | .749 | 0 |
| ne | .2788 | +2.88 | 8.14 | 0.896 | -2.32 | .720 | 0 |
| nl | .2786 | +2.86 | 8.06 | 0.890 | -1.05 | .772 | 0 |
| ny | .2829 | +3.29 | 9.19 | 1.023 | -2.05 | .722 | 0 |
| pl | .2779 | +2.79 | 7.85 | 0.868 | -1.33 | .729 | 0 |
| pt | .2816 | +3.16 | 8.92 | 0.984 | -2.72 | .760 | 0 |
| ro | .2839 | +3.39 | 9.48 | 1.054 | -2.02 | .775 | 0 |
| ru | .2784 | +2.84 | 8.18 | 0.883 | +1.38 | .645 | 0 |
| si | .2779 | +2.79 | 7.86 | 0.867 | -1.42 | .718 | 0 |
| sn | .2824 | +3.24 | 9.07 | 1.006 | -2.31 | .752 | 0 |
| so | .2773 | +2.73 | 7.66 | 0.848 | -0.49 | .720 | 0 |
| sr | .2786 | +2.86 | 8.09 | 0.890 | -2.28 | .761 | 0 |
| sv | .2816 | +3.16 | 8.87 | 0.983 | -1.22 | .775 | 0 |
| sw | .2772 | +2.72 | 7.70 | 0.844 | -2.50 | .710 | 0 |
| te | .2823 | +3.23 | 9.03 | 1.003 | +0.22 | .718 | 0 |
| tr | .2778 | +2.78 | 7.85 | 0.866 | +0.56 | .725 | 0 |
| uk | .2749 | +2.49 | 7.12 | 0.775 | +1.04 | .661 | 0 |
| vi | .2825 | +3.25 | 9.11 | 1.010 | -0.63 | .690 | 0 |
| yo | .2809 | +3.09 | 8.96 | 0.960 | -1.56 | .612 | 2 |
| zh | .2796 | +2.96 | 8.95 | 0.921 | +0.69 | .594 | 176 |

Pick-longest is a tie-aware accuracy against each language's own key; chance is 0.25 everywhere; lift = pick-longest
minus chance in percentage points; ratio = lift ÷ English lift. CS - CA uses English's labels for every language.
"Same unique longest" is the share of questions whose English unique longest option is still the unique longest
after translation. A few rows with a blank option are skipped (at most 7 per language: Amharic and Hindi).

By English subject category the lift is +5.11 pts in Medical (n 1,505), +4.73 in Humanities (4,705), +2.56 in
Business (719), +2.51 in STEM (3,153), +2.13 in Social Sciences (3,077) and -1.22 in Other (883).

**Reading it:** a closed-book Global-MMLU score faces about a 28% length-only floor in every language, not 25%, and
the CS/CA split does not change it measurably. Anyone comparing Chinese or Korean Global-MMLU scores with English
should know the two sets disagree on about 1% of answer keys.

## Limits

- **CS n = 792** gives about a 1.75-pt standard error on the CS - CA gap; a gap of 3 pts or less cannot be detected.
- CS/CA labels are English's for every language (a handful of rows carry a different label in Spanish, Italian and
  Japanese; those were ignored).
- Global-MMLU mixes machine translations with human-edited ones; this audit does not split languages by how they
  were translated.
- Key disagreements are counted, not explained (see finding 4 and audit 71).
- Observational; no model is evaluated. Lengths are Unicode code points after `str.strip()`. No question or option
  text is republished; `results.json` holds only counts, rates and parquet sha256s.

## Reproduce

```
python -m unittest -v        # hand-traced fixtures
python job.py --out-dir out  # downloads MMLU all, Global-MMLU (42 test configs) and mcq-length-floor 0.1.0
```

The sealed run (job `mcq-global-mmlu-length-census-v1`, 1 CPU, 1 GB) took under 4 minutes.

## Files

- `job.py`: loaders, MMLU reproduction, English join, per-language reports, tool cross-check, predictions; writes
  `results.json`
- `gmmlu_length.py`: tie-aware credit, CS/CA difference, within-subject estimate, comparison with English and MMLU
- `cases.py`: hand-traced fixtures, dataset configuration, structural expectations
- `test_gmmlu_length.py`: unit tests
- `results.json`: frozen output (MMLU reproduction, join counts, every language's floors and comparison with English,
  raw label histograms, predictions)
- `requirements.txt`: a parquet reader only

## Licence

Code is Apache-2.0. This write-up and `results.json` are CC BY 4.0. Upstream: Global-MMLU (`CohereLabs/Global-MMLU`)
is Apache-2.0; MMLU (`cais/mmlu`) is MIT. Authored by AI agents working in MV2's name (Munim, Inc.).
