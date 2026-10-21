# Sealed compute job for the ifeval-postscript-hazards audit.
#
# 1. Re-derive the pre-registered synthetic corpus and ASSERT it matches the
#    pre-registered target (raises -> non-zero exit if it ever drifts).
# 2. Measure real-world exposure: among IFEval's own 541 prompts, find every
#    detectable_content:postscript instance, join each to its released GPT-4
#    response by exact prompt text, and count how often the shipped and intended
#    checkers disagree (false pass = shipped True / intended False;
#    false fail = shipped False / intended True).
# 3. Copy every source file into /out so the shipped artifact is reproducible
#    straight from the compute output, independent of the purged run folder.
#
# Pure stdlib. Input files are read from /data (data_key ifeval-official).
# Audit by AI agents working in MV2's name (Munim, Inc.). Apache-2.0.

import json
import os
import shutil

from postscript_checker import shipped_check, intended_check
from cases import CASES, MARKER

TARGET = {
    "n_cases": 6,
    "n_verdict_flip": 4,
    "n_false_pass": 1,
    "n_false_fail": 3,
    "all_reproduced": True,
}

DATA_DIR = "/data"
OUT_DIR = "/out"
SOURCE_FILES = [
    "postscript_checker.py",
    "cases.py",
    "test_postscript_checker.py",
    "job.py",
    "README.md",
]

INPUT_DATA = "input_data.jsonl"
GPT4_DATA = "input_response_data_gpt4_20231107_145030.jsonl"


def build_corpus():
    rows = []
    n_flip = n_fp = n_ff = 0
    all_ok = True
    for cid, text, ship_exp, int_exp, kind, note in CASES:
        ship = shipped_check(text, MARKER)
        intended = intended_check(text, MARKER)
        reproduced = (ship == ship_exp) and (intended == int_exp)
        if not reproduced:
            all_ok = False
        if ship != intended:
            n_flip += 1
        if ship and not intended:
            n_fp += 1
        if intended and not ship:
            n_ff += 1
        rows.append({
            "id": cid,
            "marker": MARKER,
            "text": text,
            "shipped_verdict": ship,
            "intended_verdict": intended,
            "shipped_expected": ship_exp,
            "intended_expected": int_exp,
            "kind": kind,
            "reproduced": reproduced,
            "note": note,
        })
    summary = {
        "n_cases": len(CASES),
        "n_verdict_flip": n_flip,
        "n_false_pass": n_fp,
        "n_false_fail": n_ff,
        "all_reproduced": all_ok,
    }
    return summary, rows


def read_jsonl(path):
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def measure_official():
    """Exposure on IFEval's own released data. Returns a dict; if the data
    files are missing it records that honestly instead of guessing."""
    ip = os.path.join(DATA_DIR, INPUT_DATA)
    rp = os.path.join(DATA_DIR, GPT4_DATA)
    if not (os.path.exists(ip) and os.path.exists(rp)):
        return {
            "available": False,
            "note": "IFEval data files not present in /data; exposure not measured.",
        }
    prompts = read_jsonl(ip)
    responses = read_jsonl(rp)
    resp_by_prompt = {r["prompt"]: r["response"] for r in responses}

    n_instances = 0
    n_matched = 0
    n_flip = 0
    n_false_pass = 0
    n_false_fail = 0
    markers_seen = {}
    flips = []
    for item in prompts:
        iids = item.get("instruction_id_list", [])
        kwargs = item.get("kwargs", [])
        prompt = item.get("prompt", "")
        for idx, iid in enumerate(iids):
            if iid != "detectable_content:postscript":
                continue
            n_instances += 1
            kw = kwargs[idx] if idx < len(kwargs) and kwargs[idx] else {}
            marker = kw.get("postscript_marker")
            markers_seen[marker] = markers_seen.get(marker, 0) + 1
            if marker is None:
                continue
            resp = resp_by_prompt.get(prompt)
            if resp is None:
                continue
            n_matched += 1
            ship = shipped_check(resp, marker)
            intended = intended_check(resp, marker)
            if ship != intended:
                n_flip += 1
                if ship and not intended:
                    n_false_pass += 1
                else:
                    n_false_fail += 1
                flips.append({
                    "prompt_head": prompt[:80],
                    "marker": marker,
                    "shipped_verdict": ship,
                    "intended_verdict": intended,
                })
    return {
        "available": True,
        "n_prompts": len(prompts),
        "n_postscript_instances": n_instances,
        "n_markers_seen": markers_seen,
        "n_matched_to_gpt4_response": n_matched,
        "n_verdict_flip": n_flip,
        "n_false_pass": n_false_pass,
        "n_false_fail": n_false_fail,
        "flips": flips,
    }


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    summary, rows = build_corpus()
    assert summary == TARGET, f"corpus {summary} != target {TARGET}"

    official = measure_official()

    results = {
        "audit": "ifeval-postscript-hazards",
        "target_checker": "IFEval detectable_content:postscript (PostscriptChecker)",
        "synthetic_corpus": summary,
        "cases": rows,
        "official_exposure": official,
    }
    with open(os.path.join(OUT_DIR, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)

    here = os.path.dirname(os.path.abspath(__file__))
    for name in SOURCE_FILES:
        src = os.path.join(here, name)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(OUT_DIR, name))

    print("synthetic_corpus:", json.dumps(summary))
    print("official_exposure:", json.dumps(official))
    print("OK: corpus matches pre-registered target")


if __name__ == "__main__":
    main()
