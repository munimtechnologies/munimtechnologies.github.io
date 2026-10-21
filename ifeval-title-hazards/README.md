# ifeval-title-hazards

Part of the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of
Munim, Inc. One small, reproducible corpus that isolates a single mechanism by which an
LLM-benchmark checker can score a response wrongly, reproduced from a pinned upstream copy
and checkable with only the Python standard library.

**Target:** IFEval's `detectable_format:title` checker (`TitleChecker`, from
`google-research/instruction_following_eval/instructions.py`; Apache-2.0, keeps its own
licence).

**Headline:** 5 hand-traced cases, 3 false passes; on IFEval's own released data the hazard is
**reachable but unexercised — blast radius 0 of 541** (37 prompts require a title, all 37 GPT-4
responses carry a genuine `<<…>>` title, 0 false passes).

## The mechanism

`TitleChecker.check_following` accepts a response as containing a title with:

```python
titles = re.findall(r"<<[^\n]+>>", value)
for title in titles:
    if title.lstrip("<").rstrip(">").strip():
        return True
return False
```

The marker is any `<<…>>` run on a single line with non-empty content. But `<<` and `>>` are
also ordinary programming syntax — C/C++/Python **left-shift / right-shift** operators, C++
**stream** insertion/extraction (`std::cout << x >> y`), and shell **heredoc / append-redirect**
(`cat <<EOF >> out`). Any response that puts a shift, stream or heredoc expression on one line
contains a `<<…>>` substring and is credited with a "title" it never wrote — a **false pass**.

A companion `classify` compares the checker's verdict with whether the text actually presents a
deliberate title, so each case is labelled `match` / `correct_neg` / `false_pass` /
`false_fail`.

## What was found

### Synthetic corpus (5 pre-registered cases)

| id | text (abridged) | checker | real title? | kind |
|----|-----------------|---------|-------------|------|
| T1-true-title | `<<A Poem of Joy>>` then a poem | pass | yes | match |
| T2-no-title | plain prose, no marker | fail | no | correct neg |
| T3-shift-operators | `result = a << 2 >> 1` | pass | no | false pass |
| T4-heredoc-redirect | `cat <<EOF >> output.txt` | pass | no | false pass |
| T5-cpp-stream | `std::cout << value >> rest` | pass | no | false pass |

`n_cases = 5, n_checker_true = 4, n_flips = 3, n_false_pass = 3, n_false_fail = 0,
all_reproduced = true`. Each verdict was hand-traced against the regex before any code ran; the
sealed job re-derives them and asserts the aggregate matches this pre-registered target.

### Exposure on IFEval's own released data

Among IFEval's 541 prompts, **37** carry a `detectable_format:title` instruction. Each was
joined by exact prompt text to its released GPT-4 response
(`input_response_data_gpt4_20231107_145030.jsonl`); all 37 responses are present, all 37 pass
the checker, and in all 37 the matched `<<…>>` marker is a genuine, deliberate title
(`<<Resignation Notice>>`, `<<Kotlin vs Java>>`, `<<When the Skies Wept Over Donnell>>`, …).
No response uses a shift / stream / heredoc expression that would trip the marker. So:

```
n_prompts_require_title = 37   checker pass = 37   with a real title marker = 37
false passes observed   = 0
```

This is an honest **reachable-but-unexercised** negative, like `ifeval-regex-hazards`,
`ifeval-quotation-hazards` and `ifeval-postscript-hazards`: the defect is real and
demonstrable on synthetic inputs, but on this English GPT-4 set no scored response happens to
contain `<<…>>` for any non-title reason. The blast radius — scored responses that could flip
if a model emitted code with a shift/stream/heredoc on one line — is bounded at 0 of 541 here;
the risk rises for coding or shell-heavy prompts, which this released set does not stress. The
`marker_examples` in `results.json` are shipped so the all-genuine finding can be re-checked by
hand rather than taken on trust.

## Files

- `title_checker.py` — `check_title` (IFEval's `TitleChecker`, transcribed verbatim) and
  `classify`. Apache-2.0.
- `cases.py` — the 5 pre-registered labelled cases and the target. CC BY 4.0.
- `test_title_checker.py` — stdlib `unittest`; each case must reproduce its verdict and the
  aggregate must match the target.
- `job.py` — the sealed compute job: asserts the corpus, then measures official exposure and
  keeps every title-marker example for manual inspection.
- `results.json` — the sealed run's output (corpus + exposure + marker examples).

Reproduce: `python -m unittest -v` then `python job.py` (the exposure step needs IFEval's
`input_data.jsonl` and the GPT-4 response file in `/data`; the corpus assertion needs no data).

## Limits, honestly

One checker, one dataset. The synthetic corpus is hand-labelled and small; its verdicts were
traced by AI agents working in MV2's name, not by an independent human reviewer. Whether a
`<<…>>` marker on real data is a genuine title or a false pass was decided by reading each of
the 37 markers (all genuine); the classification of real responses is a manual judgement, not
an automatic label. The exposure count is exact for IFEval's released GPT-4 responses and says
nothing about other models, coding-heavy prompts, or private test sets.

## Licence

Code is Apache-2.0. The labelled corpus (`cases.py`), `results.json` and this write-up are
CC BY 4.0. The transcribed upstream function keeps its own Apache-2.0 licence. Work by AI
agents working in MV2's name (Munim, Inc.).
