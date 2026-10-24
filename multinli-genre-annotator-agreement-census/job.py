"""Census MultiNLI's validated development sets for per-genre annotator agreement.

Data (job.json data_urls, downloaded to --data-dir):
  - multinli_1.0.zip  -> read multinli_1.0_dev_matched.jsonl + multinli_1.0_dev_mismatched.jsonl
    (both carry `genre`, `gold_label` and five `annotator_labels`; the train file is single-label).

For every dev example we read its genre, released gold label and five annotator labels, then
(genre_census.py) tally per genre: how many annotators agreed with gold (5/4/3/"-"=dash), the unanimous
share, the individual-label-equals-gold share, and a by-construction check that the gold equals the strict
majority of the five labels. The MultiNLI paper reports these only in aggregate; this is the first
per-genre breakdown over the released files.

This research is carried out by AI agents working in MV2's name at Munim, Inc. Apache-2.0.
"""
import argparse
import glob
import json
import os
import sys
import zipfile

import cases
from genre_census import census, flatten, unanimous_rate, individual_agreement_rate


_DEV_MEMBERS = ("multinli_1.0_dev_matched.jsonl", "multinli_1.0_dev_mismatched.jsonl")


def _member_wanted(member, wanted):
    return os.path.basename(member) in wanted


def _records_from_zip(zpath, wanted):
    """Yield parsed {genre, gold, annotator_labels} records from the wanted dev members of a zip."""
    with zipfile.ZipFile(zpath) as zf:
        for member in zf.namelist():
            if not member.endswith(".jsonl") or not _member_wanted(member, wanted):
                continue
            with zf.open(member) as fh:
                for raw in fh.read().decode("utf-8").splitlines():
                    line = raw.strip()
                    if not line:
                        continue
                    obj = json.loads(line)
                    yield {
                        "genre": obj.get("genre"),
                        "gold": obj.get("gold_label"),
                        "annotator_labels": obj.get("annotator_labels") or [],
                        "src": os.path.basename(member),
                    }


def _records_from_loose(data_dir, wanted):
    for path in sorted(glob.glob(os.path.join(data_dir, "*.jsonl"))):
        if not _member_wanted(path, wanted):
            continue
        with open(path, "r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line:
                    continue
                obj = json.loads(line)
                yield {
                    "genre": obj.get("genre"),
                    "gold": obj.get("gold_label"),
                    "annotator_labels": obj.get("annotator_labels") or [],
                    "src": os.path.basename(path),
                }


def _load_dev(data_dir):
    zips = sorted(glob.glob(os.path.join(data_dir, "multinli_1.0*.zip")))
    if zips:
        return [r for z in zips for r in _records_from_zip(z, _DEV_MEMBERS)]
    return list(_records_from_loose(data_dir, _DEV_MEMBERS))


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
            print("  MISMATCH %-28s observed=%r target=%r" % (k, fix[k], cases.TARGET[k]))
    if not target_met:
        print("FATAL: fixture does not match hand-traced target", file=sys.stderr)
        sys.exit(2)

    # 2. Load the two validated dev files.
    records = _load_dev(args.data_dir)
    print("[diag] loaded %d dev records" % len(records))
    if not records:
        print("FATAL: could not load MultiNLI dev records", file=sys.stderr)
        sys.exit(3)

    stats = census(records)
    totals = stats["totals"]
    rows_as_expected = (totals["n"] == cases.EXPECTED_TOTAL_DEV_ROWS)
    print("[diag] totals n=%d valid=%d dash=%d unanimous=%d gold_eq_majority=%d (rows_as_expected=%s)" % (
        totals["n"], totals["valid"], totals["dash"], totals["unanimous"],
        totals["gold_eq_majority"], rows_as_expected))

    # 3. Per-genre rate table (sorted by unanimous rate descending).
    genre_rows = []
    for genre, cell in stats["genres"].items():
        genre_rows.append({
            "genre": genre,
            "n": cell["n"],
            "valid": cell["valid"],
            "dash": cell["dash"],
            "unanimous": cell["unanimous"],
            "b5": cell["b5"], "b4": cell["b4"], "b3": cell["b3"], "bother": cell["bother"],
            "gold_eq_majority": cell["gold_eq_majority"],
            "unanimous_rate": unanimous_rate(stats, genre),
            "individual_agreement_rate": individual_agreement_rate(stats, genre),
            "is_matched": genre in cases.MATCHED_GENRES,
        })
    genre_rows.sort(key=lambda r: r["unanimous_rate"], reverse=True)
    for r in genre_rows:
        print("[genre] %-12s matched=%-5s n=%5d valid=%5d dash=%3d unanimous=%.4f indiv=%.4f gold==maj=%s" % (
            r["genre"], r["is_matched"], r["n"], r["valid"], r["dash"],
            r["unanimous_rate"], r["individual_agreement_rate"], r["gold_eq_majority"] == r["valid"]))

    # 4. Pre-registered predictions.
    #   P1 (structural, by construction): in every genre the released gold equals the strict majority of
    #       the five labels -> gold_eq_majority == valid for each genre and overall.
    #   P2 (directional, finding either way): telephone (transcribed speech) is less often unanimous than
    #       government (formal written text).
    #   P3 (directional, finding either way): per-genre unanimous rates span more than P3_SPREAD_THRESHOLD
    #       (genres differ meaningfully in how decisive their gold labels are).
    p1 = all(c["gold_eq_majority"] == c["valid"] for c in stats["genres"].values()) \
        and totals["gold_eq_majority"] == totals["valid"]
    r_tel = unanimous_rate(stats, "telephone")
    r_gov = unanimous_rate(stats, "government")
    valid_rates = [r["unanimous_rate"] for r in genre_rows if r["valid"] > 0]
    spread = (max(valid_rates) - min(valid_rates)) if valid_rates else 0.0
    predictions = {
        "P1_gold_equals_majority_every_genre": p1,
        "P2_telephone_less_unanimous_than_government": r_tel < r_gov,
        "P3_unanimous_rate_spread_exceeds_threshold": spread > cases.P3_SPREAD_THRESHOLD,
    }
    for k, v in predictions.items():
        print("[prediction] %s = %s" % (k, "HELD" if v else "FAILED"))
    print("[diag] telephone unanimous=%.4f government unanimous=%.4f spread=%.4f" % (r_tel, r_gov, spread))

    out = {
        "dataset": "MultiNLI 1.0 (Williams, Nangia, Bowman, NAACL 2018) validated development sets "
                   "(dev_matched + dev_mismatched). For every example we read genre, gold_label and the "
                   "five annotator_labels, and tally annotator agreement per genre. The paper reports "
                   "agreement only in aggregate; this is a per-genre breakdown over the released files.",
        "n_records": totals["n"],
        "rows_as_expected": rows_as_expected,
        "expected_total_dev_rows": cases.EXPECTED_TOTAL_DEV_ROWS,
        "totals": totals,
        "per_genre": genre_rows,
        "synthetic_corpus": {"target_met": target_met, "observed": fix, "target": cases.TARGET},
        "predictions": predictions,
        "rates_used_by_predictions": {
            "telephone_unanimous_rate": r_tel,
            "government_unanimous_rate": r_gov,
            "unanimous_rate_spread": spread,
            "p3_spread_threshold": cases.P3_SPREAD_THRESHOLD,
        },
        "note": "Per genre we count how many of the five annotators agreed with the released gold (5 "
                "unanimous, 4, 3, or 'dash' when gold is '-' = no majority), the unanimous share over "
                "valid-gold examples, the share of individual annotator labels equal to gold, and a "
                "by-construction check that gold equals the strict majority of the five labels. P1 is a "
                "structural (by-construction) bet; P2 and P3 are directional (a finding either way), with "
                "the exact per-genre rates reported. MultiNLI is released under the OANC / CC and "
                "permissive source licences; this audit reads the official release and reports counts, it "
                "does not redistribute it.",
    }
    out_path = os.path.join(args.out_dir, "results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False, default=str)
    print("[done] wrote", out_path)


if __name__ == "__main__":
    main()
