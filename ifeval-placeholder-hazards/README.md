# IFEval PlaceholderChecker hazards

A small, dependency-free, execution-verified corpus showing that the reference IFEval
checker for the instruction *"the response must contain at least N placeholders represented
by square brackets, such as [address]"* counts **every** square-bracket span as a
placeholder. Markdown links, numeric citations, footnotes and task-list checkboxes all
satisfy the instruction with **zero** genuine fill-in placeholders, and a real placeholder
that wraps a line break is missed entirely.

Research by MV2 of Munim, Inc. (mv2@munimtech.com). The research and this write-up were made
with AI agents working in his name; no human wrote them. Code is Apache-2.0; the labelled
corpus (`cases.json`), this README and `prereg.md` are CC BY 4.0. The transcribed upstream
predicate keeps its own Apache-2.0 licence (attributed below).

## What is audited

Google's original IFEval checker
(`google-research/google-research/instruction_following_eval/instructions.py`, Apache-2.0),
the reference implementation behind the widely reported IFEval benchmark.
`PlaceholderChecker.check_following` (confirmed live against `master`, 2026-10-20):

```python
placeholders = re.findall(r"\[.*?\]", value)
num_placeholders = len(placeholders)
return num_placeholders >= self._num_placeholders
```

The instruction it drives (`detectable_content:number_placeholders`, kwarg `num_placeholders`)
asks for **fill-in placeholders** — template slots a user would replace, like `[address]` or
`[name]`. The single lazy regex `\[.*?\]` instead matches every bracketed span, and lacks
`re.DOTALL`, so it is at once too broad and too narrow.

## The two hazards

- **Silent false PASS (dominant).** A response whose bracketed spans are all markdown links
  `[text](url)`, reference links `[text][ref]`, reference/footnote definitions `[id]:`,
  footnote refs `[^1]`, task-list checkboxes `[ ]`/`[x]` or numeric citations `[12]` — and
  which contains no genuine placeholder — is scored PASS. The checker over-counts and
  inflates instruction-following credit for link- and citation-rich answers.
- **Silent false FAIL (secondary).** Because the pattern has no `re.DOTALL`, a genuine
  placeholder that wraps a line break (e.g. `[Full\nName]`) is not matched, so a response
  that does satisfy the instruction is scored FAIL.

## Corpus

Six hand-constructed cases in `cases.json`, each with its response text, the required
`num_placeholders`, and the upstream and intended outcomes reasoned by hand **before** the
machine run (see `prereg.md`). Five are false PASS (inline links, numeric citations, task-list
checkboxes, footnotes, a realistic mixed answer); one is false FAIL (a multi-line placeholder).

| Case | Required | Upstream count | Intended count | Upstream | Intended |
|---|---|---|---|---|---|
| P1 inline links | 2 | 2 | 0 | PASS | FAIL |
| P2 numeric citations | 3 | 3 | 0 | PASS | FAIL |
| P3 task-list checkboxes | 2 | 3 | 0 | PASS | FAIL |
| P4 footnotes | 2 | 2 | 0 | PASS | FAIL |
| P5 mixed link+citation answer | 3 | 3 | 0 | PASS | FAIL |
| P7 multi-line placeholder | 2 | 0 | 2 | FAIL | PASS |

`ifeval_placeholder.py` transcribes the upstream predicate verbatim in behaviour alongside a
conservative **intended** counter that excludes only the provably-non-placeholder constructs
above and adds `re.DOTALL`. The intended counter is deliberately conservative: it never
removes a genuine placeholder, so it cannot under-count real ones.

Reproduce (standard library only):

```
python -m unittest -v
```

All six cases reproduced exactly on the sealed runner (`python:3.12`, 2026-10-20): 5 false
PASS, 1 false FAIL, `all_reproduced: true`.

## Exposure on the official IFEval prompt set

`job.py` reads the official prompts
(`.../instruction_following_eval/data/input_data.jsonl`) and counts items that depend on this
checker. Measured 2026-10-20 (`results.json`):

| Quantity | Value |
|---|---|
| Prompts in the official set | 541 |
| Prompts using `number_placeholders` | 27 |
| Checker instances | 27 |

The requested `num_placeholders` ranges from 1 to 20 (most common: 1 and 3, seven prompts each).
These 27 prompts are the attack surface — the benchmark items whose score depends on this
checker.

## Honesty and limits

- This is a **correctness audit of checker code**. Exposure (how many official items use the
  checker) is reported separately and is **not** a claim that any leaderboard changed.
- The official dataset ships prompts only, not model responses. The mis-scoring fires whenever
  a model answers one of these 27 prompts with bracketed markdown instead of, or in addition
  to, genuine placeholders — common in capable models that answer in markdown. Measuring that
  rate needs a response corpus (future work).
- The intended counter is the minimal fix, not a perfect placeholder detector.
- All reasoning and hand-traced outcomes were produced by AI agents, not humans; the machine
  run independently reproduces every outcome.

## Prior art (why this is new)

Searched 2026-10-20. No issue or PR in `google-research/google-research`,
`EleutherAI/lm-evaluation-harness`, `UKGovernmentBEIS/inspect_evals` or
`allenai/open-instruct` reports the PlaceholderChecker counting markdown
links/citations/footnotes/checkboxes as placeholders, nor the missing `re.DOTALL`. The
adjacent known bug is different — `allenai/open-instruct` #1718/#1966 and `NVIDIA-NeMo/Gym`
PR #4624 fix the *paragraph-counting* checker that splits on the `* * *` divider, not the
placeholder count — and is not claimed here.

## Files

- `prereg.md` — predictions fixed before the run.
- `ifeval_placeholder.py` — verbatim upstream predicate + conservative intended counter.
- `cases.json` — the six hand-labelled cases (CC BY 4.0).
- `test_ifeval_placeholder_hazards.py` — standard-library tests asserting each pre-registered outcome.
- `job.py` — corpus verification + official-set exposure measurement.
- `results.json` — output of the sealed run (corpus reproduction + exposure counts).
