"""Run the SciQ support->answer lexical-leakage census on the official released files.

The runner downloads SciQ.zip to the data dir (job.json data_urls). This script asserts the hand-traced
fixture BEFORE touching real data, reads the three SciQ splits (train.json, valid.json, test.json)
straight from the zip, verifies the total against the published count and prints the first-row schema,
measures how often the correct answer's text occurs as a substring of its support passage (versus a
distractor's) and how many questions ship with no support, records pre-registered predictions, and
writes results.json.

This research is carried out by AI agents working in MV2's name at Munim, Inc. Apache-2.0.
"""
import argparse
import glob
import json
import os
import sys
import zipfile

import cases
from support_answer_leakage import support_answer_stats, flatten, parse_row

SCIQ_EXPECTED_TOTAL = 13679  # 11679 train + 1000 valid + 1000 test
SCIQ_BASENAMES = {"train.json", "valid.json", "test.json"}


def _members(zip_path):
    with zipfile.ZipFile(zip_path) as z:
        for m in z.namelist():
            low = m.replace("\\", "/").lower()
            if low.startswith("__macosx") or low.endswith("/"):
                continue
            yield m, low


def _read_json_array(zip_path, member):
    with zipfile.ZipFile(zip_path) as z:
        with z.open(member) as f:
            data = json.load(f)
    return data


def read_sciq(zip_paths):
    """Pool the three SciQ splits (train.json, valid.json, test.json) from the official zip."""
    recs = []
    first = None
    for zp in zip_paths:
        for member, low in _members(zp):
            if os.path.basename(low) in SCIQ_BASENAMES:
                arr = _read_json_array(zp, member)
                if not isinstance(arr, list):
                    continue
                for obj in arr:
                    if not isinstance(obj, dict):
                        continue
                    if first is None:
                        first = obj
                    recs.append(parse_row(obj))
    return recs, first


def describe_first(obj):
    if obj is None:
        return "<none>"
    return "keys=%r correct_answer=%r support_len=%d question=%r" % (
        sorted(obj.keys()), (obj.get("correct_answer") or "")[:40],
        len(obj.get("support") or ""), (obj.get("question") or "")[:40])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # 1. Assert the hand-traced fixture BEFORE touching real data.
    fix = flatten(support_answer_stats([parse_row(o) for o in cases.FIXTURE]))
    target_met = all(fix[k] == cases.TARGET[k] for k in cases.TARGET)
    print("[fixture] target_met =", target_met)
    for k in cases.TARGET:
        print("  %-30s observed=%r target=%r" % (k, fix[k], cases.TARGET[k]))
    if not target_met:
        print("FATAL: fixture does not match hand-traced target", file=sys.stderr)
        sys.exit(2)

    # 2. Locate the zip(s).
    zip_paths = sorted(glob.glob(os.path.join(args.data_dir, "*.zip")))
    print("[diag] zips in data dir:", zip_paths)
    if not zip_paths:
        print("FATAL: no zip found in data dir", file=sys.stderr)
        sys.exit(3)

    # 3. Read SciQ.
    recs, first = read_sciq(zip_paths)
    print("[diag] SciQ rows =", len(recs), "first:", describe_first(first))
    if not recs:
        print("FATAL: read 0 rows from SciQ", file=sys.stderr)
        sys.exit(4)
    rows_as_expected = len(recs) == SCIQ_EXPECTED_TOTAL
    print("[diag] rows_as_expected =", rows_as_expected, "(expect %d)" % SCIQ_EXPECTED_TOTAL)

    # 4. Lexical answer-leakage census.
    stats = support_answer_stats(recs)
    for k in cases.TARGET:
        print("[census] %-30s = %r" % (k, stats[k]))
    print("[census] gold_coverage_rate      = %.6f" % stats["gold_coverage_rate"])
    print("[census] distractor_coverage_rate= %.6f" % stats["distractor_coverage_rate"])
    print("[census] examples:", json.dumps(stats["examples"], ensure_ascii=False))

    # 5. Pre-registered predictions (held/failed reported honestly).
    predictions = {
        "P1_gold_leaks_more_than_distractor":
            stats["gold_coverage_rate"] > stats["distractor_coverage_rate"],
        "P2_some_questions_have_no_support": stats["n_empty_support"] > 0,
        "P3_gold_in_support_for_majority": stats["gold_coverage_rate"] > 0.5,
    }
    for k, v in predictions.items():
        print("[prediction] %s = %s" % (k, "HELD" if v else "FAILED"))

    out = {
        "dataset": "SciQ (Welbl, Liu and Gardner, 2017), CC BY-NC 3.0 -- train+valid+test, each "
                   "multiple-choice science question with a correct_answer, three distractors, and "
                   "(for most) a support passage",
        "expected_total": SCIQ_EXPECTED_TOTAL,
        "observed_total": len(recs),
        "rows_as_expected": rows_as_expected,
        "synthetic_corpus": {"target_met": target_met, "observed": fix, "target": cases.TARGET},
        "census": stats,
        "predictions": predictions,
        "note": "For each SciQ question the gold answer is correct_answer and the support is the support "
                "passage. 'gold in support' = the normalized gold text is a non-empty substring of the "
                "normalized support; the same test is applied to each distractor. Questions with an empty "
                "support are counted in n_empty_support and excluded from the rates (nothing to leak "
                "into); their distractors are not counted. gold_coverage_rate = with-support questions "
                "whose gold is in the support / with-support questions; distractor_coverage_rate = "
                "distractor-in-support hits / total distractors over with-support questions (option "
                "count controlled). Text is lowercased and whitespace-collapsed only (punctuation kept), "
                "so the leak counts are a conservative lower bound. n_support_eq_a_choice counts verbatim "
                "support==choice matches. Rows missing correct_answer are malformed and excluded.",
    }
    out_path = os.path.join(args.out_dir, "results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False, default=str)
    print("[done] wrote", out_path)


if __name__ == "__main__":
    main()
