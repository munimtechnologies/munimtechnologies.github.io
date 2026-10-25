"""Run the ANLI per-(round, class) verifier-agreement census on the official release.

Reads the main ANLI gold labels from anli_v1.0.zip into a uid -> {split, round, gold} index, parses the
separately released verifier_labels_R1-3.jsonl, joins them by uid, and tallies -- per (round, gold class)
-- the verifier unanimity, the gold-vs-strict-majority outcome, and the k=2/k=3 verifier-count mix. Also
reports the per-round aggregate (reproducing audit 39) and the per-class aggregate (reproducing audit 45)
as built-in cross-checks. The hand-traced fixture is asserted BEFORE any real file is touched.

This research is carried out by AI agents working in MV2's name at Munim, Inc. Apache-2.0.
"""
import argparse
import glob
import json
import os
import sys
import zipfile

import cases
from round_class_census import (
    LETTERS, ROUNDS, aggregate_over_classes, aggregate_over_rounds, census_by_round_class,
    flatten_rc, parse_verifier_row,
)

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
                    index[obj.get("uid")] = {"split": split, "round": rnd, "gold": obj.get("label")}
                    n += 1
            totals["%s/%s" % (rnd, split)] = n
    return index, totals


def _rates_cell(c):
    n = c["n"]
    return {
        "n": n,
        "unanimous": c["unanimous"],
        "unanimous_rate": (c["unanimous"] / n) if n else None,
        "match": c["match"],
        "match_rate": (c["match"] / n) if n else None,
        "differ": c["differ"],
        "no_majority": c["no_majority"],
        "no_majority_rate": (c["no_majority"] / n) if n else None,
        "k2": c["k2"], "k3": c["k3"], "k_other": c["k_other"], "k2_split": c["k2_split"],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # 1. Assert the hand-traced fixture BEFORE touching real data.
    fix_stats = census_by_round_class([parse_verifier_row(o) for o in cases.FIXTURE_VERIFIER_RAW],
                                      cases.build_gold_index(cases.FIXTURE_MAIN_RAW))
    fix = flatten_rc(fix_stats["per_round_class"], fix_stats["totals"])
    target_met = all(fix[k] == cases.TARGET[k] for k in cases.TARGET) and set(fix) == set(cases.TARGET)
    print("[fixture] target_met =", target_met)
    if not target_met:
        for k in sorted(set(fix) | set(cases.TARGET)):
            o, t = fix.get(k), cases.TARGET.get(k)
            if o != t:
                print("  MISMATCH %-16s observed=%r target=%r" % (k, o, t))
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

    # 3. Read both sides and run the per-(round, class) census.
    verifier_rows = read_verifier(verifier_files[0])
    gold_index, main_totals = read_main(zips[0])
    print("[diag] verifier lines =", len(verifier_rows), " main examples =", len(gold_index))
    stats = census_by_round_class(verifier_rows, gold_index)
    t = stats["totals"]
    print("[diag] totals =", t)

    prc = stats["per_round_class"]
    per_round_class = {r: {g: _rates_cell(prc[r][g]) for g in LETTERS} for r in ROUNDS}
    per_round = {r: _rates_cell(c) for r, c in aggregate_over_classes(prc).items()}
    per_class = {g: _rates_cell(c) for g, c in aggregate_over_rounds(prc).items()}

    # 4. Pre-registered predictions (held/failed reported honestly).
    # P1 (structural): in every round the overall match rate (across classes) exceeds MIN_MATCH_RATE.
    rounds_present = [r for r in ROUNDS if per_round[r]["n"] > 0]
    p1 = all(per_round[r]["match_rate"] is not None and per_round[r]["match_rate"] > cases.MIN_MATCH_RATE
             for r in rounds_present)

    # P2 (directional): within EVERY round, neutral is the least unanimously verified class present.
    def least_unanimous_class(r):
        present = [g for g in LETTERS if per_round_class[r][g]["n"] > 0
                   and per_round_class[r][g]["unanimous_rate"] is not None]
        if not present:
            return None
        return min(present, key=lambda g: per_round_class[r][g]["unanimous_rate"])
    least_by_round = {r: least_unanimous_class(r) for r in rounds_present}
    p2 = all(least_by_round[r] == "n" for r in rounds_present) and len(rounds_present) > 0

    # P3 (directional): overall verifier unanimous rate is non-decreasing across rounds (R1 <= R2 <= R3).
    unan_by_round = [per_round[r]["unanimous_rate"] for r in rounds_present]
    p3 = all(unan_by_round[i] <= unan_by_round[i + 1] for i in range(len(unan_by_round) - 1)) \
        and len(unan_by_round) >= 2

    predictions = {
        "P1_match_rate_above_min_every_round": p1,
        "P2_neutral_least_unanimous_within_every_round": p2,
        "P3_verifier_unanimity_nondecreasing_by_round": p3,
    }
    for k, v in predictions.items():
        print("[prediction] %s = %s" % (k, "HELD" if v else "FAILED"))

    # Per-round, per-class ordering + spread diagnostics.
    round_orderings = {}
    round_spreads = {}
    for r in rounds_present:
        present = [g for g in LETTERS if per_round_class[r][g]["n"] > 0]
        ur = {g: per_round_class[r][g]["unanimous_rate"] for g in present}
        round_orderings[r] = sorted(present, key=lambda g: ur[g], reverse=True)
        round_spreads[r] = (max(ur.values()) - min(ur.values())) if ur else None
        print("[diag] %s unanimous_rate =" % r, {g: round(ur[g], 4) for g in ur},
              " ordering =", round_orderings[r], " spread =", round(round_spreads[r], 4),
              " match_rate =", round(per_round[r]["match_rate"], 4))
    print("[diag] least-unanimous class by round =", least_by_round)
    k2_split_total = sum(prc[r][g]["k2_split"] for r in ROUNDS for g in LETTERS)
    print("[diag] k2_split anomalies (2-label lines whose verifiers disagree) =", k2_split_total)

    out = {
        "dataset": "ANLI v1.0 (Nie, Williams, Dinan, Bansal, Weston and Kiela, 2020), R1/R2/R3, joined to "
                   "the separately released verifier_labels_R1-3.jsonl by uid. This audit crosses the ROUND "
                   "dimension of audit 39 with the gold-CLASS dimension of audit 45: it tallies verifier "
                   "unanimity and writer-gold-vs-verifier-majority agreement per (round, class), to test "
                   "whether audit 45's aggregate 'neutral least decisive' holds WITHIN each adversarial "
                   "round (guarding against a Simpson's-paradox round-composition artifact) and whether "
                   "verifier decisiveness shifts as ANLI's model-in-the-loop adversary strengthens from R1 "
                   "to R3. Reuses audit 39/45 label/majority primitives verbatim.",
        "rows_as_expected": (t["n_orphan"] == 0 and t["n_gold_unexpected"] == 0),
        "synthetic_corpus": {"target_met": target_met, "observed": fix, "target": cases.TARGET},
        "main_totals_by_round_split": main_totals,
        "totals": t,
        "per_round_class": per_round_class,
        "per_round_aggregate": per_round,
        "per_class_aggregate": per_class,
        "round_unanimous_orderings_high_to_low": round_orderings,
        "round_unanimous_spreads": round_spreads,
        "least_unanimous_class_by_round": least_by_round,
        "k2_split_anomalies": k2_split_total,
        "examples_differ": stats["examples_differ"],
        "predictions": predictions,
        "note": "Verifier unanimity = all verifier labels identical (under ANLI's protocol a 3rd verifier "
                "is added only when the first 2 disagree, so this equals 'the first two agreed'). "
                "match/differ/no_majority partition each (round, class) cell by whether the writer's gold "
                "equals / differs from / lacks a strict verifier majority. P1 (structural) bets the overall "
                "writer-gold == verifier-majority rate exceeds 0.95 in EVERY round. P2 (directional, a "
                "finding either way) bets neutral is the least unanimously verified class WITHIN every "
                "round, testing whether audit 45's pooled finding is a within-round effect. P3 (directional) "
                "bets overall verifier unanimity is non-decreasing from R1 to R3 as the adversary "
                "strengthens. per_class_aggregate reproduces audit 45's per_class exactly; "
                "per_round_aggregate reproduces audit 39's per-round split. This audit measures AGREEMENT, "
                "not label correctness.",
    }
    out_path = os.path.join(args.out_dir, "results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False, default=str)
    print("[done] wrote", out_path)


if __name__ == "__main__":
    main()
