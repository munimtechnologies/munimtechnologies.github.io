# ifeval-section-hazards

The 18th audit in the [eval-reliability-audits](../eval-reliability-audits/)
catalogue by MV2 of Munim, Inc. It isolates one defect in IFEval's
`SectionChecker` (the `detectable_format:multiple_sections` instruction),
reproduces it byte-faithfully from the pinned upstream scoring code, and measures
how often it changes a published pass/fail verdict on IFEval's own released data.

This audit is carried out by AI agents working in MV2's name and is disclosed as
AI-made.

## The mechanism

IFEval checks that a response contains **at least** `num_sections` sections, each
marked by a `section_spliter` keyword followed by a number (e.g. `Section 1`). The
upstream `check_following` does, verbatim:

```python
section_splitter_patten = r"\s?" + self._section_spliter + r"\s?\d+\s?"
sections = re.split(section_splitter_patten, value)   # no re.escape,
num_sections = len(sections) - 1                      # NOT line-anchored
return num_sections >= self._num_sections             # >= (minimum)
```

The split pattern is built with no `re.escape`, is not line-anchored, and matches
the keyword case-sensitively anywhere in the text. Under the `>=` (minimum) pass
test, two things flip the verdict in **both** directions:

1. **False pass.** An inline cross-reference (`see Section 3 below`) or even a
   substring inside a word (`subSection3`, because `Section` matches anywhere) is
   counted as a section boundary. These spurious matches can push the count past
   the quota, passing a response that has too few real sections.
2. **False fail.** The pattern requires a digit (`\d+`) after the keyword, so a
   response that correctly marks its sections with spelled-out numbers
   (`Section One`, `Section Two`, `Section Three`) matches nothing — `num=0` — and
   `0 >= num_sections` fails a perfectly good answer.

## What was found

### Synthetic corpus

Seven cases (all with `section_spliter = "Section"`), each hand-traced against the
reproduced checker **before** any real data was touched, then re-derived and
asserted in a sealed container.

| id | what it exercises | ground truth | checker | verdict |
|----|-------------------|--------------|---------|---------|
| S1 | three digit-marked sections | 3 | pass | match |
| S2 | two digit-marked sections | 2 | pass | match |
| S3 | 2 real sections + inline `Section 3` cross-ref | 2 | pass (num=3) | **false pass** |
| S4 | 2 real sections + `subSection3` substring | 2 | pass (num=3) | **false pass** |
| S5 | three sections marked `Section One/Two/Three` | 3 | fail (num=0) | **false fail** |
| S6 | four digit-marked sections | 4 | pass | match |
| S7 | no section markers | 0 | fail | correct negative |

Totals: 7 cases, 3 matches, 1 correct negative, 2 false passes, 1 false fail —
**3 verdict flips**. All reproduced exactly (`all_reproduced: true`).

### Exposure on IFEval's released data

Run against IFEval's own `input_response_data_gpt4_20231107_145030.jsonl` joined
to `input_data.jsonl` (541 prompts):

- **14 of 541** prompts carry the `multiple_sections` instruction; all 14 GPT-4
  responses are present.
- **13 of 14** pass the upstream checker.
- **3** of those passing responses contain an inline or in-word match of the
  section keyword, and in **all 3** the corrected count — only a line that starts
  with the keyword followed by a digit or a spelled-out number — flips the verdict
  from pass to fail. In one, the required splitter was `SECTION`, the quota was 2,
  the upstream count was 5, and the corrected count was **0**: the checker passed
  a response with no real section headers at all. (The splitter keyword is taken
  from each prompt's own arguments; one prompt used `Audience` rather than
  `Section`.)
- **0** evaluation errors.

So on this data the hazard is **exercised in the false-pass direction** (3 of 541
published verdicts flip), while the false-fail direction (spelled-out section
numbers) is reproduced synthetically but did not occur in GPT-4's responses. The
corrected count in `section_checker.py` is a measurement instrument for counting
flips, not a proposed canonical replacement.

## Files

- `section_checker.py` — verbatim reproduction of the upstream count and pass
  condition, plus a line-start corrected count used only to measure flips.
- `cases.py` — the 7 pre-registered cases with hand-traced expected values.
- `test_section_checker.py` — unit tests asserting each case.
- `job.py` — fetches IFEval's released data and writes `results.json`.
- `results.json` — frozen synthetic-corpus and exposure results.

## Limits, honestly

One checker, one dataset. The exposure is measured only on IFEval's single
released GPT-4 response file; a different model's responses would give different
blast radius. All three flips are false passes; the false-fail direction is shown
reachable but was not exercised here. The "corrected count" encodes one reasonable
reading of a section header (line-start keyword + digit or number word); it is a
yardstick for this measurement, not a canonical fix. Prior art: `re.escape`-less
and unanchored regexes are a known class of bug generally, and this catalogue's
own [ifeval-regex-hazards](../ifeval-regex-hazards/) covers IFEval keyword
checkers lacking `re.escape`; no prior report isolates the inline/substring false
pass and the spelled-out-number false fail for IFEval's `multiple_sections`
checker or measures its verdict flips on IFEval's own data.

## Licence

Code is Apache-2.0. The corpus, results and this write-up are CC BY 4.0. The
transcribed upstream function keeps its own licence (Apache-2.0). Authored by AI
agents working in MV2's name (Munim, Inc.).
