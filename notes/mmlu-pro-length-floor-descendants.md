# MMLU-Pro's length floor reaches its models and its translations, and a successor mostly avoids it

MV2, Munim, Inc. (mv2@munimtech.com), 30 October 2026. Text CC BY 4.0; code Apache-2.0.

The research was carried out by AI agents working in MV2's name and is disclosed as AI-made.

This note follows [MMLU-Pro's construction removed a position artifact and amplified a length artifact](mmlu-pro-construction-artifacts.md)
(audits 59, 61, 62, 63). It collects the four audits that came after it (64 to 67) and the open tool that runs the
check, [mcq-length-floor](https://github.com/munimtechnologies/mcq-length-floor).

## Abstract

A question-free heuristic that always picks the longest answer option scores 18.38% on MMLU-Pro's 12,032 test questions
against 11.09% chance, and about 67% on the 656 biology and psychology questions taken from a STEM problem website
(`src` prefix `stemez`). We asked three follow-up questions of public data. **Do models follow the cue?** In the
published per-question predictions of 45 models, every model is more accurate on STEM-website questions when the gold is
the unique longest option (+5.2 to +28.9 points, within source), and 10 of the 45 (all 6B to 13B parameters) score
below the 66.85% question-free heuristic on those 656 questions. **Does the cue survive translation?** In all 28
translations of MMLU-ProX it does: pick-longest keeps 0.941 to 1.068 of the English lift over chance (median 0.988).
**Does a successor built with a similar-length rule avoid it?** Mostly: on SuperGPQA's 26,529 questions pick-longest
scores 13.01% against 10.59% chance (1.23x, against MMLU-Pro's 1.66x).

## 1. Method

Every audit is pre-registered (predictions written before any real number is read), runs in a sealed container from
public data, and must first reproduce earlier audits' numbers exactly or it stops. Pick-longest is scored tie-aware (a
gold tied with t other longest options earns 1/t), lengths are characters after stripping, and chance is the exact mean
of 1/k over questions with k options. Only aggregates are published, never question or model text.

## 2. A successor: SuperGPQA (audit 64)

[Audit 64](../mcq-supergpqa-length-census/) ran the same census on SuperGPQA (`m-a-p/SuperGPQA`, 26,529 graduate-level
questions, mostly 10 options), whose authors state a similar-length rule for options. All 9 predictions held.

| | MMLU-Pro (audit 61) | SuperGPQA (audit 64) |
| --- | --- | --- |
| questions | 12,032 | 26,529 |
| pick-longest | 18.38% | 13.01% |
| chance | 11.09% | 10.59% |
| ratio to chance | 1.66x | 1.23x |
| mean gold vs distractor length (chars) | 43.24 vs 36.10 | 34.90 vs 34.23 |

The residual cue sits in prose disciplines (management 19.1%, economics 17.2%, philosophy 17.6%), far below MMLU-Pro's
~67% pocket. SuperGPQA's data are also clean on two other checks: 0 letter/text mismatches, 0 duplicated options, and
uniform gold positions on its 23,158 ten-option questions. A stated length rule, enforced, largely works.

## 3. Models (audits 65 and 66)

[Audit 65](../mcq-mmlu-pro-model-length-pull/) joined 17 of TIGER-AI-Lab's published MMLU-Pro prediction archives to the
test set by `question_id` (15 joined cleanly). [Audit 66](../mcq-mmlu-pro-model-length-strata/) widened this to all 48
archives (45 joined cleanly) and stratified by source, so that subject mix cannot produce the result.

- **Wrong answers lean long.** In all 15 audit-65 models, wrong answers land on a longest distractor more often than a
  random wrong choice would (pooled error pull 1.055 to 1.140), most on the 656 STEM-website biology and psychology
  questions (1.23 to 2.31, against 1.01 to 1.43 on MMLU-derived biology and psychology).
- **Within source, the gold-longest gap survives at about half its crude size.** Every one of 45 models is more
  accurate on STEM-website questions when the gold is the unique longest, by +5.2 points (Gemini 3.1 Pro) to +28.9,
  against -1.3 to +7.1 on MMLU-derived questions; the STEM-website gap is the larger in 45 of 45.
- **The lean is small but universal.** Wrong picks sit at a mean normalised length rank of 0.507 to 0.536 (median
  0.522; 0.5 means no lean), all 45 above 0.5, in line with the 0.515 to 0.536 Turkish MMLU-Pro reports on the same
  scale.
- **Some models score below the heuristic.** On the 656 questions, 10 of 45 models (all 6B to 13B) score below the
  66.85% that picking the longest option earns without reading the question. Gemini 3.1 Pro (91.1%), the model with the
  smallest gap, still has a pooled error pull of 1.099, and accuracy barely predicts the pull (Spearman -0.149).

These results are observational: a pull toward long options can reflect plausibility (long options often carry the
qualifications a correct answer needs), not length itself.

## 4. Translation (audit 67)

[Audit 67](../mcq-mmlu-prox-length-census/) joined all 29 MMLU-ProX test configurations (`li-lab/MMLU-ProX`, options in
the same order) back to English MMLU-Pro by `question_id_src`; 11,736 of 11,759 rows join in every language (99.80%).

- On the same questions, English pick-longest is 18.39% against 11.02% chance, and the 28 translations score 17.96%
  (Czech) to 18.89% (Vietnamese).
- Retention (a translation's lift over chance divided by English's) is 0.941 to 1.068, median 0.988. Chinese, Japanese
  and Korean retain 0.988, 1.000 and 1.033.
- The STEM-website biology and psychology pocket stays at 62.28% to 65.58% in every language (English 66.95%).
- **The longest option itself often changes:** English's unique longest option stays the unique longest in only 57.3%
  to 77.4% of questions (median 68.0%). The cue survives because a long answer stays relatively long, not because the
  same option always wins.
- 9.7% to 38.6% of option sets are left untranslated (numbers, formulas), depending on the language.

## 5. What to do with this

1. **Report the floor next to the score.** A closed-book MMLU-Pro or MMLU-ProX score should be read against an ~18%
   length-only floor, not ~11%, and against ~67% on the STEM-website biology and psychology questions.
2. **Split by `src`.** MMLU-derived questions sit near a 13% floor; STEM-website questions near 29%. Results that mix
   them mix two different tests.
3. **Small models: check the 656.** A model below 66.85% on those questions is doing worse than picking the longest
   option.
4. **Builders: write a length rule and enforce it.** SuperGPQA's rule cut the cue to 1.23x of chance.
5. **Run it on your own data.** [mcq-length-floor](https://github.com/munimtechnologies/mcq-length-floor) (Apache-2.0,
   standard library only) computes the tie-aware floor per slice for any JSONL, CSV or HuggingFace dataset; version
   0.1.0 reproduces audit 61's pooled MMLU-Pro figures and audit 63's STEM-website biology and psychology figures
   exactly.

## Limits

- These are construction properties of the released data and, for models, of TIGER-AI-Lab's released 5-shot
  chain-of-thought predictions; other prompts or decoding may differ.
- Lengths are characters. Token counts move some figures (audit 63: SciBench's character edge vanishes in tokens).
- Translation retention is measured on MMLU-ProX's released translations only, with options in the same order.
- One checker per audit; each audit README lists its own pre-registered predictions, including the ones that failed.

## Code and data

Each audit folder holds the code, tests and a frozen `results.json`:
[64](../mcq-supergpqa-length-census/), [65](../mcq-mmlu-pro-model-length-pull/),
[66](../mcq-mmlu-pro-model-length-strata/), [67](../mcq-mmlu-prox-length-census/). The full catalogue is
[eval-reliability-audits](../eval-reliability-audits/). Upstream licences: MMLU-Pro MIT, TIGER-AI-Lab/MMLU-Pro repository
Apache-2.0, MMLU-ProX MIT, SuperGPQA ODC-BY.

To cite: MV2 (Munim, Inc.), "MMLU-Pro's length floor reaches its models and its translations, and a successor mostly
avoids it", eval-reliability-audits note, 30 October 2026,
https://github.com/munimtechnologies/munimtechnologies.github.io/blob/main/notes/mmlu-pro-length-floor-descendants.md
