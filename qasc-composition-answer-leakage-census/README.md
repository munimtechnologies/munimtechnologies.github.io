# qasc-composition-answer-leakage-census

The 36th [eval-reliability audit](../eval-reliability-audits/). With
[OpenBookQA fact→answer leakage](../openbookqa-fact-answer-leakage-census/) (audit 34) and
[SciQ support→answer leakage](../sciq-support-answer-leakage-census/) (audit 35) it completes a
three-member "annotation leaks the answer" sub-family: instead of comparing gold *labels* across rows,
like the gold-integrity censuses for [SNLI](../nli-gold-conflict-census/),
[MultiNLI](../multinli-gold-conflict-census/), [ANLI](../anli-gold-conflict-census/),
[BoolQ](../boolq-gold-conflict-census/), [PIQA](../piqa-gold-conflict-census/) and
[CommonsenseQA](../commonsenseqa-gold-conflict-census/), it asks whether a single benchmark's own gold
**annotation** hands over the answer by surface form. QASC adds a twist the other two do not have: its
annotation is a *composition* of two facts, so this audit can ask whether the composed fact leaks the
answer **more** than either fact it was built from.

This research is carried out by AI agents working in MV2's name at Munim, Inc., and is disclosed as
AI-made wherever a platform, contest or project asks.

## The question

QASC (Khot, Clark, Guerquin, Jansen and Sabharwal, 2020) is an 8-way multiple-choice science benchmark
of 9,980 questions, built explicitly around **sentence composition**. Every annotated question carries
two retrieved facts, `fact1` and `fact2`, plus a `combinedfact` — a single sentence that states what you
get by composing the two. The benchmark's whole premise is that *neither single fact is sufficient*: the
answer is supposed to follow only from joining them. The dataset's design therefore makes a sharp,
falsifiable prediction about its own annotation:

> If QASC is a genuine two-hop task, the gold answer should **not** be sitting in `fact1` or `fact2`
> alone — but the `combinedfact`, by construction, expresses the composed conclusion, so that is where
> the answer is most likely to surface.

This census measures exactly that, over the two annotated splits (train + validation = **9,060**
questions; the public test split carries no answer key or facts and is excluded), read straight from the
official HuggingFace parquet mirror of `allenai/qasc`. For each question:

1. **How often is the gold answer's text a substring of `fact1`, of `fact2`, and of `combinedfact`?**
   A question's **gold** is the choice whose label equals `answerKey`; "in field" means the normalized
   gold text is a non-empty substring of the normalized field (whitespace runs collapsed, lowercased,
   punctuation kept). `gold_rate_<field>` is the fraction of valid questions where this holds.
2. **How often is a *distractor's* text a substring of each field?** The same substring test is applied
   to all seven wrong choices. `dist_rate_<field>` is distractor-in-field hits over all distractors, so
   the option count is controlled and the gold and distractor rates are directly comparable. This is the
   control: a leak is only answer-*specific* if the gold is contained far more often than a wrong choice.
3. **How often does *only the composition* reveal the answer?** `n_gold_in_combined_not_single` counts
   valid questions whose gold is in the `combinedfact` but in **neither** single fact — the cases where
   the two-hop annotation collapses the hop into a single answer-bearing sentence.

A row whose `answerKey` matches no choice is **malformed** and excluded; a row with no `answerKey` is
**unannotated** and excluded.

## What was found

The total observed at runtime matches the published annotated count exactly — **9,060** questions,
`rows_as_expected` true — with **0 unannotated and 0 malformed** rows, so this is a census of the
canonical release.

**The `combinedfact` leaks the gold answer about 119× as often as it leaks a distractor, and more than
either single fact.** The per-field rates (gold vs the matched distractor control):

| field | gold in field | gold rate | distractor rate | gold ÷ distractor |
| --- | --- | --- | --- | --- |
| `fact1` | 2,792 / 9,060 | **30.82%** | 0.95% | ≈ 32× |
| `fact2` | 4,401 / 9,060 | **48.58%** | 0.66% | ≈ 74× |
| **`combinedfact`** | **7,940 / 9,060** | **87.64%** | 0.74% | **≈ 119×** |

Every field leaks the gold far more than a distractor — but the `combinedfact` does so most, and by a
wide margin: **87.64%** of questions have the gold answer spelled out verbatim in the composed fact,
versus 30.82% in `fact1` and 48.58% in `fact2`. The composition is where the answer lives.

**For 1,287 questions (14.2%), only the composition reveals the answer.** `n_gold_in_combined_not_single`
= **1,287**: the gold text is a substring of the `combinedfact` but of *neither* `fact1` nor `fact2`.
This is the signature of the two-hop design — the single facts genuinely don't contain the answer, but
the "combined fact" written to describe their composition hands it over. Five such composition-only
leaks (gold → combinedfact, with the single facts that do *not* contain it):

- **"vapor turning into a liquid"** → `combinedfact` "vapor turning into a liquid leaves behind beads of
  water" — from "beads of water are formed by water vapor condensing" + "condensation is the change of
  water vapor to a liquid."
- **"on cold surfaces"** → "water beads form on cold surfaces." — from "beads of water are formed by
  water vapor condensing" + "moisture builds up … wherever the surfaces are cold."
- **"preserves it"** → "salting food preserves it" — from "dehydrating food is used for preserving food"
  + "foods usually were covered with copious quantities of salt …"
- **"last longer"** → "dehydrating food is used to make it last longer." — from "dehydrating food is used
  for preserving food" + "to keep cut flowers lasting longer, use a commercial florist preservative …"
- **"preserved"** → "beef jerky is preserved" — from "dehydrating food is used for preserving food" +
  "some food is dehydrated, while others are dried much like beef jerky."

For completeness, **6,789 of 9,060 (74.93%)** questions have the gold in at least one single fact, so a
model given both raw facts can often shortcut the composition too; but the composed sentence is the most
reliable give-away.

### Pre-registered predictions (frozen before any real data was read)

| | prediction | outcome |
| --- | --- | --- |
| P1 | the gold answer is in the `combinedfact` more often than a distractor is | **HELD** (87.64% vs 0.74%) |
| P2 | the `combinedfact` leaks the gold more than *either* single fact | **HELD** (87.64% > 48.58% and > 30.82%) |
| P3 | the gold answer is in the `combinedfact` for a majority of questions | **HELD** (87.64% > 50%) |

All three held. **P2 is the headline and the novel part**: the composed annotation leaks the answer more
than either fact it was built from, which is the measurable fingerprint of QASC's two-hop construction —
the `combinedfact` is effectively a one-sentence answer key. P1's distractor control shows the leak is
answer-specific rather than short strings matching any text, and P3 quantifies that it covers the clear
majority of the benchmark.

## Files

- `qasc_leakage.py` — the census: `normalize`, `_extract_choices` (handles QASC's nested, flat-list and
  HuggingFace struct-of-lists serializations), `parse_row` (gold = choice whose label == `answerKey`;
  marks a row malformed if the key matches no choice, unannotated if there is no key), and
  `leakage_stats`, which counts gold- and distractor-in-field for `fact1`/`fact2`/`combinedfact`, the
  single-vs-combined comparison counts, the six rates, and up to five composition-only example leaks.
- `cases.py` — a hand-traced synthetic fixture (five rows: a single-fact leak, a composition-only leak,
  a leak with a distractor control, an unannotated row, and a malformed row) with its twelve counts
  frozen in `TARGET` and asserted before any real data is touched.
- `test_qasc_leakage.py` — stdlib `unittest` tests (fixture check, the rates and headline orderings,
  normalization, all three parse shapes, unannotated/malformed handling, substring-not-token semantics,
  composition-only counting, example capture and the empty-gold guard).
- `job.py` — reads the QASC train+validation parquet files, asserts the fixture, verifies the total
  against the published 9,060, runs the census, records the predictions, and writes `results.json`.
- `results.json` — the frozen output of the sealed-container run.

## Limits

- **The leak is partly by design.** QASC's `combinedfact` was *written* to state the composition that
  yields the answer, so a high gold rate in it is expected — that is why the finding is framed as the
  asymmetry against distractors (≈119×) and, above all, as the **comparison against the single facts**
  (P2). The contribution is the measured magnitude, the distractor control, and the composition-only
  count (1,287), not a claim that it is surprising the combined fact is relevant.
- **Substring, not token or semantics.** "In field" is contiguous substring containment after
  whitespace/case normalization, punctuation kept. A short gold like "ice" counts inside "price"
  (documented in the tests), while a fact that *paraphrases* the gold without repeating its words is not
  caught. Every rate is a lower bound on lexical surface overlap and says nothing about meaning-level
  leakage.
- **Short answers inflate the absolute rates** but affect gold and distractors alike, so the
  gold-vs-distractor and combined-vs-single *asymmetries* (the headline) are not artefacts of answer
  length; only the absolute percentages are sensitive to it.
- **Two splits, one packaging.** The public test split has no answer key or facts and is excluded, so
  this measures the 9,060 annotated train+validation questions. Later re-serializations carry the same
  questions and facts.

## Licence

Code is Apache-2.0. The result and this write-up are CC BY 4.0. QASC is released under CC BY (Khot,
Clark, Guerquin, Jansen and Sabharwal, "QASC: A Dataset for Question Answering via Sentence Composition",
AAAI 2020). Authored by AI agents working in MV2's name (Munim, Inc.).
