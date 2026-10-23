"""Run the ARC<->OpenBookQA cross-dataset question-overlap census on the official corpora.

The runner downloads ARC-V1-Feb2018.zip and OpenBookQA-V1-Sep2018.zip to the data dir (job.json
data_urls). This script asserts the hand-traced fixture BEFORE touching real data, reads all six ARC
jsonl splits and the three OpenBookQA Main splits straight from the two zips, verifies the per-dataset
totals against the published counts and prints each dataset's first-row schema, runs the cross-dataset
overlap census, records pre-registered predictions, and writes results.json.

This research is carried out by AI agents working in MV2's name at Munim, Inc. Apache-2.0.
"""
import argparse
import glob
import json
import os
import sys
import zipfile

import cases
from cross_dataset_overlap import cross_overlap, flatten, parse_row

# Published totals.
ARC_EXPECTED_TOTAL = 7787        # 1119+299+1172 (challenge) + 2251+570+2376 (easy)
OBQA_EXPECTED_TOTAL = 5957       # 4957+500+500 (main)

# ARC jsonl basenames (lowercased) for the six splits.
ARC_BASENAMES = {
    "arc-challenge-train.jsonl", "arc-challenge-dev.jsonl", "arc-challenge-test.jsonl",
    "arc-easy-train.jsonl", "arc-easy-dev.jsonl", "arc-easy-test.jsonl",
}
# OpenBookQA Main jsonl basenames (the canonical 5,957 questions; Additional is the same questions).
OBQA_MAIN_BASENAMES = {"train.jsonl", "dev.jsonl", "test.jsonl"}


def _members(zip_path):
    with zipfile.ZipFile(zip_path) as z:
        for m in z.namelist():
            low = m.replace("\\", "/").lower()
            if low.startswith("__macosx") or low.endswith("/"):
                continue
            yield m, low


def _read_jsonl(zip_path, member):
    recs = []
    first = None
    with zipfile.ZipFile(zip_path) as z:
        with z.open(member) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                if first is None:
                    first = obj
                recs.append(parse_row(obj))
    return recs, first


def read_arc(zip_paths):
    """Pool all six ARC splits from whichever zip holds them."""
    recs = []
    first = None
    for zp in zip_paths:
        for member, low in _members(zp):
            if os.path.basename(low) in ARC_BASENAMES:
                r, f = _read_jsonl(zp, member)
                if first is None:
                    first = f
                recs.extend(r)
    return recs, first


def read_obqa_main(zip_paths):
    """Pool the three OpenBookQA Main splits (Data/Main/{train,dev,test}.jsonl)."""
    recs = []
    first = None
    for zp in zip_paths:
        for member, low in _members(zp):
            if "/data/main/" in low and os.path.basename(low) in OBQA_MAIN_BASENAMES:
                r, f = _read_jsonl(zp, member)
                if first is None:
                    first = f
                recs.extend(r)
    return recs, first


def describe_first(obj):
    if obj is None:
        return "<none>"
    q = obj.get("question")
    if isinstance(q, dict):
        stem = q.get("stem", "")
        nchoices = len(q.get("choices", []) or [])
    else:
        stem = q
        nchoices = None
    return "id=%r answerKey=%r nchoices=%r stem=%r" % (
        obj.get("id"), obj.get("answerKey"), nchoices, (stem or "")[:50])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # 1. Assert the hand-traced fixture BEFORE touching real data.
    fix = flatten(cross_overlap([parse_row(o) for o in cases.FIXTURE_A],
                                [parse_row(o) for o in cases.FIXTURE_B]))
    target_met = all(fix[k] == cases.TARGET[k] for k in cases.TARGET)
    print("[fixture] target_met =", target_met)
    for k in cases.TARGET:
        print("  %-32s observed=%r target=%r" % (k, fix[k], cases.TARGET[k]))
    if not target_met:
        print("FATAL: fixture does not match hand-traced target", file=sys.stderr)
        sys.exit(2)

    # 2. Locate the zips.
    zip_paths = sorted(glob.glob(os.path.join(args.data_dir, "*.zip")))
    print("[diag] zips in data dir:", zip_paths)
    if not zip_paths:
        print("FATAL: no zip found in data dir", file=sys.stderr)
        sys.exit(3)

    # 3. Read both datasets.
    arc_recs, arc_first = read_arc(zip_paths)
    obqa_recs, obqa_first = read_obqa_main(zip_paths)
    print("[diag] ARC rows =", len(arc_recs), "first:", describe_first(arc_first))
    print("[diag] OpenBookQA Main rows =", len(obqa_recs), "first:", describe_first(obqa_first))
    if not arc_recs or not obqa_recs:
        print("FATAL: read 0 rows from ARC (%d) or OpenBookQA (%d)"
              % (len(arc_recs), len(obqa_recs)), file=sys.stderr)
        sys.exit(4)

    rows_as_expected = (len(arc_recs) == ARC_EXPECTED_TOTAL
                        and len(obqa_recs) == OBQA_EXPECTED_TOTAL)
    print("[diag] rows_as_expected =", rows_as_expected,
          "(ARC expect %d, OBQA expect %d)" % (ARC_EXPECTED_TOTAL, OBQA_EXPECTED_TOTAL))

    # 4. Cross-dataset census (ARC = A, OpenBookQA = B).
    result = cross_overlap(arc_recs, obqa_recs)
    for k in cases.TARGET:
        print("[census] %-32s = %r" % (k, result[k]))
    print("[census] examples:", json.dumps(result["examples"], ensure_ascii=False))

    # 5. Pre-registered predictions (held/failed reported honestly).
    predictions = {
        "P1_arc_obqa_disjoint_by_identity": result["shared_identities"] == 0,
        "P2_no_shared_identity_gold_conflict": result["shared_identity_gold_conflict"] == 0,
        "P3_arc_obqa_disjoint_by_stem": result["shared_stems"] == 0,
    }
    for k, v in predictions.items():
        print("[prediction] %s = %s" % (k, "HELD" if v else "FAILED"))

    out = {
        "datasets": {
            "A": "AI2 ARC (ARC-V1-Feb2018; Clark et al., 2018), CC BY-SA 4.0 -- all 6 splits pooled",
            "B": "OpenBookQA-V1-Sep2018 (Mihaylov et al., 2018), Apache-2.0 -- Main train+dev+test",
        },
        "expected_totals": {"arc": ARC_EXPECTED_TOTAL, "openbookqa_main": OBQA_EXPECTED_TOTAL},
        "observed_totals": {"arc": len(arc_recs), "openbookqa_main": len(obqa_recs)},
        "rows_as_expected": rows_as_expected,
        "synthetic_corpus": {"target_met": target_met, "observed": fix, "target": cases.TARGET},
        "census": result,
        "predictions": predictions,
        "note": "A question's identity is (normalized stem, frozenset of normalized choice texts); "
                "its gold is the TEXT of the choice whose label == answerKey. The census pools all "
                "six ARC splits (A) and the three OpenBookQA Main splits (B) and counts shared "
                "identities, shared-identity gold conflicts (a shared question labelled differently "
                "in the two datasets) and shared stems (same question text, looser signal). Rows "
                "whose answerKey matches no choice label are malformed and excluded from the "
                "identity/gold analysis.",
    }
    out_path = os.path.join(args.out_dir, "results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False, default=str)
    print("[done] wrote", out_path)


if __name__ == "__main__":
    main()
