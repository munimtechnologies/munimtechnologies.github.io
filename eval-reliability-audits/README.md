# eval-reliability-audits

A versioned catalogue by MV2 of Munim, Inc. of small, reproducible corpora that
show where the metrics and annotations *behind* LLM-benchmark scores fail.
Each audit isolates one mechanism, reproduces it from pinned upstream scoring code,
and ships a labelled corpus checkable with only the Python standard library, plus —
where the benchmark releases its own data — a measured blast radius on that data.

The work is carried out by AI agents working in MV2's name and is disclosed as
AI-made wherever a platform, contest or project asks.

## Method

- **Prior art first.** Search papers, issues and code before claiming a finding
  is new; state plainly why it is.
- **Pre-register before measuring.** Hand-trace a synthetic corpus and freeze its
  expected counts and verdicts before touching any real data.
- **Verify in a sealed container.** The corpus assertion and the exposure
  measurement run in an isolated runner; results are frozen to `results.json`.
- **Honest limits.** One checker, one dataset per audit; negative and latent
  results are reported as such, never dressed up.

## The audits

| # | Audit | What it targets | Headline finding |
| --- | --- | --- | --- |
| 1 | [exact-match-hazards](../exact-match-hazards/) | HuggingFace `evaluate` exact_match normalization | flips verdicts in both directions |
| 2 | [squad-normalize-hazards](../squad-normalize-hazards/) | SQuAD `normalize_answer` + token-F1 | empty-collapse false positives, guard divergence, glued articles |
| 3 | [math-annotation-consistency](../math-annotation-consistency/) | solution-vs-label self-consistency | GSM8K 0%, AQuA-RAT 6.88%, MathQA 27.90% inconsistent |
| 4 | [rouge-tokenizer-hazards](../rouge-tokenizer-hazards/) | ROUGE tokenizer ASCII-only filter | ROUGE-1 F=1.0 for opposite-meaning summaries |
| 5 | [math-equiv-hazards](../math-equiv-hazards/) | Hendrycks MATH `strip_string`/`is_equiv` | 27 cases, 14 hazards in 5 groups |
| 6 | [math-equiv-prevalence](../math-equiv-prevalence/) | 12,500 real MATH gold answers | 101 drop a unit tail; 34 flip on a leading space |
| 7 | [ifeval-placeholder-hazards](../ifeval-placeholder-hazards/) | IFEval PlaceholderChecker regex | 6 cases; 27 of 541 prompts affected |
| 8 | [ifeval-regex-hazards](../ifeval-regex-hazards/) | IFEval keyword checkers lacking `re.escape` | 9 cases; reachable but unexercised |
| 9 | [ifeval-count-words-hazards](../ifeval-count-words-hazards/) | IFEval `number_words` via `\w+` | 45/52 differ; 2 flip the published verdict |
| 10 | [ifeval-comma-hazards](../ifeval-comma-hazards/) | IFEval CommaChecker ASCII-only comma | 6 cases; Arabic comma in 2 of 541 |
| 11 | [ifeval-quotation-hazards](../ifeval-quotation-hazards/) | IFEval QuotationChecker ASCII-only quote | 6 cases; blast radius 0 of 541 |
| 12 | [ifeval-postscript-hazards](../ifeval-postscript-hazards/) | IFEval PostscriptChecker | 6 cases; blast radius 26 of 541 |
| 13 | [mwp-equation-answer-census](../mwp-equation-answer-census/) | SVAMP/ASDiv-A/MAWPS equation-answer triples | 9 of 4,030 equations don't evaluate to their answer |
| 14 | [ifeval-title-hazards](../ifeval-title-hazards/) | IFEval TitleChecker regex | 5 cases; blast radius 0 of 541 |
| 15 | [ifeval-highlight-section-hazards](../ifeval-highlight-section-hazards/) | IFEval HighlightSectionChecker | 6 cases; blast radius 0 of 541 |
| 16 | [ifeval-bullet-list-hazards](../ifeval-bullet-list-hazards/) | IFEval BulletListChecker, exact equality | 7 cases (3 flips); blast radius 0 of 31 (0 of 541) |
| 17 | [ifeval-paragraph-hazards](../ifeval-paragraph-hazards/) | IFEval ParagraphChecker, exact equality | 7 cases (3 flips); 2 of 541 flip on inline `***` |
| 18 | [ifeval-section-hazards](../ifeval-section-hazards/) | IFEval SectionChecker, `>=` minimum | 7 cases (3 flips); 3 of 541 flip on inline matches |
| 19 | [gsm8k-calculator-annotation-census](../gsm8k-calculator-annotation-census/) | GSM8K `<<expr=result>>` annotation arithmetic | 0 of 27,998 annotations miscompute; 470 of 8,679 `####` ≠ last annotation |
| 20 | [nli-gold-conflict-census](../nli-gold-conflict-census/) | SNLI duplicate (premise, hypothesis) pairs, gold labels | 64 exact + 82 normalized conflicting pairs, all in train; dev/test clean |
| 21 | [multinli-gold-conflict-census](../multinli-gold-conflict-census/) | MultiNLI duplicate (premise, hypothesis) pairs, gold labels | 83 exact + 86 normalized conflicting pairs, all in train; dev clean |

## Licence

Code is Apache-2.0. The corpora, results and write-ups are CC BY 4.0.
Transcribed upstream functions keep their own licences.
Authored by AI agents working in MV2's name (Munim, Inc.).
