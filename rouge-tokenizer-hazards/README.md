# rouge-tokenizer-hazards

A tiny, dependency-free, hand-verifiable corpus showing a specific, under-reported
way the default **ROUGE** tokenizer misfires on non-Latin text: it can report a
**ROUGE-1 of 1.0 between two summaries that mean the opposite**, and it can **rank a
wrong summary above a correct one** — not because the text matched, but because the
only thing that survived tokenization was an incidental ASCII token (a year, a
numeral, a Latin name).

This is the complement of the already-documented *zero-ROUGE phenomenon* (non-Latin
text scoring 0). That prior work covers the **false-negative** direction. This corpus
documents and verifies the **false-positive and ranking-inversion** direction, which
is more dangerous because a nonzero score looks like a real partial match.

## The root cause (documented, reproducible)

Google's reference tokenizer (`google-research/rouge/tokenize.py`, Apache-2.0), used
by default in the `rouge_score` package and by HuggingFace `evaluate`'s `rouge`, does:

1. lowercase the text;
2. replace every run of characters **not** in `[a-z0-9]` with a single space;
3. split on whitespace;
4. keep only tokens matching `^[a-z0-9]+$`.

Step 2 is **ASCII-only**. Every CJK, Arabic, Cyrillic, Devanagari, accented-Latin or
other non-ASCII character is deleted. On non-Latin text, the only tokens that survive
are the ASCII fragments that happen to be embedded — most often **digits** (years,
quantities), and Latin-script names, units or loanwords. ROUGE then compares *those*,
and reports the result as if it had compared the summaries.

## What the corpus shows

Scored with count-based ROUGE-1 exactly as `rouge_scorer._score_ngrams` defines it
(`precision = overlap / max(pred_count, 1)`, `recall = overlap / max(ref_count, 1)`,
`f = 2pr/(p+r)`):

| case | reference (gloss) | prediction (gloss) | tokens compared | ROUGE-1 F |
|---|---|---|---|---|
| opposite meaning | 2024 climate **improves** | 2024 climate **worsens** | `["2024"]` vs `["2024"]` | **1.0** |
| ranking: correct | 2024 climate improves | climate improves (no year) | `["2024"]` vs `[]` | 0.0 |
| ranking: wrong | 2024 climate improves | 2024 **war ends** | `["2024"]` vs `["2024"]` | **1.0** |
| pure non-Latin | climate improves | climate worsens | `[]` vs `[]` | 0.0 (known zero case) |
| comma in number | `2024` | `2,024` | `["2024"]` vs `["2","024"]` | 0.0 |

So a system that outputs the semantically **correct** answer but drops the year scores
**0**, while a system that outputs a semantically **wrong** answer containing the same
year scores **1.0**. On a corpus of short non-Latin summaries that share a date or a
figure, average ROUGE-1 can be driven almost entirely by that shared ASCII, with the
actual content never entering the comparison.

## Reproduce

```
python -m unittest -v test_rouge1.py
```

Standard library only — no `rouge_score`, no network. `rouge1.py` reproduces the
*documented* behaviour of the two upstream Apache-2.0 components (it does not vendor
their source); every expected value in `test_rouge1.py` and `cases.json` is
hand-traceable from the four tokenizer steps above. An execution check against the real
`rouge_score` package was run separately in a sandbox and confirmed the upstream library
returns the same scores.

## What this is and is not

- It **is** a verified demonstration that residual-ASCII overlap can make ROUGE report
  spurious partial or perfect matches, and invert rankings, on non-Latin text.
- It is **not** a claim that ROUGE is broken in general, nor a new discovery that ROUGE
  struggles on non-Latin text — that is known. The contribution is the specific,
  minimal, reproducible false-positive / ranking-inversion corpus.
- The fix is the same one the prior art recommends: pass a language-aware `tokenizer=`
  to `RougeScorer` / `evaluate.load("rouge")`, or use a Unicode-aware ROUGE
  implementation. Reporting a raw default-tokenizer ROUGE on non-Latin text is unsafe
  in **both** directions.

## Prior art

- "Zero-ROUGE phenomenon" for non-English generation — Beyond N-Grams: Rethinking
  Evaluation Metrics and Strategies for Multilingual Abstractive Summarization
  (arXiv:2507.08342).
- `kurenai` and `rougers` — community ROUGE reimplementations that add Unicode / CJK
  tokenizers precisely because the default strips non-ASCII.
- HuggingFace `evaluate` `rouge` and `rouge_score` both accept a custom `tokenizer`.

These document the **zero** (false-negative) side. This repo adds the verified
**false-positive / ranking-inversion** side.

## License

Code (`rouge1.py`, `test_rouge1.py`): Apache-2.0. Data and text (`cases.json`, this
README): CC BY 4.0. The upstream `rouge_score` / google-research `rouge` and
HuggingFace `evaluate` are Apache-2.0 and are not vendored here.

---

Research and write-up made with AI, by MV2 of Munim, Inc.
