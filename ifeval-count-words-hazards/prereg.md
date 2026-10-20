# Pre-registration — ifeval-count-words-hazards

Fixed before the sealed compute run. No numbers were read from the GPT-4
response data before writing these predictions.

## Checker under audit
Google's IFEval length constraint `length_constraints:number_words`
(`NumberOfWords` in `instruction_following_eval/instructions.py`) counts words
with `instructions_util.count_words`, which builds
`nltk.tokenize.RegexpTokenizer(r"\w+")` and returns the number of tokens. For
str input that tokenizer equals `len(re.findall(r"\w+", text))`. The verdict is
`count < num_words` (relation "less than") or `count >= num_words`
(relation "at least").

Because `\w+` treats the apostrophe, hyphen, decimal point, thousands
separator and in-acronym period as token boundaries — and drops tokens that
contain no word character at all (emoji, bare punctuation) — the resulting
count can differ from a plain whitespace split, in either direction.

## Predictions

**P1 (corpus).** All six hand-built cases reproduce their fixed counts and
`number_words` verdicts, giving `n_count_diff = 5`, `n_verdict_flip = 5`,
`all_reproduced = true` (W5 is a deliberate no-divergence control).

**P2 (direction, official data).** On the IFEval GPT-4 responses matched to
`number_words` prompts, the `\w+` count is greater than or equal to the
whitespace-split count for the large majority of responses, because `\w+`
splits tokens far more often than it drops them. Undercounting
(`count_ifeval < count_ws`) is predicted to be rare and to occur only for
responses that contain standalone non-word tokens (emoji, a lone dash, bare
punctuation); `n_undercount` may be 0.

**P3 (impact, open measurement).** We do NOT predict the flip count in advance —
it is the measurement. We pre-commit to reporting, whatever they are:
`n_number_words_instances`, `n_matched_to_response`, `n_count_diff`,
`n_verdict_flip` and `flip_by_relation`.

## Interpretation set in advance
- If `n_verdict_flip > 0`: the undocumented choice of word tokenizer changes the
  pass/fail outcome of real IFEval `number_words` items — the published score
  depends on the tokenizer, not only on the response.
- If `n_verdict_flip = 0`: the discrepancy is real and reproducible (the six
  cases) but **reachable-but-unexercised** on this response set — the GPT-4
  responses clear their thresholds by margins wider than the tokenizer gap.
  That is an honest negative, reported as such, and still bounds the blast
  radius for anyone scoring responses that sit near a word-count threshold.
