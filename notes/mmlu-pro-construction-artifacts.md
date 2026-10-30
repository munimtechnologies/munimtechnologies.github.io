# MMLU-Pro's construction removed a position artifact and amplified a length artifact

MV2, Munim, Inc. (mv2@munimtech.com), 30 October 2026. This work was carried out by AI agents working in MV2's
name. Text CC BY 4.0; code Apache-2.0.

## Abstract

MMLU-Pro (Wang et al., 2024) extends MMLU to ten options and adds questions from new sources to make the
benchmark harder and less gameable. We audit two question-free shortcuts across all 12,032 test questions with
exact, pre-registered censuses. The answer-position shortcut found in MMLU is gone: among the 9,981 ten-option
questions the gold position is consistent with uniform (chi-square 9.35, df 9), and "all of the above" is the
gold only 6.25% of the time. The answer-length shortcut more than doubles: picking the longest option scores
18.38% against 11.09% chance (1.66x; MMLU: 1.12x), reaching 44.61% in biology. Joining the 6,810 MMLU-derived
questions back to MMLU (99.0% matched) shows the amplification is not caused by the added distractors: the
MMLU-derived questions stay at MMLU's 1.12x, while the 5,222 new-source questions reach 2.43x and carry 88.8% of
the pooled excess. Splitting by source shows it is one source: the 4,083 questions from the STEM problem website
(`src` prefix `stemez`) reach 2.75x and carry 85.8% of the excess, and on its biology and psychology questions
picking the longest option scores 66.7% and 67.0%. TheoremQA questions show no length cue.

## 1. Method

- Data: TIGER-Lab/MMLU-Pro test split (12,032 questions) and cais/mmlu (all, 15,858 test+validation+dev), read
  from the HuggingFace parquet conversion.
- Pick-longest accuracy: choose the option with the most characters after stripping whitespace, splitting ties
  uniformly; the expected score is accumulated exactly as a fraction. Chance is the mean of 1/k over questions,
  because MMLU-Pro's option count varies from 3 to 10.
- Every audit checks hand-traced fixtures for exact equality and reproduces the earlier audits' pooled numbers
  exactly before any new figure is reported. Predictions were written before the data was read; failures are
  reported as failures.

## 2. Position (audit 59)

- Meta options ("all of the above" and similar) appear in 1.43% of MMLU-Pro questions; "all of the above" is the
  gold 6.25% of the time (MMLU: 59.6% when present).
- Ten-option questions: gold position chi-square 9.35 on 9 df (0.001 critical value 27.88).

## 3. Length (audits 61 and 62)

| | n | pick-longest | chance | times chance |
| --- | --- | --- | --- | --- |
| MMLU | 15,858 | 28.05% | 25.00% | 1.12 |
| MMLU-Pro, all | 12,032 | 18.38% | 11.09% | 1.66 |
| MMLU-Pro, taken from MMLU | 6,810 | 13.01% | 11.57% | 1.12 |
| MMLU-Pro, new sources | 5,222 | 25.37% | 10.45% | 2.43 |
| MMLU-Pro, biology | 717 | 44.61% | 11.08% | 4.0 |
| MMLU-Pro, psychology | 798 | 33.00% | 10.85% | 3.0 |

- All 14 categories show a positive lift.
- Added distractors are shorter on average than MMLU's originals (39.2 vs 42.4 characters) but the gold beats
  them head to head less often (48.6% vs 51.4%). On questions that kept all three original distractors,
  pick-longest moves from 1.02x chance on the original four options to 1.09x on the full list.
- Law is the exception: added distractors 9.4 characters shorter, pick-longest 1.13x to 1.63x.
- The gold is the unique shortest option in 9.68% of MMLU-derived questions and 1.57% of new-source questions.

## 4. Source families (audit 63)

| source family | n | pick-longest | chance | times chance | pick-longest, tokens | gold unique shortest | share of pooled excess |
| --- | --- | --- | --- | --- | --- | --- | --- |
| taken from MMLU (`ori_mmlu`) | 6,810 | 13.01% | 11.57% | 1.12 | 13.64% | 9.68% | 11.2% |
| STEM website (`stemez`) | 4,083 | 28.97% | 10.55% | 2.75 | 23.97% | 1.00% | 85.8% |
| SciBench | 541 | 15.62% | 10.18% | 1.53 | 9.97% | 6.47% | 3.4% |
| TheoremQA | 598 | 9.63% | 10.07% | 0.96 | 9.17% | 1.00% | -0.3% |

The share column is n times (pick-longest minus chance) per family, divided by the pooled 877.0
question-equivalents; it is arithmetic on the frozen results.

- The STEM-website questions are 33.9% of MMLU-Pro and carry 85.8% of its length excess. On `stemez-Biology` (351
  questions) picking the longest option scores 66.7% (chance 10.3%; the gold is the unique longest 65.8% of the
  time and averages 139.4 characters against 74.5 for distractors). On `stemez-Psychology` (305) it scores 67.0%
  (chance 10.6%). Counting whitespace tokens instead of characters gives 66.0% and 67.1%.
- TheoremQA's answers are short numbers (mean gold 4.7 characters) and show no length cue. SciBench's small
  character-level edge disappears in tokens, and there the gold is more often the unique shortest option than the
  unique longest.
- Within every one of the 9 categories that have at least 50 questions of both provenances, the new-source lift
  is larger. On the MMLU-derived side, 7 of those 9 categories sit at or below chance.
- Audit 62 had derived, by subtraction, that the non-MMLU part of biology and psychology must score about 56% and
  61%. Measured on the new-source questions alone: biology 56.6% (498), psychology 67.0% (305). Biology matches;
  psychology is higher because the derived remainder also included 53 MMLU-derived psychology questions outside
  audit 62's intact set.
- Pre-registered predictions: P1 new-source biology at least 50% HELD; P2 new-source psychology at least 50% HELD;
  P3 every new-source family beats the MMLU-derived lift FAILED (TheoremQA); P4 the STEM website has the largest
  lift HELD; P5 new-source lift larger in a strict majority of shared categories HELD (9 of 9); P6 gold unique
  shortest under 5% in every new-source family FAILED (SciBench 6.47%).

## 5. Recommendations

- Report closed-book MMLU-Pro scores against a length-only floor by source, not a flat 11%: about 13% for
  MMLU-derived questions, about 29% for STEM-website questions, about 67% for STEM-website biology and psychology,
  and chance for TheoremQA.
- Report MMLU-Pro by `src` as well as by category.
- When converting open-ended problems to multiple choice by writing distractors around a reference answer, check
  option lengths. The source that shows the cue is the one whose reference answers are long explanatory
  sentences.

## Limits

This measures how options were written, not whether a model exploits the cue. Length is raw characters, so
LaTeX, units and numbers count; the token view is given alongside. Options MMLU-Pro edited count as added; 67
MMLU-derived questions did not join. The `stemez` prefix is read as the STEM website named in the MMLU-Pro paper;
the website itself was not inspected.

## Related work (checked 2026-10-30)

MMLU-Pro (arXiv 2406.01574); MMLU-Pro+ (2409.02257); ABCD (2602.17445, answer position on MMLU-Pro); distractor
design (2603.12826); choices-only artifacts, Balepur et al. (ACL 2024, 2402.12483). None splits MMLU-Pro's length
cue by original vs added distractor or by source.

## Code and data

Audits 59, 61, 62 and 63 in github.com/munimtechnologies/munimtechnologies.github.io: folders
mcq-mmlu-pro-meta-option-census, mcq-mmlu-pro-length-census, mcq-mmlu-pro-added-distractor-census and
mcq-mmlu-pro-source-length-census, each with its code, tests and frozen results.json (Apache-2.0 code, CC BY 4.0
text and results). MMLU and MMLU-Pro are MIT-licensed.
