"""Run the OpenBookQA Main-vs-Additional consistency census on the official corpus.

The runner downloads OpenBookQA-V1-Sep2018.zip to the data dir (job.json data_urls). This
script asserts the hand-traced fixture BEFORE touching real data, reads the six jsonl files
(Main/{train,dev,test}.jsonl and Additional/{train,dev,test}_complete.jsonl) straight from the
zip, verifies the per-split row counts against the published totals and prints the first row's
schema, runs the census, records pre-registered predictions, and writes results.json.

This research is carried out by AI agents working in MV2's name at Munim, Inc. Apache-2.0.
"""
import argparse
import glob
import json
import os
import sys
import zipfile

import cases
from openbookqa_consistency import census, flatten, parse_row, public_summary

# Published row counts per split for the canonical OpenBookQA-V1-Sep2018 release.
EXPECTED = {"train": 4957, "dev": 500, "test": 500}

MAIN_FILES = {"train.jsonl": "train", "dev.jsonl": "dev", "test.jsonl": "test"}
ADD_FILES = {"train_complete.jsonl": "train", "dev_complete.jsonl": "dev",
             "test_complete.jsonl": "test"}


def classify(member):
    """Return ('main'|'additional', split) for a zip member, or (None, None)."""
    name = member.replace("\\", "/").lower()
    if name.startswith("__macosx") or not name.endswith(".jsonl"):
        return None, None
    base = os.path.basename(name)
    if "/data/main/" in name and base in MAIN_FILES:
        return "main", MAIN_FILES[base]
    if "/data/additional/" in name and base in ADD_FILES:
        return "additional", ADD_FILES[base]
    return None, None


def read_records(zip_path):
    """Read Main and Additional records plus raw per-split counts from the zip."""
    main, additional = [], []
    raw_counts = {"main": {}, "additional": {}}
    first = {"main": None, "additional": None}
    with zipfile.ZipFile(zip_path) as z:
        for m in z.namelist():
            kind, split = classify(m)
            if kind is None:
                continue
            with z.open(m) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    obj = json.loads(line)
                    if first[kind] is None:
                        first[kind] = obj
                    rec = parse_row(obj, split)
                    (main if kind == "main" else additional).append(rec)
                    raw_counts[kind][split] = raw_counts[kind].get(split, 0) + 1
    return main, additional, raw_counts, first


def describe_first(obj):
    if obj is None:
        return "<none>"
    q = obj.get("question", {}) or {}
    labels = [c.get("label") for c in (q.get("choices", []) or [])]
    return "id=%r stem=%r choice_labels=%r answerKey=%r" % (
        obj.get("id"), (q.get("stem", "") or "")[:60], labels, obj.get("answerKey"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # 1. Assert the hand-traced fixture BEFORE touching real data.
    fix = flatten(census(
        [parse_row(o, s) for o, s in cases.FIXTURE_MAIN],
        [parse_row(o, s) for o, s in cases.FIXTURE_ADDITIONAL],
    ))
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

    # 3. Read both file families.
    main_recs, add_recs, raw_counts, first = read_records(zip_paths[0])
    print("[diag] main raw-per-split=%r" % raw_counts["main"])
    print("[diag] additional raw-per-split=%r" % raw_counts["additional"])
    print("[diag] main first row:", describe_first(first["main"]))
    print("[diag] additional first row:", describe_first(first["additional"]))
    if not main_recs or not add_recs:
        print("FATAL: read 0 rows from Main or Additional", file=sys.stderr)
        sys.exit(4)

    rows_as_expected = (raw_counts["main"] == EXPECTED and raw_counts["additional"] == EXPECTED)
    print("[diag] rows_as_expected =", rows_as_expected)

    # 4. Census.
    result = census(main_recs, add_recs)
    print("[census]", public_summary(result))

    # 5. Pre-registered predictions (held/failed reported honestly).
    x = result["crossfile"]
    predictions = {
        "P1_crossfile_answerkey_disagree_eq_0": x["answerkey_disagree"] == 0,
        "P2_no_ids_in_only_one_file":
            x["ids_only_in_main"] == 0 and x["ids_only_in_additional"] == 0,
        "P3_no_within_file_gold_conflict":
            result["main"]["identity_keys_conflict"] == 0
            and result["additional"]["identity_keys_conflict"] == 0,
        "P4_duplicate_questions_ge_1":
            result["main"]["identity_keys_multi"] + result["additional"]["identity_keys_multi"]
            >= 1,
    }
    for k, v in predictions.items():
        print("[prediction] %s = %s" % (k, "HELD" if v else "FAILED"))

    out = {
        "dataset": "OpenBookQA-V1-Sep2018 (Mihaylov et al., EMNLP 2018), Apache-2.0",
        "expected_rows_per_split": EXPECTED,
        "observed_rows_per_split": raw_counts,
        "rows_as_expected": rows_as_expected,
        "synthetic_corpus": {"target_met": target_met, "observed": fix, "target": cases.TARGET},
        "result": result,
        "predictions": predictions,
        "note": "A question's identity is (normalized stem, sorted normalized choice texts); "
                "its gold is the TEXT of the choice whose label == answerKey. Cross-file "
                "compares Main/{split}.jsonl against Additional/{split}_complete.jsonl on every "
                "shared (split, id). Within-file flags two questions with an identical identity "
                "but different gold. Rows whose answerKey matches no choice label are malformed "
                "and excluded from the gold comparisons.",
    }
    out_path = os.path.join(args.out_dir, "results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print("[done] wrote", out_path)


if __name__ == "__main__":
    main()
