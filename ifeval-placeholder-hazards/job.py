# Copyright 2026 Munim, Inc. Licensed under the Apache License, Version 2.0.
#
# Verifies the hand-constructed hazard corpus and measures how much the OFFICIAL IFEval
# prompt set depends on the PlaceholderChecker (detectable_content:number_placeholders).
# Standard library only.
import argparse
import collections
import glob
import json
import os
import sys
import urllib.request

import ifeval_placeholder as ip

OFFICIAL_URL = (
    "https://raw.githubusercontent.com/google-research/google-research/"
    "master/instruction_following_eval/data/input_data.jsonl"
)
PLACEHOLDER_ID = "detectable_content:number_placeholders"


def verify_corpus(here):
    with open(os.path.join(here, "cases.json"), encoding="utf-8") as f:
        cases = json.load(f)["cases"]
    rows = []
    ok = True
    for c in cases:
        up, it = ip.run_case(c)
        match = (up == c["expected_upstream"] and it == c["expected_intended"]
                 and up != it)
        ok = ok and match
        rows.append({"id": c["id"], "hazard": c["hazard"],
                     "num_placeholders": c["num_placeholders"],
                     "upstream_count": ip.upstream_placeholder_count(c["value"]),
                     "intended_count": ip.intended_placeholder_count(c["value"]),
                     "upstream": up, "intended": it,
                     "expected_upstream": c["expected_upstream"],
                     "expected_intended": c["expected_intended"],
                     "reproduced": match})
    summary = {
        "n_cases": len(cases),
        "n_false_pass": sum(1 for r in rows if r["hazard"] == "false_pass"),
        "n_false_fail": sum(1 for r in rows if r["hazard"] == "false_fail"),
        "all_reproduced": ok,
    }
    return {"summary": summary, "cases": rows}


def _load_official(data_dir):
    # Prefer a file already placed in /data; fall back to a direct download.
    for path in glob.glob(os.path.join(data_dir, "**", "*.jsonl"), recursive=True):
        if os.path.basename(path) == "input_data.jsonl":
            with open(path, encoding="utf-8") as f:
                return [json.loads(line) for line in f if line.strip()], path
    try:
        with urllib.request.urlopen(OFFICIAL_URL, timeout=60) as resp:
            text = resp.read().decode("utf-8")
        return [json.loads(line) for line in text.splitlines() if line.strip()], OFFICIAL_URL
    except Exception as exc:  # network may be unavailable
        return None, "DOWNLOAD_FAILED: %r" % (exc,)


def measure_exposure(data_dir):
    rows, source = _load_official(data_dir)
    if rows is None:
        return {"source": source, "available": False}

    instances = 0
    prompts_with = 0
    n_required = collections.Counter()
    examples = []
    for item in rows:
        ids = item.get("instruction_id_list", []) or []
        kwargs = item.get("kwargs", []) or []
        key = item.get("key")
        has = False
        for i, iid in enumerate(ids):
            if iid != PLACEHOLDER_ID:
                continue
            instances += 1
            has = True
            kw = (kwargs[i] if i < len(kwargs) else {}) or {}
            req = kw.get("num_placeholders")
            n_required[req] += 1
            if len(examples) < 50:
                examples.append({"key": key, "num_placeholders": req})
        if has:
            prompts_with += 1

    return {
        "source": source,
        "available": True,
        "n_prompts": len(rows),
        "placeholder_checker": {
            "instances": instances,
            "prompts_with_checker": prompts_with,
            "num_placeholders_distribution": {str(k): v for k, v in sorted(
                n_required.items(), key=lambda kv: (kv[0] is None, kv[0]))},
            "examples": examples,
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(args.out_dir, exist_ok=True)

    corpus = verify_corpus(here)
    exposure = measure_exposure(args.data_dir)
    results = {"corpus": corpus, "exposure": exposure}

    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("=== corpus verification ===")
    print(json.dumps(corpus["summary"], indent=2))
    for r in corpus["cases"]:
        print("  %-32s up=%s(%d) intended=%s(%d) need=%d reproduced=%s" % (
            r["id"], r["upstream"], r["upstream_count"], r["intended"],
            r["intended_count"], r["num_placeholders"], r["reproduced"]))
    print("=== exposure on official IFEval ===")
    if exposure.get("available"):
        print(json.dumps({k: v for k, v in exposure.items() if k != "source"},
                         indent=2)[:4000])
    else:
        print("official data unavailable:", exposure.get("source"))

    if not corpus["summary"]["all_reproduced"]:
        print("ERROR: corpus did not reproduce as pre-registered", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
