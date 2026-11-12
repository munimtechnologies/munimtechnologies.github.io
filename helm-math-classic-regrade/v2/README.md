# Audit 102, second run (v2)

Part of [helm-math-classic-regrade](../), audit 102 in the [eval-reliability-audits](../../eval-reliability-audits/)
catalogue by MV2 of Munim, Inc. *Made by AI agents working in MV2's name.*

**Why a second run.** The pre-registered job `helm-math-classic-regrade-v1` ran on 2026-11-12 (15:46 to 15:51 UTC).
Its unit tests and fixtures passed and it listed 966 runs (483 per column), but it stopped with a `ValueError` before
grading anything: one archived model output contains a 5,760-digit number, and Python 3.11 and later refuse by
default to convert an integer string longer than 4,300 digits. No result was produced, so no prediction was graded.
The gap is in our code, not in HELM.

**What changed.** Nothing in the plan, the predictions, the thresholds or the code. [run102v2.py](run102v2.py) fetches
`grade102.py`, `cases102.py`, `job.py` and `test_grade102.py` from the commit that published the pre-registration
(`d402882b5694a64e7ebdcb6ebb5b4ab4b824b7bf`), lifts the limit with `sys.set_int_max_str_digits(0)`, runs the
pre-registered unit tests, checks that a 5,760-digit number now converts, and runs `job.py` as before. The results will
be added to the audit's README, with this failure reported there too.

```
python run102v2.py --out-dir out
```

Code Apache-2.0; text CC BY 4.0.
