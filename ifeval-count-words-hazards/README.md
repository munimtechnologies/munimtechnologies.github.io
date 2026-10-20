# ifeval-count-words-hazards

Part of the [eval-reliability-audits](../eval-reliability-audits) catalogue by
MV2 of Munim, Inc. Execution-verified; this work was produced with AI agents
working in MV2's name. Licensed Apache-2.0 (code) / CC BY 4.0 (text & data).

## What this audits

IFEval's length constraint `length_constraints:number_words` counts words with
`instructions_util.count_words`, which builds an NLTK tokenizer and returns its
token count (`instruction_following_eval/instructions_util.py`):

```python
tokenizer = nltk.tokenize.RegexpTokenizer(r"\w+")
num_words = len(tokenizer.tokenize(text))
```

For str input this is exactly `len(re.findall(r"\w+", text))`. The verdict
(`NumberOfWords` in `instructions.py`) is `num_words < N` for relation
"less than" and `num_words >= N` for "at least".

`\w+` counts **runs of word characters**, so the apostrophe, hyphen, decimal
point, thousands separator and in-acronym period all act as word boundaries,
while a token with no word character (emoji, a lone dash, bare punctuation) is
dropped entirely. The word count — and therefore the pass/fail verdict — depends
on this undocumented tokenizer choice, not only on the response.

## Two questions, two answers

**1. Is the discrepancy real?** Yes. Six minimal, hand-traced cases
(`cases.json`) compare IFEval's `\w+` count with a plain whitespace split and
the `number_words` verdict under each:

| case | text (abbrev.) | `\w+` | whitespace | flips verdict |
| --- | --- | --- | --- | --- |
| W1 contractions | `I don't … can't …` | 9 | 7 | yes |
| W2 hyphen + decimal | `state-of-the-art … 3.5 …` | 9 | 5 | yes |
| W3 acronyms | `… U.S.A. … U.K.` | 8 | 5 | yes |
| W4 emoji / punctuation | `Done ✅ !!! 🎉 — finally` | 2 | 6 | yes (undercount) |
| W5 underscore (control) | `… max_retries …` | 6 | 6 | no |
| W6 grouped digits | `… 1,000,000 … 2026.` | 8 | 6 | yes |

`n_count_diff = 5`, `n_verdict_flip = 5`, `all_reproduced = true`. W4 shows the
*undercount* direction (emoji / punctuation tokens dropped); the others
overcount.

**2. Does it touch real benchmark scores? Yes — on IFEval's own released GPT-4
responses, the tokenizer choice flips the published verdict for 2 items.** This
is the measurement in `job.py`: across all IFEval
`length_constraints:number_words` prompts, it joins each prompt to IFEval's own
released GPT-4 response, computes both word counts, and reports the divergence.
The sealed-run headline (`results.json`, exposure):

- **`n_number_words_instances = 52`** — every `number_words` constraint in IFEval.
- **`n_matched_to_response = 52`** — all 52 joined to their GPT-4 response.
- `n_count_diff = 45` of 52 responses (87%) have a different `\w+` vs
  whitespace count; `n_overcount_ifeval_gt_ws = 42`, `n_undercount = 3`
  (direction matches the pre-registered P2); `abs_diff_mean ≈ 8.1`,
  `abs_diff_median = 5`, `abs_diff_max = 39`.
- **`n_verdict_flip = 2`**, both under relation "at least"
  (`flip_by_relation = {"less than": 0, "at least": 2}`). In both, IFEval's
  `\w+` count clears the threshold while a whitespace split does not
  (key 19: 618 vs 584 for "at least 600"; key 2246: 424 vs 392 for
  "at least 400").

The pre-registration (`prereg.md`) fixed the interpretation before the run:
because **`n_verdict_flip > 0`**, the undocumented choice of word tokenizer
changes the pass/fail outcome of real IFEval `number_words` items — the
published score depends on the tokenizer, not only on the response. (A zero flip
count would have been an honest *reachable-but-unexercised* negative; it was not
the outcome here.)

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
- `count_words_audit.py` — the reproduced `\w+` counter, a whitespace-split
  counter, and the `number_words` verdict.
- `cases.json` — the six hand-traced cases with mechanism notes.
- `job.py` — corpus verification + the GPT-4-response flip measurement.
- `test_ifeval_count_words_hazards.py` — stdlib tests.
- `prereg.md` — predictions fixed before the run.
- `results.json` — sealed-run output.
