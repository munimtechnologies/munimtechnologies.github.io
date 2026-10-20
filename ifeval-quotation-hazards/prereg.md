# Pre-registration — ifeval-quotation-hazards

Fixed before the sealed compute run. No numbers were read from the official
IFEval data before writing these predictions.

## Checker under audit
Google's IFEval constraint `startend:quotation` (`QuotationChecker` in
`instruction_following_eval/instructions.py`) decides a response "is wrapped in
double quotation marks" with:

```python
value = value.strip()
return len(value) > 1 and value[0] == '"' and value[-1] == '"'
```

Both end tests compare against the ASCII QUOTATION MARK U+0022 only. A response
wrapped in any other double quotation mark — the curly typographic pair
LEFT/RIGHT DOUBLE QUOTATION MARK U+201C/U+201D, the German low-9 mark U+201E, the
double angle guillemets U+00AB/U+00BB — is marked NOT wrapped even though it
plainly is. Because curly quotes are produced routinely by language models,
editors, word processors and markdown renderers, this is a false-fail hazard: a
compliant response is scored as non-compliant.

The plainly-intended reading, used as the comparator, treats a character as a
double quotation mark iff its Unicode name contains `QUOTATION MARK` and the mark
is a DOUBLE one (its name contains `DOUBLE`, or it is the ASCII U+0022), and it
is not a SINGLE quotation mark (`unicodedata.name`). A response is wrapped iff,
after stripping, its first and last characters are both double quotation marks.

Prior art: the general distinction between ASCII straight quotes and curly/smart
quotes is well known in text processing. What is new here is isolating it inside
IFEval's `QuotationChecker`, reproducing it as a labelled corpus, and measuring
its exposure on IFEval's own released data.

## Predictions

**P1 (corpus).** All six hand-built cases reproduce their fixed verdicts:
`n_flip = 4` (the curly, German low-9, guillemet and mixed curly-open/ASCII-close
cases), with the ASCII-wrapped and no-quote controls showing no flip, giving
`all_reproduced = true`.

**P2 (exposure, official data).** On the IFEval GPT-4 responses matched to
`startend:quotation` prompts, the number of *false fails* (shipped verdict FAIL
while the response is wrapped in a non-ASCII double quotation mark) is NOT
predicted in advance — it is the measurement. We pre-commit to reporting
`n_quotation_instances`, `n_matched_to_response`, `n_shipped_pass`, and
`n_false_fail`. Because a model told to "wrap in double quotation marks" will
often reach for the ASCII key, our honest expectation is that `n_false_fail` is
small, possibly 0; but because models also emit curly quotes, it may be non-zero.

**P3 (blast radius).** Across ALL 541 released GPT-4 responses (not only
`quotation` prompts), we report `n_responses_wrapped_in_nonascii_double_quotes`
(wrapped under the intended reading but failing the ASCII-only check) and the set
of distinct boundary quote characters seen, to characterise how often responses
are wrapped in non-ASCII double quotes at all.

## Interpretation set in advance
- If `n_false_fail > 0`: the ASCII-only quotation check penalises real IFEval
  responses that DID wrap themselves in double quotation marks — the published
  `startend:quotation` outcome depends on which quote glyph the model used, not
  on whether it complied.
- If `n_false_fail = 0`: the hazard is real and reproducible (the six cases) but
  **reachable-but-unexercised** on this English response set. It is reported as
  an honest negative that still bounds the blast radius: any model that wraps its
  answer in curly or other non-ASCII double quotes would have its
  `startend:quotation` score silently zeroed. This mirrors the reachable-but-
  unexercised finding in the sibling `ifeval-comma-hazards` audit.
