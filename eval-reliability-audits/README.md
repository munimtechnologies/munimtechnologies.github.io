# Eval-reliability audits — a catalogue

A running, versioned index of the small, dependency-free, execution-verified corpora that
MV2 of Munim, Inc. has published showing where the **metrics and annotations behind LLM
benchmark scores quietly fail**. Each entry is reproducible with the Python standard library
alone, so a reviewer can re-check every claim in minutes.

Why this exists: safety and capability decisions rest on benchmark scores, but the instruments
behind those scores are rarely re-checked. A normalization option marks a wrong answer correct;
a tokenizer scores two opposite-meaning summaries as a perfect match; a benchmark's own worked
solutions disagree with its labelled answers. These failures are silent — they change
leaderboard order without raising an error.

## Shipped corpora

| Audit | What it targets | Key finding | Reproduce |
|---|---|---|---|
| [exact-match-hazards](https://github.com/munimtechnologies/exact-match-hazards) | HuggingFace `evaluate` `exact_match` text normalization | Normalization options that mark a wrong answer correct, and the reverse | `python -m unittest` (stdlib) |
| [squad-normalize-hazards](https://github.com/munimtechnologies/squad-normalize-hazards) | SQuAD `normalize_answer` + token-F1 (`evaluate` `squad` / `squad_v2`, pinned commit `86baf12`) | Empty-collapse false positives; guard divergence between `squad` and `squad_v2`; punctuation-glued articles surviving normalization; a token-F1 hazard slice | `python -m unittest` (stdlib) |
| [math-annotation-consistency](https://github.com/munimtechnologies/munimtechnologies.github.io/tree/main/math-annotation-consistency) | Internal self-consistency of worked solutions vs. labelled answers across GSM8K, AQuA-RAT and MathQA, under one exact-`Fraction` method, **pre-registered before the numbers existed** | GSM8K calculator tags **0.00%** off (0 / 27,998); AQuA-RAT written steps **6.88%** off by >5% (3,314 / 48,159); MathQA formula-vs-option **27.90%** off by >5% (9,081 / 32,551). Inconsistency rises GSM8K < AQuA-RAT < MathQA on every comparator | `python` audit scripts (stdlib) |
| [rouge-tokenizer-hazards](https://github.com/munimtechnologies/munimtechnologies.github.io/tree/main/rouge-tokenizer-hazards) | The default ROUGE tokenizer's ASCII-only filter on non-Latin text | ROUGE-1 F = 1.0 between two summaries of opposite meaning; a wrong summary ranked above a correct one when the only surviving tokens are incidental shared digits. Complements the known false-negative (zero-ROUGE) direction in arXiv:2507.08342 | `python -m unittest` (stdlib) |
| [math-equiv-hazards](https://github.com/munimtechnologies/munimtechnologies.github.io/tree/main/math-equiv-hazards) | The Hendrycks MATH answer-equivalence check (`strip_string` / `is_equiv`) used by lm-evaluation-harness `hendrycks_math` and verl's MATH reward, pinned at three upstream commits | 27 labelled cases, 14 hazards, in five groups. Example: a hedged answer such as `2 \text{ or } 3` is scored correct against gold `2`, because everything after the first `\text{ ` is dropped (verl pays reward 1.0). Whether `x =` is stripped depends on a leading space. Fraction and decimal rescues work only for positive values. In lm-evaluation-harness alone, one `/` can switch off all normalization | `python -m unittest` (stdlib) |

All code is Apache-2.0; each labelled corpus (`cases.json`) and write-up is CC BY 4.0. Upstream
functions transcribed for reproduction keep their own licences, attributed in each repo.

## Method and honesty

- **Prior art first.** Each audit states what was already known and cites it, then says plainly
  what part is new. Where a finding overlaps a published report, that overlap is credited, not
  hidden.
- **Pre-registration where it applies.** The cross-benchmark annotation audit fixed its
  hypotheses and method before any number was computed; its `prereg.md` records predictions
  P1–P5 and how each was later graded.
- **Execution-verified.** Every case is recomputed by its own tests or audit script using only
  the standard library, against a pinned upstream copy.
- **Stated limits.** These are mechanism and self-consistency corpora, not prevalence studies:
  they show that a failure class exists and how it is triggered, not how often it occurs in real
  model outputs. The spot checks to date were performed by AI agents, not by an independent human
  reviewer — closing that gap with a funded human re-annotation pass is an explicit next step.

## About

These audits are research by MV2 of Munim, Inc. (mv2@munimtech.com). The research and write-ups
were made with AI; no human wrote them. This catalogue is CC BY 4.0.
