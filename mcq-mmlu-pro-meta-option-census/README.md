# mcq-mmlu-pro-meta-option-census

Audit 59 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code, the pre-registered
predictions and the frozen `results.json` are open and reproducible in a sealed container with only the Python
standard library plus a parquet reader.*

## What this targets

Audit 56 ([mcq-mmlu-meta-option-census](../mcq-mmlu-meta-option-census/)) showed that MMLU's "the answer is D"
gold-position tilt is **mostly** an artifact of *meta options* — "All of the above", "None of the above", "Both A
and B", Roman-numeral statement sets — which are written last by convention and are the gold far above chance
("all of the above" is correct **59.6%** of the time vs 25%). Audit 57 then showed the mechanism is absent from
ARC, CommonsenseQA and HellaSwag, so it is MMLU-specific among those benchmarks.

This audit asks a different question about the *same* content: **does MMLU-Pro's deliberate 10-option expansion
remove the artifact?** [MMLU-Pro](https://huggingface.co/datasets/TIGER-Lab/MMLU-Pro) rebuilds MMLU with up to ten
options per question, adding harder distractors and reshuffling, and a large share of its questions are inherited
from the original 4-option MMLU (`src` starting `ori_mmlu`). If the leak was a property of MMLU's *authoring*, the
expansion should erase it. So we port audit 56's meta-option classifier (`meta_option.py`, applied verbatim) and
audit 53's gold-position census (`position_census.py`) to MMLU-Pro and measure, over the 12,032 test questions:
the meta-option rate, where meta options sit and how often they are the gold, the gold-position distribution at the
modal 10-option count (pooled, per category, and by provenance `ori_mmlu` vs `other`), and a k-independent
first/last gold rate.

This is a **construction** property — where the correct answer was placed and how long the option list is — not
any model's position or selection behaviour.

## Pre-registered predictions (frozen before any real number)

| # | Prediction | Verdict |
| --- | --- | --- |
| P1 | Clean parse; modal option count 10; variable option counts present | **HELD** |
| P2 | "All/none of the above"-type meta options are rare in MMLU-Pro (< 2% of valid questions) | **HELD** |
| P3 | Among the 10-option questions, the gold position rejects uniform at α=0.001 (df 9) | **FAILED** |
| P4 | The last option (index 9) is **not** the modal gold position | **HELD** |
| P5 | Questions inherited from 4-option MMLU (`src` `ori_mmlu*`) were expanded to a modal 10 options | **HELD** |

Each is a finding either way; the verdicts were decided before any real value was seen. P3 is reported as a
failed prediction because the failure — a gold position **consistent with uniform** — is the headline result.

## What it found

**MMLU-Pro's 10-way expansion erases both halves of MMLU's "the answer is D" artifact.**

- **Meta options are rare and no longer a cue.** 172 of 12,032 questions (**1.43%**) carry a meta option (80
  all-of-the-above, 52 none-of-the-above, 33 Roman-numeral, 7 letter-reference). The reversal: "all of the above"
  is the gold only **6.25%** of the time (n=80; below the 10% chance rate, and far below MMLU's 59.6%) — after
  expansion AOTA is an *anti*-cue, not a shortcut. None-of-the-above is gold 19.2% (chance 13.1%).
- **Gold position is consistent with uniform.** Among the 9,981 ten-option questions (82.95% of the set) the gold
  position gives χ² = **9.35** (df 9) against a uniform distribution, below the α=0.001 critical value of 27.877 —
  it does **not** reject (P3 FAILED). The plain (non-meta) remainder is likewise uniform (χ² = 9.08, df 9).
- **If anything, a mild *first* lean, not last.** The modal gold position is the **first** option (index 0,
  10.50%), while the last option (index 9) is the *least* common gold at 9.47% (P4 HELD). The k-independent
  gold-last rate is **10.49%** and gold-first **11.66%**, against a uniform last-or-first expectation of 11.09%.
- **The inheritance is real.** 6,810 questions come from the original 4-option MMLU (`src` `ori_mmlu*`) and were
  expanded to a modal 10 options (P5 HELD); their gold position is also uniform (χ² = 11.46, df 9), as is the
  `other` provenance (χ² = 6.33).

So the exact leakage audits 53 and 56 measured on MMLU — a last-position gold tilt driven by unshufflable
all-of-the-above options — is **gone** on MMLU-Pro. A question-free position-only guesser, or one that always picks
the all-of-the-above option, earns essentially nothing on MMLU-Pro. The harder distractors and reshuffle did their
job on this construction axis.

## Reproduce

```
python -m unittest -v        # hand-traced synthetic fixtures (meta classifier + position census)
python job.py --out-dir out  # downloads MMLU-Pro parquet, writes out/results.json
```

`job.py` reads the MMLU-Pro `default` test split from the HuggingFace auto-converted parquet via the
datasets-server parquet API. The unit tests pin a synthetic corpus with hand-computed meta categories and gold
positions, so a transcription error fails the run before any real data is touched. All statistics are standard
library (Pearson chi-square, exact critical values); no SciPy, no network at test time.

### Note on the classifier

`meta_option.py` is applied **verbatim** from audit 56 to keep the instrument identical across benchmarks. Its
`letterref` predicate recognises references to option letters A–D only, so on MMLU-Pro's A–J lists it is a
conservative lower bound (documented, not silently widened). This does not affect the headline: the position
census is classifier-independent.

## Files

- `job.py` — loader, census driver, writes `results.json`
- `meta_option.py` — meta-option classifier (verbatim from audit 56)
- `position_census.py` — gold-position / chi-square census (from audit 53)
- `cases.py` — hand-traced synthetic fixtures
- `test_meta_option.py`, `test_position_census.py` — unit tests over the fixtures
- `results.json` — frozen output
- `requirements.txt` — a parquet reader only

## Licence

Code is Apache-2.0. This write-up and `results.json` are CC BY 4.0. Upstream: MMLU-Pro
(TIGER-Lab/MMLU-Pro) is MIT-licensed. Authored by AI agents working in MV2's name (Munim, Inc.).
