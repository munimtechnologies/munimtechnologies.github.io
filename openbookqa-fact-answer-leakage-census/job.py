"""Run the OpenBookQA fact->answer lexical-leakage census on the official Additional corpus.

The runner downloads OpenBookQA-V1-Sep2018.zip to the data dir (job.json data_urls; reuses the
arc-openbookqa-v1 data volume that already holds it). This script asserts the hand-traced fixture
BEFORE touching real data, reads the three OpenBookQA Additional splits
(Data/Additional/{train,dev,test}_complete.jsonl) straight from the zip, verifies the total against the
published count and prints the first-row schema, measures how often the gold answer's text occurs as a
substring of its annotated fact (versus a distractor's), records pre-registered predictions, and
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
from fact_answer_leakage import fact_answer_stats, flatten, parse_row

OBQA_ADDITIONAL_EXPECTED_TOTAL = 5957  # 4957 + 500 + 500
OBQA_ADDITIONAL_BASENAMES = {"train_complete.jsonl", "dev_complete.jsonl", "test_complete.jsonl"}


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


def read_obqa_additional(zip_paths):
    """Pool the three OpenBookQA Additional splits (Data/Additional/{train,dev,test}_complete.jsonl)."""
    recs = []
    first = None
    for zp in zip_paths:
        for member, low in _members(zp):
            if "/data/additional/" in low and os.path.basename(low) in OBQA_ADDITIONAL_BASENAMES:
                r, f = _read_jsonl(zp, member)
                if first is None:
                    first = f
                recs.extend(r)
    return recs, first


def describe_first(obj):
    if obj is None:
        return "<none>"
    q = obj.get("question")
    stem = q.get("stem", "") if isinstance(q, dict) else obj.get("question_stem", "")
    nchoices = len(q.get("choices", []) or []) if isinstance(q, dict) else None
    return "id=%r answerKey=%r nchoices=%r fact1=%r stem=%r" % (
        obj.get("id"), obj.get("answerKey"), nchoices,
        (obj.get("fact1") or "")[:40], (stem or "")[:40])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # 1. Assert the hand-traced fixture BEFORE touching real data.
    fix = flatten(fact_answer_stats([parse_row(o) for o in cases.FIXTURE]))
    target_met = all(fix[k] == cases.TARGET[k] for k in cases.TARGET)
    print("[fixture] target_met =", target_met)
    for k in cases.TARGET:
        print("  %-28s observed=%r target=%r" % (k, fix[k], cases.TARGET[k]))
    if not target_met:
        print("FATAL: fixture does not match hand-traced target", file=sys.stderr)
        sys.exit(2)

    # 2. Locate the zip(s).
    zip_paths = sorted(glob.glob(os.path.join(args.data_dir, "*.zip")))
    print("[diag] zips in data dir:", zip_paths)
    if not zip_paths:
        print("FATAL: no zip found in data dir", file=sys.stderr)
        sys.exit(3)

    # 3. Read the Additional set.
    recs, first = read_obqa_additional(zip_paths)
    print("[diag] OpenBookQA Additional rows =", len(recs), "first:", describe_first(first))
    if not recs:
        print("FATAL: read 0 rows from OpenBookQA Additional", file=sys.stderr)
        sys.exit(4)
    rows_as_expected = len(recs) == OBQA_ADDITIONAL_EXPECTED_TOTAL
    print("[diag] rows_as_expected =", rows_as_expected,
          "(expect %d)" % OBQA_ADDITIONAL_EXPECTED_TOTAL)

    # 4. Lexical answer-leakage census.
    stats = fact_answer_stats(recs)
    for k in cases.TARGET:
        print("[census] %-28s = %r" % (k, stats[k]))
    print("[census] gold_coverage_rate      = %.6f" % stats["gold_coverage_rate"])
    print("[census] distractor_coverage_rate= %.6f" % stats["distractor_coverage_rate"])
    print("[census] examples:", json.dumps(stats["examples"], ensure_ascii=False))

    # 5. Pre-registered predictions (held/failed reported honestly).
    predictions = {
        "P1_gold_leaks_more_than_distractor":
            stats["gold_coverage_rate"] > stats["distractor_coverage_rate"],
        "P2_some_gold_text_in_fact": stats["n_gold_in_fact"] > 0,
        "P3_no_fact_equals_a_choice": stats["n_fact_eq_a_choice"] == 0,
    }
    for k, v in predictions.items():
        print("[prediction] %s = %s" % (k, "HELD" if v else "FAILED"))

    out = {
        "dataset": "OpenBookQA-V1-Sep2018 Additional (Mihaylov et al., 2018), Apache-2.0 -- "
                   "train+dev+test, each question annotated with its gold core fact fact1",
        "expected_total": OBQA_ADDITIONAL_EXPECTED_TOTAL,
        "observed_total": len(recs),
        "rows_as_expected": rows_as_expected,
        "synthetic_corpus": {"target_met": target_met, "observed": fix, "target": cases.TARGET},
        "census": stats,
        "predictions": predictions,
        "note": "For each Additional question, the gold answer is the choice whose label == answerKey "
                "and the gold fact is fact1. 'gold in fact' = the normalized gold text is a non-empty "
                "substring of the normalized fact; the same test is applied to each distractor. "
                "gold_coverage_rate = questions with gold-in-fact / valid questions; "
                "distractor_coverage_rate = distractor-in-fact hits / total distractors (option count "
                "controlled). Text is lowercased and whitespace-collapsed only (punctuation kept), so "
                "the leak counts are a conservative lower bound. n_fact_eq_a_choice counts verbatim "
                "fact==choice matches. Rows whose answerKey matches no choice label are malformed and "
                "excluded.",
    }
    out_path = os.path.join(args.out_dir, "results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False, default=str)
    print("[done] wrote", out_path)


if __name__ == "__main__":
    main()
