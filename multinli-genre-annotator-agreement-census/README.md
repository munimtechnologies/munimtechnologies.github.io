# multinli-genre-annotator-agreement-census

The 41st eval-reliability audit by MV2 of Munim, Inc., and a companion to the "gold-label derivation" family
(audits 37 SNLI and 38 MultiNLI). Those audits verified that MultiNLI's shipped `gold_label` is the strict
majority of its five `annotator_labels`. This audit asks a different question of the same validated data:
**does annotator agreement vary by genre?** The MultiNLI paper (Williams, Nangia, Bowman, NAACL 2018)
reports agreement only in aggregate — 58.2% of pairs unanimous, 88.7% of individual labels equal to gold —
but never breaks those numbers down across the ten genres that make up its matched and mismatched
development sets. This is the first per-genre breakdown over the released files.

The work is carried out by AI agents working in MV2's name and is disclosed as AI-made wherever a platform,
contest or project asks.

## What it measures

Over the two validated development files inside `multinli_1.0.zip` (`dev_matched` + `dev_mismatched`,
20,000 rows, five genres each), for **each genre** we tally:

- how many of the five annotators agreed with the released gold (5 unanimous / 4 / 3 / `-` = no majority),
- the **unanimous rate** (share of valid-gold examples on which all five agreed),
- the **individual-agreement rate** (share of individual annotator labels equal to gold — the paper's
  "Agrmt." statistic), and
- a by-construction check that the released gold equals the strict majority of the five labels.

Each synthetic fixture count is hand-traced and frozen before the real files are touched; the census logic
runs in a sealed container and the output is frozen to `results.json`.

## Pre-registered predictions

- **P1 (structural / by construction):** in every genre the released gold equals the strict majority of its
  five labels. — **HELD** (gold == majority on all 19,647 valid-gold rows, every genre).
- **P2 (directional, a finding either way):** `telephone` (transcribed speech) is *less* often unanimous
  than `government` (formal written text). — **FAILED, and this is the headline:** telephone is unanimous
  **more** often (60.5%) than government (53.4%). Informal/spoken source material did **not** produce noisier
  gold labels here — the opposite held.
- **P3 (directional, a finding either way):** the per-genre unanimous rates span more than 0.05. — **HELD**
  (spread 0.118, from government 0.534 to letters 0.653).

## Results

Totals over 20,000 dev rows: 19,647 valid-gold, 353 `-` (no majority), 11,743 unanimous. The gold equals
the strict majority on all 19,647 valid rows (0 exceptions). The aggregate individual-agreement rate is
88.9% (87,286 / 98,235) — reproducing the paper's reported 88.7%.

| Genre | matched | valid | `-` | unanimous rate | individual agreement |
| --- | --- | --- | --- | --- | --- |
| letters | no | 1,977 | 23 | 0.6525 | 0.9052 |
| travel | yes | 1,976 | 24 | 0.6407 | 0.9003 |
| nineeleven | no | 1,974 | 26 | 0.6272 | 0.8971 |
| facetoface | no | 1,974 | 26 | 0.6221 | 0.8955 |
| fiction | yes | 1,973 | 27 | 0.6092 | 0.8907 |
| telephone | yes | 1,966 | 34 | 0.6053 | 0.8905 |
| oup | no | 1,961 | 39 | 0.5813 | 0.8858 |
| verbatim | no | 1,946 | 54 | 0.5591 | 0.8777 |
| slate | yes | 1,955 | 45 | 0.5432 | 0.8715 |
| government | yes | 1,945 | 55 | 0.5342 | 0.8704 |

The two statistics move together (a genre's unanimous rate and its individual-agreement rate rank almost
identically), and the decisiveness of the gold label is genuinely genre-dependent: the most decisive genre
(`letters`) is unanimous on roughly two examples in three, the least (`government`) on barely more than one
in two. Genre also tracks the no-consensus `-` rate — `government` sheds 55 rows to `-`, `letters` only 23.
The matched/mismatched (in-domain vs out-of-domain) split does **not** explain the ordering: the extremes
are a mismatched genre (`letters`) and a matched one (`government`).

## Scope and limits

This checks annotator *agreement* per genre, not label *correctness*; a unanimous gold can still be wrong,
and a `-` row is not an error. It covers only the validated dev sets (the train split is single-annotator;
see audit 38). The P1 holding is by construction and not surprising — the contribution is the per-genre
table, the reproduction of the paper's aggregate agreement, and the pre-registered P2 result overturning the
intuition that spoken/informal genres yield noisier labels.

## Files

- `genre_census.py` — per-genre tally logic (file-free, fully unit-testable).
- `cases.py` — the hand-traced seven-record / two-genre fixture and frozen target counts.
- `test_genre_census.py` — stdlib `unittest` suite (hand-traced fixture, totals, label/majority/rate helpers).
- `job.py` — asserts the fixture, loads the two dev files from `multinli_1.0.zip`, writes `results.json`.
- `results.json` — the frozen sealed-container output.

Reproduce: `python -m unittest -v` then `python job.py --data-dir <dir with multinli_1.0.zip> --out-dir <out>`.

## Licence

Code is Apache-2.0. This README, the fixture corpus and the results are CC BY 4.0. MultiNLI 1.0 is from
Williams, Nangia and Bowman (NAACL 2018), derived from the Open American National Corpus; this audit reads
the official release and reports counts, it does not redistribute it. Authored by AI agents working in MV2's
name at Munim, Inc.
