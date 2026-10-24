"""Run the ANLI verifier-majority / gold-derivation census on the official release.

The runner downloads two files to the data dir (job.json data_urls):
  - anli_v1.0.zip  (the main R1/R2/R3 train/dev/test jsonl, each row carrying uid, premise, hypothesis,
    label (gold), reason);
  - verifier_labels_R1-3.jsonl  (uid -> list of 2 or 3 verifier labels, dev/test only).

This script asserts the hand-traced fixture BEFORE touching real data, parses the verifier file, reads
the main gold labels straight from the zip into a uid -> {split, round, gold} index, joins the two,
counts how often the writer's gold label equals / differs from / has no strict verifier majority (per
round and split), records the pre-registered predictions, and writes results.json.

This research is carried out by AI agents working in MV2's name at Munim, Inc. Apache-2.0.
"""
import argparse
import glob
import json
import os
import sys
import zipfile

import cases
from anli_verifier import census, flatten, parse_verifier_row

ROUNDS = cases.ROUNDS
SPLITS = cases.SPLITS


def read_verifier(path):
    """Parse verifier_labels_R1-3.jsonl into [{uid, labels}, ...]."""
    rows = []
    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            rows.append(parse_verifier_row(json.loads(line)))
    return rows


def _member_round_split(name):
    """Return (round, split) for a main ANLI jsonl member, else (None, None)."""
    if not name.endswith(".jsonl") or name.endswith("/"):
        return None, None
    parts = name.split("/")
    rnd = next((p for p in parts if p in ROUNDS), None)
    stem = parts[-1][:-len(".jsonl")]
    split = stem if stem in SPLITS else None
    return rnd, split


def read_main(zip_path):
    """Read every R{1,2,3}/{train,dev,test}.jsonl from the zip into a uid -> {split, round, gold} index.

    Also returns per-(round, split) row totals for diagnostics.
    """
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
                    uid = obj.get("uid")
                    index[uid] = {"split": split, "round": rnd, "gold": obj.get("label")}
                    n += 1
            totals["%s/%s" % (rnd, split)] = n
    return index, totals


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # 1. Assert the hand-traced fixture BEFORE touching real data.
    fix = flatten(census([parse_verifier_row(o) for o in cases.FIXTURE_VERIFIER_RAW],
                         cases.build_gold_index(cases.FIXTURE_MAIN_RAW)))
    target_met = all(fix[k] == cases.TARGET[k] for k in cases.TARGET)
    print("[fixture] target_met =", target_met)
    for k in cases.TARGET:
        print("  %-30s observed=%r target=%r" % (k, fix[k], cases.TARGET[k]))
    if not target_met:
        print("FATAL: fixture does not match hand-traced target", file=sys.stderr)
        sys.exit(2)

    # 2. Locate the two downloads.
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

    # 3. Read both sides and join.
    verifier_rows = read_verifier(verifier_files[0])
    gold_index, main_totals = read_main(zips[0])
    print("[diag] verifier lines =", len(verifier_rows), " main examples =", len(gold_index))
    print("[diag] main totals by round/split =", main_totals)
    stats = census(verifier_rows, gold_index)

    # 4. Pre-registered predictions (held/failed reported honestly).
    predictions = {
        "P1_verification_is_dev_test_only": stats["n_join_train"] == 0,
        "P2_every_verifier_line_has_2_or_3_labels": stats["n_k_other"] == 0,
        "P3_anli_gold_differs_from_verifier_majority": stats["n_gold_differs_from_majority"] > 0,
    }
    for k, v in predictions.items():
        print("[prediction] %s = %s" % (k, "HELD" if v else "FAILED"))

    denom = stats["n_joined"] - stats["n_gold_unexpected"]
    rates = {
        "gold_matches_majority_frac": (stats["n_gold_matches_majority"] / denom) if denom else None,
        "gold_differs_from_majority_frac": (stats["n_gold_differs_from_majority"] / denom) if denom else None,
        "no_majority_frac": (stats["n_no_majority"] / denom) if denom else None,
        "unanimous_differs_from_gold_frac": (stats["n_unanimous_differs_from_gold"] / denom) if denom else None,
    }
    print("[diag] joined=%d match=%d differ=%d no_majority=%d unanimous_differ=%d orphan=%d" % (
        stats["n_joined"], stats["n_gold_matches_majority"], stats["n_gold_differs_from_majority"],
        stats["n_no_majority"], stats["n_unanimous_differs_from_gold"], stats["n_orphan"]))
    print("[diag] per_round =", stats["per_round"])
    print("[diag] rates =", rates)

    out = {
        "dataset": "ANLI v1.0 (Nie, Williams, Dinan, Bansal, Weston and Kiela, 2020), R1/R2/R3, joined to "
                   "the separately released verifier_labels_R1-3.jsonl (dev/test examples checked by 2 or "
                   "3 verifiers). ANLI's gold label is the writer's label, retained whether or not the "
                   "verifiers later agreed -- so gold == verifier majority is a genuine, non-tautological "
                   "question here, unlike SNLI (audit 37) and MultiNLI (audit 38) where gold is defined as "
                   "the annotator majority.",
        "rows_as_expected": True,
        "synthetic_corpus": {"target_met": target_met, "observed": fix, "target": cases.TARGET},
        "main_totals_by_round_split": main_totals,
        "census": stats,
        "rates": rates,
        "predictions": predictions,
        "note": "For each verifier line, uid is joined to the main example. gold is the writer's label "
                "(ANLI field 'label'); verifier labels are 2 (or 3 when the first 2 disagreed) independent "
                "checks. strict majority = a label held by more than half the verifier votes (a 1-1 pair "
                "or a 1-1-1 triple has none). n_gold_matches_majority / n_gold_differs_from_majority / "
                "n_no_majority partition the joined dev/test examples with a recognised gold. "
                "n_unanimous_differs_from_gold counts the striking case where every verifier agreed with "
                "each other but none agreed with the writer's gold. P1 bets verification is dev/test only "
                "(no verifier uid maps to a train example); P2 bets every verifier line carries 2 or 3 "
                "labels; P3 bets -- unlike the majority-defined SNLI/MultiNLI gold -- ANLI's gold differs "
                "from the verifier majority on a nonzero number of rows. The exact agreement rate is "
                "reported, not pre-bet on a guessed number; orphan verifier uids (no main example) are "
                "reported, not bet on.",
    }
    out_path = os.path.join(args.out_dir, "results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False, default=str)
    print("[done] wrote", out_path)


if __name__ == "__main__":
    main()
