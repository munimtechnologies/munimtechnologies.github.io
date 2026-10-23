"""Run the WinoGrande nested-subset / gold-consistency census on the official corpus.

The runner downloads winogrande_1.1.zip to the data dir (job.json data_urls). This script asserts
the hand-traced fixture BEFORE touching real data, reads the five nested training sizes plus dev
straight from the zip, verifies per-split row counts against the published totals and prints the
first row's schema, runs the nesting + gold-consistency census, cross-checks the inline answers
against the -labels.lst files, records pre-registered predictions, and writes results.json.

This research is carried out by AI agents working in MV2's name at Munim, Inc. Apache-2.0.
"""
import argparse
import glob
import json
import os
import sys
import zipfile

import cases
from winogrande_consistency import (
    census, flatten, overlap, parse_row, public_summary, within_file,
)

# Published row counts (AllenAI / TFDS, WinoGrande 1.1). Reported, not fatal on mismatch.
EXPECTED = {"xs": 160, "s": 640, "m": 2558, "l": 10234, "xl": 40398, "dev": 1267}
SIZES = ["xs", "s", "m", "l", "xl"]  # ordered smallest -> largest for the nesting check

# map jsonl basename -> split name
JSONL = {
    "train_xs.jsonl": "xs", "train_s.jsonl": "s", "train_m.jsonl": "m",
    "train_l.jsonl": "l", "train_xl.jsonl": "xl", "dev.jsonl": "dev",
}
LST = {
    "train_xs-labels.lst": "xs", "train_s-labels.lst": "s", "train_m-labels.lst": "m",
    "train_l-labels.lst": "l", "train_xl-labels.lst": "xl", "dev-labels.lst": "dev",
}


def _base(member):
    return os.path.basename(member.replace("\\", "/"))


def read_everything(zip_path):
    """Read every split's parsed records, raw counts, first rows, and raw label lists."""
    records = {}
    raw_counts = {}
    first = {}
    labels = {}
    with zipfile.ZipFile(zip_path) as z:
        for m in z.namelist():
            if m.replace("\\", "/").lower().startswith("__macosx"):
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
                records[split] = recs
                raw_counts[split] = len(recs)
            elif base in LST:
                split = LST[base]
                vals = []
                with z.open(m) as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            vals.append(line.decode("utf-8").strip())
                labels[split] = vals
    return records, raw_counts, first, labels


def describe_first(obj):
    if obj is None:
        return "<none>"
    return "qID=%r sentence=%r option1=%r option2=%r answer=%r" % (
        obj.get("qID"), (obj.get("sentence", "") or "")[:50],
        obj.get("option1"), obj.get("option2"), obj.get("answer"))


def label_cross_check(records, labels):
    """Compare each split's inline jsonl answers against its -labels.lst (by line order)."""
    out = {}
    for split, recs in records.items():
        lst = labels.get(split)
        if lst is None:
            out[split] = {"rows": len(recs), "lst_lines": None, "mismatches": None,
                          "note": "no -labels.lst present for this split"}
            continue
        if len(lst) != len(recs):
            out[split] = {"rows": len(recs), "lst_lines": len(lst), "mismatches": None,
                          "note": "row/label count differ; not compared by index"}
            continue
        mism = sum(1 for r, lab in zip(recs, lst) if r["answer"] != lab)
        out[split] = {"rows": len(recs), "lst_lines": len(lst), "mismatches": mism, "note": ""}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # 1. Assert the hand-traced fixture BEFORE touching real data.
    fix_result = census([("A", [parse_row(o) for o in cases.FIXTURE_A]),
                         ("B", [parse_row(o) for o in cases.FIXTURE_B])])
    fix = flatten(fix_result, cases.NAMES, cases.PAIRS)
    target_met = all(fix[k] == cases.TARGET[k] for k in cases.TARGET)
    print("[fixture] target_met =", target_met)
    for k in cases.TARGET:
        print("  %-34s observed=%r target=%r" % (k, fix[k], cases.TARGET[k]))
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
    records, raw_counts, first, labels = read_everything(zip_paths[0])
    print("[diag] raw per-split counts =", raw_counts)
    for split in SIZES + ["dev"]:
        print("[diag] %s first row: %s" % (split, describe_first(first.get(split))))
    missing = [s for s in SIZES + ["dev"] if s not in records or not records[s]]
    if missing:
        print("FATAL: missing or empty splits: %r" % missing, file=sys.stderr)
        sys.exit(4)

    rows_as_expected = all(raw_counts.get(s) == EXPECTED[s] for s in EXPECTED)
    print("[diag] rows_as_expected =", rows_as_expected,
          "(expected %r)" % EXPECTED)

    # 4. Census over the nested training sizes; dev handled separately.
    ordered = [(s, records[s]) for s in SIZES]
    result = census(ordered)
    nesting_keys = ["%s->%s" % (SIZES[i], SIZES[i + 1]) for i in range(len(SIZES) - 1)]
    print("[census]", public_summary(result, nesting_keys))

    dev_within = within_file(records["dev"])
    dev_overlap_xl = overlap(records["dev"], records["xl"])
    # include dev in the within-file conflict total
    result["within"]["dev"] = dev_within

    xcheck = label_cross_check(records, labels)
    print("[labels] answer-vs-lst mismatches:",
          {s: xcheck[s]["mismatches"] for s in xcheck})

    # 5. Pre-registered predictions (held/failed reported honestly).
    nest_viol = sum(result["nesting"][k]["qids_only_in_smaller"] for k in nesting_keys)
    cross_size_conf = sum(result["nesting"][k]["shared_answer_conflict"] for k in nesting_keys)
    within_conf = sum(w["identity_keys_conflict"] for w in result["within"].values())
    predictions = {
        "P1_nesting_holds_no_ids_lost": nest_viol == 0,
        "P2_no_cross_size_answer_conflict": cross_size_conf == 0,
        "P3_no_within_split_gold_conflict": within_conf == 0,
        "P4_dev_disjoint_from_xl": dev_overlap_xl["shared_qids"] == 0,
    }
    for k, v in predictions.items():
        print("[prediction] %s = %s" % (k, "HELD" if v else "FAILED"))

    out = {
        "dataset": "WinoGrande 1.1 (Sakaguchi et al., AAAI 2020), Apache-2.0 / CC-BY",
        "expected_rows_per_split": EXPECTED,
        "observed_rows_per_split": raw_counts,
        "rows_as_expected": rows_as_expected,
        "synthetic_corpus": {"target_met": target_met, "observed": fix, "target": cases.TARGET},
        "result": result,
        "dev_overlap_with_xl": dev_overlap_xl,
        "label_cross_check": xcheck,
        "nesting_keys": nesting_keys,
        "predictions": predictions,
        "note": "Identity = normalized (sentence, option1, option2); gold = the jsonl 'answer' "
                "field ('1'/'2'). Nesting checks each smaller training size is a subset of the next "
                "larger by qID, with the same answer for shared qIDs. Within-split flags two "
                "questions with an identical identity but a different gold. dev_overlap_with_xl is a "
                "train/dev leakage check. label_cross_check compares the inline answers against the "
                "-labels.lst files by line order.",
    }
    out_path = os.path.join(args.out_dir, "results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print("[done] wrote", out_path)


if __name__ == "__main__":
    main()
