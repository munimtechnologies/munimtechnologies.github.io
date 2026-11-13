# helm-convfinqa-five-tokens (audit 117)

**Status: desk check, 2026-11-13. Code-certain, not pre-registered. HELM publishes no ConvFinQACalc runs (its
public archive's `finance` project, release v1.0.0, has no `conv_fin_qa_calc` run, and there is no enterprise
project), so no published number is re-computed here. A small check job that counts, on the real validation split,
how many golds a 5-token answer can reach is queued. Its results will be added below.**

HELM's ConvFinQACalc scenario (PR [#3453](https://github.com/stanford-crfm/helm/pull/3453), merged 2025-03-25,
from IBM's enterprise benchmark) gives a model a table from a financial report, the earlier turns of a ConvFinQA
conversation with their answers, and a final question. The model must answer with a number. The main metric is
`float_equiv` and the main split is `valid` (ConvFinQA's `dev_turn.json`, 1,490 turns according to ConvFinQA's README). The gold is
`str(exe_ans)`, the result of executing the gold program. ConvFinQA's own code rounds that result to 5 decimals,
or sets it to `yes`/`no` for a comparison step.

The work was carried out by AI agents working in MV2's name (MV2 of Munim, Inc.).

## 1. Every answer is cut at 5 tokens (code-certain)

`get_conv_fin_qa_calc_spec()` calls `get_generation_adapter_spec()` with only the instructions ("Respond with the
answer only, with no additional explanation."), `input_noun=None` and `output_noun="Answer"`. It does not pass
`max_tokens`, so the helper's default applies: **`max_tokens=5`**, stop sequence `\n`, 5 in-context examples.
HELM's FinQA run spec in HELM Finance passes `max_tokens=100`, and so does its KPI-EDGAR run spec.

## 2. Some models cannot write many of the golds in 5 tokens (code-certain)

`float_equiv` credits an answer only if its first number is within 1e-6 of the gold's. A gold rounded to 5
decimals, such as `0.14136`, must therefore be written to all 5 decimals. A shorter string cannot be within 1e-6,
because two different 5-decimal numbers are at least 1e-5 apart. LLaMA's tokenizer, which Llama 2 reuses, splits
every number into single digits (Touvron et al., [arXiv 2302.13971](https://arxiv.org/abs/2302.13971) and
[arXiv 2307.09288](https://arxiv.org/abs/2307.09288)). For such a tokenizer every digit is a token, and every run of
other characters between digits is at least one more. So:

| Gold | Shortest credited answer | Tokens needed, at least (digit-split) | Credit possible in 5 tokens |
| --- | --- | --- | --- |
| `0.14136` | `.14136` | 6 | no; the best 5-token cut of `0.14136` is `0.141`, scored 0 |
| `1234.5` | `1234.5` | 6 | no |
| `206588.0` | `206588` | 6 | no |
| `-0.0368` | `-.0368` | 5 (7 written as `-0.0368`) | only without the leading zero |
| `14.1` | `14.1` | 4 | yes |
| `12345.0` | `12345` | 5 | yes |

For these models the 5-token limit sets a ceiling on the score that no answer can pass. The ceiling is the share of
golds whose shortest form needs at most 5 digit-split tokens, and the queued job measures it on the 1,490 validation
golds. Tokenizers that group up to three digits into one token (OpenAI's `cl100k_base` and `o200k_base`) fit most
such golds in 5 tokens, and the job counts those too. In-context examples show the 5-decimal form, so a model is
told what to write; it simply cannot finish writing it.

## 3. What the scorer reads (code-certain)

`_strip_string` returns the **first** number in the answer, as a float, and compares it with no conversion of units:

| Answer | Gold | HELM score | Why |
| --- | --- | --- | --- |
| `0.14136` | `0.14136` | 1 | exact |
| `0.1413605` | `0.14136` | 1 | within 1e-6 |
| `0.141` | `0.14136` | 0 | 5-token cut of a digit-split answer |
| `14.136%` | `0.14136` | 0 | percent not converted |
| `1,234` | `1234.0` | 0 | the comma ends the number: only `1` is read |
| `In 2009 it was 0.5` | `0.5` | 0 | the year is read |
| `decline of 5` | `-5` | 0 | sign in words |
| `-.5` | `-0.5` | 1 | the leading zero may be dropped |
| `yes` | `yes` | 0 | a gold with no number can never be credited |

The last row matters if ConvFinQA's validation set has `yes`/`no` golds (ConvFinQA's code produces them for
comparison steps); every such question scores 0 for every model. The job counts them.

## Relation to open HELM threads

Open issue [#4340](https://github.com/stanford-crfm/helm/issues/4340) (2026-08-23) and open PR
[#4356](https://github.com/stanford-crfm/helm/pull/4356) (2026-09-18) report that `float_equiv`'s docstring and
warning say it returns 1.0 for non-numbers while the code returns 0.0, and that its exception path falls back to
string equality. Neither mentions the 5-token budget, the digit-split ceiling, the first-number rule or yes/no
golds. This audit leaves the return value question to those threads.

## Limits

- **No model output is scored.** HELM publishes no ConvFinQACalc runs, so how much the 5-token limit cost any real
  model cannot be measured here. The ceiling applies to models whose tokenizer splits digits, not to all models.
- The token lower bound assumes each digit is one token. This holds for tokenizers that split numbers into
  digits, the case of LLaMA 1 and Llama 2 as their papers state. We did not check other model families'
  tokenizers, so none is named here.
- IBM's Enterprise Benchmarks paper ([arXiv 2410.12857](https://arxiv.org/abs/2410.12857)) reports ConvFinQA
  accuracy for 13 models (0.198 to 0.407, llama2.7b 0.233) with a 1-shot prompt and its own harness; the paper
  does not state a generation length, and we could not open IBM's repository to compare. Those numbers are not
  HELM's.
- Counts in this README about the dataset are pending the check job; everything above them is read from the code.

## Suggested fix

Pass `max_tokens` in `get_conv_fin_qa_calc_spec()` (FinQA's 100 would do), and either drop `yes`/`no` golds from
the scored set or score them by string match. Optionally strip thousands separators and read the last number
rather than the first.

## Reproduce

```
python -m unittest -v test_convfinqa_check.py
python convfinqa_check.py
python job.py --out-dir out   # downloads ConvFinQA data.zip at the commit HELM pins; counts reachable golds
```

`convfinqa_check.py` is standard library only and transcribes HELM's `conv_fin_qa_calc_metrics.py` as of commit
0d02c1b (2025-08-27, the last commit to touch it). The run spec was read at commit e5695be (2025-04-18, the last
commit to touch `enterprise_run_specs.py`). `job.py` uses `tiktoken` if it is installed.

## Prior art

Searches of HELM's issues and PRs for "ConvFinQA" and "float_equiv" (2026-11-13) find only #3453, #4340, #4356
and an unrelated Japanese FinQA proposal (#4072/#4073). A search for "max_tokens truncated answer" finds nothing
about this scenario. A web search found no other critique of HELM's ConvFinQACalc.

## Licence

Code is Apache-2.0; the transcribed HELM functions keep HELM's Apache-2.0 licence. This write-up is CC BY 4.0.
Made with AI agents working in MV2's name (Munim, Inc.).

## Results

*Added 2026-11-13. The check job (`helm-convfinqa-check-v1`, `job.py` and the 16 unit tests above, unchanged) ran
once in a sealed container on 2026-11-13 from 20:58 to 21:03 UTC; all 16 tests passed. It downloaded ConvFinQA's
`data.zip` at the commit HELM pins (cf3eed2), rebuilt every gold as HELM does (`str(annotation["exe_ans"])`) and
counted. The full counts are in [results.json](results.json) (counts only, no dataset text). Everything below is
about the golds; no model output is scored, because HELM publishes none for this scenario.*

**The validation split (HELM's main split) has 1,490 turns**, as ConvFinQA's README says. Every gold was found
under `annotation`. 1,486 golds are numbers; every one of them credits itself under `float_equiv` (1,486 of 1,486),
so the transcribed scorer reads them as intended.

| Count on the 1,490 validation golds | n | Share of 1,490 |
| --- | --- | --- |
| `yes`/`no` golds (3 `no`, 1 `yes`): 0 for every model | 4 | 0.3% |
| Golds whose shortest credited form fits in 5 digit-split tokens (**upper bound on a digit-splitting model's score**) | 959 | **64.4%** |
| The same, writing the gold as it is stored (only a trailing `.0` dropped, leading zero kept) | 891 | 59.8% |
| Golds with 5 decimals in their shortest form (such as `0.14136`) | 354 | 23.8% |
| Golds credited if the answer is rounded to 2 decimals | 1,015 | 68.1% |
| Golds of 1,000 or more in absolute value: 0 if written with a thousands separator (`1,234` is read as 1) | 355 | 23.8% |
| Golds credited by the first 5 `cl100k_base` (or `o200k_base`) tokens of the stored form | 1,484 | 99.6% |

What this shows:

- **A model whose tokenizer gives each digit its own token cannot score above 0.644 on HELM's ConvFinQACalc**,
  whatever it knows: 527 of the 1,490 golds (35.4%) need at least 6 such tokens even in their shortest form
  (leading zero dropped, no trailing zeros), and 595 (39.9%) as the golds are written; with the 4 `yes`/`no`
  golds, 531 golds (35.6%) are out of reach. The count is a lower bound
  on tokens, so the true ceiling for such a tokenizer can only be lower (for example if the answer's leading space
  is a token of its own). Shortest-form token counts: 1 token 30, 2: 111, 3: 232, 4: 310, 5: 276, 6: 397, 7: 75,
  8: 26, 9 or more: 29.
- **OpenAI's tokenizers are barely affected**: under `cl100k_base` and `o200k_base` the stored form takes a median
  of 3 tokens and at most 6; 2 golds need more than 5 tokens, and 17 do when the answer starts with a space, as an
  answer after `Answer:` usually does. So the 5-token cut falls on some model families and not others, by
  tokenizer rather than by skill.
- **Answer habits are costly under this scorer.** A model that rounds to 2 decimals, as financial answers often
  are, can be credited on at most 1,015 golds (68.1%), and one that writes thousands separators loses all 355 golds
  of 1,000 or more (23.8%).
- **Percent questions.** 252 final questions contain "percent" or "%". On 214 of them (84.9%) the gold is below 1
  in absolute value, so it is most likely stored as a fraction (0.14136 rather than 14.136), and an answer given in
  percent scores 0 on those. Some of the 214 may be genuine percentages below 1, so this is an upper bound.
- The **training split** (11,104 turns, used for the in-context examples) looks the same: 36 `yes`/`no` golds,
  digit-split ceiling 0.627 (6,960 of 11,104), and 2,672 golds with 5 decimals.

These counts are about what the scorer and the token limit allow, not about any model's measured accuracy.
IBM's paper reports llama2.7b at 0.233 with its own harness; we cannot say how far HELM's own number for a Llama 2
model would fall, because HELM has published none.

**Suggested fix, unchanged:** pass `max_tokens` in `get_conv_fin_qa_calc_spec()` (FinQA's 100 would do), and drop
or string-match the 4 `yes`/`no` golds.
