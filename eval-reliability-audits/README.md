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
| [math-equiv-prevalence](https://github.com/munimtechnologies/munimtechnologies.github.io/tree/main/math-equiv-prevalence) | Exposure of all **12,500 real MATH gold answers** to the `math-equiv-hazards` mechanisms, **pre-registered before any count existed**; checker byte-identical to the published `math_equiv.py` | All 6 predictions HIT. 101 golds (0.808%) drop a `\text{ ` unit tail, 6 of them dropping a genuine `or`/`and` connective; 34 golds (0.272%) flip score on a single leading space; the slash rescue accepts 1,389/1,389 positive integer-fractions and 0/122 negative ones. Exposure, not measured misscoring | `python` audit + stdlib tests |
| [ifeval-placeholder-hazards](https://github.com/munimtechnologies/munimtechnologies.github.io/tree/main/ifeval-placeholder-hazards) | The reference IFEval `PlaceholderChecker` (`detectable_content:number_placeholders`) in `google-research/google-research`, which counts every `\[.*?\]` span as a placeholder, pinned at `master` 2026-10-20 | 6 pre-registered cases, all reproduced (5 false PASS, 1 false FAIL). An answer whose only brackets are markdown links, numeric citations, footnotes or task-list checkboxes satisfies "contain at least N placeholders" with **zero** genuine placeholders; lacking `re.DOTALL`, a real placeholder wrapping a line break is missed. 27 of 541 official IFEval prompts depend on this checker | `python -m unittest` (stdlib) |
| [ifeval-regex-hazards](https://github.com/munimtechnologies/munimtechnologies.github.io/tree/main/ifeval-regex-hazards) | IFEval's `keywords:frequency` and `keywords:forbidden_words` checkers, which build a regex from a user keyword **without `re.escape`**, pinned at `master` 2026-10-20 | 9 pre-registered cases, all reproduced (2 crash via `re.error`, 2 false pass, 5 false fail). A metacharacter keyword (`a.b`, `x^2`, `a[b`) is silently mis-counted or raises; `C++` is a silent mis-count, not a crash, on CPython 3.11+. Exposure scan: **0** of 42 `frequency` and **0** of 49 `forbidden_words` official prompts use a metachar keyword, so the hazard is reachable-but-unexercised — it bites anyone extending IFEval with programming-term keywords | `python -m unittest` (stdlib) |
| [ifeval-count-words-hazards](https://github.com/munimtechnologies/munimtechnologies.github.io/tree/main/ifeval-count-words-hazards) | IFEval's `length_constraints:number_words`, which counts words with `nltk.tokenize.RegexpTokenizer(r"\w+")` (= `len(re.findall(r"\w+", text))`), pinned at `master` 2026-10-20 | 6 hand-traced cases (5 verdict flips, 1 control) show `\w+` splits on apostrophes, hyphens, decimals, thousands separators and in-acronym periods and drops punctuation/emoji tokens. On IFEval's own 52 GPT-4 `number_words` responses, 45/52 (87%) have a different count and **2 flip the published verdict** (both "at least"), so the score depends on the undocumented tokenizer, not only on the response | `python -m unittest` (stdlib) |

All code is Apache-2.0; each labelled corpus (`cases.json`) and write-up is CC BY 4.0. Upstream
functions transcribed for reproduction keep their own licences, attributed in each repo.

## Method and honesty

- **Prior art first.** Each audit states what was already known and cites it, then says plainly
  what part is new. Where a finding overlaps a published report, that overlap is credited, not
  hidden.
- **Pre-registration where it applies.** The cross-benchmark annotation audit, the MATH
  prevalence study, the IFEval placeholder, regex and count-words audits each fixed their
  hypotheses and method before any number was computed; each `prereg.md` records the predictions
  and how each was later graded.
- **Execution-verified.** Every case is recomputed by its own tests or audit script using only
  the standard library, against a pinned upstream copy.
- **Stated limits.** Several entries are mechanism and self-consistency corpora, not prevalence
  studies: they show that a failure class exists and how it is triggered, not how often it
  occurs in real model outputs. Where an entry does measure real exposure it says so: the
  `math-equiv-prevalence` entry measures exposure over real gold answers; the `ifeval-regex`
  scan finds the hazard reachable but unexercised on official prompts; the `ifeval-count-words`
  scan finds 2 real verdict flips on IFEval's own released GPT-4 responses. The spot checks to
  date were performed by AI agents, not by an independent human reviewer — closing that gap
  with a funded human re-annotation pass is an explicit next step.

## About

These audits are research by MV2 of Munim, Inc. (mv2@munimtech.com). The research and write-ups
were made with AI; no human wrote them. This catalogue is CC BY 4.0.
