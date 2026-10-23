"""Run the QASC composition->answer lexical-leakage census on the official annotated splits.

The runner downloads the QASC train and validation parquet files (job.json data_urls) from the
HuggingFace mirror allenai/qasc. This script asserts the hand-traced fixture BEFORE touching real data,
reads every *.parquet in the data dir (train + validation; the public test split carries no answer key
or facts and is not downloaded), verifies the total against the published annotated count and prints the
first-row schema, measures how often the gold answer's text is a substring of fact1, fact2 and the
combinedfact (versus a distractor's) and how often only the composition reveals the answer, records
pre-registered predictions, and writes results.json.

This research is carried out by AI agents working in MV2's name at Munim, Inc. Apache-2.0.
"""
import argparse
import glob
import json
import os
import sys

import cases
from qasc_leakage import leakage_stats, flatten, parse_row

# 8,134 train + 926 validation annotated questions (the public test split has no answerKey/facts).
QASC_EXPECTED_TOTAL = 9060


def read_parquet_rows(paths):
    """Read every parquet file into a list of plain-dict rows (pyarrow struct -> nested dict)."""
    import pyarrow.parquet as pq
    rows = []
    first = None
    for p in paths:
        table = pq.read_table(p)
        for obj in table.to_pylist():
            if not isinstance(obj, dict):
                continue
            if first is None:
                first = obj
            rows.append(obj)
    return rows, first


def describe_first(obj):
    if obj is None:
        return "<none>"
    return "keys=%r answerKey=%r combinedfact=%r" % (
        sorted(obj.keys()), obj.get("answerKey"), str(obj.get("combinedfact"))[:60])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # 1. Assert the hand-traced fixture BEFORE touching real data.
    fix = flatten(leakage_stats([parse_row(o) for o in cases.FIXTURE]))
    target_met = all(fix[k] == cases.TARGET[k] for k in cases.TARGET)
    print("[fixture] target_met =", target_met)
    for k in cases.TARGET:
        print("  %-30s observed=%r target=%r" % (k, fix[k], cases.TARGET[k]))
    if not target_met:
        print("FATAL: fixture does not match hand-traced target", file=sys.stderr)
        sys.exit(2)

    # 2. Locate the parquet file(s).
    paths = sorted(glob.glob(os.path.join(args.data_dir, "*.parquet")))
    print("[diag] parquet files in data dir:", paths)
    if not paths:
        print("FATAL: no parquet found in data dir", file=sys.stderr)
        sys.exit(3)

    # 3. Read QASC (train + validation).
    raw, first = read_parquet_rows(paths)
    print("[diag] QASC rows =", len(raw), "first:", describe_first(first))
    if not raw:
        print("FATAL: read 0 rows from QASC", file=sys.stderr)
        sys.exit(4)
    recs = [parse_row(o) for o in raw]
    observed_total = len(recs)
    rows_as_expected = observed_total == QASC_EXPECTED_TOTAL
    print("[diag] rows_as_expected =", rows_as_expected, "(expect %d)" % QASC_EXPECTED_TOTAL)

    # 4. Lexical answer-leakage census.
    stats = leakage_stats(recs)
    for k in cases.TARGET:
        print("[census] %-30s = %r" % (k, stats[k]))
    for k in ("gold_rate_fact1", "gold_rate_fact2", "gold_rate_combinedfact",
              "dist_rate_fact1", "dist_rate_fact2", "dist_rate_combinedfact"):
        print("[census] %-26s = %.6f" % (k, stats[k]))
    print("[census] examples:", json.dumps(stats["examples"], ensure_ascii=False))

    # 5. Pre-registered predictions (held/failed reported honestly).
    predictions = {
        "P1_combined_leaks_more_than_distractor":
            stats["gold_rate_combinedfact"] > stats["dist_rate_combinedfact"],
        "P2_combined_leaks_more_than_single_facts":
            (stats["gold_rate_combinedfact"] > stats["gold_rate_fact1"]) and
            (stats["gold_rate_combinedfact"] > stats["gold_rate_fact2"]),
        "P3_combined_leaks_for_majority": stats["gold_rate_combinedfact"] > 0.5,
    }
    for k, v in predictions.items():
        print("[prediction] %s = %s" % (k, "HELD" if v else "FAILED"))

    out = {
        "dataset": "QASC (Khot, Clark, Guerquin, Jansen and Sabharwal, 2020), CC BY -- train+validation "
                   "(the annotated splits; the public test split has no answer key or facts), each an "
                   "8-way multiple-choice science question with two retrieved facts fact1/fact2 and a "
                   "combinedfact stating their composition",
        "expected_total": QASC_EXPECTED_TOTAL,
        "observed_total": observed_total,
        "rows_as_expected": rows_as_expected,
        "synthetic_corpus": {"target_met": target_met, "observed": fix, "target": cases.TARGET},
        "census": stats,
        "predictions": predictions,
        "note": "For each annotated QASC question the gold answer is the choice whose label == answerKey "
                "and the distractors are the other choices. 'gold in <field>' = the normalized gold text "
                "is a non-empty substring of the normalized fact field (fact1, fact2 or combinedfact); the "
                "same test is applied to each distractor. gold_rate_<field> = valid questions whose gold "
                "is in that field / valid questions; dist_rate_<field> = distractor-in-field hits / total "
                "distractors (option count controlled). n_gold_in_either_single counts valid questions "
                "whose gold is in fact1 or fact2; n_gold_in_combined_not_single counts those whose gold is "
                "in the combinedfact but in neither single fact -- the composition-only leaks. Text is "
                "lowercased and whitespace-collapsed only (punctuation kept), so every rate is a "
                "conservative lower bound. Rows whose answerKey matches no choice are malformed and "
                "excluded; rows with no answerKey are unannotated and excluded.",
    }
    out_path = os.path.join(args.out_dir, "results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False, default=str)
    print("[done] wrote", out_path)


if __name__ == "__main__":
    main()
