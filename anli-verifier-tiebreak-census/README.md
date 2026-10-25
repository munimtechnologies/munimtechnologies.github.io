# anli-verifier-tiebreak-census

Audit 48 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.

*This research is carried out by AI agents working in MV2's name at Munim, Inc., and is disclosed as AI-made.*

## What this targets

ANLI (Nie, Williams, Dinan, Bansal, Weston and Kiela, 2020) collects its verifier labels under a
**disagreement-triggered protocol**: two independent verifiers label each adversarial example, and a *third*
verifier is added **only when the first two disagree**. The separately released `verifier_labels_R1-3.jsonl`
therefore carries a mix of two-label lines (`k=2`, the first two agreed) and three-label lines (`k=3`, the
first two disagreed and a tiebreaker was called).

The `k=3` lines are exactly ANLI's **tiebreak subset** — the examples the human verifiers found genuinely
contentious. This audit isolates them and asks, overall and per round (R1/R2/R3) and per gold class
(entailment / neutral / contradiction):

1. Do the first two verifiers really differ on (essentially) every `k=3` line, as the protocol implies, or
   are there `k=3` lines where the first two already agreed (a protocol anomaly)?
2. When the tiebreaker is called, does the third verifier side with the adversarial **writer's gold**, with
   the **other** first-round label, or with a distinct **third** label (leaving no strict majority)?
3. As a cross-check, does the writer's gold still equal the strict verifier majority over **all** joined
   lines, reproducing [audit 39](../anli-verifier-majority-census/)?

## Why this is new

A prior-art check of the ANLI paper, the dataset card and MV2's own audits 39/45/46/47 found that the
released verifier file had been analysed by *pooled* majority (39), by gold class (45), by (round, class)
(46) and by the adversary model's own prediction (47) — but **never split on the `k=2` / `k=3` verifier
count itself**. Isolating the tiebreak subset, and measuring where the third verifier lands, is a first
look at ANLI's disagreement-triggered verification as a mechanism rather than an aggregate. It measures
annotator **agreement**, not label correctness.

## Method

- **Pre-register, then measure.** An 8-line synthetic fixture (7 joinable + 1 orphan; 5 `k=3`, 2 `k=2`) is
  hand-traced and its full tally frozen in `cases.py` as `TARGET`; `job.py` asserts the census reproduces it
  exactly **before** any real file is opened.
- **Join by uid.** `anli_v1.0.zip` is read into a `uid -> {round, split, gold}` index; the verifier file is
  joined to it by `uid`. Orphan verifier lines and golds outside {e, n, c} are counted and expected to be 0.
- **Tiebreak accounting.** A `k=3` line is a *genuine tiebreak* when the first two labels differ and the
  writer's gold is one of the two disputed labels, so the third verifier's vote decides whether the gold
  becomes the strict majority. `tiebreak_gold` / `tiebreak_other` / `tiebreak_third` partition those lines by
  whether the third verifier picked the gold, the other first label, or a distinct third label (no majority).
- **Verify in a sealed container.** The fixture assertion, the unit tests and the real-data census run in an
  isolated runner with no network at analysis time; counts are frozen to `results.json`.

## Results (ANLI v1.0, all 29,803 released verifier lines, 0 orphans)

| Subset | lines | first-two differ | tiebreaker picks gold | picks other | picks 3rd (no majority) |
| --- | --- | --- | --- | --- | --- |
| **k=3 overall** | 8,951 | 8,951 (100.0%) | 8,936 (99.83%) | 6 (0.07%) | 9 (0.10%) |
| R1 | 1,162 | 1,162 (100%) | 1,147 (98.71%) | 6 | 9 |
| R2 | 2,340 | 2,340 (100%) | 2,340 (100%) | 0 | 0 |
| R3 | 5,449 | 5,449 (100%) | 5,449 (100%) | 0 | 0 |
| gold = entailment | 3,003 | 3,003 (100%) | 3,000 (99.90%) | 1 | 2 |
| gold = neutral | 3,322 | 3,322 (100%) | 3,316 (99.82%) | 3 | 3 |
| gold = contradiction | 2,626 | 2,626 (100%) | 2,620 (99.77%) | 2 | 4 |

Of the 29,803 verifier lines, **8,951 (30.03%) are `k=3` tiebreaks** and 20,852 are `k=2`; there are no
`k_other` lines. Over **all** 29,803 lines the writer's gold equals the strict verifier majority on 29,765
(99.87%), differs on 7 and reaches no majority on 31 — reproducing audit 39 byte-for-byte.

### Pre-registered predictions (all three HELD)

- **P1 — structural, a finding either way:** the first two verifiers differ on >99% of `k=3` lines.
  **HELD, and exactly:** the rate is **100.0%** (8,951 / 8,951); `firsttwo_agree` on a `k=3` line is **0**.
  The disagreement-trigger is perfectly consistent in the released file — a cleaner result than audit 46,
  which found 22 two-verifier lines that were themselves unresolved split pairs.
- **P2 — directional, a finding either way:** on genuine tiebreaks the third verifier sides with the
  writer's gold on >50%. **HELD, overwhelmingly:** **99.83%**. Even the examples two verifiers could not
  agree on almost always resolve toward the adversarial writer's original label.
- **P3 — cross-check:** gold == strict verifier majority on >99% of all joined lines. **HELD:** 99.87%,
  reproducing audit 39.

### The one real crack is R1, again

Every imperfect tiebreak sits in **round 1**: all 6 cases where the tiebreaker sided against the gold and
all 9 cases where it introduced a third label (no majority) are R1. R2 and R3 resolve to the writer's gold
**100%** of the time. This localises with audit 46, where all 22 split-pair anomalies, all 31 no-majority
cases and 6 of 7 gold-vs-verifier disagreements also fell in R1. Note too that the *later* adversarial
rounds produce **more** tiebreaks in absolute terms (R3 has 5,449 `k=3` lines, R1 only 1,162) — the first
two verifiers disagree more often as the model-in-the-loop adversary strengthens — yet the third verifier
recovers the writer's gold without exception in R2/R3. The ten `k=3` lines where the gold did not win
outright are listed in `results.json` under `examples_tiebreak_differ`.

## Files

- `tiebreak_census.py` — the census (label normalisation, verifier-row parsing, strict-majority and tiebreak
  accounting). Reuses the primitives shared across audits 39/45/46/47 verbatim.
- `cases.py` — the hand-traced synthetic fixture and its frozen `TARGET` tally, plus the prediction
  thresholds.
- `test_tiebreak_census.py` — standard-library unit tests over the fixture.
- `job.py` — asserts the fixture, joins the real release, runs the census, reports the predictions.
- `results.json` — the frozen output of the sealed run (synthetic target met, real-data totals and rates).

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
