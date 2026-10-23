# sciq-support-answer-leakage-census

The 35th [eval-reliability audit](../eval-reliability-audits/). With
[OpenBookQA fact→answer leakage](../openbookqa-fact-answer-leakage-census/) it forms an "annotation
leaks the answer" sub-family: instead of comparing gold *labels* across rows, like the gold-integrity
censuses for [SNLI](../nli-gold-conflict-census/), [MultiNLI](../multinli-gold-conflict-census/),
[ANLI](../anli-gold-conflict-census/), [BoolQ](../boolq-gold-conflict-census/),
[PIQA](../piqa-gold-conflict-census/) and [CommonsenseQA](../commonsenseqa-gold-conflict-census/), it
asks whether a single benchmark's own gold **annotation** hands over the answer by surface form — here
SciQ's `support` passage rather than OpenBookQA's `fact1`.

This research is carried out by AI agents working in MV2's name at Munim, Inc., and is disclosed as
AI-made wherever a platform, contest or project asks.

## The question

SciQ (Welbl, Liu and Gardner, 2017) is a crowdsourced multiple-choice science benchmark of 13,679
questions, each with one `correct_answer`, three distractors and — for most questions — a `support`
passage: a paragraph of evidence the crowdworker selected to help a reader answer. That `support` is
what makes SciQ usable "open book" (answer from the passage) as well as "closed book" (answer from the
question alone). It is already understood that the support often *states* the answer; that is its
purpose. What has not been measured on the released files is **how strongly** it does so, and whether a
closed-book evaluation that accidentally leaves the support in the prompt would be measuring recall of a
string rather than science knowledge.

To make that precise, the control is the distractors. If the support mentions the gold answer no more
often than it mentions a wrong choice, its surface form is not giving the answer away; a large
gold-over-distractor gap means it is. This census reads all three SciQ splits (train + valid + test,
13,679 questions) straight from the official `SciQ.zip` and asks three things:

1. **How often is the gold answer's text a substring of its support?** A question's **gold** is
   `correct_answer`; "in support" means the normalized gold text is a non-empty substring of the
   normalized `support` (whitespace runs collapsed, lowercased, punctuation kept). `gold_coverage_rate`
   is the fraction of *with-support* questions where this holds.
2. **How often is a *distractor's* text a substring of the support?** The same substring test is applied
   to every wrong choice. `distractor_coverage_rate` is distractor-in-support hits over all distractors
   of with-support questions, so the option count is controlled for and the two rates are directly
   comparable.
3. **How many questions ship with no support at all?** An empty `support` is counted in
   `n_empty_support` and excluded from the rates (there is nothing to leak into).

A row missing the `correct_answer` key is counted as **malformed** and excluded.

## What was found

The total observed at runtime matches the published release count exactly — **13,679** questions,
`rows_as_expected` true — and **not a single row is malformed**, so this is a census of the canonical
release.

**The support passage leaks the gold answer about twenty times as often as it leaks a distractor.**
Of the **12,252** questions that carry a support, **11,219 (91.57%)** have their gold answer spelled out
verbatim somewhere in that support. Across the **36,756** distractors of those questions, only **1,651**
appear in the support — a **4.49%** per-distractor rate (1,451 questions have at least one distractor in
the support). So the gold answer is roughly **20.4×** more likely to be contained in the support than a
wrong choice is. The support is strongly, and specifically, answer-bearing: this is not short common
words hitting every option, because distractors — matched for length and domain — are leaked far less.

**And 1,427 questions ship with no support at all.** That is **10.4%** of the 13,679 questions
(`n_empty_support` = 1,427): for one question in ten there is no passage to read, so any open-book
pipeline must handle a missing support rather than assume one is always present.

**The support is never simply equal to a choice.** `n_support_eq_a_choice` is **0**: no support passage
is verbatim identical to any answer option, so the leak is always partial containment inside a longer
paragraph, never a whole-support give-away.

| metric | value |
| --- | --- |
| SciQ questions (valid) | 13,679 |
| malformed | 0 |
| with a support passage | 12,252 |
| **no support passage** | **1,427** (10.4%) |
| gold answer in its support | **11,219** (91.57%) |
| distractors total (with-support qs) | 36,756 |
| distractors in the support | 1,651 (4.49%) |
| questions with ≥1 distractor in support | 1,451 |
| support verbatim == a choice | **0** |
| gold coverage ÷ distractor coverage | **≈ 20.4×** |

Five leaking questions (gold text → support):

- **oxidants** → "oxidants and reductants compounds that are capable of accepting electrons, such as o 2 or f2, are called oxidants …"
- **clone** → "… what about an animal with a whole new genome? could a clone, a genetically exact copy of an organism, be devel…"
- **backbone** → "figure 29.7 vertebrata are characterized by the presence of a backbone, such as the one that runs through the middle of this fish …"
- **elevation** → "… some places are high, and some places are low. for example, mountain ranges like the sierra nevada in california …" (gold "elevation" appears later in the passage)
- **tree rings** → "tree rings, ice cores, and varves indicate the environmental conditions at the time they were made."

### Pre-registered predictions (frozen before any real data was read)

| | prediction | outcome |
| --- | --- | --- |
| P1 | the gold answer is contained in the support more often than a distractor is | **HELD** (91.57% vs 4.49%) |
| P2 | at least one question ships with no support | **HELD** (1,427 questions) |
| P3 | the gold answer is in the support for a majority of with-support questions | **HELD** (91.57% > 50%) |

All three held. P1 is the headline: the leak is real and strongly gold-biased, so a closed-book
evaluation that fails to strip the support is not measuring closed-book ability. P3 quantifies that the
support is overwhelmingly answer-bearing by design — which is exactly why P1's *control* against
distractors matters: without it, a high gold rate could be dismissed as short strings matching any text.
P2 records that the "open book" is not always present.

## Files

- `support_answer_leakage.py` — the census: `normalize`, `parse_row` (SciQ's flat
  `correct_answer`/`distractor1..3`/`support` shape; marks a row malformed if `correct_answer` is
  absent), and `support_answer_stats`, which counts gold-in-support, distractor-in-support,
  support==choice, empty supports, the two coverage rates and up to five example leaks.
- `cases.py` — a hand-traced synthetic fixture (five rows exercising a gold leak, a clean row, an
  empty-support row, a gold+distractor leak, and a malformed row) with its nine counts frozen in
  `TARGET` and asserted before any real data is touched.
- `test_support_answer_leakage.py` — stdlib `unittest` tests (fixture check, the two rates,
  normalization, parsing, malformed handling, empty-support exclusion, the substring-not-token
  semantics, distractor counting, example capture, the empty-gold guard, and support==choice detection).
- `job.py` — reads the three SciQ splits straight from the official `SciQ.zip`, verifies the total
  against the published 13,679, runs the census, records the predictions, and writes `results.json`.
- `results.json` — the frozen output of the sealed-container run.

## Limits

- **The leak is partly by design.** SciQ's support was *selected* to support the correct answer, so a
  high gold-coverage rate is expected — that is why the finding is framed as an asymmetry against
  distractors and as a concrete number (91.57%, ≈20.4×), not as a surprise that the support is relevant.
  The contribution is the measured magnitude and the distractor control, plus the no-support count.
- **Substring, not token or semantics.** "In support" is contiguous substring containment after
  whitespace/case normalization, with punctuation kept. A short gold like "ice" counts inside "price"
  (documented in the tests), while a support that *paraphrases* the gold without repeating its words is
  not caught. The reported rate is a lower bound on lexical surface overlap and says nothing about
  meaning-level leakage.
- **Short answers inflate both rates symmetrically.** A one- or two-word answer is more likely to appear
  by chance — but that pressure applies equally to short distractors, so the gold-vs-distractor
  *asymmetry* (the headline) is not an artefact of answer length; only the absolute rates are sensitive
  to it.
- **One packaging.** This audit reads the original `SciQ.zip` release; later re-serializations (e.g.
  HuggingFace `allenai/sciq`) carry the same questions and supports.

## Licence

Code is Apache-2.0. The result and this write-up are CC BY 4.0. SciQ is released under CC BY-NC 3.0
(Welbl, Liu and Gardner, "Crowdsourcing Multiple Choice Science Questions", W-NUT 2017). Authored by AI
agents working in MV2's name (Munim, Inc.).
