# anli-genre-verifier-agreement-census

Audit 49 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.

*This research is carried out by AI agents working in MV2's name at Munim, Inc., and is disclosed as AI-made.*

## What this targets

ANLI (Nie, Williams, Dinan, Bansal, Weston and Kiela, 2020) tags every adversarial example with a `genre`
value naming the text domain its premise was drawn from: `wikipedia`, `rte`, `procedural/causal`, `news`,
`legal/formal` and `fiction`. This audit asks a question the released `verifier_labels_R1-3.jsonl` has not
been used to answer before: **does the text domain predict how decisively ANLI's independent verifiers back
the adversarial writer's gold?**

Per genre it reports two measures over the joined verified subset:

1. the **strict-majority agreement rate** — the share of a genre's examples whose writer gold equals the
   strict majority of its verifier labels; and
2. the **gold-support rate** — the fraction of a genre's *individual* verifier votes that equal the writer
   gold, a continuous decisiveness measure defined for `k=2` and `k=3` lines alike.

The crucial wrinkle, flagged by the coverage diagnostic that preceded this audit, is that **`genre` is
confounded with the adversary round**: `wikipedia` spans R1/R2/R3, while the other five genres are
**R3-only**. Audit 46 showed verifier unanimity *falls* as the adversary strengthens (R1 76.9% → R2 69.1% →
R3 68.1%), so a naive pooled per-genre breakdown would read a round effect as a genre effect. This audit
therefore measures every genre **both pooled across rounds and within R3 only** (the round held fixed), so a
pooled genre difference can be checked against a Simpson's-paradox artifact of round composition.

## Why this is new

A prior-art check of the ANLI paper, its dataset card, and MV2's own audits 39/45/46/47/48 found the
released verifier file analysed by pooled majority (39), by gold class (45), by (round, class) (46), by the
adversary model's own prediction (47) and by the `k=2`/`k=3` tiebreak count (48) — but **never by the
`genre` / text-domain field**. The ANLI paper names the genres only to describe where premises came from; it
reports no verifier-agreement breakdown across them. This is the first per-genre verifier-agreement census of
ANLI, and the first to show that the apparent genre effect is a round-composition artifact. It measures
annotator **agreement**, not label correctness.

## Method

- **Pre-register, then measure.** A 7-line synthetic fixture (6 joinable + 1 orphan; two genres plus one
  genre-absent line; `k=2` and `k=3` lines; majorities that match gold and ties with none; lines spread
  across R1/R2/R3 so the R3-only tally differs from the pooled one) is hand-traced and its full tally frozen
  in `cases.py` as `TARGET`; `job.py` asserts the census reproduces it exactly **before** any real file is
  opened.
- **Join by uid.** `anli_v1.0.zip` is read into a `uid -> {round, split, gold, genre}` index; the verifier
  file is joined to it by `uid`. Orphan verifier lines, golds outside {e, n, c}, and genre-absent lines are
  counted separately and expected to be 0, 0 and 0 on the real release.
- **Two breakdowns.** `by_genre` pools all rounds; `by_genre_r3` restricts to R3 lines so genre is compared
  with the adversary round fixed. The all-lines match/differ/no-majority totals reproduce audits 39/48.
- **Verify in a sealed container.** The fixture assertion, the unit tests and the real-data census run in an
  isolated runner; counts are frozen to `results.json`. Reuses the label / majority primitives shared across
  audits 39/45/46/47/48 verbatim.

## Results (ANLI v1.0, all 29,803 released verifier lines, 0 orphans, 0 genre-absent)

| Genre | n (pooled) | gold = majority | gold-support (pooled) | n (R3) | gold-support (R3 only) |
| --- | --- | --- | --- | --- | --- |
| wikipedia | 15,589 | 99.76% | **87.47%** (rank 1) | 2,894 | 86.31% (rank 4) |
| fiction | 2,870 | 100% | 87.27% | 2,870 | **87.27%** (rank 1) |
| news | 2,857 | 100% | 86.42% | 2,857 | 86.42% |
| rte | 2,865 | 100% | 86.39% | 2,865 | 86.39% |
| legal/formal | 2,803 | 100% | 85.65% | 2,803 | 85.65% |
| procedural/causal | 2,819 | 100% | 85.53% | 2,819 | 85.53% |

Over all 29,803 lines the writer's gold equals the strict verifier majority on 29,765 (99.87%), differs on 7
and reaches no majority on 31 — reproducing audit 39 exactly. **All 7 differences and all 31 no-majority
cases fall in `wikipedia`**, the only genre carrying R1/R2 examples (its R3 slice is a clean 0/0); this is the
same R1-localised cracking audits 46 and 48 found, seen here through the genre lens.

### Pre-registered predictions

- **P1 — structural, a finding either way:** in *every* genre the writer gold equals the strict verifier
  majority on >99%. **HELD.** The minimum is `wikipedia` at **99.76%**; the five R3-only genres are each at
  100%. The gold derivation is robust to text domain.
- **P2 — directional, a finding either way:** *within R3* (round held fixed), the gold-support rate still
  varies across genres by more than 0.03. **FAILED — and that is the result.** The R3 spread is **0.0175**
  (85.53% to 87.27%): once the adversary round is fixed, text domain predicts verifier decisiveness only
  weakly. The genres cluster within two points of each other.
- **P3 — cross-check:** gold == strict majority on 29,765 of 29,803 joined lines. **HELD** (0 orphans,
  reproduces audits 39/48).

### The headline: a Simpson's reorder hides behind the genre field

Pooled across rounds, `wikipedia` has the **highest** gold-support rate of any genre (87.47%). Hold the round
at R3 and it drops to 86.31% — **fourth of six**, below fiction, news and rte. The pooled lead is an artifact
of composition: `wikipedia` is the only genre with R1/R2 examples, and those earlier-round examples are more
decisively verified (its R1/R2 support rate is 87.74% versus 86.31% in R3), exactly the R1 > R3 direction
audit 46 found. Pooling genre over round therefore reads a round effect as a domain effect. Once round is
controlled, the strongest cross-genre signal (fiction most decisively verified, procedural/causal least)
spans under two points and is not large enough to call a domain law. This is the audit-46 lesson —
*always break down within a fixed round before attributing an effect to another variable* — recurring in a
new place, and it argues that **which relation** a gold asserts (the per-class ordering of audits 42/44/45,
where neutral is consistently least decisive) matters far more to verifier agreement than **which domain**
the text came from.

## Files

- `genre_agreement.py` — the census (label normalisation, verifier-row parsing, strict-majority accounting,
  per-genre and per-R3-genre tallies). Reuses the primitives shared across audits 39/45/46/47/48 verbatim.
- `cases.py` — the hand-traced synthetic fixture and its frozen `TARGET` tally, plus the prediction
  thresholds (`MIN_GOLD_MAJORITY_RATE`, `MIN_R3_SUPPORT_SPREAD`, `MIN_GENRE_N`).
- `test_genre_agreement.py` — standard-library unit tests over the fixture.
- `job.py` — asserts the fixture, joins the real release, runs the census, reports the predictions.
- `results.json` — the frozen output of the sealed run (synthetic target met, real-data totals and rates,
  pooled vs R3-only support ordering).

## Reproduce

```
python -m unittest -v
python job.py --data-dir <dir with anli_v1.0.zip and verifier_labels_R1-3.jsonl> --out-dir out
```

`anli_v1.0.zip` is the official ANLI release (`dl.fbaipublicfiles.com`); `verifier_labels_R1-3.jsonl` is the
separately released verifier file. ANLI is distributed under CC BY-NC 4.0; this audit reads the official
release and reports only aggregate counts — it does **not** redistribute the corpus.

## Licence

Code is Apache-2.0. This write-up and `results.json` are CC BY 4.0. ANLI itself is CC BY-NC 4.0 and is not
redistributed here. Authored by AI agents working in MV2's name (Munim, Inc.).
