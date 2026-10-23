"""Run the ARC disjointness / cross-split leakage / gold-conflict census on the official corpus.

The runner downloads ARC-V1-Feb2018.zip to the data dir (job.json data_urls). This script asserts
the hand-traced fixture BEFORE touching real data, reads the six ARC jsonl splits (Easy and
Challenge x train/dev/test) straight from the zip, verifies per-split counts against the published
totals and prints the first row's schema, runs the within-split census plus the Easy<->Challenge and
cross-split overlap checks, records pre-registered predictions, and writes results.json.

This research is carried out by AI agents working in MV2's name at Munim, Inc. Apache-2.0.
"""
import argparse
import glob
import itertools
import json
import os
import sys
import zipfile

import cases
from arc_consistency import flatten, overlap, parse_row, within_file

# Published row counts (Clark et al. 2018 / AI2 release). Reported, not fatal on mismatch.
EXPECTED = {
    "c_train": 1119, "c_dev": 299, "c_test": 1172,
    "e_train": 2251, "e_dev": 570, "e_test": 2376,
}
CHALLENGE = ["c_train", "c_dev", "c_test"]
EASY = ["e_train", "e_dev", "e_test"]

# map lowercased jsonl basename -> split name
JSONL = {
    "arc-challenge-train.jsonl": "c_train", "arc-challenge-dev.jsonl": "c_dev",
    "arc-challenge-test.jsonl": "c_test", "arc-easy-train.jsonl": "e_train",
    "arc-easy-dev.jsonl": "e_dev", "arc-easy-test.jsonl": "e_test",
}


def _base(member):
    return os.path.basename(member.replace("\\", "/")).lower()


def read_everything(zip_path):
    """Read every split's parsed records, raw counts and first raw object."""
    records = {}
    raw_counts = {}
    first = {}
    with zipfile.ZipFile(zip_path) as z:
        for m in z.namelist():
            low = m.replace("\\", "/").lower()
            if low.startswith("__macosx") or low.endswith("/"):
                continue
            base = _base(m)
            if base in JSONL:
                split = JSONL[base]
                recs = []
                with z.open(m) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        obj = json.loads(line)
                        if split not in first:
                            first[split] = obj
                        recs.append(parse_row(obj))
                # a split may theoretically appear in two members; keep the first non-empty
                if split not in records or not records[split]:
                    records[split] = recs
                    raw_counts[split] = len(recs)
    return records, raw_counts, first


def describe_first(obj):
    if obj is None:
        return "<none>"
    q = obj.get("question")
    stem = q.get("stem") if isinstance(q, dict) else q
    nchoices = len(q.get("choices", [])) if isinstance(q, dict) else None
    return "id=%r answerKey=%r nchoices=%r stem=%r" % (
        obj.get("id"), obj.get("answerKey"), nchoices, (stem or "")[:50])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # 1. Assert the hand-traced fixture BEFORE touching real data.
    within_fix = {n: within_file([parse_row(o) for o in f])
                  for n, f in zip(cases.NAMES, [cases.FIXTURE_X, cases.FIXTURE_Y])}
    overlap_fix = {("X", "Y"): overlap([parse_row(o) for o in cases.FIXTURE_X],
                                       [parse_row(o) for o in cases.FIXTURE_Y])}
    fix = flatten(within_fix, overlap_fix, cases.NAMES, cases.PAIRS)
    target_met = all(fix[k] == cases.TARGET[k] for k in cases.TARGET)
    print("[fixture] target_met =", target_met)
    for k in cases.TARGET:
        print("  %-38s observed=%r target=%r" % (k, fix[k], cases.TARGET[k]))
    if not target_met:
        print("FATAL: fixture does not match hand-traced target", file=sys.stderr)
        sys.exit(2)

    # 2. Locate the zip.
    zip_paths = sorted(glob.glob(os.path.join(args.data_dir, "*.zip")))
    print("[diag] zips in data dir:", zip_paths)
    if not zip_paths:
        print("FATAL: no zip found in data dir", file=sys.stderr)
        sys.exit(3)

    # 3. Read every split.
    records, raw_counts, first = read_everything(zip_paths[0])
    print("[diag] raw per-split counts =", raw_counts)
    for split in CHALLENGE + EASY:
        print("[diag] %s first row: %s" % (split, describe_first(first.get(split))))
    missing = [s for s in CHALLENGE + EASY if s not in records or not records[s]]
    if missing:
        print("FATAL: missing or empty splits: %r" % missing, file=sys.stderr)
        sys.exit(4)

    rows_as_expected = all(raw_counts.get(s) == EXPECTED[s] for s in EXPECTED)
    print("[diag] rows_as_expected =", rows_as_expected, "(expected %r)" % EXPECTED)

    # 4. Within-split census.
    within = {s: within_file(records[s]) for s in CHALLENGE + EASY}

    # 5. Easy <-> Challenge disjointness (pooled over each set's three splits).
    challenge_all = [r for s in CHALLENGE for r in records[s]]
    easy_all = [r for s in EASY for r in records[s]]
    easy_vs_challenge = overlap(easy_all, challenge_all)
    print("[census] easy vs challenge:", easy_vs_challenge)

    # 6. Within-set cross-split leakage (each pair of the three splits in a set).
    cross_split = {}
    for setname, splits in (("challenge", CHALLENGE), ("easy", EASY)):
        for a, b in itertools.combinations(splits, 2):
            cross_split["%s:%s|%s" % (setname, a, b)] = overlap(records[a], records[b])
    for k, v in cross_split.items():
        print("[census] cross-split", k, "shared_ids=%d shared_identities=%d"
              % (v["shared_ids"], v["shared_identities"]))

    # 7. Pre-registered predictions (held/failed reported honestly).
    within_conf = sum(within[s]["identity_keys_conflict"] for s in within)
    cross_split_leak_ids = sum(v["shared_ids"] for v in cross_split.values())
    predictions = {
        "P1_easy_challenge_disjoint_by_id": easy_vs_challenge["shared_ids"] == 0,
        "P2_easy_challenge_disjoint_by_identity": easy_vs_challenge["shared_identities"] == 0,
        "P3_no_cross_split_id_leakage_within_set": cross_split_leak_ids == 0,
        "P4_no_within_split_gold_conflict": within_conf == 0,
    }
    for k, v in predictions.items():
        print("[prediction] %s = %s" % (k, "HELD" if v else "FAILED"))

    out = {
        "dataset": "AI2 ARC (ARC-V1-Feb2018; Clark et al., 2018), CC BY-SA 4.0",
        "expected_rows_per_split": EXPECTED,
        "observed_rows_per_split": raw_counts,
        "rows_as_expected": rows_as_expected,
        "synthetic_corpus": {"target_met": target_met, "observed": fix, "target": cases.TARGET},
        "within_split": within,
        "easy_vs_challenge": easy_vs_challenge,
        "cross_split": cross_split,
        "predictions": predictions,
        "note": "Identity = normalized (stem, frozenset of choice texts); gold = the choice text "
                "whose label == answerKey. Malformed rows (answerKey matches no label) are counted "
                "and excluded from the identity/gold analysis. easy_vs_challenge pools each set's "
                "three splits and counts shared ids, shared identities and shared-identity gold "
                "conflicts. cross_split counts leakage between the train/dev/test splits inside each "
                "set. within_split counts duplicate ids and self-conflicting duplicate questions.",
    }
    out_path = os.path.join(args.out_dir, "results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False, default=str)
    print("[done] wrote", out_path)


if __name__ == "__main__":
    main()
