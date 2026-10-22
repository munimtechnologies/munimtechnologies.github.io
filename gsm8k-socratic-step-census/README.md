# gsm8k-socratic-step-census

The 25th audit in [eval-reliability-audits](../eval-reliability-audits/).

## The question

GSM8K (Cobbe et al. 2021) ships every training and test problem twice: once in
the plain `train.jsonl` / `test.jsonl` files and once in the socratic
`train_socratic.jsonl` / `test_socratic.jsonl` files, where each reasoning step
is preceded by a sub-question of the form `<sub-question>? ** <step>`.

Audit 24 ([gsm8k-socratic-answer-census](../gsm8k-socratic-answer-census/)) showed
that the two formats agree on the final `####` answer for all 8,792 questions. This
audit goes one level deeper and asks whether the **bodies** agree: once the
sub-question prefix is stripped from each socratic line, are the socratic step lists
identical to the main step lists, and does every `<<expr=result>>` calculator
annotation survive the rewrite unchanged? Audit 19
([gsm8k-calculator-annotation-census](../gsm8k-calculator-annotation-census/))
verified the calculator annotations on the **main** files only; this audit re-runs
the very same arithmetic checker, verbatim, on the **socratic** files and compares.

Prior art (searched 2026-10-22): the HuggingFace `gsm8k` card and the upstream
`openai/grade-school-math` README state that the socratic split carries the same
problems with sub-questions added, but no published work does a line-level census
confirming that the socratic step bodies and calculator annotations are a lossless
reformatting of the main solutions, nor flags where that reformatting is irregular.

- **Pairing.** Rows are paired by exact question text; a question present in only
  one of the two files is counted as `only_in_main` / `only_in_socratic`.
- **Steps.** The lines before the last `####` are taken; each socratic line loses
  the text up to and including its first ` ** `; the two line lists are `identical`
  iff they are equal after that strip.
- **Annotations.** Every `<<expr=result>>` in the whole answer is extracted in
  order by `calc_eval.find_annotations` (transcribed verbatim from audit 19) and
  classified by `classify_annotation`; a pair is annotation-`identical` iff the two
  sequences are equal, and each annotation is re-checked for arithmetic.
- **Fixture.** A 3-pair synthetic corpus with one `only_in_main`, one
  `only_in_socratic`, one dangling sub-question and one deliberately altered
  socratic annotation is hand-traced and frozen before any real data is read.

## What was found

The socratic rewrite is a faithful, arithmetic-preserving copy of the main
solutions — with six reproducible exceptions.

| Measure | train | test | combined |
| --- | --- | --- | --- |
| pairs (same question in both files) | 7,473 | 1,319 | 8,792 |
| only in main / only in socratic | 0 / 0 | 0 / 0 | 0 / 0 |
| socratic step lines | 26,724 | 4,821 | 31,545 |
| &nbsp;&nbsp;carrying the ` ** ` separator | 26,720 | 4,819 | 31,539 |
| step lists identical (after prefix strip) | 7,469 | 1,317 | 8,786 |
| annotation sequences identical | 7,473 | 1,319 | 8,792 |
| `<<expr=result>>` annotations | 23,716 | 4,282 | 27,998 |
| &nbsp;&nbsp;match / mismatch | 23,714 / 0 | 4,281 / 0 | 27,995 / 0 |
| &nbsp;&nbsp;unparseable expr / result | 2 / 0 | 0 / 1 | 2 / 1 |

Every one of the 8,792 paired questions carries an **identical** ordered sequence
of calculator annotations in its main and socratic solutions, and re-running audit
19's arithmetic checker on the socratic files reproduces its class counts exactly:
27,995 verified-correct, 0 miscomputations, and the same 3 annotations (2 with an
unparseable expression, 1 with an unparseable result) that audit 19 already flagged
on the main files. The socratic reformatting introduces no calculator error.

The step bodies match in 8,786 of 8,792 pairs. The remaining **6** pairs (4 in
train, 2 in test) differ in one identical way: a socratic line is a bare
sub-question ending in ` **` with no step text after the separator, and that step's
answer sits on the **next** line with no sub-question of its own — the only 6
socratic step lines in the whole corpus (of 31,545) that lack the ` ** ` separator.
So those 6 solutions are not a clean one-to-one insertion of sub-questions; the
sub-question and its answer are split across two lines instead of joined into one.

Pre-registered predictions (frozen before reading real data), all held:

- **P1** — 8,792 paired questions: **held** (8,792).
- **P2** — at least 99% of pairs annotation-identical: **held** (100.0%).
- **P3** — zero socratic annotation miscomputations: **held** (0).
- **P4** — at least 99% of socratic step lines carry ` ** `: **held** (99.981%).

Reproducibility cross-check against audit 19 (frozen main-file annotation classes
`{match: 27995, rounded: 0, mismatch: 0, unparseable_expr: 2, unparseable_result: 1}`):
the combined main-file classes measured here reproduce those exactly — `ok: true`.

The six split pairs, from `results.json` (`step_diff_examples`), e.g.:

> *"In 10 years, Terry will be 4 times the age that Nora is currently. If Nora is
> currently 10 years old, how old is Terry now?"*
>
> main steps: `Terry will be 4*10=<<4*10=40>>40 years old in 10 years` /
> `Currently, Terry is 40-10 = <<40-10=30>>30 years old.`
>
> socratic steps: `Terry will be 4*10=<<4*10=40>>40 years old in 10 years` /
> `How old is Terry now? **` / `Currently, Terry is 40-10 = <<40-10=30>>30 years old.`

The other five are the plane New-York-to-Miami problem, the ice-cream-truck
problem, Kirt's salary, Mark's apartment, and Johnny's dad at the races; in each the
dangling sub-question is `How many hours ... ?`, `How many children ... ?`,
`How much are his total earnings ... ?`, `How many square feet ... ?` and
`How much did he lose on average ... ?` respectively.

## Files

- `gsm8k_socratic_steps.py`: `reasoning_lines()`, `strip_subquestion()`,
  `annotation_classes()`, `census()` and `public_summary()`, standard library only.
- `calc_eval.py`: `find_annotations()` and `classify_annotation()`, transcribed
  verbatim from audit 19.
- `cases.py`: the hand-traced 3-pair synthetic corpus and its frozen target counts.
- `test_gsm8k_socratic_steps.py`: 8 unit tests (run green in the sealed container).
- `job.py`: downloads the four GSM8K files, asserts the fixture, measures the real
  files, guards `rows > 0`, records the predictions, and freezes `results.json`.
- `results.json`: the full frozen measurement, including every split pair.

## Limits

One checker, one dataset. "Identical" is measured after stripping each socratic
line up to and including its first ` ** `; a socratic line whose own step text
happens to contain ` ** ` would be truncated, though none in GSM8K do. The
annotation comparison is by exact `<<expr=result>>` string sequence; the three
unparseable annotations are counted and reported, not silently dropped. The audit
confirms the socratic files are a faithful reformatting of the main files; it does
not re-derive whether the underlying solutions are themselves correct.

## Licence

Code is Apache-2.0. The synthetic corpus, results and this write-up are CC BY 4.0.
GSM8K retains its own licence (MIT, per `openai/grade-school-math`), and the
transcribed `calc_eval.py` functions keep that upstream licence. Authored by AI
agents working in MV2's name (Munim, Inc.).
