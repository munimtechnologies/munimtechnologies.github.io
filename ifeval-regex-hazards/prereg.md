# Pre-registration — ifeval-regex-hazards

Fixed before the sealed compute run. No numbers were read from data before
writing these predictions.

## Checkers under audit
Google's IFEval (`instruction_following_eval/instructions.py`), two checkers
that pass a user-supplied string into `re` with no `re.escape`:

- `keywords:frequency` — `len(re.findall(self._keyword, value, re.IGNORECASE))`
- `keywords:forbidden_words` — `re.search(r"\b" + word + r"\b", value, re.IGNORECASE)`

## Predictions

**P1 (corpus).** All nine hand-built cases reproduce their expected
`(upstream, intended)` verdict pair, giving `n_crash = 2`, `n_false_pass = 2`,
`n_false_fail = 5`, `all_reproduced = true`.

**P2 (exposure — keyword:frequency).** The 541-prompt official IFEval set
(`input_data.jsonl`) contains keyword:frequency instructions, and the count of
those whose keyword contains a regex metacharacter is **0**, and the count
whose keyword fails to compile is **0**. (Prediction: the hazard is reachable
in principle but is NOT triggered by any official prompt.)

**P3 (exposure — forbidden_words).** Likewise, the number of official
forbidden-word entries containing a regex metacharacter is **0**, and the
number that fail to compile is **0**.

## Interpretation set in advance
If P2/P3 hold, the honest finding is a **reachable-but-unexercised** hazard:
the shipped checkers mis-handle metacharacter keywords (proven by the nine
reproduced cases), but the public benchmark's own prompts never use such
keywords, so official IFEval scores are unaffected by this mechanism. That is
a deliberately modest, partly negative result — it bounds the blast radius
rather than claiming the benchmark is broken.
