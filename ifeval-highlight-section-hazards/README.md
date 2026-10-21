# ifeval-highlight-section-hazards

Part of the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of
Munim, Inc. One small, reproducible corpus that isolates a single mechanism by which an
LLM-benchmark checker can score a response wrongly, reproduced from a pinned upstream copy
and checkable with only the Python standard library.

**Target:** IFEval's `detectable_format:number_highlighted_sections` checker
(`HighlightSectionChecker`, from
`google-research/instruction_following_eval/instructions.py`; Apache-2.0, keeps its own
licence).

**Headline:** 6 hand-traced cases, 1 false pass (a single `***text***` span counted as **2**
highlights); on IFEval's own released data the hazard is **reachable but unexercised — blast
radius 0 of 541** (48 prompts require highlights, 0 GPT-4 responses use a triple-asterisk span,
0 inflated counts, 0 verdict flips).

## The mechanism

`HighlightSectionChecker.check_following` counts highlighted sections as the sum of
single-asterisk and double-asterisk matches:

```python
num = 0
for h in re.findall(r"\*[^\n\*]*\*",   value):   # singles
    if h.strip("*").strip():        num += 1
for h in re.findall(r"\*\*[^\n\*]*\*\*", value):  # doubles
    if h.removeprefix("**").removesuffix("**").strip():  num += 1
# pass iff num >= num_highlights
```

A single markdown **bold-italic** span written with three asterisks, `***text***`, is **one**
visual highlighted section. But against these two patterns it matches **twice**:

- the singles pattern finds `**` (empty, skipped), then `*text*` (counted), then `**`
  (empty, skipped) → **1**;
- the doubles pattern finds `**text**` (counted) → **1**;
- total `num = 2` for one visual highlight.

So a response that highlights **one** span with `***…***` satisfies a "highlight at least 2
sections" instruction it did not really meet — an **over-count false pass**. A companion
`corrected_count` subtracts one per `***…***` span (`\*\*\*[^\n\*]+\*\*\*`), and `classify`
labels each case against the ground-truth number of deliberate highlights.

## What was found

### Synthetic corpus (6 pre-registered cases)

| id | text (abridged) | quota | real highlights | checker count | kind |
|----|-----------------|------:|----------------:|--------------:|------|
| C1-two-singles | `*first point*` … `*second point*` | 2 | 2 | 2 | match |
| C2-triple-overcount | `***only one***` span | 2 | 1 | 2 | false pass |
| C3-triple-correct | one `***emphasis***` span | 1 | 1 | 2 | match |
| C4-empty-guard | `**  **` (strips to empty) | 1 | 0 | 0 | correct neg |
| C5-two-doubles | `**alpha**` … `**beta**` | 2 | 2 | 2 | match |
| C6-no-highlight | plain prose, no asterisks | 1 | 0 | 0 | correct neg |

`n_cases = 6, n_match = 3, n_correct_neg = 2, n_false_pass = 1, n_false_fail = 0, n_flips = 1,
all_reproduced = true`. C3 shows the over-count is only *latent* when the quota is 1 (count 2
still passes correctly); C2 is where it actually flips a fail into a pass. Every verdict was
hand-traced against the two patterns before any code ran; the sealed job re-derives them and
asserts the aggregate matches this pre-registered target.

### Exposure on IFEval's own released data

Among IFEval's 541 prompts, **48** carry a `number_highlighted_sections` instruction; **47** of
their released GPT-4 responses are present (1 missing). Of those, **44** pass the checker, and:

```
responses using a ***text*** span      = 0
responses with an inflated count       = 0
verdict flips if the count is corrected = 0
```

So this is an honest **reachable-but-unexercised** negative: the over-count is a real,
demonstrable checker defect (see C2), but GPT-4's responses in this corpus never use a
triple-asterisk bold-italic span, so none of their counts is inflated and none of the 44 passes
depends on the defect. The blast radius — scored responses that could flip if a model used
`***…***` to meet the quota — is bounded at 0 of 541 here. `results.json` ships the empty
`inflate_examples` / `flip_examples` lists so the null result is explicit and re-checkable.

## Files

- `highlight_checker.py` — `count_highlights` (IFEval's `HighlightSectionChecker`, transcribed
  verbatim), `count_triple_spans`, `corrected_count`, `check_following` and `classify`.
  Apache-2.0.
- `cases.py` — the 6 pre-registered labelled cases and the target. CC BY 4.0.
- `test_highlight_checker.py` — stdlib `unittest`; each case must reproduce its count/verdict
  and the aggregate must match the target.
- `job.py` — the sealed compute job: asserts the corpus, then measures official exposure
  (triple spans, inflated counts, corrected-verdict flips).
- `results.json` — the sealed run's output (corpus + exposure).

Reproduce: `python -m unittest -v` then `python job.py` (the exposure step needs IFEval's
`input_data.jsonl` and the GPT-4 response file in `/data`; the corpus assertion needs no data).

## Limits, honestly

One checker, one dataset. The synthetic corpus is hand-labelled and small; its verdicts were
traced by AI agents working in MV2's name, not by an independent human reviewer.
`corrected_count` subtracts one highlight per `***…***` span — one reasonable correction, not an
upstream standard; it exists to decide whether the over-count would flip a verdict, not as a
proposed replacement. The exposure count is exact for IFEval's released GPT-4 responses and
says nothing about other models or private test sets.

## Licence

Code is Apache-2.0. The labelled corpus (`cases.py`), `results.json` and this write-up are
CC BY 4.0. The transcribed upstream function keeps its own Apache-2.0 licence. Work by AI
agents working in MV2's name (Munim, Inc.).
