# ifeval-comma-hazards

Part of the [eval-reliability-audits](../eval-reliability-audits) catalogue by
MV2 of Munim, Inc. Execution-verified; this work was produced with AI agents
working in MV2's name. Licensed Apache-2.0 (code) / CC BY 4.0 (text & data).

## What this audits

IFEval's punctuation constraint `punctuation:no_comma` (`CommaChecker` in
`instruction_following_eval/instructions.py`) decides whether a response "uses no
comma" with a single line:

```python
return not re.search(r"\,", value)
```

`re.search(r"\,", value)` matches only the **ASCII comma U+002C**. Every other
Unicode comma is invisible to it: FULLWIDTH COMMA `，` (U+FF0C, ubiquitous in
Chinese/Japanese text and from CJK input methods), IDEOGRAPHIC COMMA `、`
(U+3001), ARABIC COMMA `،` (U+060C), ARMENIAN COMMA (U+055D), and others. A
response that visibly contains commas therefore *passes* `no_comma` whenever its
commas are non-ASCII.

The comparator here is the plainly-intended reading: a character is a comma iff
its Unicode name contains `COMMA` (`unicodedata.name`) — a crisp, standard-
library-only definition covering every script.

Prior art: that an ASCII-only check misses the fullwidth comma (U+FF0C vs U+002C)
is a well-known text-processing trap. What is new here is isolating it inside
IFEval's `CommaChecker`, reproducing it as a labelled corpus, and measuring its
exposure on IFEval's own released data.

## Two questions, two answers

**1. Is the hazard real?** Yes. Six minimal, hand-traced cases (`cases.json`,
stored as code points so the file is pure ASCII) compare the shipped ASCII-only
verdict with the intended any-Unicode-comma reading:

| case | text | shipped `no_comma` | has a comma? | flips |
| --- | --- | --- | --- | --- |
| K1 fullwidth comma | `a，b` (U+FF0C) | PASS | yes | yes |
| K2 ideographic comma | `a、b` (U+3001) | PASS | yes | yes |
| K3 arabic comma | `a،b` (U+060C) | PASS | yes | yes |
| K4 fullwidth comma in English | `Yes，I agree` | PASS | yes | yes |
| K5 ASCII comma (control) | `a,b` (U+002C) | FAIL | yes | no |
| K6 no comma (control) | `a b` | PASS | no | no |

`n_verdict_flip = 4`, `all_reproduced = true`. The ASCII-comma and no-comma
controls behave identically under both readings.

**2. Does it touch real benchmark scores?** We measured this on IFEval's own
released GPT-4 responses, under the interpretation fixed in advance in
`prereg.md`. Joining every `punctuation:no_comma` instruction to its GPT-4
response gives **66** `no_comma` instances, all **66** matched to a response, of
which **44** are scored PASS by the shipped checker. The number of *false
passes* — responses marked comma-free that actually contain a non-ASCII comma —
is **0**. No `no_comma`-constrained GPT-4 response used a non-ASCII comma, so no
published `no_comma` verdict in this English response set is wrong because of the
hazard.

That is an honest **reachable-but-unexercised** negative, exactly the outcome
pre-registered as possible: the hazard is real and reproducible (the six cases)
but not triggered on this English data. The blast radius bounds what it would
cost elsewhere. Across **all 541** released GPT-4 responses (not only
`no_comma` prompts), **2** contain a non-ASCII comma, and the one non-ASCII comma
character seen is **ARABIC COMMA U+060C** (in 2 responses). So the exact
character class the shipped checker cannot see does occur in real IFEval
responses — it simply did not land on a `no_comma`-constrained prompt this time.
Any multilingual IFEval variant, or any model that answers with CJK/Arabic
punctuation, would have its `no_comma` score silently inflated. The full numbers
are in `results.json`.

## Reproduce

```
python -m unittest -v
python job.py --data-dir <dir with the two IFEval files> --out-dir out
```

`input_data.jsonl` and `input_response_data_gpt4_20231107_145030.jsonl` are the
public IFEval prompt and GPT-4 response files from
`google-research/google-research/instruction_following_eval/data/`.
`prereg.md` fixed every prediction beforehand; `results.json` is the sealed-run
output.

## Files
- `comma_checker.py` — the reproduced ASCII-only checker, the intended
  any-Unicode-comma reading, and helpers.
- `cases.json` — the six hand-traced cases (as code points) with mechanism notes.
- `job.py` — corpus verification + the GPT-4-response false-pass and blast-radius
  measurement.
- `test_ifeval_comma_hazards.py` — stdlib tests.
- `prereg.md` — predictions fixed before the run.
- `results.json` — sealed-run output.
