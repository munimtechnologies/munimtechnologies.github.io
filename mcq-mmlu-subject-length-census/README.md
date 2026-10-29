# mcq-mmlu-subject-length-census

Audit 60 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code, the pre-registered
predictions and the frozen `results.json` are open and reproducible in a sealed container with only the Python
standard library plus a parquet reader.*

## What this targets

Audit 52 ([mcq-answer-length-generalization-census](../mcq-answer-length-generalization-census/)) found, as an
unpredicted result, that the exam benchmark **MMLU** carries the *strongest* answer-length shortcut of the three it
tested: a tie-aware "pick the longest option" heuristic scores **0.2805** against the 0.25 random baseline — a
+3.0-point question-free lift from the gold option averaging **+1.68 characters** longer than its distractors.

This audit asks whether that pooled edge is a **pervasive authoring property of MMLU** or **concentrated in
particular subjects**. For each of MMLU's 57 subjects (`cais/mmlu` config `all`, test+validation+dev = 15,858
gold-bearing questions) it measures: how often the gold is the unique longest / unique shortest option, the
accuracy of a tie-aware pick-longest heuristic versus that subject's chance baseline, and the mean gold vs mean
distractor length (characters after `str.strip()`, with a whitespace-token view alongside). It then reproduces
audit 52's pooled MMLU numbers **exactly** as a hard validity gate.

This measures **agreement with a length heuristic** — a construction property of how long each subject's correct
answers were written — not the correctness of any model.

## Pre-registered predictions (frozen before any real number)

| # | Prediction | Verdict |
| --- | --- | --- |
| P1 | Clean, well-defined, complete partition (0 bad_key/degenerate, all modal-4, per-subject counts sum to 15,858) | **HELD** |
| P2 | The pick-longest shortcut is pervasive: it beats chance in a strict majority of subjects | **HELD** (42/57) |
| P3 | The mean gold option is longer than the mean distractor in a strict majority of subjects | **HELD** (46/57) |
| P4 | The pooled +3-pt lift is **diffuse**: fewer than a quarter of subjects individually show a pick-longest lift ≥ +5 pts | **FAILED** (23/57) |

Each is a finding either way. P4 is reported as failed because its failure — the lift is **concentrated**, not
diffuse — is the headline.

## Validity gate (must match audit 52 to the digit)

The pooled recomputation reproduces audit 52's MMLU-all numbers exactly, so the per-subject cut is comparable:

| quantity | this audit | audit 52 | match |
| --- | --- | --- | --- |
| valid questions | 15,858 | 15,858 | ✓ |
| gold unique-longest (char) | 3,727 | 3,727 | ✓ |
| pick-longest accuracy (char) | 0.280500 | 0.280500 | ✓ |
| mean gold length (char) | 43.1469 | 43.1469 | ✓ |
| mean distractor length (char) | 41.4718 | 41.4718 | ✓ |

## What it found

**The length shortcut is real and directionally near-universal, but strongly concentrated by subject.**

- **Direction is near-universal (P2, P3 HELD).** The tie-aware pick-longest heuristic beats the subject's chance
  baseline in **42 of 57** subjects, and the mean gold option is longer than the mean distractor in **46 of 57**.
- **Magnitude is concentrated, not diffuse (P4 FAILED — the finding).** **23 of 57** subjects (40%) individually
  carry a pick-longest lift of at least +5 points — far above the predicted "under a quarter". The pooled +3-point
  lift lives in a large law / clinical / social-science cluster rather than smearing evenly.
- **It peaks on international law.** The gold is the unique longest option **51.1%** of the time and pick-longest
  scores **52.7%** — a **+27.7-point** lift, with the gold averaging **+29.8 characters** (109.0 vs 79.2) longer
  than its distractors. Reading the longest option without reading the question answers over half of MMLU
  international law.
- **A clear high-lift cluster follows:** jurisprudence (40.7%, +15.7), nutrition (37.8%, +12.8), us_foreign_policy
  (37.1%, +12.1), medical_genetics (36.5%, +11.5), clinical_knowledge (34.5%, +9.5), sociology (34.1%, +9.1),
  logical_fallacies, high_school_european_history, high_school_microeconomics, high_school_statistics.
- **And it reverses in a handful.** In **public_relations** the gold is the unique longest only 17.7% of the time
  and "pick the *shortest*" option wins (32.3%); econometrics (17.8%), anatomy (18.9%), conceptual_physics and
  human_aging all sit below chance for pick-longest. One subject (security_studies) picks longest well despite the
  gold being *shorter* on average — its options vary enough that a unique-longest cue still exists.

So a closed-book MMLU accuracy should be read against a length-only floor that is ~28% *pooled* but near **50% in
international law** and *below chance* in public relations. Whether a length shortcut exists is a property of how
each subject's options were authored, not of the subject's difficulty.

## Reproduce

```
python -m unittest -v        # hand-traced synthetic fixtures for the length census
python job.py --out-dir out  # downloads MMLU-all parquet, writes out/results.json
```

`job.py` reads the `cais/mmlu` `all` config (test + validation + dev; `auxiliary_train` is excluded as a mix of
other datasets) from the HuggingFace auto-converted parquet via the datasets-server parquet API. The pooled
reproduction gate inside the job fails the run if any of audit 52's five pinned MMLU numbers drift, so a
transcription or loader change cannot silently move the per-subject cut. All statistics are standard library.

## Files

- `job.py` — loader, per-subject length census, pooled reproduction gate, writes `results.json`
- `gold_length.py` — length / unique-longest / pick-longest logic
- `cases.py` — hand-traced synthetic fixtures
- `test_mmlu_subject_length.py` — unit tests over the fixtures
- `results.json` — frozen output (pooled, per-subject, cross-subject summary, predictions)
- `requirements.txt` — a parquet reader only

## Licence

Code is Apache-2.0. This write-up and `results.json` are CC BY 4.0. Upstream: MMLU (`cais/mmlu`) is MIT-licensed.
Authored by AI agents working in MV2's name (Munim, Inc.).
