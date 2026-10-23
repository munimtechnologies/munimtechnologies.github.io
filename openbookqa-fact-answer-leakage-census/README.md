# openbookqa-fact-answer-leakage-census

The 34th [eval-reliability audit](../eval-reliability-audits/). It belongs to the gold-integrity family
of censuses — for [SNLI](../nli-gold-conflict-census/), [MultiNLI](../multinli-gold-conflict-census/),
[ANLI](../anli-gold-conflict-census/), [BoolQ](../boolq-gold-conflict-census/),
[PIQA](../piqa-gold-conflict-census/), [CommonsenseQA](../commonsenseqa-gold-conflict-census/),
[OpenBookQA Main-vs-Additional](../openbookqa-main-additional-census/),
[WinoGrande](../winogrande-nested-subset-census/), [ARC](../arc-easy-challenge-overlap-census/) and the
cross-dataset [SNLI↔MultiNLI](../snli-multinli-overlap-census/) and
[ARC↔OpenBookQA](../arc-openbookqa-cross-dataset-census/) overlaps — but instead of comparing gold
*labels* across rows it asks whether a single benchmark's own gold **annotation** gives the answer
away.

This research is carried out by AI agents working in MV2's name at Munim, Inc., and is disclosed as
AI-made wherever a platform, contest or project asks.

## The question

OpenBookQA (Mihaylov et al., 2018) is a multiple-choice science benchmark built around an explicit
premise: each question is answerable from a small "open book" of core science facts **plus** a second,
unstated piece of common knowledge, and the core fact alone is *not* supposed to be sufficient. The
dataset's **Additional** release makes that premise checkable by annotating every question with the
single core fact, `fact1`, it was written against.

That annotation creates a latent risk the benchmark's design is meant to avoid: if the gold answer's
own text is literally contained in `fact1`, then a pipeline handed the gold fact could answer the item
by a trivial string match, with no second-hop reasoning at all. The gold fact would then **leak** the
answer. The clean control is the distractors: if the fact mentions the gold answer no more often than
it mentions a wrong choice, the surface form of the fact is not giving the answer away.

This census reads all three OpenBookQA Additional splits (5,957 questions) and asks three things:

1. **How often is the gold answer's text a substring of its annotated fact?** A question's **gold** is
   the text of the choice whose `label` equals `answerKey`; "in fact" means the normalized gold text is
   a non-empty substring of the normalized `fact1` (whitespace runs collapsed, lowercased, punctuation
   kept). `gold_coverage_rate` is the fraction of valid questions where this holds.
2. **How often is a *distractor's* text a substring of the fact?** The same substring test is applied
   to every wrong choice. `distractor_coverage_rate` is distractor-in-fact hits over all distractors,
   so the option count is controlled for and the two rates are directly comparable.
3. **Is the fact ever verbatim equal to one of the choices?** A whole `fact1` that equals a choice text
   would be an outright answer give-away (`n_fact_eq_a_choice`).

A row whose `answerKey` matches no choice label is counted as **malformed** and excluded, so it can
neither manufacture nor hide a leak.

## What was found

The total observed at runtime matches the published release count exactly — 5,957 Additional questions,
`rows_as_expected` true — and **not a single row is malformed**, so this is a census of the canonical
release.

**The gold fact leaks the gold answer about eleven times as often as it leaks a distractor.** In
**379 of 5,957** questions (**6.36%**) the gold answer's text appears verbatim inside its annotated
`fact1`. Across all **17,871** distractors, only **105** are contained in the fact — a
**0.59%** per-distractor rate (97 questions have at least one distractor in the fact). So the gold
answer is roughly **10.8×** more likely to be spelled out in the core fact than a wrong choice is. This
is a measurable lexical answer leak in the Additional annotation: for about one question in sixteen, a
system given the gold fact can read the answer straight off it.

**But the fact is never simply equal to a choice.** `n_fact_eq_a_choice` is **0**: no `fact1` is
verbatim identical to any answer option, gold or distractor, so the leak is always partial containment
inside a longer sentence, never a whole-fact give-away. That is the benchmark's design holding at the
coarsest level even while it leaks at the substring level.

| metric | value |
| --- | --- |
| Additional questions (valid) | 5,957 |
| malformed | 0 |
| gold answer in its fact | **379** (6.36%) |
| distractors total | 17,871 |
| distractors in the fact | 105 (0.59%) |
| questions with ≥1 distractor in fact | 97 |
| fact verbatim == a choice | **0** |
| gold coverage ÷ distractor coverage | **≈ 10.8×** |

Five leaking questions (gold text → fact):

- `9-794` — **carbon** → "as the population of plants decreases , carbon in the atmosphere will increase"
- `1189` — **keeping warm** → "thick feathers can be used for keeping warm"
- `9-271` — **the circulatory system** → "the circulatory system carries oxygen from the digestive and respiratory systems to the rest of the body"
- `8-79` — **expand** → "as heat increases , a flexible container containing gas will expand"
- `1835` — **arctic** → "arctic animals live in an arctic environment"

### Pre-registered predictions (frozen before any real data was read)

| | prediction | outcome |
| --- | --- | --- |
| P1 | the gold answer is contained in the fact more often than a distractor is | **HELD** (6.36% vs 0.59%) |
| P2 | at least one gold answer's text appears in its fact | **HELD** (379 questions) |
| P3 | no fact is verbatim equal to one of the choices | **HELD** (0 fact==choice) |

All three held. P1 is the headline: the leak is real and strongly gold-biased, not an artefact of facts
happening to contain short common words (which would hit distractors too). P2 confirms the leak is
non-empty. P3 bounds it: the leak is always substring containment inside a longer fact, never a whole
fact equal to a choice — so the benchmark's intended "fact is not the answer" design survives as a
coarse-grained property while failing as a surface-form one.

## Files

- `fact_answer_leakage.py` — the census: `normalize`, `parse_row` (accepts both the raw nested
  OpenBookQA shape and the flat HuggingFace shape; marks a row malformed if `answerKey` matches no
  label), and `fact_answer_stats`, which counts gold-in-fact, distractor-in-fact, fact==choice, the two
  coverage rates and up to five example leaks.
- `cases.py` — a hand-traced synthetic fixture (five rows exercising a gold leak, a clean row, a
  fact-equals-gold-choice row, a malformed row, and a distractor-only leak) with its eight counts frozen
  in `TARGET` and asserted before any real data is touched.
- `test_fact_answer_leakage.py` — stdlib `unittest` tests (fixture check, the two rates, the flat-HF
  shape, malformed handling, the substring-not-token semantics, fact==choice detection, example
  capture, and the empty-gold guard).
- `job.py` — reads the three OpenBookQA Additional splits straight from the official
  `OpenBookQA-V1-Sep2018.zip`, verifies the total against the published 5,957, runs the census, records
  the predictions, and writes `results.json`.
- `results.json` — the frozen output of the sealed-container run.

## Limits

- **Substring, not token or semantics.** "In fact" is contiguous substring containment after
  whitespace/case normalization, with punctuation kept. This both over- and under-counts a true
  semantic leak: a short gold like "ice" counts inside "price" (documented in the tests), while a fact
  that *paraphrases* the gold without repeating its words is not caught. The reported rate is therefore
  a lower bound on lexical surface overlap and says nothing about meaning-level leakage.
- **Short gold answers inflate both rates symmetrically.** A one- or two-word answer is more likely to
  appear by chance in any sentence — but that pressure applies equally to short distractors, so the
  gold-vs-distractor *asymmetry* (the headline) is not an artefact of answer length; only the absolute
  rates are sensitive to it.
- **Only the Additional set carries `fact1`.** OpenBookQA Main (the same 5,957 questions) has no gold
  fact, so the leak is a property of the Additional annotation, not of the questions themselves.
- Later packagings (e.g. HuggingFace `allenai/openbookqa`) re-serialize the same questions and facts;
  this audit reads the original OpenBookQA-V1-Sep2018 release.

## Licence

Code is Apache-2.0. The result and this write-up are CC BY 4.0. OpenBookQA-V1-Sep2018 is released under
Apache-2.0 (Mihaylov, Clark, Khot and Sabharwal, "Can a Suit of Armor Conduct Electricity? A New
Dataset for Open Book Question Answering", EMNLP 2018). Authored by AI agents working in MV2's name
(Munim, Inc.).
