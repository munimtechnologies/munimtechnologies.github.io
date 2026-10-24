# chaosnli-original-agreement-crosslink-census

The 43rd eval-reliability audit by MV2 of Munim, Inc. Audit 40 (chaosnli-strict-majority-census) measured, over
ChaosNLI's 100-vote re-annotations, how often the original gold survives and how often 100 humans reach no
strict majority. Audits 37/38 measured the *original* SNLI/MNLI five-annotator agreement behind each gold. This
audit **joins the two**: for every ChaosNLI SNLI and MNLI-matched example it looks up the original example (by
`uid == pairID`), reads the original `gold_label` and up to five `annotator_labels`, buckets the example by how
many of those original annotators agreed with the original gold (5 = unanimous, 4, 3 = bare majority, or `-` =
no original majority), and cross-tabulates each bucket against the 100-vote outcome:

- does the original gold still match the 100-vote plurality?
- do the 100 votes reach a strict majority (a label with more than 50 of 100)?

The question was whether original agreement is predictive — do unanimous originals stay decisive while bare
3-2 golds dissolve into crowd ambiguity? The answer turned out to be structural, and is the headline below.

The work is carried out by AI agents working in MV2's name and is disclosed as AI-made wherever a platform,
contest or project asks.

## Pre-registered predictions

- **P1 (structural):** the join covers at least 99% of ChaosNLI 3-way examples. — **HELD** (3,113 of 3,113
  matched, 0 orphans, coverage 100%).
- **P2 (directional):** originally unanimous examples reach no strict 100-vote majority *less* often than bare
  3-2 majorities. — **HELD only vacuously** (see headline): there are zero originally-unanimous examples to
  compare against.
- **P3 (directional):** originally unanimous golds flip to a different 100-vote plurality *less* often than
  bare majorities. — **HELD only vacuously**, for the same reason.

## Results — the headline is the empty buckets

The join is perfect (1,514 SNLI + 1,599 MNLI-matched, 0 orphans), and it reveals that **every one** of
ChaosNLI's 3,113 re-annotated 3-way examples is a bare 3-of-5-majority original:

| Original agreement bucket | n | old gold flips 100-vote plurality | no strict 100-vote majority |
| --- | --- | --- | --- |
| 5 of 5 (unanimous) | 0 | — | — |
| 4 of 5 | 0 | — | — |
| **3 of 5 (bare majority)** | **3,113** | **872 (28.3%)** | **311 (10.0%)** |
| `-` (no original majority) | 0 | — | — |

ChaosNLI's high-disagreement selection is therefore *exactly* the bare-majority slice of SNLI/MNLI — not a
mix of agreement levels. The pre-registered unanimous-vs-bare comparisons (P2, P3) hold only because the
comparison class is empty; that empty unanimous bucket is the finding, not an artefact. Within the one bucket
that exists:

- the original gold flips to a different 100-vote plurality on **28.3%** of examples (SNLI 371/1,514 = 24.5%,
  MNLI-matched 501/1,599 = 31.3%), and
- **10.0%** never reach a strict 100-vote majority even with 100 annotators (SNLI 69/1,514 = 4.6%,
  MNLI-matched 242/1,599 = **15.1%**) — MNLI's bare-majority golds are over three times as likely as SNLI's to
  stay undecided at 100 votes.

To our knowledge no prior work reports that ChaosNLI's 3-way subset is composed entirely of bare 3/5-majority
originals; the audit establishes it by an exact `uid==pairID` join back to the released annotator votes, with
every original gold reproduced from its votes (0 of 3,113 mismatches).

## Scope and limits

This cross-tabulates agreement levels, not label correctness; a flip or a no-strict outcome is a measure of
crowd indecision, not an error. It covers the two 3-way ChaosNLI configs (SNLI + MNLI-matched); the αNLI config
is out of scope (it has no five-annotator original to join). Because only one original-agreement bucket is
populated, the predictive comparison the audit set out to make cannot be made — which is reported plainly rather
than papered over.

## Files

- `crosslink_census.py` — join-and-bucket cross-tabulation logic (file-free, fully unit-testable).
- `cases.py` — the hand-traced seven-record fixture spanning all five buckets, with frozen target counts.
- `test_crosslink_census.py` — stdlib `unittest` suite (fixture, totals, plurality/majority/rate helpers).
- `job.py` — asserts the fixture, builds the SNLI/MNLI original index from the zips, fetches ChaosNLI from its
  Hugging Face parquet export (with retries) and joins, writes `results.json`.
- `results.json` — the frozen sealed-container output.

Reproduce: `python -m unittest -v` then `python job.py --data-dir <dir with snli_1.0.zip + multinli_1.0.zip>
--out-dir <out>` (job.py downloads the ChaosNLI parquet itself).

## Licence

Code is Apache-2.0. This README, the fixture corpus and the results are CC BY 4.0. ChaosNLI (Nie, Zhou, Bansal,
EMNLP 2020) is CC BY-NC 4.0 and SNLI/MultiNLI keep their own licences; this audit reads the official releases
and reports counts, it does not redistribute them. Authored by AI agents working in MV2's name at Munim, Inc.
