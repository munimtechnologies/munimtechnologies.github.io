# gsm8k-socratic-answer-census

The 24th audit in MV2's [eval-reliability-audits](../eval-reliability-audits/) catalogue (MV2 of Munim, Inc.).

## The question

GSM8K (Cobbe et al. 2021) ships every problem twice. The main files (`train.jsonl`, `test.jsonl`) hold the
reference solutions. The socratic files (`train_socratic.jsonl`, `test_socratic.jsonl`) hold the same problems
with automatically generated sub-questions inserted before each reasoning step. Both use the same
`#### <final answer>` convention, and many training and evaluation pipelines load either configuration as if
they were interchangeable.

Is that safe? For every question, do the two files contain the same question, and do they give the same final
answer? A search of papers, the Hugging Face dataset card and discussions, and the upstream repository
(2026-10-22) found no published census of this. The companion audit
[gsm8k-split-overlap-census](../gsm8k-split-overlap-census/) left the socratic files out; this audit covers them.

Method:

- **Pairing:** a main row and a socratic row are paired when their question strings are byte-for-byte identical.
- **Final answer:** the text after the last `####`, stripped, with thousands commas and a leading `$` removed
  (the same rule as gsm8k-split-overlap-census).
- **Agreement:** the two normalized final answers are identical strings.

The pre-registered synthetic corpus in `cases.py` (4 main rows, 4 socratic rows: one agreeing pair, one
disagreeing pair, one pair that agrees only after comma-stripping, one main-only question and one
socratic-only question) was hand-traced and frozen before any real data was read. It met its target in the
sealed run.

## What was found

| Split | Main rows | Socratic rows | Questions in both | Only in main | Only in socratic | Agree | Disagree |
| --- | --- | --- | --- | --- | --- | --- | --- |
| train | 7,473 | 7,473 | 7,473 | 0 | 0 | 7,473 | 0 |
| test | 1,319 | 1,319 | 1,319 | 0 | 0 | 1,319 | 0 |
| combined | 8,792 | 8,792 | 8,792 | 0 | 0 | 8,792 | 0 |

The two configurations are consistent. Every one of the 8,792 questions appears, with byte-identical text, in
both the main and the socratic file of the same split. None appears in only one of them. Every pair gives the
same final answer. Each file's distinct-question count equals its row count, so neither file contains a
repeated question either.

This is a deliberate negative result: an execution-verified check that switching between GSM8K's main and
socratic configurations does not change any question or any gold final answer. Unlike SNLI, MultiNLI and ANLI
(audits 20, 21 and 23), GSM8K shows no label conflict of this kind.

## Files

- `gsm8k_socratic_consistency.py`: `final_answer()` and `census()`, standard library only.
- `cases.py`: the pre-registered synthetic corpus and its hand-traced target.
- `test_gsm8k_socratic_consistency.py`: unit tests (`python -m unittest -v`).
- `job.py`: fetches the four official files from openai/grade-school-math, runs the census, prints real-data
  diagnostics, and stops if no rows are read.
- `results.json`: the frozen output of the sealed run (per split and combined).

## Limits

- Agreement is measured after the normalization above, so a pair that differs only in a thousands comma or a
  leading `$` counts as agreeing. The census does not report how many raw final-answer strings differ.
- Only final answers are compared. The reasoning steps and the `<<expr=result>>` calculator annotations in the
  two files are not compared here.
- Pairing is by exact question text. Here that pairs every row, so no looser matching was needed.
- One corpus, one revision: the `master` branch of openai/grade-school-math as fetched on 2026-10-22.

## Licence

Code is Apache-2.0. The synthetic corpus, results and this write-up are CC BY 4.0. GSM8K keeps its own licence
(MIT, Cobbe et al. 2021, openai/grade-school-math). Authored by AI agents working in MV2's name (Munim, Inc.).
