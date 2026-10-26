"""Run the ANLI per-genre verifier-agreement census on the official release.

Reads the main ANLI examples from anli_v1.0.zip into a uid -> {round, split, gold, genre} index, parses
the separately released verifier_labels_R1-3.jsonl, joins them by uid, and tallies -- per genre, pooled
over all rounds and again restricted to R3 -- how decisively ANLI's verifiers back the writer's
adversarial gold (strict-majority agreement and the fraction of individual votes equalling gold). The
hand-traced fixture is asserted BEFORE any real file is touched.

This research is carried out by AI agents working in MV2's name at Munim, Inc. Apache-2.0.
"""
import argparse
import glob
import json
import os
import sys
import zipfile

import cases
from genre_agreement import GENRE_FIELDS, ROUNDS, census_genre, flatten, parse_verifier_row


SPLITS = cases.SPLITS


def read_verifier(path):
    rows = []
    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if line:
                rows.append(parse_verifier_row(json.loads(line)))
    return rows


def _member_round_split(name):
    if not name.endswith(".jsonl") or name.endswith("/"):
        return None, None
    parts = name.split("/")
    rnd = next((p for p in parts if p in ROUNDS), None)
    stem = parts[-1][:-len(".jsonl")]
    split = stem if stem in SPLITS else None
    return rnd, split


def read_main(zip_path):
    index = {}
    totals = {}
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            rnd, split = _member_round_split(name)
            if rnd is None or split is None:
                continue
            n = 0
            with zf.open(name) as fh:
                for raw in fh:
                    line = raw.decode("utf-8").strip()
                    if not line:
                        continue
                    obj = json.loads(line)
                    index[obj.get("uid")] = {"round": rnd, "split": split,
                                             "gold": obj.get("label"), "genre": obj.get("genre")}
                    n += 1
            totals["%s/%s" % (rnd, split)] = n
    return index, totals


def _rates(tally):
    n = tally["n"]
    tv = tally["total_votes"]
    out = dict(tally)
    out["gold_majority_rate"] = (tally["gold_majority"] / n) if n else None
    out["no_majority_rate"] = (tally["no_majority"] / n) if n else None
    out["gold_support_rate"] = (tally["gold_votes"] / tv) if tv else None
    return out


def _spread(rate_by_genre):
    vals = [r for r in rate_by_genre.values() if r is not None]
    return (max(vals) - min(vals)) if len(vals) >= 2 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # 1. Assert the hand-traced fixture BEFORE touching real data.
    fix_stats = census_genre([parse_verifier_row(o) for o in cases.FIXTURE_VERIFIER_RAW],
                             cases.build_gold_index(cases.FIXTURE_MAIN_RAW))
    fix = flatten(fix_stats)
    target_met = (set(fix) == set(cases.TARGET)) and all(fix[k] == cases.TARGET[k] for k in cases.TARGET)
    print("[fixture] target_met =", target_met)
    if not target_met:
        for k in sorted(set(fix) | set(cases.TARGET)):
            o, t = fix.get(k), cases.TARGET.get(k)
            if o != t:
                print("  MISMATCH %-28s observed=%r target=%r" % (k, o, t))
        print("FATAL: fixture does not match hand-traced target", file=sys.stderr)
        sys.exit(2)

    # 2. Locate the two inputs in the (reused) data volume.
    verifier_files = sorted(glob.glob(os.path.join(args.data_dir, "*verifier*.jsonl")))
    zips = sorted(glob.glob(os.path.join(args.data_dir, "*.zip")))
    print("[diag] verifier files:", verifier_files)
    print("[diag] zip files:", zips)
    if not verifier_files:
        print("FATAL: no verifier jsonl found in data dir", file=sys.stderr)
        sys.exit(3)
    if not zips:
        print("FATAL: no anli zip found in data dir", file=sys.stderr)
        sys.exit(4)

    # 3. Read both sides and run the per-genre census.
    verifier_rows = read_verifier(verifier_files[0])
    gold_index, main_totals = read_main(zips[0])
    print("[diag] verifier lines =", len(verifier_rows), " main examples =", len(gold_index))
    stats = census_genre(verifier_rows, gold_index)
    t = stats["totals"]
    print("[diag] totals =", t)

    by_genre = {g: _rates(stats["by_genre"][g]) for g in sorted(stats["by_genre"])}
    by_genre_r3 = {g: _rates(stats["by_genre_r3"][g]) for g in sorted(stats["by_genre_r3"])}
    for g, r in by_genre.items():
        print("[diag] pooled  %-18s n=%6d gold_maj_rate=%s support=%s no_maj=%d"
              % (g, r["n"], None if r["gold_majority_rate"] is None else round(r["gold_majority_rate"], 4),
                 None if r["gold_support_rate"] is None else round(r["gold_support_rate"], 4),
                 r["no_majority"]))
    for g, r in by_genre_r3.items():
        print("[diag] R3only  %-18s n=%6d gold_maj_rate=%s support=%s no_maj=%d"
              % (g, r["n"], None if r["gold_majority_rate"] is None else round(r["gold_majority_rate"], 4),
                 None if r["gold_support_rate"] is None else round(r["gold_support_rate"], 4),
                 r["no_majority"]))

    # 4. Pre-registered predictions (held/failed reported honestly).
    # P1 (structural): in EVERY genre the gold == strict verifier majority rate exceeds the threshold.
    maj_rates = {g: r["gold_majority_rate"] for g, r in by_genre.items()
                 if r["gold_majority_rate"] is not None}
    min_genre = min(maj_rates, key=maj_rates.get) if maj_rates else None
    p1 = bool(maj_rates) and min(maj_rates.values()) > cases.MIN_GOLD_MAJORITY_RATE
    # P2 (directional): WITHIN R3, the gold-support rate spread across genres (n >= MIN_GENRE_N) exceeds threshold.
    r3_support = {g: r["gold_support_rate"] for g, r in by_genre_r3.items()
                  if r["n"] >= cases.MIN_GENRE_N and r["gold_support_rate"] is not None}
    r3_spread = _spread(r3_support)
    p2 = r3_spread is not None and r3_spread > cases.MIN_R3_SUPPORT_SPREAD
    # P3 (cross-check, reproduces audits 39/48): gold == strict majority on the expected count, clean join.
    p3 = (t["all_lines_match"] == cases.EXPECTED_ALL_LINES_MATCH
          and t["n_joined"] == cases.EXPECTED_N_JOINED and t["n_orphan"] == 0
          and t["n_gold_unexpected"] == 0)

    predictions = {
        "P1_every_genre_gold_majority_above_min": p1,
        "P2_r3_support_spread_above_min": p2,
        "P3_reproduces_audit39_join": p3,
    }
    print("[diag] P1 min gold_majority_rate =",
          None if not maj_rates else round(min(maj_rates.values()), 4), "at genre", min_genre)
    print("[diag] P2 R3 gold_support spread =", None if r3_spread is None else round(r3_spread, 4),
          "over", {g: round(v, 4) for g, v in r3_support.items()})
    print("[diag] P3 all_lines_match =", t["all_lines_match"], "n_joined =", t["n_joined"],
          "n_orphan =", t["n_orphan"])
    for k, v in predictions.items():
        print("[prediction] %s = %s" % (k, "HELD" if v else "FAILED"))

    # Compare pooled vs R3-only support ordering (the Simpson's-paradox read, reported for the write-up).
    pooled_support = {g: r["gold_support_rate"] for g, r in by_genre.items()
                      if r["n"] >= cases.MIN_GENRE_N and r["gold_support_rate"] is not None}

    out = {
        "dataset": "ANLI v1.0 (Nie, Williams, Dinan, Bansal, Weston and Kiela, 2020), R1/R2/R3, joined to "
                   "the separately released verifier_labels_R1-3.jsonl by uid. This audit tallies, per "
                   "`genre` value, how decisively ANLI's verifiers back the writer's adversarial gold -- "
                   "both pooled across rounds and within R3 only, so genre is compared with the adversary "
                   "round held fixed (wikipedia spans R1/R2/R3; the other five genres are R3-only). Two "
                   "measures: the strict-majority agreement rate (gold == strict verifier majority) and the "
                   "gold-support rate (fraction of individual verifier votes equalling gold). The all-lines "
                   "match/differ/no-majority totals reproduce audits 39/48 as a cross-check. Reuses audits "
                   "39/45/46/47/48 label/majority primitives verbatim. Measures AGREEMENT, not correctness.",
        "rows_as_expected": (t["n_orphan"] == 0 and t["n_gold_unexpected"] == 0
                             and t["n_joined"] == cases.EXPECTED_N_JOINED),
        "synthetic_corpus": {"target_met": target_met, "observed": fix, "target": cases.TARGET},
        "main_totals_by_round_split": main_totals,
        "totals": t,
        "by_genre": by_genre,
        "by_genre_r3": by_genre_r3,
        "pooled_support_rate": pooled_support,
        "r3_support_rate": r3_support,
        "r3_support_spread": r3_spread,
        "predictions": predictions,
        "note": "Per-genre verifier agreement on ANLI's verified subset. gold_majority_rate = share of a "
                "genre's examples whose writer gold equals the strict verifier majority; gold_support_rate = "
                "fraction of that genre's individual verifier votes that equal the writer gold (a continuous "
                "decisiveness measure, defined for k=2 and k=3 lines alike). by_genre pools across rounds "
                "(confounded with the adversary round, since 5 of 6 genres are R3-only); by_genre_r3 holds "
                "the round fixed at R3. P1 (structural, finding either way) bets gold == strict majority on "
                ">99% of examples in EVERY genre (gold derivation robust to domain). P2 (directional, finding "
                "either way) bets that WITHIN R3 the gold-support rate still varies across genres by >0.03, "
                "so text domain predicts verifier decisiveness even at a single adversary round. P3 "
                "(cross-check) bets gold == strict majority on 29,765 of 29,803 joined lines (reproduces "
                "audits 39/48). Compare pooled_support_rate with r3_support_rate for any Simpson's-paradox "
                "reordering once the round is controlled.",
    }
    out_path = os.path.join(args.out_dir, "results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False, default=str)
    print("[done] wrote", out_path)


if __name__ == "__main__":
    main()
