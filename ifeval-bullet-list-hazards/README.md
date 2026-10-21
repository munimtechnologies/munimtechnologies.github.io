# ifeval-bullet-list-hazards

The 16th audit in the [eval-reliability-audits](../eval-reliability-audits)
catalogue. It isolates one mechanism in the scoring code behind a widely-used
LLM benchmark, reproduces it from the pinned upstream source, and ships a small
pre-registered corpus plus a measured blast radius on the benchmark's own data.
Work by AI agents working in MV2's name (Munim, Inc.), disclosed as AI-made.

**Target:** IFEval `BulletListChecker` — the instruction
`detectable_format:number_bullet_lists`, which requires a response to contain
*exactly* a given number of markdown bullet points.

## The mechanism

IFEval counts bullet points with two regular expressions over the response and
then passes only on **exact equality** with the required count:

```python
bullet_lists   = re.findall(r"^\s*\*[^\*].*$", value, flags=re.MULTILINE)
bullet_lists_2 = re.findall(r"^\s*-.*$",       value, flags=re.MULTILINE)
num_bullet_lists = len(bullet_lists) + len(bullet_lists_2)
following = (num_bullet_lists == self._num_bullets)   # EXACT equality
```

Two counting rules are looser than the markdown they are meant to detect, and
the exact-equality pass turns both into verdict flips in **both** directions:

1. **The dash pattern `^\s*-.*$` needs no space after the `-`.** CommonMark
   renders a list item only when the marker is followed by whitespace, so a
   negative number (`-5 degrees`), a horizontal rule (`---`) or a stray leading
   dash is *not* a bullet — yet the checker counts each as one.
2. **The asterisk pattern `^\s*\*[^\*].*$` counts a `*italic*` line as a
   bullet.** The leading `*` then a non-`*` character matches, though the line
   renders as italic text, not a list item. (It correctly skips `**bold**`,
   because `[^\*]` fails on the second `*`.)

Because the pass condition is `== num_bullets`, an over-count can make a
response with the *right* number of real bullets fail (false fail), or — when
the accidental lines happen to make the total land on the target — let a
response with too *few* real bullets pass (false pass).

## What was found

### Synthetic corpus (7 pre-registered cases)

Every count and verdict was hand-traced against the reproduced checker *before*
any real data was touched; the sealed job re-derives the aggregate and asserts
it equals the pre-registered target.

| id | text (abridged) | quota | real bullets | checker count | kind |
|----|-----------------|:-----:|:-----:|:-----:|------|
| B1 | `* first` / `* second` / `* third` | 3 | 3 | 3 | match |
| B2 | `- alpha` / `- beta` | 2 | 2 | 2 | match |
| B3 | two `- ` bullets + a line `-5 degrees overnight.` | 3 | 2 | 3 | **false pass** |
| B4 | four `* ` bullets with a `---` rule between | 4 | 4 | 5 | **false fail** |
| B5 | two `- ` bullets + a line `*note this is important*` | 2 | 2 | 3 | **false fail** |
| B6 | `Just a sentence with no bullets at all.` | 2 | 0 | 0 | correct neg |
| B7 | `**Summary**` heading + three `- ` bullets | 3 | 3 | 3 | match |

```
n_cases=7  n_match=3  n_correct_neg=1  n_false_pass=1  n_false_fail=2
n_flips=3  all_reproduced=true
```

B3 shows the false pass (a negative number lands the total on the quota); B4 and
B5 show the two false fails (a horizontal rule and an italic line inflate the
count past the quota). B7 is a control: the `**bold**` guard correctly keeps the
heading from being counted.

### Exposure on IFEval's own released data

Of IFEval's **541** prompts, **31** carry the
`detectable_format:number_bullet_lists` instruction. All 31 released GPT-4
responses are present and **27** pass the checker. Scanning each for a
counted-but-unrendered marker line (a dash or asterisk with no following space
and content):

```
responses with a counted-but-unrendered marker line : 0 of 31
responses whose count is inflated by such a line     : 0 of 31
verdict flips if the count is corrected              : 0 of 31
```

So on this data the hazard is **reachable but unexercised**: GPT-4's bullet
lists all use a space after the marker, so the blast radius here is bounded at
**0 of 31** (0 of 541 overall). This is a latent brittleness in the checker,
not a measured error in these published scores. `results.json` therefore ships
an empty `examples` list.

## Files

- `bullet_checker.py` — verbatim reproduction of `BulletListChecker`, plus a
  `corrected_count` that counts only markers followed by a space and content.
- `cases.py` — the 7 pre-registered cases with their hand-traced labels.
- `test_bullet_checker.py` — stdlib unit tests over the corpus.
- `job.py` — asserts the corpus matches the target, then measures exposure on
  IFEval's released GPT-4 responses.
- `results.json` — the frozen output of the sealed run.

Reproduce: `python -m unittest -v` then `python job.py`. The corpus assertion
needs no network; the exposure step fetches IFEval's `input_data.jsonl` and
`input_response_data_gpt4_20231107_145030.jsonl` from the public
google-research release.

## Limits, honestly

One checker, one dataset. The 7-case corpus is small and was hand-labelled by
AI agents working in MV2's name, not by an independent human reviewer.
`corrected_count` (marker + space + content) is one reasonable notion of a
rendered CommonMark list item, offered to measure flips — not proposed as the
canonical upstream fix. The exposure count covers only the released GPT-4
responses; a model that writes negative numbers, horizontal rules or
italic-emphasis lines inside a bullet-list answer would exercise the hazard.

## Licence

Code is Apache-2.0. The corpus, `results.json` and this write-up are CC BY 4.0.
The transcribed upstream function keeps its own Apache-2.0 licence
(google-research/google-research, `instruction_following_eval`). Authored by AI
agents working in MV2's name (Munim, Inc.).
