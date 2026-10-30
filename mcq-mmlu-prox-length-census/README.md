# mcq-mmlu-prox-length-census

Audit 67 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code, the pre-registered
predictions and the frozen `results.json` are open and reproducible in a sealed container with only the Python
standard library plus a parquet reader.*

## What this targets

Audits 61-63 found that on MMLU-Pro a question-free "pick the longest option" heuristic scores 18.4% against 11.1%
chance, and about 67% on the 656 STEM-website (`stemez`) biology and psychology questions. Audits 65-66 found that
models' answers follow that cue. MMLU-ProX (`li-lab/MMLU-ProX`, MIT) translates MMLU-Pro into 29 languages with the
options kept in the same order, and is used to compare models across languages.

**Does the length shortcut survive translation?** Option lengths change when text is translated, and they change
differently by script. If translation scrambled them, MMLU-ProX would have no length floor in most languages and
cross-language score gaps on the leaky questions would partly reflect the floor disappearing, not ability.

This audit joins every translated test question back to its English MMLU-Pro row and measures, per language and on
exactly the same questions: pick-longest accuracy, its lift over chance relative to English (**retention** = lift in
the language / lift in English), and how often the option that is the unique longest in English is still the unique
longest after translation (**unique-longest kept**).

## Prior art

The MMLU-ProX paper (arXiv 2503.10497, EMNLP 2025) describes translation by LLMs with expert review and a prompt
that keeps the number of options; it does not analyse option length. Earlier audits in this catalogue and the
Turkish MMLU Pro paper (arXiv 2609.15467) measure length effects in one language. A search on 2026-10-30 found no
measurement of whether MMLU-Pro's length shortcut carries over into MMLU-ProX or any other translated MCQ benchmark.

## Pre-registered predictions (frozen before any MMLU-ProX file was opened)

| # | Prediction | Verdict |
| --- | --- | --- |
| P1 | Every one of the 29 languages joins at least 95% of its rows to MMLU-Pro | **HELD** (99.80% in every language) |
| P2 | Pick-longest beats chance in every language | **HELD** (29 of 29) |
| P3 | Pick-longest at least 0.5 on STEM-website biology + psychology in at least 25 languages | **HELD** (29 of 29) |
| P4 | Median retention across languages in [0.6, 1.2] | **HELD** (0.988) |
| P5 | Median unique-longest-kept share at least 0.70 | **FAILED** (0.680) |
| P6 | The `en` config reproduces English MMLU-Pro within 0.005 | **HELD** (gap 0.0003) |
| P7 | Chinese, Japanese and Korean each below the median retention | **FAILED** (zh 0.988 is the median; ja 1.000, ko 1.033) |

## Validity gates

- Hand-traced fixtures for the join, the accumulator and the report match exactly.
- The MMLU-Pro parse reproduces audit 63 exactly: 12,032 questions; families `ori_mmlu` 6,810, `stemez` 4,083,
  `scibench` 541, `theoremQA` 598; `stemez-Biology` (n 351) and `stemez-Psychology` (n 305) pick-longest to all
  printed digits.
- A translated row joins only if its MMLU-Pro id finds an English row with the same `answer_index`, `N/A` or blank
  in every option slot past the English option count, and non-blank text in the slots before it. MMLU-ProX carries
  two id columns; `question_id_src` (the MMLU-Pro id) joins 11,736 of 11,759 test rows in every language (zh 11,735),
  while its own `question_id` joins only 897, so `question_id_src` is used everywhere. The rows that fail are the
  same in every language: 16 with a different answer index, 4 with different padding, 3 with an empty option (zh 4).

## What it found

**1. The shortcut survives translation almost intact, in every language.** On the 11,736 joined questions English
pick-longest is 0.1839 against 0.1102 chance. In the 28 translated languages it is 0.1796 (Czech) to 0.1889
(Vietnamese), and the lift over chance keeps 0.941 to 1.068 of its English size (median over all 29 configs 0.988).
In 18 languages the lift shrinks slightly, in 10 it grows slightly. No script stands out.

**2. ...even though the longest option often changes.** Among the 6,792 questions whose English options have a unique
longest, that same option is still the unique longest in only 57.3% (Chinese, Japanese) to 77.4% (Afrikaans) of
translated questions (median 0.680, so P5 failed). The identity of the longest option is noisy under translation;
the gold's tendency to be long is not. One reading, not tested here: swaps happen mostly among options of similar
length, while golds that lead by a wide margin keep their lead. Consistent with that, on the STEM-website biology
and psychology questions, where the gold leads most, the unique longest is kept more often (0.767 to 0.883) than on
the whole set in all 28 translated languages.

**3. The 67% pocket stays above 62% everywhere.** On the 655 joined STEM-website biology and psychology questions
English pick-longest is 0.6695. Translated, it is 0.6228 (Wolof) to 0.6558 (Russian): about six times the 0.104
chance rate in every language. Here, unlike the pooled figure, every translated language is a little below English
(retention 0.917 to 0.986, all 28 below 1; exploratory, not pre-registered).

**4. Chinese, Japanese and Korean are not special.** Characters per option fall sharply in CJK scripts, so P7
guessed these three would keep less of the cue. They did not: retention 0.988, 1.000 and 1.033. Their unique-longest
kept share is the lowest (0.573, 0.573, 0.609), which again leaves the shortcut itself in place.

**5. Many option sets are not translated at all.** In 1,134 (Bengali, 9.7%) to 4,526 (Zulu, 38.6%) of the joined
questions every option is character-for-character identical to English, mostly numbers, formulas and units. These
keep English lengths exactly and are part of why retention is so high; the share is reported per language below.
The `en` config itself differs from current English MMLU-Pro options in 373 questions (11,363 identical), yet its
pick-longest is within 0.0003 of English.

| lang | pick-longest | retention | unique-longest kept | options identical to English | STEM-web bio+psy pick-longest |
| --- | --- | --- | --- | --- | --- |
| af | .1831 | 0.989 | .774 | 3,937 | .6618 |
| ar | .1808 | 0.957 | .636 | 2,495 | .6361 |
| bn | .1812 | 0.963 | .659 | 1,134 | .6358 |
| cs | .1796 | 0.941 | .706 | 2,314 | .6526 |
| de | .1808 | 0.958 | .713 | 2,310 | .6480 |
| en | .1843 | 1.005 | .999 | 11,363 | .6696 |
| es | .1827 | 0.983 | .742 | 3,231 | .6536 |
| fr | .1812 | 0.963 | .733 | 2,216 | .6411 |
| hi | .1839 | 0.999 | .663 | 3,068 | .6422 |
| hu | .1817 | 0.969 | .706 | 2,357 | .6315 |
| id | .1847 | 1.010 | .723 | 2,701 | .6523 |
| it | .1828 | 0.984 | .756 | 2,812 | .6437 |
| ja | .1840 | 1.000 | .573 | 3,230 | .6441 |
| ko | .1863 | 1.033 | .609 | 3,558 | .6510 |
| mr | .1871 | 1.043 | .688 | 3,172 | .6373 |
| ne | .1827 | 0.983 | .680 | 2,827 | .6347 |
| pt | .1818 | 0.971 | .740 | 2,228 | .6544 |
| ru | .1843 | 1.005 | .685 | 2,835 | .6558 |
| sr | .1843 | 1.005 | .717 | 2,486 | .6522 |
| sw | .1816 | 0.969 | .654 | 3,771 | .6317 |
| te | .1858 | 1.025 | .677 | 3,880 | .6467 |
| th | .1861 | 1.029 | .629 | 3,143 | .6307 |
| uk | .1833 | 0.991 | .682 | 2,562 | .6528 |
| ur | .1862 | 1.031 | .677 | 3,650 | .6376 |
| vi | .1889 | 1.068 | .677 | 2,822 | .6480 |
| wo | .1827 | 0.983 | .672 | 4,303 | .6228 |
| yo | .1803 | 0.950 | .663 | 4,445 | .6277 |
| zh | .1831 | 0.988 | .573 | 2,925 | .6399 |
| zu | .1816 | 0.969 | .673 | 4,526 | .6483 |

All figures are on the joined questions of that language: 11,736 (zh 11,735) for the first four columns and 655 for
the last. English MMLU-Pro on the same questions: pick-longest 0.1839, chance 0.1102; STEM-website biology +
psychology 0.6695, chance 0.1041. "Unique-longest kept" is over the 6,792 questions (zh 6,791) whose English options
have a unique longest. Percentages in the text are derived from these counts.

**Reading it:** a closed-book MMLU-ProX score carries the same length-only floor as MMLU-Pro in every language:
about 18% overall against 11% chance, and 62-67% on the STEM-website biology and psychology questions. Translation
does not wash the shortcut out, so comparing a model's MMLU-ProX scores across languages on those questions compares
it against nearly the same floor; the floor should be reported per slice, not assumed to be 1/k.

## Limits

- **Construction property only.** No model is evaluated; whether models exploit the cue in other languages is open
  (audits 65-66 measure it in English only).
- MMLU-ProX's test split has 11,759 questions, 273 fewer than MMLU-Pro's 12,032, and 23 of them (24 in zh) fail
  the join, so the English comparison figures are on the joined subset, not the full 12,032.
- Lengths are Unicode code points after `str.strip()`. Code points are not a measure of reading effort, and scripts
  differ in how much they pack into one; retention compares each language with itself through chance and English,
  so it does not depend on cross-script length comparisons.
- The explanation in finding 2 is an interpretation, and the STEM-website retention and agreement comparisons in
  findings 2 and 3 are exploratory.
- No question or option text is republished; `results.json` holds only counts and rates.

## Reproduce

```
python -m unittest -v        # hand-traced fixtures: join, accumulation, report
python job.py --out-dir out  # downloads MMLU-Pro test and the 29 MMLU-ProX test configs, writes out/results.json
```

`job.py` reads `TIGER-Lab/MMLU-Pro` (`default`, `test`) and `li-lab/MMLU-ProX` (29 configs, `test`) from the
HuggingFace auto-converted parquet via the datasets-server parquet API. It aborts unless the fixtures match and the
parse reproduces audit 63 exactly. Accumulation is exact (`fractions.Fraction`) and standard library only. The
sealed run took about 5 minutes on 2 CPUs with 0.26 GB peak memory.

To compute the same floor on your own benchmark, use
[mcq-length-floor](https://github.com/munimtechnologies/mcq-length-floor).

## Files

- `job.py`: loaders, the audit-63 gate, per-language join and accumulation; writes `results.json`
- `prox.py`: join rules, key choice, per-language accumulators, retention and unique-longest agreement, the
  pre-registered predictions
- `model_length.py`: tie-aware pick-longest credit and source keys (from audit 65)
- `cases.py`: hand-traced fixtures, the language list, pinned audit-63 numbers
- `test_prox.py`: unit tests
- `results.json`: frozen output (per language: join status by key, counts, every report by family, source,
  category and subset; predictions with details)
- `requirements.txt`: a parquet reader only

## Licence

Code is Apache-2.0. This write-up and `results.json` are CC BY 4.0. Upstream: MMLU-Pro (`TIGER-Lab/MMLU-Pro`) and
MMLU-ProX (`li-lab/MMLU-ProX`) are MIT-licensed. Authored by AI agents working in MV2's name (Munim, Inc.).
