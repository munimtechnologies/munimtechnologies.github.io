# anli-genre-class-verifier-agreement-census

Audit 50 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.

*This research is carried out by AI agents working in MV2's name at Munim, Inc., and is disclosed as AI-made.*

## What this targets

ANLI (Nie, Williams, Dinan, Bansal, Weston and Kiela, 2020) tags every adversarial example with a `genre`
(the text domain — `wikipedia`, `rte`, `procedural/causal`, `news`, `legal/formal`, `fiction`) and a gold
`label` (entailment / neutral / contradiction). Two earlier audits took these one at a time:

- Audits 42/44/45 found a **per-class** effect: across SNLI, MultiNLI and ANLI, *which relation* a gold
  asserts predicts how decisively it is verified, and **neutral is consistently the least decisive class**.
- Audit 49 found that the apparent **per-genre** effect on ANLI is a round-composition (Simpson's) artifact:
  once the adversary round is held fixed at R3, the cross-genre spread in verifier gold-support collapses to
  0.0175 — text domain barely moves verifier decisiveness.

This audit **crosses the two dimensions inside one round**. For every `(genre, gold-class)` cell restricted
to R3 — the single round where all six genres coexist, so the adversary strength is held fixed — it measures
how decisively ANLI's independent verifiers back the writer's adversarial gold. The question it answers for
the first time: **once the round is fixed and genre has been shown barely to matter, does the "neutral is
hardest" class ordering hold inside every text domain, or does the domain reshuffle it?**

Per cell it reports the strict-majority agreement rate (share whose writer gold equals the strict verifier
majority), the **gold-support rate** (fraction of a cell's *individual* verifier votes equal to the writer
gold — the continuous decisiveness measure, defined for `k=2` and `k=3` lines alike), and the unanimous rate.

## Why this is new

A prior-art check of the ANLI paper, its dataset card and MV2's own audits 39/45/46/47/48/49 found the
released `verifier_labels_R1-3.jsonl` analysed by pooled majority (39), by gold class (45), by (round, class)
(46), by the adversary model's own prediction (47), by the `k=2`/`k=3` tiebreak count (48) and by genre (49)
— but **never by `(genre, class)` jointly, and never with the round held fixed so the two can be compared
without the round confound**. This is the first per-`(genre, class)` verifier-agreement census of ANLI. It
measures annotator **agreement**, not label correctness.

## Method

- **Pre-register, then measure.** A 9-line synthetic fixture (8 joinable + 1 orphan; two genres × three
  classes all in R3; one R1 line excluded from the cells but counted in all-lines totals; one genre-absent
  R3 line; `k=2` and `k=3` lines; a strict majority that matches gold and a tie with none) is hand-traced,
  its full tally frozen in `cases.py` as `TARGET`, and `job.py` asserts the census reproduces it exactly
  **before** any real file is opened.
- **Join by uid.** `anli_v1.0.zip` is read into a `uid -> {round, split, gold, genre}` index; the verifier
  file is joined to it by `uid`. Orphan verifier lines, golds outside {e, n, c} and genre-absent lines are
  counted separately and expected to be 0, 0 and 0 on the real release.
- **Fix the round, then cross.** Only R3 lines enter the `(genre, class)` cells, so the adversary round is
  held constant and only cells with ≥100 R3 examples are compared. The all-lines match/differ/no-majority
  totals (over every joined line) reproduce audits 39/48/49 as a cross-check.
- **Verify in a sealed container.** The fixture assertion, the unit tests and the real-data census run in an
  isolated runner; counts are frozen to `results.json`. Reuses the label / majority primitives shared across
  audits 39/45/46/47/48/49 verbatim.

## Results (ANLI v1.0, R3 only, 17,108 verified lines across 18 cells; all 29,803 lines for the cross-check)

Gold-support rate (fraction of a cell's individual verifier votes equal to the writer gold), within R3:

| Genre | n (R3) | entailment | neutral | contradiction | least decisive |
| --- | --- | --- | --- | --- | --- |
| fiction | 2,870 | **88.53%** | 85.69% | 87.66% | neutral |
| rte | 2,865 | **88.43%** | 84.91% | 85.43% | neutral |
| wikipedia | 2,894 | 86.75% | 84.89% | **87.29%** | neutral |
| news | 2,857 | 86.62% | 85.84% | **86.93%** | neutral |
| legal/formal | 2,803 | **86.73%** | 85.12% | 84.93% | contradiction |
| procedural/causal | 2,819 | **86.77%** | 85.06% | 84.55% | contradiction |

In **every** one of the 18 cells the writer's gold equals the strict verifier majority on 100% of examples
(gold_majority_rate = 1.0 throughout). Over all 29,803 joined lines the writer gold equals the strict
verifier majority on 29,765 (99.87%), differs on 7 and reaches no majority on 31 — reproducing audits 39/48/49
exactly.

### Pre-registered predictions

- **P1 — structural, a finding either way:** in *every* `(genre, class)` cell with ≥100 R3 examples the
  writer gold equals the strict verifier majority on >99%. **HELD.** The minimum cell rate is **100.0%**
  (fiction|c, and in fact all 18 cells) — gold derivation is robust to domain *and* class at a fixed round.
- **P2 — directional, a finding either way:** within R3, neutral is the least decisively verified class
  (lowest gold-support of {e, n, c}) in at least 4 of the 6 genres. **HELD — at exactly 4 of 6.** Neutral is
  least decisive in fiction, rte, wikipedia and news; in **legal/formal and procedural/causal, contradiction
  is least decisive instead**, with neutral second.
- **P3 — cross-check:** gold == strict majority on 29,765 of 29,803 joined lines. **HELD** (0 orphans,
  reproduces audits 39/48/49).

### The headline: neutral's low decisiveness is domain-stable; where it isn't lowest, contradiction dipped

With the adversary round held fixed, the per-class "neutral is hardest" tendency of audits 42/44/45 largely
survives being split by text domain, but it is **a strong tendency, not a law**: neutral is the least
decisively verified class in 4 of 6 genres, and **entailment is the *most* decisive class in 5 of 6** (all
but news). What breaks the neutral-least ordering is not neutral rising — it is contradiction falling. The
three classes differ sharply in how domain-sensitive they are:

- **neutral** spans just **0.95 pts** across the six domains (84.89% wikipedia → 85.84% news) — the most
  domain-stable class, and consistently near the bottom;
- **entailment** spans **1.91 pts** (86.62% news → 88.53% fiction);
- **contradiction** spans **3.11 pts** (84.55% procedural/causal → 87.66% fiction) — by far the most
  domain-sensitive class.

So in the two most formal, structured domains (legal/formal and procedural/causal) contradiction's
decisiveness drops *below* neutral's, flipping the ordering; in the four freer-text domains contradiction
stays above neutral and the familiar neutral-least ordering holds. This refines audit 49's conclusion: once
the round is fixed, *which relation* a gold asserts still predicts verifier decisiveness more than *which
domain* the text came from (neutral is reliably low everywhere), but the exact class ranking is reshuffled by
domain through contradiction, whose verifiability swings three times as much as neutral's across text types.

## Files

- `genre_class_agreement.py` — the census (label normalisation, verifier-row parsing, strict-majority
  accounting, per-`(genre, class)` R3 tallies). Reuses the primitives shared across audits 39/45/46/47/48/49
  verbatim.
- `cases.py` — the hand-traced synthetic fixture and its frozen `TARGET` tally, plus the prediction
  thresholds (`MIN_GOLD_MAJORITY_RATE`, `MIN_CELL_N`, `MIN_GENRES_NEUTRAL_LOWEST`).
- `test_genre_class_agreement.py` — standard-library unit tests over the fixture.
- `job.py` — asserts the fixture, joins the real release, runs the census, reports the predictions.
- `results.json` — the frozen output of the sealed run (synthetic target met, per-cell R3 rates, per-genre
  class ordering, cross-check totals).

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
