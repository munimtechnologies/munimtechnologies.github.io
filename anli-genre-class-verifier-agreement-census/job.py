"""Run the ANLI per-(genre, class) within-R3 verifier-agreement census on the official release.

Reads the main ANLI examples from anli_v1.0.zip into a uid -> {round, split, gold, genre} index, parses
the separately released verifier_labels_R1-3.jsonl, joins them by uid, and tallies -- per (genre, class)
cell, restricted to R3 so the adversary round is held fixed -- how decisively ANLI's verifiers back the
writer's adversarial gold (strict-majority agreement, the fraction of individual votes equalling gold, and
the unanimous rate). The hand-traced fixture is asserted BEFORE any real file is touched.

This research is carried out by AI agents working in MV2's name at Munim, Inc. Apache-2.0.
"""
import argparse
import glob
import json
import os
import sys
import zipfile

import cases
from genre_class_agreement import (CELL_FIELDS, ROUNDS, census_genre_class, flatten,
                                   parse_verifier_row)


SPLITS = cases.SPLITS
LETTERS = ("e", "n", "c")


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


def _rates(cell):
    n = cell["n"]
    tv = cell["total_votes"]
    out = dict(cell)
    out["gold_majority_rate"] = (cell["gold_majority"] / n) if n else None
    out["no_majority_rate"] = (cell["no_majority"] / n) if n else None
    out["gold_support_rate"] = (cell["gold_votes"] / tv) if tv else None
    out["unanimous_rate"] = (cell["unanimous"] / n) if n else None
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # 1. Assert the hand-traced fixture BEFORE touching real data.
    fix_stats = census_genre_class([parse_verifier_row(o) for o in cases.FIXTURE_VERIFIER_RAW],
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

    # 3. Read both sides and run the per-(genre,class) within-R3 census.
    verifier_rows = read_verifier(verifier_files[0])
    gold_index, main_totals = read_main(zips[0])
    print("[diag] verifier lines =", len(verifier_rows), " main examples =", len(gold_index))
    stats = census_genre_class(verifier_rows, gold_index)
    t = stats["totals"]
    print("[diag] totals =", t)

    by_cell = {key: _rates(stats["by_cell"][key]) for key in sorted(stats["by_cell"])}
    for key, r in by_cell.items():
        print("[diag] R3 %-22s n=%6d gold_maj=%s support=%s unanimous=%s no_maj=%d"
              % (key, r["n"],
                 None if r["gold_majority_rate"] is None else round(r["gold_majority_rate"], 4),
                 None if r["gold_support_rate"] is None else round(r["gold_support_rate"], 4),
                 None if r["unanimous_rate"] is None else round(r["unanimous_rate"], 4),
                 r["no_majority"]))

    # Organise cells into a genre -> class -> rates map (R3, cells with n >= MIN_CELL_N).
    genres = sorted({key.split("|")[0] for key in by_cell})
    per_genre = {}
    for g in genres:
        row = {}
        for c in LETTERS:
            key = "%s|%s" % (g, c)
            if key in by_cell and by_cell[key]["n"] >= cases.MIN_CELL_N:
                row[c] = by_cell[key]
        per_genre[g] = row

    # 4. Pre-registered predictions (held/failed reported honestly).
    # P1 (structural): in EVERY cell with n >= MIN_CELL_N the gold == strict verifier majority rate > min.
    big_cells = {key: r for key, r in by_cell.items() if r["n"] >= cases.MIN_CELL_N}
    maj_rates = {key: r["gold_majority_rate"] for key, r in big_cells.items()
                 if r["gold_majority_rate"] is not None}
    min_cell = min(maj_rates, key=maj_rates.get) if maj_rates else None
    p1 = bool(maj_rates) and min(maj_rates.values()) > cases.MIN_GOLD_MAJORITY_RATE

    # P2 (directional): within R3, neutral has the lowest gold_support_rate of {e,n,c} in >= MIN genres.
    neutral_lowest = {}
    full_genres = []  # genres with all three classes present at n >= MIN_CELL_N
    for g in genres:
        row = per_genre[g]
        if all(c in row for c in LETTERS):
            full_genres.append(g)
            supports = {c: row[c]["gold_support_rate"] for c in LETTERS}
            lowest = min(supports, key=supports.get)
            neutral_lowest[g] = (lowest == "n")
    n_neutral_lowest = sum(1 for g in full_genres if neutral_lowest[g])
    p2 = n_neutral_lowest >= cases.MIN_GENRES_NEUTRAL_LOWEST

    # P3 (cross-check, reproduces audits 39/48/49): all joined gold==majority on the expected count, clean join.
    p3 = (t["all_lines_match"] == cases.EXPECTED_ALL_LINES_MATCH
          and t["n_joined"] == cases.EXPECTED_N_JOINED and t["n_orphan"] == 0
          and t["n_gold_unexpected"] == 0)

    predictions = {
        "P1_every_cell_gold_majority_above_min": p1,
        "P2_neutral_lowest_support_in_majority_of_genres": p2,
        "P3_reproduces_audit39_join": p3,
    }

    # Per-genre class ordering by gold_support_rate (for the write-up).
    class_support_by_genre = {}
    class_order_by_genre = {}
    for g in full_genres:
        row = per_genre[g]
        supports = {c: row[c]["gold_support_rate"] for c in LETTERS}
        class_support_by_genre[g] = supports
        class_order_by_genre[g] = sorted(LETTERS, key=lambda c: supports[c], reverse=True)

    print("[diag] P1 min cell gold_majority_rate =",
          None if not maj_rates else round(min(maj_rates.values()), 4), "at", min_cell)
    print("[diag] P2 neutral lowest-support in", n_neutral_lowest, "of", len(full_genres),
          "full genres:", neutral_lowest)
    print("[diag] P3 all_lines_match =", t["all_lines_match"], "n_joined =", t["n_joined"],
          "n_orphan =", t["n_orphan"])
    for k, v in predictions.items():
        print("[prediction] %s = %s" % (k, "HELD" if v else "FAILED"))

    out = {
        "dataset": "ANLI v1.0 (Nie, Williams, Dinan, Bansal, Weston and Kiela, 2020), R1/R2/R3, joined to "
                   "the separately released verifier_labels_R1-3.jsonl by uid. This audit tallies, per "
                   "(genre, gold-class) cell RESTRICTED TO R3 (the single round where all six genres "
                   "coexist, so the adversary round is held fixed), how decisively ANLI's verifiers back "
                   "the writer's adversarial gold: strict-majority agreement, the fraction of individual "
                   "verifier votes equalling gold (gold_support_rate), and the unanimous rate. It crosses "
                   "audit 49's genre dimension with audits 42/44/45's class dimension inside one round. The "
                   "all-lines match/differ/no-majority totals (over every joined line) reproduce audits "
                   "39/48/49 as a cross-check. Reuses audits 39/45/46/47/48/49 label/majority primitives "
                   "verbatim. Measures AGREEMENT, not correctness.",
        "rows_as_expected": (t["n_orphan"] == 0 and t["n_gold_unexpected"] == 0
                             and t["n_joined"] == cases.EXPECTED_N_JOINED),
        "synthetic_corpus": {"target_met": target_met, "observed": fix, "target": cases.TARGET},
        "main_totals_by_round_split": main_totals,
        "totals": t,
        "by_cell_r3": by_cell,
        "full_genres": full_genres,
        "class_support_by_genre": class_support_by_genre,
        "class_order_by_genre": class_order_by_genre,
        "neutral_lowest_by_genre": neutral_lowest,
        "n_genres_neutral_lowest": n_neutral_lowest,
        "predictions": predictions,
        "note": "Per-(genre, class) verifier agreement on ANLI's verified subset, within R3 only (round "
                "held fixed). gold_majority_rate = share of a cell's examples whose writer gold equals the "
                "strict verifier majority; gold_support_rate = fraction of that cell's individual verifier "
                "votes equalling the writer gold; unanimous_rate = share of lines on which all verifiers "
                "agree. P1 (structural, finding either way) bets gold == strict majority on >99% in EVERY "
                "cell with >=100 R3 examples. P2 (directional, finding either way) bets that WITHIN R3 "
                "neutral is the least decisively verified class (lowest gold_support_rate) in at least 4 of "
                "the 6 genres -- testing whether the 'neutral is hardest' class effect of audits 42/44/45 "
                "is robust across text domains once the round is fixed. P3 (cross-check) reproduces audits "
                "39/48/49 (gold == strict majority on 29,765 of 29,803 joined lines). Measures AGREEMENT, "
                "not correctness.",
    }
    out_path = os.path.join(args.out_dir, "results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False, default=str)
    print("[done] wrote", out_path)


if __name__ == "__main__":
    main()
