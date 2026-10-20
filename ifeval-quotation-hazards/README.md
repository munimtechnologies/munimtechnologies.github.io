# ifeval-quotation-hazards

Part of the [eval-reliability-audits](../eval-reliability-audits) catalogue by
MV2 of Munim, Inc. Execution-verified; this work was produced with AI agents
working in MV2's name. Licensed Apache-2.0 (code) / CC BY 4.0 (text & data).

## Headline

IFEval's `startend:quotation` checker only recognises the **ASCII QUOTATION MARK
U+0022** at a response's two ends. A response wrapped in curly “smart” quotes,
German low-9 quotes or guillemets is silently marked NOT wrapped. The hazard is
**real and reproducible** (4 of 6 hand-traced cases flip), but on IFEval's own
released data it is **reachable-but-unexercised**:

- `startend:quotation` instructions in IFEval: **41** (`n_quotation_instances`),
  all 41 matched to their released GPT-4 response (`n_matched_to_response = 41`).
- GPT-4 responses the shipped ASCII-only checker scored PASS: **41**
  (`n_shipped_pass = 41`).
- **False fails** — responses wrapped in a non-ASCII double quote that the
  shipped checker wrongly marked NOT wrapped: **0** (`n_false_fail = 0`).
- Blast radius across **all 541** released GPT-4 responses: **0** are wrapped in
  a non-ASCII double quotation mark (`n_responses_wrapped_in_nonascii_double_quotes = 0`);
  the set of distinct non-ASCII boundary quote characters seen is **empty**.

So on this English GPT-4 response set the ASCII-only check never silently zeroes
a compliant answer — a clean negative. But any model that wraps its answer in
`“ ”`, `„ “` or `« »` (routine output of chat models, editors and markdown
renderers) would have its `startend:quotation` score silently set to fail. This
mirrors — and is even cleaner than — the sibling
[ifeval-comma-hazards](../ifeval-comma-hazards) audit, whose blast radius was 2
(both an Arabic comma U+060C); here it is 0.

## What this audits

IFEval's constraint `startend:quotation` (`QuotationChecker` in
`instruction_following_eval/instructions.py`) decides whether a response is
"wrapped in double quotation marks" with:

```python
value = value.strip()
return len(value) > 1 and value[0] == '"' and value[-1] == '"'
```

Both boundary tests compare against the **ASCII QUOTATION MARK U+0022** only. A
response wrapped in any other double quotation mark is marked NOT wrapped even
though it plainly is: the curly typographic pair LEFT/RIGHT DOUBLE QUOTATION MARK
`“ ”` (U+201C/U+201D), the German low-9 mark `„` (U+201E), the double angle
guillemets `« »` (U+00AB/U+00BB). Because curly quotes are produced routinely by
language models, editors, word processors and markdown renderers, this is a
**false-fail** hazard: a compliant response is scored as non-compliant.

The comparator here is the plainly-intended reading: a character is a double
quotation mark iff its Unicode name contains `QUOTATION MARK` and the mark is a
DOUBLE one (its name contains `DOUBLE`, or it is the ASCII U+0022), excluding
single quotes — a crisp, standard-library-only definition (`unicodedata`).

Prior art: the distinction between ASCII straight quotes and curly/smart quotes
is a well-known text-processing issue. What is new here is isolating it inside
IFEval's `QuotationChecker`, reproducing it as a labelled corpus, and measuring
its exposure on IFEval's own released data.

## Two questions, two answers

**1. Is the hazard real?** Yes. Six minimal, hand-traced cases (`cases.json`,
stored as code points so the file is pure ASCII) compare the shipped ASCII-only
verdict with the intended any-double-quote reading:

| case | wrapping | shipped `quotation` | wrapped? | flips |
| --- | --- | --- | --- | --- |
| Q1 curly double quotes | `“hello”` (U+201C/U+201D) | FAIL | yes | yes |
| Q2 German low-9 quotes | `„hello“` (U+201E/U+201C) | FAIL | yes | yes |
| Q3 guillemets | `«hello»` (U+00AB/U+00BB) | FAIL | yes | yes |
| Q4 ASCII double quotes (control) | `"hello"` (U+0022) | PASS | yes | no |
| Q5 no quotes (control) | `hello` | FAIL | no | no |
| Q6 curly open, ASCII close | `“hello"` (U+201C/U+0022) | FAIL | yes | yes |

`n_verdict_flip = 4`, `all_reproduced = true`. The ASCII-wrapped and no-quote
controls behave identically under both readings.

**2. Does it touch real benchmark scores?** Measured in `job.py`, across all
IFEval `startend:quotation` prompts joined to IFEval's own released GPT-4
responses: `n_quotation_instances = 41`, `n_matched_to_response = 41`,
`n_shipped_pass = 41`, **`n_false_fail = 0`**, and a blast radius of **0** across
all 541 responses (no response is wrapped in a non-ASCII double quotation mark).
The pre-registration (`prereg.md`) fixed this interpretation before the run: a
zero false-fail count is an honest *reachable-but-unexercised* negative on this
English response set that still bounds the blast radius — any model that wraps
its answer in a curly or other non-ASCII double quote would have its
`startend:quotation` score silently zeroed. The sealed-run numbers are in
`results.json`.

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
- `quote_checker.py` — the reproduced ASCII-only checker, the intended
  any-double-quote reading, and helpers.
- `cases.json` — the six hand-traced cases (as code points) with mechanism notes.
- `job.py` — corpus verification + the GPT-4-response false-fail and blast-radius
  measurement.
- `test_ifeval_quotation_hazards.py` — stdlib tests.
- `prereg.md` — predictions fixed before the run.
- `results.json` — sealed-run output.
