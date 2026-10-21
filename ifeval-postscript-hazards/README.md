# ifeval-postscript-hazards

Part of the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of
Munim, Inc. One small, reproducible corpus that isolates a single mechanism by which an
LLM-benchmark checker can score a response wrongly, reproduced from a pinned upstream copy
and checkable with only the Python standard library.

**Target:** IFEval's `detectable_content:postscript` checker (`PostscriptChecker`, from
`google-research/instruction_following_eval/instructions.py`; Apache-2.0, keeps its own
licence).

**Headline:** 6 hand-traced cases, 4 verdict flips (1 false pass, 3 false fails);
on IFEval's own released data the hazard is **reachable but unexercised — blast radius 26
of 541** (26 postscript instances, all matched to their GPT-4 response, 0 flips).

## The mechanism

`PostscriptChecker.check_following` builds, for the two built-in markers, these patterns and
runs `re.findall(..., flags=re.MULTILINE)`:

- `P.S.` → `\s*p\.\s?s\..*$`
- `P.P.S` → `\s*p\.\s?p\.\s?s.*$`

Two defects fall straight out of that:

1. **No line-start anchor.** `\s*` matches whitespace *anywhere*, not just at the start of a
   line, so an inline mention of a postscript marker in the middle of a sentence is found and
   the response passes even though it contains no actual postscript. (`re.MULTILINE` only
   changes what `^`/`$` mean; it adds no anchor on its own, and this pattern has no `^`.)
2. **A brittle dotted literal.** The pattern hard-codes the dots of `p.` and `s.`, so common,
   legitimate postscript spellings — `PS` (no dots), `P.S` (no trailing dot), `P.S:` (colon)
   — never match and the response fails.

`intended_check` in `postscript_checker.py` is MV2's proposed line-anchored, dot-tolerant
variant (`^\s*p\.?\s?s\.?(?![a-z])`), used only to decide, per case, whether a shipped verdict
is a false pass or a false fail. The `(?![a-z])` guard keeps it from matching a word such as
"Psychology" that merely starts with `ps`.

## What was found

### Synthetic corpus (6 pre-registered cases, marker `P.S.`)

| id | text (abridged) | shipped | intended | kind |
|----|-----------------|---------|----------|------|
| P1-inline-false-pass | "I think **p.s.** stands for postscript…" | pass | fail | false pass |
| P2-PS-no-dots-false-fail | "**PS** I forgot to mention…" | fail | pass | false fail |
| P3-one-dot-false-fail | "**P.S** I will call you…" | fail | pass | false fail |
| P4-colon-false-fail | "**P.S:** remember to bring…" | fail | pass | false fail |
| P5-canonical-control | "**P.S.** Thanks again…" | pass | pass | control |
| P6-psychology-control | "**Psychology** is a fascinating field…" | fail | fail | control |

`n_cases = 6, n_verdict_flip = 4, n_false_pass = 1, n_false_fail = 3, all_reproduced = true`.
Every verdict was hand-traced against the two regexes before any code ran; the sealed compute
job re-derives them and asserts the aggregate matches this pre-registered target.

### Exposure on IFEval's own released data

Among IFEval's 541 prompts there are **26** `detectable_content:postscript` instances (markers
seen: `P.S.` ×10, `P.P.S` ×16). Each was joined by exact prompt text to its released GPT-4
response (`input_response_data_gpt4_20231107_145030.jsonl`); all 26 matched. The shipped and
intended checkers **agree on all 26** — `n_verdict_flip = 0`, `n_false_pass = 0`,
`n_false_fail = 0`.

So this is an honest **reachable-but-unexercised** negative, like `ifeval-regex-hazards` and
`ifeval-quotation-hazards`: the defect is real and demonstrable, but on this English GPT-4 set
no scored response happens to use one of the off-spec spellings. The blast radius — the count
of scored instances that *could* flip if a model used an inline marker or an off-spec
postscript spelling — is bounded at 26 of 541.

## Loose-scoring caveat

IFEval reports both a strict and a "loose" accuracy (arXiv:2311.07911): loose scoring strips a
few common wrappers (leading markdown, a first/last line) from the response and re-runs the
same checkers, to rescue formatting **false negatives**. It does not help here:

- The **false pass** (P1) is a *strict* over-match — the checker says a non-postscript response
  complies. Loose scoring only *relaxes* the response before re-checking; it can never turn an
  over-match into a rejection, so a loose pass is still a pass.
- The **false fails** (P2–P4) come from the hard-coded dots in the pattern, not from a wrapper
  loose scoring removes, so stripping lines leaves `PS` / `P.S` / `P.S:` failing just the same.

## Files

- `postscript_checker.py` — `shipped_check` (IFEval's `PostscriptChecker`, transcribed
  verbatim) and `intended_check` (the proposed fix). Apache-2.0.
- `cases.py` — the 6 pre-registered labelled cases. CC BY 4.0.
- `test_postscript_checker.py` — stdlib `unittest`; each case must reproduce both verdicts and
  the aggregate must match the target.
- `job.py` — the sealed compute job: asserts the corpus, then measures official exposure.
- `results.json` — the sealed run's output (corpus + per-case verdicts + official exposure).

Reproduce: `python -m unittest -v` then `python job.py` (needs IFEval's `input_data.jsonl` and
the GPT-4 response file in `/data` for the exposure step; the corpus assertion needs no data).

## Limits, honestly

One checker, one dataset. The synthetic corpus is hand-labelled and small; its verdicts were
traced by AI agents working in MV2's name, not by an independent human reviewer. The exposure
count is exact for IFEval's released GPT-4 responses and says nothing about other models or
private test sets. `intended_check` is one reasonable fix, not a standard — it is here only to
classify each flip, not proposed as the canonical replacement.

## Licence

Code is Apache-2.0. The labelled corpus (`cases.py`), `results.json` and this write-up are
CC BY 4.0. The transcribed upstream function keeps its own Apache-2.0 licence. Work by AI
agents working in MV2's name (Munim, Inc.).
