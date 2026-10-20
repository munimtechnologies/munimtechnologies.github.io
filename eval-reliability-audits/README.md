# Eval-reliability audits — a catalogue

A versioned catalogue, by MV2 of Munim, Inc., of small reproducible corpora that
show where the metrics and annotations behind LLM benchmark scores quietly fail.
Each audit isolates one mechanism, reproduces it from a pinned upstream copy, and
ships a labelled corpus that can be checked with only the Python standard library.

The method for each entry: state the prior art, pre-register the predictions,
verify in a sealed container, and declare the limits honestly. Some entries are
mechanism / self-consistency corpora rather than prevalence studies, and that is
stated per row. Spot checks were performed by AI agents working in MV2's name,
not by an independent human reviewer.

| Audit | What it targets | Headline number |
| --- | --- | --- |
| [exact-match-hazards](https://github.com/munimtechnologies/exact-match-hazards) | HuggingFace `evaluate` exact_match normalization | flips in both directions (false matches and false misses) |
| [squad-normalize-hazards](https://github.com/munimtechnologies/squad-normalize-hazards) | SQuAD `normalize_answer` + token-F1 | empty-collapse false positives, guard divergence, surviving glued articles |
| [math-annotation-consistency](https://github.com/munimtechnologies/munimtechnologies.github.io/tree/main/math-annotation-consistency) | self-consistency of worked solutions vs. labels | GSM8K 0.00%, AQuA-RAT 6.88% (3,314/48,159), MathQA 27.90% (9,081/32,551) |
| [rouge-tokenizer-hazards](https://github.com/munimtechnologies/munimtechnologies.github.io/tree/main/rouge-tokenizer-hazards) | ROUGE tokenizer's ASCII-only filter | ROUGE-1 F = 1.0 between opposite-meaning summaries |
| [math-equiv-hazards](https://github.com/munimtechnologies/munimtechnologies.github.io/tree/main/math-equiv-hazards) | Hendrycks MATH `strip_string`/`is_equiv` | 27 cases, 14 hazards in 5 groups |
| [math-equiv-prevalence](https://github.com/munimtechnologies/munimtechnologies.github.io/tree/main/math-equiv-prevalence) | 12,500 real MATH gold answers | 101 golds (0.808%) drop a unit tail; 34 (0.272%) flip on leading space |
| [ifeval-placeholder-hazards](https://github.com/munimtechnologies/munimtechnologies.github.io/tree/main/ifeval-placeholder-hazards) | IFEval `PlaceholderChecker` `\[.*?\]` | 6 cases (5 false pass, 1 false fail); 27 of 541 prompts affected |
| [ifeval-regex-hazards](https://github.com/munimtechnologies/munimtechnologies.github.io/tree/main/ifeval-regex-hazards) | IFEval keyword checkers built without `re.escape` | 9 cases; hazard reachable but unexercised (0/42, 0/49 prompts) |
| [ifeval-count-words-hazards](https://github.com/munimtechnologies/munimtechnologies.github.io/tree/main/ifeval-count-words-hazards) | IFEval `number_words` counting with `\w+` | 45/52 (87%) differ in count; 2 flip the published verdict |
| [ifeval-comma-hazards](https://github.com/munimtechnologies/munimtechnologies.github.io/tree/main/ifeval-comma-hazards) | IFEval `CommaChecker` ASCII comma U+002C only | 6 cases (4 flips); 0 false passes on 44 scored responses, Arabic comma U+060C in 2 of 541 |
| [ifeval-quotation-hazards](https://github.com/munimtechnologies/munimtechnologies.github.io/tree/main/ifeval-quotation-hazards) | IFEval `QuotationChecker` ASCII quote U+0022 only | 6 cases (4 flips); 0 false fails on 41 official instances, blast radius 0 of 541 |

## Licensing

Code is Apache-2.0; each corpus and write-up is CC BY 4.0. Transcribed upstream
functions keep their own licences, stated per audit. This catalogue page itself
is CC BY 4.0.
