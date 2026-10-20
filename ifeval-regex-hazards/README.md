# ifeval-regex-hazards

Part of the [eval-reliability-audits](../eval-reliability-audits) catalogue by
MV2 of Munim, Inc. Execution-verified; this work was produced with AI agents
working in MV2's name. Licensed Apache-2.0 (code) / CC BY 4.0 (text & data).

## What this audits

Two of IFEval's instruction checkers build a regular expression directly from a
user-supplied keyword, **without `re.escape`**
(`instruction_following_eval/instructions.py`):

| instruction_id | shipped line |
| --- | --- |
| `keywords:frequency` | `len(re.findall(self._keyword, value, flags=re.IGNORECASE))` |
| `keywords:forbidden_words` | `re.search(r"\b" + word + r"\b", value, flags=re.IGNORECASE)` |

Because the string is treated as a regex pattern instead of literal text, a
keyword that contains a regex metacharacter (`. ^ $ * + ? { } [ ] \ | ( )`) is
silently mis-counted, or makes the scorer raise `re.error`.

## Two questions, two answers

**1. Is the hazard real?** Yes. Nine minimal, self-contained cases
(`cases.json`) each reproduce one failure mode — verdicts computed by the
reproduced checker (`ifeval_regex.py`) vs. the plainly-intended literal reading
(the same checker with `re.escape`):

| class | count | example |
| --- | --- | --- |
| crash (`re.error`) | 2 | forbidden word `a[b` → unterminated character set |
| false pass | 2 | keyword `a.b` matches `axb/ayb/azb`, so "at least 3" passes with 0 literal occurrences |
| false fail | 5 | keyword `x^2` (the `^` anchors mid-pattern) matches 0 times though `x^2` appears 3 times |

`n_crash = 2`, `n_false_pass = 2`, `n_false_fail = 5`, `all_reproduced = true`.

A note that is often stated wrong: the keyword `C++` does **not** crash the
scorer on CPython 3.11+. There, `++` is a *possessive* quantifier, so `C++` is a
valid regex that counts runs of `C` rather than the literal token `C++` — a
silent mis-count, not a crash. (On CPython ≤ 3.10 the same pattern raises
`re.error: multiple repeat`.) This audit ran on CPython 3.12.

**2. Does it touch real benchmark scores?** No — and that is the point of the
exposure scan. Across all **541** official IFEval prompts
(`input_data.jsonl`):

| checker | official instances | with a regex metachar | invalid regex |
| --- | --- | --- | --- |
| `keywords:frequency` | 42 | **0** | **0** |
| `keywords:forbidden_words` | 49 | **0** | **0** |

So the hazard is **reachable but unexercised**: the shipped code mishandles
metacharacter keywords, yet no official prompt uses one, so published IFEval
numbers are not affected by this mechanism. This is a deliberately modest,
partly negative result — it bounds the blast radius rather than claiming the
benchmark is broken. It matters for anyone who *extends* IFEval with new
keyword prompts (e.g. programming terms like `C++`, `a.out`, `f(x)`), where the
mechanism would begin to bite.

## Reproduce

```
python -m unittest -v
python job.py --data-dir <dir with input_data.jsonl> --out-dir out
```

`input_data.jsonl` is the public IFEval prompt file from
`google-research/google-research/instruction_following_eval/data/`.
`results.json` is the output of the sealed run; `prereg.md` fixed every
prediction beforehand.

## Files
- `ifeval_regex.py` — faithful reproduction of both checkers + the intended
  (`re.escape`) reading + metachar detection.
- `cases.json` — the nine hand-labelled cases with mechanism notes.
- `job.py` — corpus verification + the 541-prompt exposure scan.
- `test_ifeval_regex_hazards.py` — stdlib tests.
- `prereg.md` — predictions fixed before the run.
- `results.json` — sealed-run output.
