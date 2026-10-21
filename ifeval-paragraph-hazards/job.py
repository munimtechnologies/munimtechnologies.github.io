# Sealed compute job for the ifeval-paragraph-hazards audit.
#
# 1. Re-derive the pre-registered synthetic corpus and ASSERT it matches TARGET
#    (guards the checker reproduction; non-zero exit if it drifts).
# 2. Measure exposure on IFEval's own released data: how many of the 541 prompts
#    require an exact number of paragraphs (length_constraints:number_paragraphs),
#    and across the released GPT-4 responses how often the response contains a
#    divider that is NOT a standalone '***' line (inline emphasis / separators),
#    how often it hard-fails on an interior-empty segment, and whether using the
#    corrected (standalone-line) count would FLIP the exact-equality verdict.
#    Examples are kept for manual review.
# 3. Copy every source file into /out so the artifact is reproducible straight
#    from the compute output, independent of the purged run folder.
#
# Pure stdlib. IFEval data is downloaded over the network from the public
# google-research release; missing/failed files are recorded honestly.
# Audit by AI agents working in MV2's name (Munim, Inc.). Apache-2.0.

import json
import os
import shutil
import urllib.request

from paragraph_checker import (
    count_paragraphs, check_following, corrected_count,
    n_upstream_dividers, n_standalone_dividers,
)
from cases import CASES, TARGET

OUT_DIR = "/out"
SOURCE_FILES = [
    "paragraph_checker.py",
    "cases.py",
    "test_paragraph_checker.py",
    "job.py",
    "README.md",
]

RAW = ("https://raw.githubusercontent.com/google-research/google-research/"
       "master/instruction_following_eval/data")
INPUT_URL = RAW + "/input_data.jsonl"
GPT4_URL = RAW + "/input_response_data_gpt4_20231107_145030.jsonl"

PARAGRAPH_ID = "length_constraints:number_paragraphs"


def fetch_lines(url):
    req = urllib.request.Request(url, headers={"User-Agent": "mv2-research-audit"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        text = resp.read().decode("utf-8")
    return [json.loads(ln) for ln in text.splitlines() if ln.strip()]


def build_corpus():
    agg = {"n_cases": 0, "n_match": 0, "n_correct_neg": 0,
           "n_false_pass": 0, "n_false_fail": 0, "n_flips": 0,
           "all_reproduced": True}
    key = {"match": "n_match", "correct_neg": "n_correct_neg",
           "false_pass": "n_false_pass", "false_fail": "n_false_fail"}
    from paragraph_checker import classify
    for (cid, value, num_req, true_count, exp_num, exp_hard_fail,
         exp_verdict, _note) in CASES:
        num, hard_fail = count_paragraphs(value)
        if num != exp_num or hard_fail != exp_hard_fail:
            agg["all_reproduced"] = False
        if corrected_count(value) != true_count:
            agg["all_reproduced"] = False
        verdict = classify(value, num_req, true_count)
        if verdict != exp_verdict:
            agg["all_reproduced"] = False
        agg["n_cases"] += 1
        agg[key[verdict]] += 1
    agg["n_flips"] = agg["n_false_pass"] + agg["n_false_fail"]
    return agg


def paragraph_requirement(item):
    """Return the required num_paragraphs for such a prompt, else None."""
    ids = item.get("instruction_id_list") or []
    kwargs = item.get("kwargs") or []
    for i, iid in enumerate(ids):
        if iid == PARAGRAPH_ID:
            kw = kwargs[i] if i < len(kwargs) else {}
            return (kw or {}).get("num_paragraphs")
    return None


def measure_exposure():
    try:
        inputs = fetch_lines(INPUT_URL)
    except Exception as e:
        return {"available": False, "note": "input_data.jsonl failed: %r" % e}
    try:
        responses = fetch_lines(GPT4_URL)
    except Exception as e:
        return {"available": False, "note": "gpt4 responses failed: %r" % e}

    prompt_to_resp = {}
    for r in responses:
        p = r.get("prompt")
        if p is not None:
            prompt_to_resp[p] = r.get("response", "")

    para_prompts = []
    for it in inputs:
        n = paragraph_requirement(it)
        if n is not None:
            para_prompts.append((it.get("prompt"), n))

    present = missing = checker_pass = 0
    n_nonstandalone = n_hard_fail = n_flips = 0
    examples = []
    for prompt, n_required in para_prompts:
        resp = prompt_to_resp.get(prompt)
        if resp is None:
            missing += 1
            continue
        present += 1
        num, hard_fail = count_paragraphs(resp)
        passed = check_following(resp, n_required)
        if passed:
            checker_pass += 1
        if hard_fail:
            n_hard_fail += 1
        nonstandalone = n_upstream_dividers(resp) > n_standalone_dividers(resp)
        if nonstandalone:
            n_nonstandalone += 1
        corrected = corrected_count(resp)
        corrected_verdict = (corrected == n_required)
        if passed != corrected_verdict:
            n_flips += 1
            if len(examples) < 25:
                examples.append({
                    "prompt_head": str(prompt)[:90],
                    "num_required": n_required,
                    "upstream_num": num,
                    "hard_fail": hard_fail,
                    "corrected_count": corrected,
                    "nonstandalone_divider": nonstandalone,
                    "checker_pass": passed,
                    "corrected_pass": corrected_verdict,
                })

    return {
        "available": True,
        "n_prompts_total": len(inputs),
        "n_prompts_require_paragraphs": len(para_prompts),
        "n_responses_present": present,
        "n_responses_missing": missing,
        "n_checker_pass": checker_pass,
        "n_responses_with_nonstandalone_divider": n_nonstandalone,
        "n_responses_hard_fail": n_hard_fail,
        "n_verdict_flips_if_corrected": n_flips,
        "examples": examples,
    }


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    summary = build_corpus()
    assert summary == TARGET, "corpus %r != target %r" % (summary, TARGET)

    exposure = measure_exposure()

    results = {
        "audit": "ifeval-paragraph-hazards",
        "target": "IFEval ParagraphChecker (length_constraints:number_paragraphs)",
        "what": ("IFEval splits a response on the divider regex r'\\s?\\*\\*\\*\\s?' "
                 "(NOT line-anchored), trims boundary-empty segments, HARD-FAILS on "
                 "an interior-empty segment, and passes only on EXACT equality with "
                 "the required paragraph count. An inline '***emphasis***' span is "
                 "matched twice and over-counts; a single prose line using '***' as "
                 "separators is read as multiple paragraphs; a doubled divider "
                 "triggers an interior-empty hard fail. Under exact equality this "
                 "flips verdicts in both directions."),
        "method": {
            "checker": "verbatim reproduction of ParagraphChecker.check_following.",
            "corpus": "7 hand-traced cases; verdict = checker exact-equality vs ground truth.",
            "corrected_count": ("split only on a STANDALONE '***' divider line and keep "
                                "non-empty blocks."),
            "exposure": ("across GPT-4 responses to the paragraph-requiring prompts: how "
                         "many contain a non-standalone (inline) divider, how many hard-fail "
                         "on an interior-empty segment, and in how many the corrected count "
                         "flips the exact-equality verdict; examples kept for manual review."),
        },
        "synthetic_corpus": summary,
        "exposure": exposure,
    }
    with open(os.path.join(OUT_DIR, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)

    here = os.path.dirname(os.path.abspath(__file__))
    for name in SOURCE_FILES:
        src = os.path.join(here, name)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(OUT_DIR, name))

    print("synthetic_corpus:", json.dumps(summary))
    if exposure.get("available"):
        print("prompts_requiring_paragraphs: %d of %d" % (
            exposure["n_prompts_require_paragraphs"], exposure["n_prompts_total"]))
        print("responses_present=%d checker_pass=%d nonstandalone=%d hard_fail=%d flips=%d" % (
            exposure["n_responses_present"], exposure["n_checker_pass"],
            exposure["n_responses_with_nonstandalone_divider"],
            exposure["n_responses_hard_fail"],
            exposure["n_verdict_flips_if_corrected"]))
    else:
        print("exposure UNAVAILABLE:", exposure.get("note"))
    print("OK: corpus matches pre-registered target")


if __name__ == "__main__":
    main()
