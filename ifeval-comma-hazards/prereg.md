# Pre-registration — ifeval-comma-hazards

Fixed before the sealed compute run. No numbers were read from the official
IFEval data before writing these predictions.

## Checker under audit
Google's IFEval punctuation constraint `punctuation:no_comma`
(`CommaChecker` in `instruction_following_eval/instructions.py`) decides a
response "uses no comma" with a single line:

```python
return not re.search(r"\,", value)
```

`re.search(r"\,", value)` matches only the ASCII comma U+002C. Any other
Unicode character that is a comma — FULLWIDTH COMMA U+FF0C, IDEOGRAPHIC COMMA
U+3001, ARABIC COMMA U+060C, ARMENIAN COMMA U+055D, and the rest — is invisible
to the check, so a response that visibly contains commas passes `no_comma`.

The plainly-intended reading, used as the comparator, treats a character as a
comma iff its Unicode name contains the word `COMMA` (via `unicodedata.name`), a
crisp, standard-library-only definition.

Prior art: the general hazard that an ASCII-only punctuation check misses
fullwidth/CJK commas (U+FF0C vs U+002C) is well known in text processing. What
is new here is isolating it in IFEval's `CommaChecker`, reproducing it as a
labelled corpus, and measuring its exposure on IFEval's own released data.

## Predictions

**P1 (corpus).** All six hand-built cases reproduce their fixed verdicts:
`n_flip = 4` (the fullwidth, ideographic and Arabic commas, plus the
fullwidth-comma-in-English case), with the ASCII-comma and no-comma controls
showing no flip, giving `all_reproduced = true`.

**P2 (exposure, official data).** On the IFEval GPT-4 responses matched to
`punctuation:no_comma` prompts, the number of *false passes* (shipped verdict
PASS while the response contains a non-ASCII comma) is NOT predicted in advance —
it is the measurement. We pre-commit to reporting `n_no_comma_instances`,
`n_matched_to_response`, `n_shipped_pass`, and `n_false_pass` (shipped PASS but
a non-ASCII comma present). Because the released responses are English GPT-4
text, our honest expectation is that `n_false_pass` is 0 or very small.

**P3 (blast radius).** Across ALL 541 released GPT-4 responses (not only
`no_comma` prompts), we report `n_responses_with_nonascii_comma` and the set of
distinct non-ASCII comma characters seen, to characterise how often this
character class appears at all in benchmark responses.

## Interpretation set in advance
- If `n_false_pass > 0`: the ASCII-only comma check passes real IFEval responses
  that visibly contain commas — the published `no_comma` outcome depends on the
  script of the response's punctuation, not only on whether it used commas.
- If `n_false_pass = 0`: the hazard is real and reproducible (the six cases) but
  **reachable-but-unexercised** on this English response set. It is reported as
  an honest negative that still bounds the blast radius: any multilingual IFEval
  variant, or any model that answers with CJK/Arabic punctuation, would have its
  `no_comma` score silently inflated. This mirrors the reachable-but-unexercised
  finding in the sibling `ifeval-regex-hazards` audit.
