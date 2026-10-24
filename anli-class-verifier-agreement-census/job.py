"""Run the ANLI per-gold-class verifier-agreement census on the official release.

Reads the main ANLI gold labels from anli_v1.0.zip into a uid -> {split, round, gold} index, parses the
separately released verifier_labels_R1-3.jsonl, joins them by uid, and tallies -- per gold class (e/n/c)
-- the verifier unanimity, the gold-vs-strict-majority outcome, and the k=2/k=3 verifier-count mix. The
hand-traced fixture is asserted BEFORE any real file is touched. Writes results.json.

This research is carried out by AI agents working in MV2's name at Munim, Inc. Apache-2.0.
"""
import argparse
import glob
import json
import os
import sys
import zipfile

import cases
from class_census import LETTERS, census_by_class, flatten, parse_verifier_row

ROUNDS = cases.ROUNDS
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


def _rates(table):
    """Per-class rate dict from a per-class count table."""
    out = {}
    for g in LETTERS:
        c = table[g]
        n = c["n"]
        out[g] = {
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
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # 1. Assert the hand-traced fixture BEFORE touching real data.
    fix_stats = census_by_class([parse_verifier_row(o) for o in cases.FIXTURE_VERIFIER_RAW],
                                cases.build_gold_index(cases.FIXTURE_MAIN_RAW))
    fix = flatten(fix_stats)
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

    # 3. Read both sides and run the per-class census.
    verifier_rows = read_verifier(verifier_files[0])
    gold_index, main_totals = read_main(zips[0])
    print("[diag] verifier lines =", len(verifier_rows), " main examples =", len(gold_index))
    stats = census_by_class(verifier_rows, gold_index)
    t = stats["totals"]
    print("[diag] totals =", t)

    per_class = _rates(stats["per_class"])
    per_class_devtest = _rates(stats["per_class_devtest"])
    per_class_train = _rates(stats["per_class_train"])

    # 4. Pre-registered predictions (held/failed reported honestly).
    valid_classes = [g for g in LETTERS if per_class[g]["n"] > 0]
    match_rates = {g: per_class[g]["match_rate"] for g in valid_classes}
    unan_rates = {g: per_class[g]["unanimous_rate"] for g in valid_classes}
    min_unan_class = min(unan_rates, key=unan_rates.get)
    spread = max(unan_rates.values()) - min(unan_rates.values())
    ordering = sorted(valid_classes, key=lambda g: unan_rates[g], reverse=True)

    predictions = {
        "P1_gold_survives_verification_every_class": all(
            r is not None and r > cases.MIN_MATCH_RATE for r in match_rates.values()),
        "P2_neutral_least_unanimous_verifiers": ("n" in unan_rates and min_unan_class == "n"),
        "P3_unanimous_rate_spread_exceeds_min": spread > cases.MIN_UNANIMOUS_SPREAD,
    }
    for k, v in predictions.items():
        print("[prediction] %s = %s" % (k, "HELD" if v else "FAILED"))
    print("[diag] per-class unanimous_rate =", {g: round(unan_rates[g], 4) for g in unan_rates})
    print("[diag] per-class match_rate =", {g: round(match_rates[g], 4) for g in match_rates})
    print("[diag] unanimous-rate ordering (high->low) =", ordering, " spread =", round(spread, 4))
    k2_split_total = sum(stats["per_class"][g]["k2_split"] for g in LETTERS)
    print("[diag] k2_split anomalies (2-label lines whose verifiers disagree) =", k2_split_total)

    out = {
        "dataset": "ANLI v1.0 (Nie, Williams, Dinan, Bansal, Weston and Kiela, 2020), R1/R2/R3, joined to "
                   "the separately released verifier_labels_R1-3.jsonl by uid. ANLI's gold is the writer's "
                   "adversarial label; verifier labels are 2 independent checks (a 3rd added only when the "
                   "first 2 disagree). This audit breaks the writer-vs-verifier agreement down by gold "
                   "class, to test whether the per-class decisiveness pattern of SNLI (audit 42) and "
                   "MultiNLI (audit 44) -- neutral least decisive -- recurs with an adversarial gold and "
                   "independent verifiers. Reuses audit 39's label/majority primitives verbatim.",
        "rows_as_expected": (t["n_orphan"] == 0 and t["n_gold_unexpected"] == 0),
        "synthetic_corpus": {"target_met": target_met, "observed": fix, "target": cases.TARGET},
        "main_totals_by_round_split": main_totals,
        "totals": t,
        "per_class": per_class,
        "per_class_devtest": per_class_devtest,
        "per_class_train": per_class_train,
        "unanimous_rate_ordering_high_to_low": ordering,
        "unanimous_rate_spread": spread,
        "k2_split_anomalies": k2_split_total,
        "examples_differ": stats["examples_differ"],
        "predictions": predictions,
        "note": "Verifier unanimity = all verifier labels identical; under ANLI's protocol (a 3rd verifier "
                "is added only when the first 2 disagree) this equals 'the first two verifiers agreed, no "
                "third needed', i.e. a k=2 line. k2_split counts any 2-label line whose two verifiers in "
                "fact disagree (expected 0). match/differ/no_majority partition each class's examples by "
                "whether the writer's gold equals / differs from / lacks a strict verifier majority. P1 "
                "(structural) bets ANLI's adversarial gold equals the verifier majority on more than 95% of "
                "examples in EVERY class. P2 (directional, a finding either way) bets neutral is the LEAST "
                "unanimously verified class, mirroring SNLI/MultiNLI. P3 bets the per-class unanimous-rate "
                "spread exceeds 0.05. Rates are reported, not pre-bet on guessed numbers. per_class is over "
                "all joined examples with a recognised gold; per_class_devtest and per_class_train split it "
                "(audit 39 showed the released verifier file also covers train). This audit measures "
                "AGREEMENT per class, not label correctness.",
    }
    out_path = os.path.join(args.out_dir, "results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False, default=str)
    print("[done] wrote", out_path)


if __name__ == "__main__":
    main()
