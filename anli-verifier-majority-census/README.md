# anli-verifier-majority-census

The 39th eval-reliability audit by MV2 of Munim, Inc., and the third — and first *non-tautological* —
member of the **gold-label derivation** family started by audit 37 (SNLI) and continued by audit 38
(MultiNLI).

The derivation family asks whether a benchmark's gold label actually follows the rule the dataset says
it follows, checked row by row on the raw released files. For SNLI and MultiNLI the answer is yes *by
construction*: their gold label is **defined** as the strict majority of the per-annotator votes, so
"gold == majority" can only hold. ANLI (Nie, Williams, Dinan, Bansal, Weston and Kiela, 2020) is built
the opposite way, which makes the same question genuinely open.

This research is carried out by AI agents working in MV2's name at Munim, Inc., and is disclosed as
AI-made wherever a platform, contest or project asks.

## The question

ANLI is adversarial, human-and-model-in-the-loop. A human writer invents a (premise, hypothesis, label)
triple that fools a model; **the writer's label becomes the gold and is kept whether or not later readers
agree with it**. Every dev and test example was then independently checked by 2 verifiers (a 3rd added
when the first 2 disagreed), and those verifier labels were released separately in May 2022
(`verifier_labels_R1-3.jsonl`).

So for ANLI "does the gold equal the strict majority of the independent verifiers?" is not a tautology —
it is a real measurement of how often the adversarial writer's label survives independent review. No
prior-art search of the ANLI paper, dataset card or public loaders found a published row-level join of
the released verifier labels back to the main gold labels.

Three predictions were pre-registered and hand-traced against a 5-row fixture before any real data was
touched:

- **P1** — verification is **dev/test only** (no verifier uid maps to a train example).
- **P2** — every verifier line carries **2 or 3** labels.
- **P3** — unlike the majority-defined SNLI/MultiNLI gold, ANLI's gold **differs** from the verifier
  majority on a **nonzero** number of rows.

The exact agreement *rate* was deliberately **reported, not pre-bet** on a guessed number.

## What was found

A sealed-container join of all 29,803 released verifier lines to the 169,265 main R1/R2/R3 examples read
straight from `anli_v1.0.zip` (0 orphan verifier uids — every verifier line matched a main example):

| Round | joined | gold == majority | gold differs | no majority | unanimous but differs from gold |
| --- | --- | --- | --- | --- | --- |
| R1 | 5,130 | 5,093 | 6 | 31 | 0 |
| R2 | 7,565 | 7,564 | 1 | 0 | 1 |
| R3 | 17,108 | 17,108 | 0 | 0 | 0 |
| **all** | **29,803** | **29,765 (99.87%)** | **7 (0.023%)** | **31 (0.10%)** | **1 (0.0034%)** |

- **The writer's adversarial gold almost always survives independent review.** Across the 29,803 verified
  examples, the writer's gold equals the strict verifier majority **99.87%** of the time. It differs on
  just **7** rows and the verifiers reach no majority on **31** — a strong, non-trivial confirmation that
  ANLI's examples are not merely "fooled the model" but hold up to fresh human judgement. Agreement rises
  monotonically by round: R3 (the hardest round) shows **zero** disagreements and zero no-majority
  verifier sets.
- **P1 FAILED — and that is the headline.** The released verifier labels are **not** restricted to
  dev/test. Of the 29,803 joined lines, **23,403 map to training examples** (and only 3,200 to dev and
  3,200 to test). The ANLI paper describes verification as the dev/test gate, but the public
  `verifier_labels_R1-3.jsonl` also carries independent verifier judgements for the training split — an
  under-documented, usable multi-annotator signal on ANLI *train* that a reader taking the paper at face
  value would not expect to exist. All 7 gold-vs-majority disagreements, and the single
  unanimous-but-differs case, fall in **train**; dev and test are clean.
- **The one striking case.** Exactly one row (uid `d7050303…`, R2/train) has **both** verifiers unanimous
  (`n`, `n`) while the writer's gold is `c` — two independent readers agreed with each other and neither
  agreed with the adversarial label. It is in `results.json` under `examples_unanimous_differ`.
- **P2 HELD.** Every verifier line carries 2 or 3 labels (20,852 with 2, 8,951 with 3, 0 otherwise),
  exactly matching the documented "2 verifiers, +1 on disagreement" protocol.
- **P3 HELD.** ANLI's gold differs from the verifier majority on a nonzero number of rows (7) — the
  family's first genuine, non-tautological derivation gap, in sharp contrast to SNLI (audit 37) and
  MultiNLI (audit 38), which are 0-mismatch by construction.

## Files

- `anli_verifier.py` — the ANLI-specific census: `norm_label` (e/n/c or spelled-out), `parse_verifier_row`
  (tolerates `"verifier labels"` or `verifier_labels`), `strict_majority`, and `census`, which joins
  verifier lines to the gold index and counts match / differ / no-majority / unanimous-differs per round
  and split. Logic is ANLI-specific (the join and the writer-vs-verifier framing), not reused from
  audits 37/38.
- `cases.py` — a five-row hand-traced fixture with its frozen `TARGET`, exercising match,
  unanimous-but-differs, 2-1 majority match, 1-1-1 no-majority and an orphan verifier uid.
- `test_anli_verifier.py` — 11 stdlib `unittest` tests (the hand-traced target plus the majority,
  no-majority, orphan, unexpected-gold and per-round edge cases).
- `job.py` — asserts the fixture before touching real data, joins the verifier file to the main zip, runs
  the census, records the predictions, and writes `results.json`.
- `results.json` — the frozen sealed-container output (per-round counts, rates, predictions, example
  rows).

## Limits

This audit checks the **derivation** relationship — does gold equal the verifier majority — not label
*correctness*: whether the writer or the verifiers were "right" is out of scope. The agreement rate is
measured, not a guess, and P1's failure is reported as found rather than tuned away. The verifier file is
joined on `uid`; 0 orphans confirm the released verifier file and `anli_v1.0.zip` are the same version.
The "train also has verifier labels" finding is about what the *released file* contains, not a claim that
ANLI's training gold was itself chosen by verifier vote — it was not; the gold stays the writer's label,
which is exactly why the 7 train disagreements can exist.

Related: audit 37 ([snli-annotator-agreement-census](../snli-annotator-agreement-census/)) and audit 38
([multinli-annotator-agreement-census](../multinli-annotator-agreement-census/)) are the first two,
by-construction members of this family. Audit 23
([anli-gold-conflict-census](../anli-gold-conflict-census/)) looks at the *same corpus* from the other
side — whether duplicate (premise, hypothesis) pairs carry conflicting gold — while this audit verifies
how each single gold relates to its independent verifier votes.

## Licence

Code is Apache-2.0. The corpus, results and this write-up are CC BY 4.0. ANLI v1.0 is released under
CC BY-NC 4.0 (Nie, Williams, Dinan, Bansal, Weston and Kiela, "Adversarial NLI: A New Benchmark for
Natural Language Understanding", ACL 2020); the verifier labels are from the facebookresearch/anli
repository. Authored by AI agents working in MV2's name (Munim, Inc.).
