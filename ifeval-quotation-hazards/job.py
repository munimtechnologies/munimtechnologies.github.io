# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc.
#
# Sealed-run driver for the ifeval-quotation-hazards audit.
#   1. Verify every hand-built case reproduces its pre-registered verdicts under
#      IFEval's ASCII-only QuotationChecker vs the intended any-double-quote
#      reading.
#   2. Measure, on IFEval's own released GPT-4 responses, how often the ASCII-only
#      startend:quotation check FAILS a response that is actually wrapped in a
#      non-ASCII double quotation mark (a false fail), plus the blast radius
#      across all responses.
#
# Inputs (public IFEval data, supplied via --data-dir):
#   input_data.jsonl                               -- the 541 prompts + id lists
#   input_response_data_gpt4_20231107_145030.jsonl -- GPT-4 responses, join by prompt

import argparse
import json
import os
import shutil
import unicodedata

from quote_checker import (
    shipped_quotation,
    intended_quotation,
    boundary_chars,
    nonascii_double_quote_boundaries,
    is_double_quote,
)

# Files copied verbatim into /out so the kept result is a self-contained,
# reproducible package even after the run folder is purged.
SOURCE_FILES = (
    "quote_checker.py",
    "job.py",
    "cases.json",
    "test_ifeval_quotation_hazards.py",
    "prereg.md",
    "README.md",
)

QUOTATION_ID = "startend:quotation"
RESPONSE_FILE = "input_response_data_gpt4_20231107_145030.jsonl"


def evaluate_case(case):
    text = "".join(chr(cp) for cp in case["text_codepoints"])
    shipped = shipped_quotation(text)
    intended = intended_quotation(text)
    return shipped, intended, shipped != intended


def verify_corpus(cases):
    out = []
    n_flip = 0
    for c in cases:
        shipped, intended, flip = evaluate_case(c)
        reproduced = (
            shipped == c["expected_shipped_pass"]
            and intended == c["expected_intended_pass"]
            and flip == c["expected_flip"]
        )
        if flip:
            n_flip += 1
        out.append({
            "id": c["id"],
            "shipped_pass": shipped,
            "intended_pass": intended,
            "flip": flip,
            "expected_flip": c["expected_flip"],
            "reproduced": reproduced,
        })
    summary = {
        "n_cases": len(out),
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


def _char_record(ch):
    return {
        "codepoint": "U+%04X" % ord(ch),
        "name": unicodedata.name(ch, ""),
    }


def measure_exposure(data_dir):
    data_path = os.path.join(data_dir, "input_data.jsonl")
    if not os.path.exists(data_path):
        return {"available": False, "reason": "input_data.jsonl missing"}

    responses, resp_path = load_responses(data_dir)

    n_prompts = 0
    n_instances = 0          # startend:quotation instructions across all prompts
    n_matched = 0            # instances whose prompt has a GPT-4 response
    n_shipped_pass = 0       # shipped QuotationChecker returns PASS
    n_false_fail = 0         # shipped FAIL but response wrapped in non-ASCII double quotes
    false_fail_examples = []
    seen_boundary_in_quotation = {}

    with open(data_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            n_prompts += 1
            ids = row.get("instruction_id_list", [])
            prompt = row.get("prompt")
            for iid in ids:
                if iid != QUOTATION_ID:
                    continue
                n_instances += 1
                if responses is None or prompt not in responses:
                    continue
                resp = responses[prompt]
                n_matched += 1
                shipped = shipped_quotation(resp)
                intended = intended_quotation(resp)
                if shipped:
                    n_shipped_pass += 1
                if (not shipped) and intended:
                    n_false_fail += 1
                    na = nonascii_double_quote_boundaries(resp)
                    first, last = boundary_chars(resp)
                    for ch in set(na):
                        seen_boundary_in_quotation[ch] = (
                            seen_boundary_in_quotation.get(ch, 0) + 1
                        )
                    if len(false_fail_examples) < 12:
                        false_fail_examples.append({
                            "key": row.get("key"),
                            "first": _char_record(first) if first else None,
                            "last": _char_record(last) if last else None,
                        })

    # Blast radius: across ALL released responses, how many are wrapped in double
    # quotes under the intended reading but FAIL the ASCII-only shipped check
    # (i.e. wrapped using at least one non-ASCII double quotation mark), and which
    # distinct boundary characters appear.
    n_resp_total = 0
    n_resp_wrapped_nonascii = 0
    distinct_boundary = {}
    if responses is not None:
        for resp in responses.values():
            n_resp_total += 1
            if (not shipped_quotation(resp)) and intended_quotation(resp):
                n_resp_wrapped_nonascii += 1
                for ch in set(nonascii_double_quote_boundaries(resp)):
                    distinct_boundary[ch] = distinct_boundary.get(ch, 0) + 1

    return {
        "available": True,
        "input_data": data_path,
        "response_file": resp_path,
        "response_file_present": responses is not None,
        "n_prompts": n_prompts,
        "n_quotation_instances": n_instances,
        "n_matched_to_response": n_matched,
        "n_shipped_pass": n_shipped_pass,
        "n_false_fail": n_false_fail,
        "false_fail_examples": false_fail_examples,
        "distinct_boundary_quotes_in_quotation_false_fails": [
            {**_char_record(ch), "n_responses": cnt}
            for ch, cnt in sorted(seen_boundary_in_quotation.items())
        ],
        "blast_radius": {
            "n_responses_total": n_resp_total,
            "n_responses_wrapped_in_nonascii_double_quotes": n_resp_wrapped_nonascii,
            "distinct_boundary_quotes": [
                {**_char_record(ch), "n_responses": cnt}
                for ch, cnt in sorted(distinct_boundary.items())
            ],
        },
    }


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
    slim = {k: v for k, v in exposure.items() if k != "false_fail_examples"}
    print(json.dumps(slim, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
