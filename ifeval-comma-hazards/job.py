# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc.
#
# Sealed-run driver for the ifeval-comma-hazards audit.
#   1. Verify every hand-built case reproduces its pre-registered verdicts under
#      IFEval's ASCII-only CommaChecker vs the intended any-Unicode-comma reading.
#   2. Measure, on IFEval's own released GPT-4 responses, how often the ASCII-only
#      punctuation:no_comma check PASSES a response that actually contains a
#      non-ASCII comma (a false pass), plus the blast radius across all responses.
#
# Inputs (public IFEval data, supplied via --data-dir):
#   input_data.jsonl                               -- the 541 prompts + id lists
#   input_response_data_gpt4_20231107_145030.jsonl -- GPT-4 responses, join by prompt

import argparse
import json
import os
import shutil
import unicodedata

from comma_checker import (
    ifeval_no_comma,
    nonascii_comma_chars,
    evaluate_case,
)

# Files copied verbatim into /out so the kept result is a self-contained,
# reproducible package even after the run folder is purged.
SOURCE_FILES = (
    "comma_checker.py",
    "job.py",
    "cases.json",
    "test_ifeval_comma_hazards.py",
    "prereg.md",
    "README.md",
)

NO_COMMA_ID = "punctuation:no_comma"
RESPONSE_FILE = "input_response_data_gpt4_20231107_145030.jsonl"


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
    n_instances = 0          # punctuation:no_comma instructions across all prompts
    n_matched = 0            # instances whose prompt has a GPT-4 response
    n_shipped_pass = 0       # shipped CommaChecker returns PASS (no ASCII comma)
    n_false_pass = 0         # shipped PASS but response has a non-ASCII comma
    false_pass_examples = []
    seen_nonascii_in_nocomma = {}

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
                if iid != NO_COMMA_ID:
                    continue
                n_instances += 1
                if responses is None or prompt not in responses:
                    continue
                resp = responses[prompt]
                n_matched += 1
                shipped = ifeval_no_comma(resp)
                na = nonascii_comma_chars(resp)
                if shipped:
                    n_shipped_pass += 1
                if shipped and na:
                    n_false_pass += 1
                    for ch in set(na):
                        seen_nonascii_in_nocomma[ch] = (
                            seen_nonascii_in_nocomma.get(ch, 0) + 1
                        )
                    if len(false_pass_examples) < 12:
                        false_pass_examples.append({
                            "key": row.get("key"),
                            "nonascii_commas": [_char_record(c) for c in sorted(set(na))],
                        })

    # Blast radius: across ALL released responses, how many contain any
    # non-ASCII comma, and which distinct characters appear.
    n_resp_total = 0
    n_resp_with_nonascii_comma = 0
    distinct_nonascii = {}
    if responses is not None:
        for resp in responses.values():
            n_resp_total += 1
            na = nonascii_comma_chars(resp)
            if na:
                n_resp_with_nonascii_comma += 1
                for ch in set(na):
                    distinct_nonascii[ch] = distinct_nonascii.get(ch, 0) + 1

    return {
        "available": True,
        "input_data": data_path,
        "response_file": resp_path,
        "response_file_present": responses is not None,
        "n_prompts": n_prompts,
        "n_no_comma_instances": n_instances,
        "n_matched_to_response": n_matched,
        "n_shipped_pass": n_shipped_pass,
        "n_false_pass": n_false_pass,
        "false_pass_examples": false_pass_examples,
        "distinct_nonascii_commas_in_nocomma_responses": [
            {**_char_record(ch), "n_responses": cnt}
            for ch, cnt in sorted(seen_nonascii_in_nocomma.items())
        ],
        "blast_radius": {
            "n_responses_total": n_resp_total,
            "n_responses_with_nonascii_comma": n_resp_with_nonascii_comma,
            "distinct_nonascii_commas": [
                {**_char_record(ch), "n_responses": cnt}
                for ch, cnt in sorted(distinct_nonascii.items())
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
    slim = {k: v for k, v in exposure.items() if k != "false_pass_examples"}
    print(json.dumps(slim, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
