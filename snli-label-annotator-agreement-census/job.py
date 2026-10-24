"""Per-gold-label annotator-agreement census over SNLI's validated five-vote dev + test splits.

Data (job.json data_urls, downloaded to --data-dir):
  - snli_1.0.zip -> read snli_1.0_dev.jsonl + snli_1.0_test.jsonl (both carry 5 annotator_labels).

For each valid-gold row we bucket by the normalised gold (e / n / c) and tally the unanimous rate, the
individual-agreement rate (the paper's "Agrmt"), and a by-construction check that the gold equals the
strict majority of the five labels. Rows whose gold is "-" (no majority) are counted separately.

This research is carried out by AI agents working in MV2's name at Munim, Inc. Apache-2.0.
"""
import argparse
import glob
import json
import os
import sys
import zipfile

import cases
from label_census import (
    census, flatten, unanimous_rate, individual_agreement_rate, aggregate_individual_agreement, LABELS,
)


def _rows_from_zip(zpath, wanted):
    """Yield parsed {'gold','annotators'} records for the wanted .jsonl members inside a zip."""
    with zipfile.ZipFile(zpath) as zf:
        for member in zf.namelist():
            if not member.endswith(".jsonl") or os.path.basename(member) not in wanted:
                continue
            with zf.open(member) as fh:
                for raw in fh.read().decode("utf-8").splitlines():
                    line = raw.strip()
                    if not line:
                        continue
                    obj = json.loads(line)
                    yield {
                        "gold": obj.get("gold_label"),
                        "annotators": obj.get("annotator_labels") or [],
                        "member": os.path.basename(member),
                    }


def _load_records(data_dir, wanted):
    zips = sorted(glob.glob(os.path.join(data_dir, "snli_1.0*.zip")))
    records = []
    per_member = {}
    for z in zips:
        for rec in _rows_from_zip(z, wanted):
            per_member[rec["member"]] = per_member.get(rec["member"], 0) + 1
            records.append(rec)
    return records, per_member, sorted(zips)


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
        if fix[k] != cases.TARGET[k]:
            print("  MISMATCH %-20s observed=%r target=%r" % (k, fix[k], cases.TARGET[k]))
    if not target_met:
        print("FATAL: fixture does not match hand-traced target", file=sys.stderr)
        sys.exit(2)

    # 2. Load SNLI dev + test from the zip.
    records, per_member, zips = _load_records(args.data_dir, set(cases.SNLI_MEMBERS))
    print("[diag] snli zips=%s per_member=%s n=%d" % (zips, per_member, len(records)))
    if not records:
        print("FATAL: could not read snli_1.0_dev/test from snli_1.0.zip", file=sys.stderr)
        sys.exit(3)
    rows_as_expected = (len(records) == cases.EXPECTED_TOTAL_ROWS)

    # 3. Census.
    stats = census(records)
    flat = flatten(stats)
    n_valid = stats["totals"]["n_valid"]
    n_dash = stats["totals"]["n_dash"]
    agg_agree = aggregate_individual_agreement(stats)

    rates = {}
    for L in LABELS:
        rates[L] = {
            "n": stats["per_label"][L]["n"],
            "unanimous": stats["per_label"][L]["unanimous"],
            "unanimous_rate": unanimous_rate(stats, L),
            "individual_agreement_rate": individual_agreement_rate(stats, L),
            "gold_eq_majority": stats["per_label"][L]["gold_eq_majority"],
        }
    print("[diag] per-label rates:")
    for L in LABELS:
        print("   %s: n=%d unanimous_rate=%.4f indiv=%.4f gold_eq_majority=%d/%d" % (
            L, rates[L]["n"], rates[L]["unanimous_rate"], rates[L]["individual_agreement_rate"],
            rates[L]["gold_eq_majority"], rates[L]["n"]))
    print("[diag] aggregate individual agreement = %.4f  (n_valid=%d, n_dash=%d)" % (
        agg_agree, n_valid, n_dash))

    # 4. Pre-registered predictions.
    #   P1 (structural / by construction): in every class gold == strict majority on all valid rows.
    #   P2 (directional, finding either way): neutral is LESS often unanimous than entailment.
    #   P3 (directional, finding either way): the per-class unanimous rates span more than 0.05.
    gold_is_majority_everywhere = all(
        stats["per_label"][L]["gold_eq_majority"] == stats["per_label"][L]["n"] for L in LABELS)
    u_rates = [unanimous_rate(stats, L) for L in LABELS]
    spread = max(u_rates) - min(u_rates)
    predictions = {
        "P1_gold_is_strict_majority_in_every_class": gold_is_majority_everywhere,
        "P2_neutral_less_unanimous_than_entailment":
            unanimous_rate(stats, "n") < unanimous_rate(stats, "e"),
        "P3_unanimous_rate_spread_exceeds_0_05": spread > cases.MIN_UNANIMOUS_SPREAD,
    }
    for k, v in predictions.items():
        print("[prediction] %s = %s" % (k, "HELD" if v else "FAILED"))
    print("[diag] unanimous-rate spread = %.4f" % spread)

    out = {
        "dataset": "SNLI 1.0 (Bowman, Angeli, Potts, Manning, EMNLP 2015), validated five-vote dev + test "
                   "splits read from snli_1.0.zip. Each valid-gold row is bucketed by its normalised gold "
                   "(entailment / neutral / contradiction) and tallied for unanimity and individual "
                   "annotator agreement; '-' (no-majority) rows are counted separately.",
        "members_read": per_member,
        "n_total": stats["totals"]["n_total"],
        "n_valid": n_valid,
        "n_dash": n_dash,
        "rows_as_expected": rows_as_expected,
        "expected_total_rows": cases.EXPECTED_TOTAL_ROWS,
        "aggregate_individual_agreement": agg_agree,
        "unanimous_rate_spread": spread,
        "per_label": rates,
        "synthetic_corpus": {"target_met": target_met, "observed": fix, "target": cases.TARGET},
        "predictions": predictions,
        "note": "Unanimous = all five annotators chose the gold. 'individual_agreement_rate' is the share "
                "of individual annotator labels equal to the gold (the SNLI paper's agreement statistic), "
                "reported per class and in aggregate. P1 is a by-construction check (expected to hold, as "
                "audit 37 verified across all splits); P2 and P3 are directional bets, a finding either "
                "way, with the exact per-class rates reported. This audit measures annotator AGREEMENT per "
                "class, not label correctness: a unanimous gold can still be wrong and a '-' row is not an "
                "error. It covers only the validated dev + test splits (SNLI train is largely "
                "single-annotator). This audit reads the official release and reports counts; it does not "
                "redistribute SNLI.",
    }
    out_path = os.path.join(args.out_dir, "results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False, default=str)
    print("[done] wrote", out_path)


if __name__ == "__main__":
    main()
