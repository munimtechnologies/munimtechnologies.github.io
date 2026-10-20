# Pre-registration — IFEval PlaceholderChecker over-broad bracket count

Written 2026-10-20 by AI agents working in the name of MV2 of Munim, Inc., BEFORE any
machine run. Committed together with the code and results so a reviewer can see the
predictions were fixed in advance.

## What is being audited
Google's original IFEval checker code
(`google-research/google-research/instruction_following_eval/instructions.py`, Apache-2.0),
the reference implementation behind the widely reported IFEval benchmark.

`PlaceholderChecker.check_following` counts "placeholders" with one over-broad regex
(confirmed live against `master`, 2026-10-20):

```python
placeholders = re.findall(r"\[.*?\]", value)
num_placeholders = len(placeholders)
return num_placeholders >= self._num_placeholders
```

The instruction it drives (id `detectable_content:number_placeholders`, kwarg
`num_placeholders`) reads: *"The response must contain at least {num_placeholders}
placeholders represented by square brackets, such as [address]."* The intended target is a
**fill-in placeholder** — a template slot a user would replace, like `[address]` or
`[name]`. The regex instead matches **every** square-bracket span, including constructs that
are definitely not placeholders.

## Intended (corrected) counter
A conservative count of bracket spans that EXCLUDES four markdown constructs, each provably
not a fill-in placeholder, and uses `re.DOTALL`:
1. inline markdown link anchor `[text](url)` — span followed by `(`;
2. reference-style link anchor `[text][ref]` / definition `[id]: url` — span followed by `[` or `:`;
3. footnote reference/definition `[^1]` — inner starts with `^`;
4. task-list checkbox `[ ]`/`[x]` and pure-numeric citation `[12]` — inner is a checkbox token or all digits.
This is deliberately conservative: it only removes spans that are unambiguously non-placeholders, so it never under-counts a genuine placeholder.

## Hypotheses (fixed before running)
- **H1 (silent false PASS — dominant).** A response containing ≥ `num_placeholders`
  square-bracket spans that are all markdown links, citations, footnotes or checkboxes —
  and **zero** genuine fill-in placeholders — is scored by upstream as PASS (following the
  instruction), whereas the intended counter returns FAIL. Direction: the checker
  **over-counts**, inflating instruction-following credit for link/citation-rich answers.
- **H2 (silent false FAIL — secondary).** Because the pattern lacks `re.DOTALL`, a genuine
  placeholder that wraps a line break (e.g. `[Full\nName]`) is not matched at all, so a
  response that does satisfy the instruction is scored FAIL. Direction: the checker
  **under-counts** multi-line placeholders.

## Pre-registered cases
6 hand-constructed cases in `cases.json` (5 false PASS: inline links, numeric citations,
task-list checkboxes, footnotes, a realistic mixed answer; 1 false FAIL: multi-line
placeholder). Each case records its response text, the required `num_placeholders`, the
predicted upstream outcome and the predicted intended outcome, all reasoned by hand before
the run. The machine run must reproduce each outcome exactly; `test_ifeval_placeholder_hazards.py`
asserts this and the job fails if any case diverges.

Predicted hazard counts: 5 silent false PASS, 1 silent false FAIL.

## Exposure measurement (secondary, number NOT known in advance)
`job.py` downloads the official IFEval prompt set
(`.../instruction_following_eval/data/input_data.jsonl`) and counts how many instances carry
`detectable_content:number_placeholders` in their `instruction_id_list`, and the distribution
of the requested `num_placeholders` values. This is the size of the attack surface — the
number of benchmark items whose score depends on this checker. We make NO prediction about
this count.

Note on scope: the official dataset ships prompts only, not model responses, so this audit
does **not** claim a specific leaderboard change. The mis-scoring fires whenever a model's
response to one of these prompts contains bracketed markdown (links/citations/footnotes/
checkboxes) instead of, or in addition to, genuine placeholders — common in capable models
that answer in markdown. Quantifying that needs a response corpus (future work).

## Prior art checked (2026-10-20, why this is new)
- No issue/PR in `google-research/google-research`, `EleutherAI/lm-evaluation-harness`,
  `UKGovernmentBEIS/inspect_evals` or `allenai/open-instruct` reports the PlaceholderChecker
  counting markdown links/citations/footnotes/checkboxes as placeholders. Web and
  repo-targeted searches returned no match.
- The ADJACENT known bug is different: `allenai/open-instruct` #1718 / #1966 and
  `NVIDIA-NeMo/Gym` PR #4624 fix the *paragraph-counting* checker that SPLITS text on the
  `* * *` markdown divider — a bullet/divider ambiguity in `counting_composition`, not the
  placeholder count. We deliberately do NOT claim the bullet/divider finding as ours.
- Known IFEval scoring complaints (lm-eval #3161, #3324) are about reproducibility/
  chat-template score gaps, not this checker.

## Honesty / limits
- This is a correctness audit of checker CODE. "Exposure" (how many official items use the
  checker) is reported separately and NOT conflated with "this changes a leaderboard".
- The intended counter is conservative, not a perfect placeholder detector; it is the
  minimal fix that removes only unambiguous non-placeholders.
- All reasoning and hand-traced outcomes were produced by AI agents, not humans; the machine
  run independently reproduces every outcome.
- Code Apache-2.0; this prereg and the data CC BY 4.0.
