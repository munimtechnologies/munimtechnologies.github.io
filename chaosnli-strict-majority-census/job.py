"""Run the ChaosNLI strict-majority / old-gold-stability census on the official release.

The runner downloads the three ChaosNLI jsonl files to the data dir (job.json data_urls):
  - chaosNLI_snli.jsonl, chaosNLI_mnli_m.jsonl  (3-way NLI, label_count ordered [E, N, C])
  - chaosNLI_alphanli.jsonl                      (2-choice abductive NLI, label_count [1, 2])
Each record carries uid, old_label (the original 5-annotator gold), majority_label (the 100-annotation
plurality), label_count (per-label vote counts summing to 100), and entropy. (If only a zip is present
the jsonl members are extracted from it.)

This script asserts the hand-traced fixture BEFORE touching real data, parses each subset with its own
label-name ordering, runs the census, records the pre-registered predictions (verifying the documented
old!=majority counts and measuring how often even 100 annotators lack a strict majority), and writes
results.json.

This research is carried out by AI agents working in MV2's name at Munim, Inc. Apache-2.0.
"""
import argparse
import glob
import json
import os
import sys
import zipfile

import cases
from chaos_derivation import census, flatten


def _subset_of(path):
    name = os.path.basename(path).lower()
    if "mnli" in name:
        return "mnli_m"
    if "alphanli" in name or "abdnli" in name:
        return "alphanli"
    if "snli" in name:
        return "snli"
    return None


def _records_from_lines(lines, subset):
    names = cases.SUBSET_NAMES[subset]
    recs = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        obj = json.loads(line)
        counts = obj.get("label_count")
        if not isinstance(counts, list):
            counts = []
        counts = [int(c) for c in counts]
        recs.append({
            "uid": obj.get("uid"),
            "old": _norm(obj.get("old_label")),
            "majority": _norm(obj.get("majority_label")),
            "counts": counts,
            "names": names,
            "entropy": obj.get("entropy"),
        })
    return recs


def _norm(x):
    from chaos_derivation import norm_label
    return norm_label(x)


def _load_subsets(data_dir):
    """Return {subset: [raw_json_line, ...]} from any chaosNLI_*.jsonl files (or a zip) in data_dir."""
    out = {}
    for path in sorted(glob.glob(os.path.join(data_dir, "*.jsonl"))):
        subset = _subset_of(path)
        if subset is None:
            continue
        with open(path, "r", encoding="utf-8") as fh:
            out[subset] = fh.readlines()
    if out:
        return out
    for zpath in sorted(glob.glob(os.path.join(data_dir, "*.zip"))):
        with zipfile.ZipFile(zpath) as zf:
            for member in zf.namelist():
                if not member.endswith(".jsonl"):
                    continue
                subset = _subset_of(member)
                if subset is None:
                    continue
                with zf.open(member) as fh:
                    out[subset] = fh.read().decode("utf-8").splitlines()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # 1. Assert the hand-traced fixture BEFORE touching real data.
    fix = flatten(census(cases.FIXTURE))
    target_met = all(fix[k] == cases.TARGET[k] for k in cases.TARGET)
    print("[fixture] target_met =", target_met)
    for k in cases.TARGET:
        print("  %-28s observed=%r target=%r" % (k, fix[k], cases.TARGET[k]))
    if not target_met:
        print("FATAL: fixture does not match hand-traced target", file=sys.stderr)
        sys.exit(2)

    # 2. Load the subsets.
    subsets = _load_subsets(args.data_dir)
    print("[diag] subsets found:", sorted(subsets))
    if "snli" not in subsets or "mnli_m" not in subsets:
        print("FATAL: snli and mnli_m jsonl both required", file=sys.stderr)
        sys.exit(3)

    # 3. Census each subset.
    per_subset = {}
    for subset in sorted(subsets):
        recs = _records_from_lines(subsets[subset], subset)
        stats = census(recs)
        per_subset[subset] = stats
        print("[diag] %s: records=%d sum100=%d old!=maj=%d no_strict=%d old_on_no_strict=%d "
              "maj==plur=%d entropy_max=%.4f" % (
                  subset, stats["n_records"], stats["n_sum100"], stats["n_old_differs_majority"],
                  stats["n_no_strict_majority"], stats["n_old_on_no_strict"],
                  stats["n_majority_eq_plurality"], stats["entropy_max"] or 0.0))

    # 4. Pre-registered predictions (held/failed reported honestly).
    snli = per_subset["snli"]
    mnli = per_subset["mnli_m"]
    all_sum100 = all(per_subset[s]["n_sum100"] == per_subset[s]["n_records"] for s in per_subset)
    predictions = {
        "P1_old_differs_majority_matches_card": (
            snli["n_old_differs_majority"] == cases.CARD_OLD_DIFFERS_MAJORITY["snli"]
            and mnli["n_old_differs_majority"] == cases.CARD_OLD_DIFFERS_MAJORITY["mnli_m"]),
        "P2_all_counts_sum_to_100": all_sum100,
        "P3_some_examples_lack_strict_majority_at_100": (
            snli["n_no_strict_majority"] + mnli["n_no_strict_majority"] > 0),
    }
    for k, v in predictions.items():
        print("[prediction] %s = %s" % (k, "HELD" if v else "FAILED"))

    rows_as_expected = all(
        per_subset[s]["n_records"] == cases.SUBSET_ROWS[s] for s in per_subset if s in cases.SUBSET_ROWS)

    rates = {}
    for s in sorted(per_subset):
        st = per_subset[s]
        n = st["n_records"] or 1
        rates[s] = {
            "old_differs_majority_frac": st["n_old_differs_majority"] / n,
            "no_strict_majority_frac": st["n_no_strict_majority"] / n,
            "old_on_no_strict_frac": st["n_old_on_no_strict"] / n,
        }
    print("[diag] rates =", rates)

    out = {
        "dataset": "ChaosNLI v1.0 (Nie, Zhou and Bansal, EMNLP 2020): 100 fresh crowd annotations per "
                   "example for samples of the SNLI, MNLI-matched and alphaNLI development sets. Each "
                   "record carries old_label (the original 5-annotator benchmark gold), majority_label "
                   "(the 100-annotation plurality), and label_count (per-label vote counts summing to "
                   "100). Unlike SNLI/MultiNLI (audits 37/38) the comparison here is non-tautological: it "
                   "pits the original gold against an independent, much larger annotation round.",
        "rows_as_expected": rows_as_expected,
        "synthetic_corpus": {"target_met": target_met, "observed": fix, "target": cases.TARGET},
        "subset_rows_expected": cases.SUBSET_ROWS,
        "card_old_differs_majority_expected": cases.CARD_OLD_DIFFERS_MAJORITY,
        "per_subset": per_subset,
        "rates": rates,
        "predictions": predictions,
        "note": "For each example we read label_count (per-label votes, sum 100), the original gold "
                "old_label, and ChaosNLI's majority_label (a plurality / argmax). strict_majority = a "
                "label with strictly more than half (> 50) of the 100 votes; plurality = the unique "
                "argmax (a tie at the top -> none). n_old_differs_majority verifies ChaosNLI's documented "
                "old-vs-plurality disagreement (378 SNLI / 508 MNLI). n_no_strict_majority counts "
                "examples where even 100 fresh annotators reach no strict majority, yet the benchmark "
                "assigns one hard gold label; n_old_on_no_strict counts how many of those still carry an "
                "old gold. n_majority_eq_plurality checks that ChaosNLI's majority_label equals our "
                "recomputed argmax. P1 verifies the documented disagreement counts; P2 that every "
                "label_count sums to 100; P3 (direction only, exact count reported) that a nonzero number "
                "of examples lack a strict 100-vote majority. alphaNLI is reported (2-choice) but not bet "
                "on; headline predictions are on the two 3-way subsets.",
    }
    out_path = os.path.join(args.out_dir, "results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False, default=str)
    print("[done] wrote", out_path)


if __name__ == "__main__":
    main()
