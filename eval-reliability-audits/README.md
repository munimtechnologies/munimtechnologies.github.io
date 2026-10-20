# Eval-reliability audits — a catalogue

A running, versioned index of the small, dependency-free, execution-verified
corpora that MV2 of Munim, Inc. publishes where the metrics and annotations
behind LLM benchmark scores fail quietly. Every corpus here reproduces with
nothing but the Python standard library.

Why this exists: a benchmark's instruments — its scorers, normalizers and gold
annotations — are rarely re-checked once published, so when one of them is wrong
the error is silent and propagates into every score built on it. Each audit
below isolates one such instrument, reproduces its behaviour against a pinned
upstream copy, and states plainly how often (if at all) the failure touches real
benchmark data.

This work was produced with AI agents working in MV2's name.

## Shipped corpora

| Audit | What it targets | Key finding | Reproduce |
|---|---|---|---|
| [exact-match-hazards](https://github.com/munimtechnologies/exact-match-hazards) | HuggingFace `evaluate` `exact_match` normalization | normalization options that flip wrong answers to correct and vice versa | `python -m unittest` (stdlib) |
| [squad-normalize-hazards](https://github.com/munimtechnologies/squad-normalize-hazards) | SQuAD `normalize_answer` + token-F1 (commit `86baf12`) | empty-collapse false positives, guard divergence, punctuation-glued articles | `python -m unittest` (stdlib) |
| [math-annotation-consistency](https://github.com/munimtechnologies/munimtechnologies.github.io/tree/main/math-annotation-consistency) | self-consistency of GSM8K / AQuA-RAT / MathQA gold answers | GSM8K calculator tags 0.00% off, AQuA-RAT 6.88%, MathQA 27.90% | `python` audit scripts (stdlib) |
| [rouge-tokenizer-hazards](https://github.com/munimtechnologies/munimtechnologies.github.io/tree/main/rouge-tokenizer-hazards) | ROUGE tokenizer's ASCII-only filter | ROUGE-1 F = 1.0 between two summaries of opposite meaning | `python -m unittest` (stdlib) |
| [math-equiv-hazards](https://github.com/munimtechnologies/munimtechnologies.github.io/tree/main/math-equiv-hazards) | Hendrycks MATH equivalence check (three commits) | 27 labelled cases, 14 hazards in five groups (e.g. hedged answers scored correct) | `python -m unittest` (stdlib) |
| [math-equiv-prevalence](https://github.com/munimtechnologies/munimtechnologies.github.io/tree/main/math-equiv-prevalence) | exposure of all 12,500 Hendrycks MATH gold answers | all 6 pre-registered predictions hit; 101 golds drop a unit tail | `python` audit + stdlib tests |
| [ifeval-placeholder-hazards](https://github.com/munimtechnologies/munimtechnologies.github.io/tree/main/ifeval-placeholder-hazards) | IFEval `PlaceholderChecker` (pinned master 2026-10-20) | 6 pre-registered cases, all reproduced (5 false PASS, 1 false FAIL) | `python -m unittest` (stdlib) |
| [ifeval-regex-hazards](https://github.com/munimtechnologies/munimtechnologies.github.io/tree/main/ifeval-regex-hazards) | IFEval `keywords:frequency` + `keywords:forbidden_words` (regex built without `re.escape`) | 9 cases reproduced (2 crash, 2 false pass, 5 false fail); 0 of 541 official prompts exercise it | `python -m unittest` (stdlib) |

All code is Apache-2.0; each corpus and write-up is CC BY 4.0, except
transcribed upstream functions, which keep their own licences.

## Method and honesty
- **Prior art first.** Each audit searches existing issues, papers and repos and
  says why its finding is new before claiming it.
- **Pre-registration where it applies.** Predictions are fixed in writing before
  any number is read from data.
- **Execution-verified.** Every case is run against a pinned copy of the upstream
  code on a sealed runner; the sealed output ships with the write-up.
- **Stated limits.** Most entries show that a failure class exists, not how often
  it bites real benchmark data — and say so plainly. Honest negative and partial
  results are kept.

## About
Contact mv2@munimtech.com. The research and write-ups here were produced with AI
agents working in MV2's name; spot checks to date were done by those agents
rather than an independent human reviewer, which remains a next step. This
catalogue is CC BY 4.0.
