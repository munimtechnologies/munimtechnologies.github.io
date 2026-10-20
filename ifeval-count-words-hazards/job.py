# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc.
#
# Sealed-run driver for the ifeval-count-words-hazards audit.
#   1. Verify every hand-built case reproduces its pre-registered counts and
#      number_words verdicts under IFEval's \w+ counter vs a whitespace split.
#   2. Measure, on IFEval's own released GPT-4 responses, how often the two word
#      counts differ and how often that difference flips the length_constraints:
#      number_words pass/fail verdict.
#
# Inputs (public IFEval data, supplied via --data-dir):
#   input_data.jsonl                               -- the 541 prompts + kwargs
#   input_response_data_gpt4_20231107_145030.jsonl -- GPT-4 responses, join by prompt

import argparse
import json
import os
import re
import shutil
import statistics

from count_words_audit import (
    count_words_ifeval,
    count_words_whitespace,
    number_words_pass,
    evaluate_case,
)

# Files copied verbatim into /out so the kept result is a self-contained,
# reproducible package even after the run folder is purged.
SOURCE_FILES = (
    "count_words_audit.py",
    "job.py",
    "cases.json",
    "test_ifeval_count_words_hazards.py",
    "prereg.md",
    "README.md",
)

NW_ID = "length_constraints:number_words"
RESPONSE_FILE = "input_response_data_gpt4_20231107_145030.jsonl"


def _verdict_str(ok):
    return "PASS" if ok else "FAIL"


def verify_corpus(cases):
    out = []
    n_flip = 0
    n_count_diff = 0
    for c in cases:
        c_if, c_ws, v_if, v_ws, flip = evaluate_case(c)
        reproduced = (
            c_if == c["expected_count_ifeval"]
            and c_ws == c["expected_count_ws"]
            and _verdict_str(v_if) == c["expected_verdict_ifeval"]
            and _verdict_str(v_ws) == c["expected_verdict_ws"]
            and flip == c["expected_flip"]
        )
        if flip:
            n_flip += 1
        if c_if != c_ws:
            n_count_diff += 1
        out.append({
            "id": c["id"],
            "count_ifeval": c_if,
            "count_ws": c_ws,
            "verdict_ifeval": _verdict_str(v_if),
            "verdict_ws": _verdict_str(v_ws),
            "flip": flip,
            "expected_flip": c["expected_flip"],
            "reproduced": reproduced,
        })
    summary = {
        "n_cases": len(out),
        "n_count_diff": n_count_diff,
        "n_verdict_flip": n_flip,
        "all_reproduced": all(c["reproduced"] for c in out),
    }
    return {"summary": summary, "cases": out}


def load_responses(data_dir):
    """Map prompt -> response from the GPT-4 response file (if present)."""
    path = os.path.join(data_dir, RESPONSE_FILE)
    if not os.path.exists(path):
        return None, path
    responses = {}
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            prompt = row.get("prompt")
            if prompt is not None:
                responses[prompt] = row.get("response", "")
    return responses, path


def measure_exposure(data_dir):
    data_path = os.path.join(data_dir, "input_data.jsonl")
    if not os.path.exists(data_path):
        return {"available": False, "reason": "input_data.jsonl missing"}

    responses, resp_path = load_responses(data_dir)

    n_prompts = 0
    n_instances = 0          # number_words instructions across all prompts
    n_matched = 0            # instances whose prompt has a GPT-4 response
    n_count_diff = 0
    n_overcount = 0          # ifeval count > whitespace count
    n_undercount = 0         # ifeval count < whitespace count
    n_flip = 0
    flip_by_relation = {"less than": 0, "at least": 0}
    abs_diffs = []
    flip_examples = []

    with open(data_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            n_prompts += 1
            ids = row.get("instruction_id_list", [])
            kwargs = row.get("kwargs", [])
            prompt = row.get("prompt")
            for idx, iid in enumerate(ids):
                if iid != NW_ID:
                    continue
                n_instances += 1
                kw = kwargs[idx] if idx < len(kwargs) else {}
                kw = kw or {}
                num_words = kw.get("num_words")
                relation = kw.get("relation")
                if num_words is None or relation is None:
                    continue
                if responses is None or prompt not in responses:
                    continue
                resp = responses[prompt]
                n_matched += 1
                c_if = count_words_ifeval(resp)
                c_ws = count_words_whitespace(resp)
                diff = c_if - c_ws
                abs_diffs.append(abs(diff))
                if diff > 0:
                    n_overcount += 1
                elif diff < 0:
                    n_undercount += 1
                if diff != 0:
                    n_count_diff += 1
                v_if = number_words_pass(c_if, num_words, relation)
                v_ws = number_words_pass(c_ws, num_words, relation)
                if v_if != v_ws:
                    n_flip += 1
                    if relation in flip_by_relation:
                        flip_by_relation[relation] += 1
                    if len(flip_examples) < 12:
                        flip_examples.append({
                            "key": row.get("key"),
                            "relation": relation,
                            "num_words": num_words,
                            "count_ifeval": c_if,
                            "count_ws": c_ws,
                            "verdict_ifeval": _verdict_str(v_if),
                            "verdict_ws": _verdict_str(v_ws),
                        })

    result = {
        "available": True,
        "input_data": data_path,
        "response_file": resp_path,
        "response_file_present": responses is not None,
        "n_prompts": n_prompts,
        "n_number_words_instances": n_instances,
        "n_matched_to_response": n_matched,
        "n_count_diff": n_count_diff,
        "n_overcount_ifeval_gt_ws": n_overcount,
        "n_undercount_ifeval_lt_ws": n_undercount,
        "n_verdict_flip": n_flip,
        "flip_by_relation": flip_by_relation,
        "flip_examples": flip_examples,
    }
    if abs_diffs:
        result["abs_diff_mean"] = round(statistics.mean(abs_diffs), 4)
        result["abs_diff_median"] = statistics.median(abs_diffs)
        result["abs_diff_max"] = max(abs_diffs)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "cases.json"), "r", encoding="utf-8") as fh:
        cases = json.load(fh)["cases"]

    corpus = verify_corpus(cases)
    exposure = measure_exposure(args.data_dir)
    results = {"corpus": corpus, "exposure": exposure}

    os.makedirs(args.out_dir, exist_ok=True)
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)

    for name in SOURCE_FILES:
        src = os.path.join(here, name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(args.out_dir, name))

    print("=== corpus verification ===")
    print(json.dumps(corpus["summary"], indent=2))
    print("=== exposure on official IFEval GPT-4 responses ===")
    slim = {k: v for k, v in exposure.items() if k != "flip_examples"}
    print(json.dumps(slim, indent=2))


if __name__ == "__main__":
    main()
