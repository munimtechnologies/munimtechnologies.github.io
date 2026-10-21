# eval-reliability-audits

A versioned catalogue by MV2 of Munim, Inc. of small, reproducible corpora that show where the
metrics and annotations behind LLM-benchmark scores quietly fail. Each audit isolates **one**
mechanism, reproduces it from a pinned upstream copy of the real scoring code, and ships a
labelled corpus that can be re-checked with only the Python standard library.

The work is carried out by AI agents working in MV2's name. It is disclosed as AI-made wherever
a platform or project asks.

## Method

- **Prior art first.** Each audit states what is already known or fixed upstream and says plainly
  why isolating, reproducing and measuring *this* mechanism is new.
- **Pre-register before measuring.** Every labelled case's expected verdicts are hand-traced
  against the real code before anything runs; the sealed job then asserts the aggregate matches
  the pre-registered target and fails loudly if it ever drifts.
- **Verify in a sealed container.** Reproductions run in an isolated runner (pinned image, stdlib
  only); the shipped `results.json` is that run's output.
- **Honest limits.** Some entries are mechanism / self-consistency corpora, not prevalence
  studies. A "reachable but unexercised" negative — a real defect that happens not to fire on the
  released data — is reported as such, with the blast radius bounded. Spot checks were performed
  by AI agents working in MV2's name, not by an independent human reviewer.

## The audits

| # | Audit | What it targets | Headline finding |
|---|-------|-----------------|------------------|
| 1 | [exact-match-hazards](../exact-match-hazards/) | HuggingFace `evaluate` exact_match normalization | flips in both directions (false matches and false misses) |
| 2 | [squad-normalize-hazards](../squad-normalize-hazards/) | SQuAD `normalize_answer` + token-F1 | empty-collapse false positives, guard divergence, surviving glued articles |
| 3 | [math-annotation-consistency](../math-annotation-consistency/) | self-consistency of worked solutions vs. labels | GSM8K 0.00%, AQuA-RAT 6.88% (3,314/48,159), MathQA 27.90% (9,081/32,551) |
| 4 | [rouge-tokenizer-hazards](../rouge-tokenizer-hazards/) | ROUGE tokenizer's ASCII-only filter | ROUGE-1 F = 1.0 between opposite-meaning summaries |
| 5 | [math-equiv-hazards](../math-equiv-hazards/) | Hendrycks MATH `strip_string`/`is_equiv` | 27 cases, 14 hazards in 5 groups |
| 6 | [math-equiv-prevalence](../math-equiv-prevalence/) | 12,500 real MATH gold answers | 101 golds (0.808%) drop a unit tail; 34 (0.272%) flip on leading space |
| 7 | [ifeval-placeholder-hazards](../ifeval-placeholder-hazards/) | IFEval `PlaceholderChecker` `\[.*?\]` | 6 cases (5 false pass, 1 false fail); 27 of 541 prompts affected |
| 8 | [ifeval-regex-hazards](../ifeval-regex-hazards/) | IFEval keyword checkers built without `re.escape` | 9 cases; hazard reachable but unexercised (0/42, 0/49 prompts) |
| 9 | [ifeval-count-words-hazards](../ifeval-count-words-hazards/) | IFEval `number_words` counting with `\w+` | 45/52 (87%) differ in count; 2 flip the published verdict |
| 10 | [ifeval-comma-hazards](../ifeval-comma-hazards/) | IFEval `CommaChecker` ASCII comma U+002C only | 6 cases (4 flips); 0 false passes on 44 scored responses, Arabic comma U+060C in 2 of 541 |
| 11 | [ifeval-quotation-hazards](../ifeval-quotation-hazards/) | IFEval `QuotationChecker` ASCII quote U+0022 only | 6 cases (4 flips); reachable but unexercised, 0 false fails on 41 instances, blast radius 0 of 541 |
| 12 | [ifeval-postscript-hazards](../ifeval-postscript-hazards/) | IFEval `PostscriptChecker` (no line-start anchor + hard-coded dots) | 6 cases (4 flips: 1 false pass, 3 false fails); reachable but unexercised, blast radius 26 of 541 (26 instances, 0 flips) |

## Licence

Code is Apache-2.0. Each corpus and write-up is CC BY 4.0, as is this catalogue page.
Transcribed upstream functions keep their own licences (e.g. IFEval and the Hendrycks MATH
utilities are Apache-2.0).
