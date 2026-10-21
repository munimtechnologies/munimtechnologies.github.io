# ifeval-paragraph-hazards

The 17th audit in the [eval-reliability-audits](../eval-reliability-audits/)
catalogue by MV2 of Munim, Inc. It isolates one defect in IFEval's
`ParagraphChecker` (the `length_constraints:number_paragraphs` instruction),
reproduces it byte-faithfully from the pinned upstream scoring code, and measures
how often it changes a published pass/fail verdict on IFEval's own released data.

This audit is carried out by AI agents working in MV2's name and is disclosed as
AI-made.

## The mechanism

IFEval checks that a response contains **exactly** `num_paragraphs` paragraphs,
where paragraphs are "separated with the markdown divider: `***`". The upstream
`check_following` does, verbatim:

```python
paragraphs = re.split(r"\s?\*\*\*\s?", value)   # NOT line-anchored
num_paragraphs = len(paragraphs)
for index, paragraph in enumerate(paragraphs):
    if not paragraph.strip():
        if index == 0 or index == len(paragraphs) - 1:
            num_paragraphs -= 1                 # boundary empty: trim
        else:
            return False                        # interior empty: HARD FAIL
return num_paragraphs == self._num_paragraphs   # EXACT equality
```

The divider pattern `r"\s?\*\*\*\s?"` is not line-anchored, and the pass test is
exact equality. Two things follow, and because the test is exact they flip the
verdict in **both** directions:

1. **Over-count.** An inline emphasis span `***like this***` is matched at *both*
   runs of three asterisks, splitting a single paragraph into extra segments. A
   single prose line that uses `***` as a visual separator (`a *** b *** c`) is
   likewise read as several paragraphs. This can fail a correct answer, or — when
   the spurious splits happen to land on the required number — pass a response
   that has no real paragraph breaks.
2. **Hard fail.** A *doubled* divider (`\n***\n***\n`) leaves an empty segment in
   the *middle* of the split, which the interior-empty rule turns into an
   immediate `return False`, failing a response that reads as the right number of
   paragraphs.

## What was found

### Synthetic corpus

Seven cases, each hand-traced against the reproduced checker **before** any real
data was touched, then re-derived and asserted in a sealed container.

| id | what it exercises | ground truth | checker | verdict |
|----|-------------------|--------------|---------|---------|
| P1 | three paragraphs, two standalone `***` lines | 3 | pass | match |
| P2 | two paragraphs, one standalone divider | 2 | pass | match |
| P3 | one paragraph using inline `***emphasis***` | 1 | fail (num=3) | **false fail** |
| P4 | two paragraphs, divider doubled | 2 | fail (hard fail) | **false fail** |
| P5 | one line, `***` used twice as separators | 1 | pass (num=3=quota) | **false pass** |
| P6 | single paragraph, no divider | 1 | fail | correct negative |
| P7 | three paragraphs, two standalone dividers | 3 | pass | match |

Totals: 7 cases, 3 matches, 1 correct negative, 1 false pass, 2 false fails —
**3 verdict flips**. All reproduced exactly (`all_reproduced: true`).

### Exposure on IFEval's released data

Run against IFEval's own `input_response_data_gpt4_20231107_145030.jsonl` joined
to `input_data.jsonl` (541 prompts):

- **27 of 541** prompts carry the `number_paragraphs` instruction; all 27 GPT-4
  responses are present.
- **23 of 27** pass the upstream checker.
- **2** of those passing responses contain an inline (non-standalone) `***`, and
  in **both** the corrected count — splitting only on a standalone `***` line —
  flips the verdict from pass to fail. In each the inline `***` separators split
  a single block into exactly the required number of segments, so the checker
  credited paragraph breaks that a reader would not count.
- **0** responses triggered a doubled-divider interior-empty hard fail.

So on this data the hazard is **exercised in the false-pass direction** (2 of 541
published verdicts flip), while the false-fail directions (inline emphasis
over-count, doubled-divider hard fail) are reproduced synthetically but did not
occur in GPT-4's responses. The corrected count in `paragraph_checker.py` is a
measurement instrument for counting flips, not a proposed canonical replacement.

## Files

- `paragraph_checker.py` — verbatim reproduction of the upstream count and pass
  condition, plus a standalone-divider corrected count used only to measure flips.
- `cases.py` — the 7 pre-registered cases with hand-traced expected values.
- `test_paragraph_checker.py` — unit tests asserting each case.
- `job.py` — fetches IFEval's released data and writes `results.json`.
- `results.json` — frozen synthetic-corpus and exposure results.

## Limits, honestly

One checker, one dataset. The exposure is measured only on IFEval's single
released GPT-4 response file; a different model's responses would give different
blast radius. The two flips are false passes; the false-fail directions are shown
reachable but were not exercised here. The "corrected count" encodes one
reasonable reading of a paragraph (standalone divider lines); it is a yardstick
for this measurement, not a canonical fix. Prior art: the general markdown `***`
emphasis double-count is known in editors and linters, and
[open-instruct#1718](https://github.com/allenai/open-instruct/issues/1718) /
[NeMo-Skills#4624](https://github.com/NVIDIA/NeMo-Skills/issues/4624) fixed the
*opposite* `***` **under-count** in a derived `counting_composition` checker; no
prior report isolates this over-count / hard-fail pair for IFEval's
`number_paragraphs` checker or measures its verdict flips on IFEval's own data.

## Licence

Code is Apache-2.0. The corpus, results and this write-up are CC BY 4.0. The
transcribed upstream function keeps its own licence (Apache-2.0). Authored by AI
agents working in MV2's name (Munim, Inc.).
