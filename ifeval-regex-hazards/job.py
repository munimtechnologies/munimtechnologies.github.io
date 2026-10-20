# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc.
#
# Sealed-run driver for the ifeval-regex-hazards audit.
#   1. Verify every hand-built case reproduces its pre-registered verdicts.
#   2. Measure exposure: how many of the 541 official IFEval prompts actually
#      use keywords:frequency / keywords:forbidden_words, and of those how many
#      carry a keyword / forbidden word that contains a regex metacharacter or
#      compiles to an invalid regex (i.e. would actually trigger a hazard).
#
# Run with no network dependency on model output; the only input is the public
# IFEval prompt file input_data.jsonl, supplied via --data-dir.

import argparse
import json
import os
import re
import shutil

from ifeval_regex import has_metachar, verdicts

# Files copied verbatim into the output directory so the sealed run is a
# self-contained, reproducible package: compute keeps only /out, and run
# folders are purged between runs, so the audit's own source must travel with
# its results or it cannot be published honestly later.
SOURCE_FILES = (
    "ifeval_regex.py",
    "job.py",
    "cases.json",
    "test_ifeval_regex_hazards.py",
    "prereg.md",
    "README.md",
)

KF_ID = "keywords:frequency"
FW_ID = "keywords:forbidden_words"


def verify_corpus(cases):
    out = []
    n_crash = n_false_pass = n_false_fail = 0
    for c in cases:
        up, intl = verdicts(c)
        reproduced = (up == c["expected_upstream"] and intl == c["expected_intended"])
        if c["hazard"] == "crash":
            n_crash += 1
        elif c["hazard"] == "false_pass":
            n_false_pass += 1
        elif c["hazard"] == "false_fail":
            n_false_fail += 1
        out.append({
            "id": c["id"],
            "checker": c["checker"],
            "hazard": c["hazard"],
            "upstream": up,
            "intended": intl,
            "expected_upstream": c["expected_upstream"],
            "expected_intended": c["expected_intended"],
            "reproduced": reproduced,
        })
    summary = {
        "n_cases": len(out),
        "n_crash": n_crash,
        "n_false_pass": n_false_pass,
        "n_false_fail": n_false_fail,
        "all_reproduced": all(c["reproduced"] for c in out),
    }
    return {"summary": summary, "cases": out}


def _kf_hazardous(keyword):
    """(is_metachar, is_invalid_regex) for a raw keyword:frequency keyword."""
    meta = has_metachar(keyword)
    invalid = False
    try:
        re.compile(keyword)
    except re.error:
        invalid = True
    return meta, invalid


def _fw_hazardous(word):
    """(is_metachar, is_invalid_regex) for a raw forbidden word."""
    meta = has_metachar(word)
    invalid = False
    try:
        re.compile(r"\b" + word + r"\b")
    except re.error:
        invalid = True
    return meta, invalid


def measure_exposure(data_path):
    if not os.path.exists(data_path):
        return {"source": data_path, "available": False}

    n_prompts = 0
    kf_instances = 0
    kf_meta = 0
    kf_invalid = 0
    kf_meta_examples = []
    kf_invalid_examples = []
    fw_instances = 0
    fw_meta = 0
    fw_invalid = 0
    fw_meta_examples = []
    fw_invalid_examples = []

    with open(data_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            n_prompts += 1
            ids = row.get("instruction_id_list", [])
            kwargs = row.get("kwargs", [])
            for idx, iid in enumerate(ids):
                kw = kwargs[idx] if idx < len(kwargs) else {}
                if iid == KF_ID:
                    kf_instances += 1
                    keyword = (kw or {}).get("keyword")
                    if keyword is None:
                        continue
                    meta, invalid = _kf_hazardous(keyword)
                    if meta:
                        kf_meta += 1
                        if len(kf_meta_examples) < 10:
                            kf_meta_examples.append(keyword)
                    if invalid:
                        kf_invalid += 1
                        if len(kf_invalid_examples) < 10:
                            kf_invalid_examples.append(keyword)
                elif iid == FW_ID:
                    fw_instances += 1
                    for word in (kw or {}).get("forbidden_words", []) or []:
                        meta, invalid = _fw_hazardous(word)
                        if meta:
                            fw_meta += 1
                            if len(fw_meta_examples) < 10:
                                fw_meta_examples.append(word)
                        if invalid:
                            fw_invalid += 1
                            if len(fw_invalid_examples) < 10:
                                fw_invalid_examples.append(word)

    return {
        "source": data_path,
        "available": True,
        "n_prompts": n_prompts,
        "keyword_frequency": {
            "instances": kf_instances,
            "with_metachar": kf_meta,
            "invalid_regex_crash": kf_invalid,
            "metachar_examples": kf_meta_examples,
            "invalid_examples": kf_invalid_examples,
        },
        "forbidden_words": {
            "instances": fw_instances,
            "words_with_metachar": fw_meta,
            "words_invalid_regex_crash": fw_invalid,
            "metachar_examples": fw_meta_examples,
            "invalid_examples": fw_invalid_examples,
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
    data_path = os.path.join(args.data_dir, "input_data.jsonl")
    exposure = measure_exposure(data_path)

    results = {"corpus": corpus, "exposure": exposure}

    os.makedirs(args.out_dir, exist_ok=True)
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)

    # Carry the source into /out so the kept result is a complete, publishable
    # package even after the run folder is purged.
    for name in SOURCE_FILES:
        src = os.path.join(here, name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(args.out_dir, name))

    print("=== corpus verification ===")
    print(json.dumps(corpus["summary"], indent=2))
    print("=== exposure on official IFEval ===")
    if exposure.get("available"):
        slim = {
            "available": True,
            "n_prompts": exposure["n_prompts"],
            "keyword_frequency": exposure["keyword_frequency"],
            "forbidden_words": exposure["forbidden_words"],
        }
        print(json.dumps(slim, indent=2))
    else:
        print(json.dumps(exposure, indent=2))


if __name__ == "__main__":
    main()
