# Eval-reliability audits — a catalogue

A versioned catalogue, by MV2 of Munim, Inc., of small, reproducible corpora that
show where the metrics and annotations behind LLM benchmark scores silently fail.
Each audit isolates one scoring or annotation mechanism, reproduces it faithfully
from a pinned upstream copy, and ships a labelled corpus that can be re-checked
using only the Python standard library.

Method, applied throughout: state the prior art; pre-register predictions before
reading any number where a prevalence claim is involved; verify by execution in a
sealed container; and declare limits plainly. Some entries are mechanism or
self-consistency corpora rather than prevalence studies, and that is labelled as
such. Spot checks were performed by AI agents working in MV2's name, not by an
independent human reviewer.

| Audit | What it targets | Headline number |
| --- | --- | --- |
| [exact-match-hazards](https://github.com/munimtechnologies/exact-match-hazards) | HuggingFace `evaluate` `exact_match` text normalization | Normalization flips correct/incorrect in both directions |
| [squad-normalize-hazards](https://github.com/munimtechnologies/squad-normalize-hazards) | SQuAD `normalize_answer` + token-F1 | Empty-collapse false positives; guard divergence; surviving glued articles |
| [math-annotation-consistency](https://github.com/munimtechnologies/munimtechnologies.github.io/tree/main/math-annotation-consistency) | Self-consistency of worked solutions vs. labels (GSM8K, AQuA-RAT, MathQA) | GSM8K 0.00% off; AQuA-RAT 6.88% (3,314/48,159); MathQA 27.90% (9,081/32,551) |
| [rouge-tokenizer-hazards](https://github.com/munimtechnologies/munimtechnologies.github.io/tree/main/rouge-tokenizer-hazards) | Default ROUGE tokenizer's ASCII-only filter on non-Latin text | ROUGE-1 F = 1.0 between opposite-meaning summaries |
| [math-equiv-hazards](https://github.com/munimtechnologies/munimtechnologies.github.io/tree/main/math-equiv-hazards) | Hendrycks MATH `strip_string`/`is_equiv` equivalence check | 27 cases, 14 hazards in 5 groups |
| [math-equiv-prevalence](https://github.com/munimtechnologies/munimtechnologies.github.io/tree/main/math-equiv-prevalence) | Exposure of 12,500 real MATH gold answers to those mechanisms | All 6 predictions hit; 101 golds (0.808%) drop a unit tail; 34 (0.272%) flip on a leading space |
| [ifeval-placeholder-hazards](https://github.com/munimtechnologies/munimtechnologies.github.io/tree/main/ifeval-placeholder-hazards) | IFEval `PlaceholderChecker` counting every `\[.*?\]` span | 6 cases reproduced (5 false pass, 1 false fail); 27 of 541 prompts affected |
| [ifeval-regex-hazards](https://github.com/munimtechnologies/munimtechnologies.github.io/tree/main/ifeval-regex-hazards) | IFEval keyword checkers building regex without `re.escape` | 9 cases reproduced; hazard reachable but unexercised (0/42, 0/49 prompts) |
| [ifeval-count-words-hazards](https://github.com/munimtechnologies/munimtechnologies.github.io/tree/main/ifeval-count-words-hazards) | IFEval `number_words` using `\w+` tokenization | 45/52 (87%) differ in count; 2 flip the published verdict |
| [ifeval-comma-hazards](https://github.com/munimtechnologies/munimtechnologies.github.io/tree/main/ifeval-comma-hazards) | IFEval `punctuation:no_comma` (`CommaChecker`) matching only ASCII comma U+002C | 6 cases reproduced (4 flips); 0 false passes on 44 scored GPT-4 responses, but ARABIC COMMA U+060C appears in 2 of 541 responses (reachable-but-unexercised) |

## Licensing

Code is Apache-2.0; each corpus and write-up is CC BY 4.0. Transcribed upstream
functions keep their own licences (stated in each audit). This catalogue page is
CC BY 4.0.
