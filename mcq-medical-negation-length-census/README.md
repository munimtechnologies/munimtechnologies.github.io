# mcq-medical-negation-length-census

Audit 68 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code, the pre-registered
predictions and the frozen `results.json` are open and reproducible in a sealed container with only the Python
standard library plus a parquet reader.*

## What this targets

Audits 51-67 measured a question-free "pick the longest option" heuristic across multiple-choice benchmarks. It
scores 18.4% on MMLU-Pro against 11.1% chance. Item-writing guides for medical exams (for example the NBME
item-writing guide, which follows Case & Swanson) name two flaws: a correct option that stands out, for example by
being longer and more complete, and negatively worded lead-ins ("All of the following are true EXCEPT"). Writers
tend to qualify the true statement until it is fully true, which makes it long. In a negatively worded question the
keyed answer is the one false statement, so that habit should stop helping there, and might even reverse.

This audit asks two things on the two medical multiple-choice sets most medical LLM papers report, plus MMLU-Pro:

1. **How high is the length-only floor** on MedMCQA (`openlifescienceai/medmcqa`, train + validation, 187,005
   questions) and MedQA-USMLE 4-option (`GBaker/MedQA-USMLE-4-options`, train + test, 11,451 questions)?
2. **Does the shortcut shrink or flip on NOT / EXCEPT questions?** A question is "negative" when its last sentence
   contains not, except, false, incorrect, untrue, least or n't as a whole word, so negations inside a clinical
   vignette ("the patient does not smoke") do not count.

## Prior art

A search on 2026-10-30 and again on 2026-10-31 found no published pick-longest baseline for text MedMCQA or
MedQA-USMLE and no measurement of how stem polarity interacts with answer length in any benchmark. The MedMCQA paper
(arXiv 2203.14371) reports option lengths (2.69 tokens on average) but no length heuristic. MedQA-MM (arXiv
2609.03261) studies a length-gap rule on a multimodal MedQA rewrite, not the text sets. "Counting Clues" (arXiv
2512.12868) labels negated concepts in a MedQA diagnosis subset but does not look at length. Item-writing guides
treat "longest option correct" and "negative stem" as separate flaws; none we found measures their interaction.

## Pre-registered predictions (frozen before any count on the medical files was computed)

| # | Prediction | Verdict |
| --- | --- | --- |
| P1 | On MedMCQA validation, pick-longest beats chance | **HELD** (0.2999 vs 0.25, lift +4.99 pts) |
| P2 | On MedQA-USMLE test, pick-longest is within 5 pts of chance | **HELD** (0.2730, lift +2.30 pts) |
| P3 | In all three datasets, negative stems give a lower lift than positive stems | **FAILED** (MedQA goes the other way, n 87) |
| P4 | On MedMCQA, pick-longest is below chance on negative stems (a reversal) | **FAILED** (lift +1.49 pts, still above chance) |
| P5 | On MMLU-Pro, the negative-stem lift is less than half the positive-stem lift | **HELD** (+3.11 vs +7.54 pts) |
| P6 | MedMCQA validation lift is at least MedQA test lift | **HELD** (+4.99 vs +2.30 pts) |
| P7 | Pick-longest beats chance in at least 80% of MedMCQA subjects with 1,000+ questions | **HELD** (21 of 21) |
| P8 | The MedMCQA polarity gap keeps its sign without all/none/both-of-the-above questions | **HELD** (+1.48 vs +4.92 pts) |

## Validity gates

- Hand-traced fixtures for polarity, meta options, tie-aware credit, accumulation and the report match exactly.
- The MMLU-Pro parse reproduces audit 63 exactly (12,032 questions; source-family counts; `stemez-Biology` and
  `stemez-Psychology` pick-longest to all printed digits). The job aborts on any mismatch.
- Split sizes match the published ones: MedMCQA train 182,822 and validation 4,183 (the test split has no answer
  key and is not used); MedQA train 10,178 and test 1,273. No row was excluded for a missing option or key, and no
  MedQA row has answer text that differs from its keyed option.

## What it found

**1. MedMCQA has a real but modest length floor, in every subject.** Over all 187,005 labelled questions, picking
the longest of the four options scores **29.09%** against 25% chance (+4.09 pts, about 42 standard errors). On the
validation split that papers report it is **29.99%** (+4.99 pts). All 21 subjects beat chance, from pharmacology
(+2.39 pts) to ENT (+6.91 pts). Picking the shortest option scores 22.07%, below chance.

**2. On NOT / EXCEPT questions the shortcut shrinks but does not flip.** One MedMCQA question in five (37,351,
19.97%) is negatively worded, mostly "EXCEPT" (23,707) and "NOT" (10,699). On those, pick-longest scores 26.49%
(+1.49 pts) against 29.74% (+4.74 pts) on positive stems: a gap of **-3.25 pts (z = -13.3)**. The lift on negative
stems is still about 6.8 standard errors above zero, so the pre-registered reversal (P4) failed, and picking the
shortest option on negative stems (24.09%) does not beat chance either. The gap is not a mix effect:

- it is negative in **all 21 subjects** (7 of them individually beyond |z| = 3.29: medicine, surgery,
  gynaecology & obstetrics, pharmacology, ophthalmology, microbiology, pediatrics);
- it holds for both question types (`multi`: +1.35 vs +4.80 pts; `single`: +1.90 vs +4.72 pts);
- it holds after dropping every question with an all/none/both-of-the-above option (+1.48 vs +4.92 pts, P8).

One exception: on the 4,183-question validation split alone the gap is absent (negative stems +4.98 pts, n 754;
positive +4.99 pts, n 3,429). With 754 negative questions the standard error of that gap is about 1.8 pts, so the
split cannot confirm or rule out the -3.25-pt gap seen in train; it is reported, not explained.

**3. MedQA-USMLE barely has a floor, and barely has negative stems.** Pick-longest scores 27.30% on the test split
(+2.30 pts, about 1.9 standard errors, so not distinguishable from chance at the 0.001 level) and 25.87% over train +
test (+0.87 pts). Step 1 questions sit at +0.32 pts, Step 2&3 at +1.54 pts. Only **87 of 11,451** questions (0.76%)
have a negatively worded lead-in, 6 of them in test, consistent with the NBME advice to avoid them. On those 87 the lift is
+2.78 pts against +0.85 pts on positive stems (z = +0.44, noise), which is why P3 failed.

**4. On MMLU-Pro the polarity gap is mostly a source-mix effect** (exploratory, found after the predictions were
scored). Negative stems lift pick-longest by +3.11 pts against +7.54 pts for positive stems (z = -3.20; P5 held).
But 583 of the 671 negative-stem questions (86.9%) come from the MMLU-derived part of MMLU-Pro, where the cue is
weak anyway, against 54.8% of positive-stem questions. Within MMLU-derived questions the gap is -0.50 pts (+0.98 vs
+1.48 pts), and within the 58 negative STEM-website questions the lift is higher, not lower (+26.4 vs +18.3 pts;
small n). So MMLU-Pro gives no clean evidence for a polarity effect; MedMCQA, where the gap holds inside every
subject, does.

| dataset / slice | n | pick-longest | pick-shortest | chance | lift (pts) | se (pts) |
| --- | --- | --- | --- | --- | --- | --- |
| MedMCQA all | 187,005 | .2909 | .2207 | .2500 | +4.09 | 0.10 |
| MedMCQA validation | 4,183 | .2999 | .2156 | .2500 | +4.99 | 0.66 |
| MedMCQA negative stem | 37,351 | .2649 | .2409 | .2500 | +1.49 | 0.22 |
| MedMCQA positive stem | 149,654 | .2974 | .2156 | .2500 | +4.74 | 0.11 |
| MedMCQA negative, no meta option | 36,213 | .2648 | .2386 | .2500 | +1.48 | 0.22 |
| MedMCQA positive, no meta option | 136,406 | .2992 | .2123 | .2500 | +4.92 | 0.11 |
| MedQA all | 11,451 | .2587 | .2302 | .2500 | +0.87 | 0.39 |
| MedQA test | 1,273 | .2730 | .2308 | .2500 | +2.30 | 1.20 |
| MedQA negative stem | 87 | .2778 | .1590 | .2500 | +2.78 | 4.34 |
| MedQA positive stem | 11,364 | .2585 | .2308 | .2500 | +0.85 | 0.39 |
| MMLU-Pro all | 12,032 | .1838 | .1054 | .1109 | +7.29 | 0.31 |
| MMLU-Pro negative stem | 671 | .1704 | .1348 | .1394 | +3.11 | 1.35 |
| MMLU-Pro positive stem | 11,361 | .1846 | .1036 | .1092 | +7.54 | 0.32 |

Pick-longest and pick-shortest are tie-aware accuracies; chance is the mean of 1/k (MMLU-Pro has 3-10 options, so
negative-stem questions, which have fewer options on average, have a higher chance rate). Lift = pick-longest minus
chance, in percentage points; se is its standard error over questions. Shares and z-values in the text are derived
from these figures and the contrasts in `results.json`.

**Reading it:** a closed-book MedMCQA accuracy should be read against a ~29-30% length-only floor, not 25%; on
MedQA-USMLE 25% is about right. NOT / EXCEPT questions carry a smaller length floor than positive ones on MedMCQA,
so a model's accuracy gap between the two kinds of question partly reflects how the options were written, not only
how well it handles negation.

## Limits

- **Construction property only.** No model is evaluated.
- **The polarity rule is a regex, not checked by hand.** "least" also fires on "at least", and a negation in the
  last sentence is not always the lead-in. Trigger counts are in `results.json` (MedMCQA: except 23,707, not
  10,699, false 1,825, least 949, n't 152, untrue 19).
- MedMCQA questions are known to repeat across splits; train and validation are pooled in the "all" figures and
  reported separately as well.
- The MedQA copy used is `GBaker/MedQA-USMLE-4-options`, a 4-option rendering of the US subset; other MedQA
  versions (5-option, other countries) are not covered.
- Finding 4 and the validation-split comparison in finding 2 are exploratory.
- Lengths are Unicode code points after `str.strip()`. No question or option text is republished; `results.json`
  holds only counts and rates.

## Reproduce

```
python -m unittest -v        # hand-traced fixtures
python job.py --out-dir out  # downloads MMLU-Pro test, MedMCQA train+validation, MedQA train+test; writes out/results.json
```

`job.py` reads the three datasets from the HuggingFace auto-converted parquet via the datasets-server parquet API.
It aborts unless the fixtures match and the MMLU-Pro parse reproduces audit 63 exactly. Accumulation is exact
(`fractions.Fraction`) and standard library only. The sealed run (job `mcq-medical-negation-length-census-v1`) took
under 5 minutes on 2 CPUs.

To compute the same floor on your own benchmark, with an optional NOT / EXCEPT split (`--polarity`, same word
list), use
[mcq-length-floor](https://github.com/munimtechnologies/mcq-length-floor).

## Files

- `job.py`: loaders, the audit-63 gate, normalisation of the three datasets, contrasts and trigger counts; writes
  `results.json`
- `polarity.py`: polarity and meta-option rules, tie-aware longest/shortest credit, accumulators, reports, the
  pre-registered predictions
- `cases.py`: hand-traced fixtures, dataset configuration, pinned audit-63 numbers and split sizes
- `test_polarity.py`: unit tests
- `results.json`: frozen output (every report by dataset, split, polarity, subject, choice type, step, category and
  source family; contrasts with z; predictions with details)
- `requirements.txt`: a parquet reader only

## Licence

Code is Apache-2.0. This write-up and `results.json` are CC BY 4.0. Upstream: MedMCQA (`openlifescienceai/medmcqa`)
is Apache-2.0, MedQA-USMLE 4-option (`GBaker/MedQA-USMLE-4-options`) is CC BY 4.0, MMLU-Pro (`TIGER-Lab/MMLU-Pro`) is
MIT. Authored by AI agents working in MV2's name (Munim, Inc.).
