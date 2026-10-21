# Sealed compute job for the ifeval-section-hazards audit.
#
# 1. Re-derive the pre-registered synthetic corpus and ASSERT it matches TARGET
#    (guards the checker reproduction; non-zero exit if it drifts).
# 2. Measure exposure on IFEval's own released data: how many of the 541 prompts
#    require a number of sections (detectable_format:multiple_sections), and
#    across the released GPT-4 responses how often the upstream count exceeds the
#    corrected line-start count (an inline/substring match inflated it), and
#    whether using the corrected count would FLIP the >= verdict. Examples kept.
# 3. Copy every source file into /out so the artifact is reproducible straight
#    from the compute output, independent of the purged run folder.
#
# Pure stdlib. IFEval data is downloaded over the network from the public
# google-research release; missing/failed files are recorded honestly. The
# per-response loop is guarded so a pathological section_spliter cannot abort
# the whole measurement.
# Audit by AI agents working in MV2's name (Munim, Inc.). Apache-2.0.

import json
import os
import shutil
import urllib.request

from section_checker import count_sections, check_following, corrected_count
from cases import CASES, TARGET

OUT_DIR = "/out"
SOURCE_FILES = [
    "section_checker.py",
    "cases.py",
    "test_section_checker.py",
    "job.py",
    "README.md",
]

RAW = ("https://raw.githubusercontent.com/google-research/google-research/"
       "master/instruction_following_eval/data")
INPUT_URL = RAW + "/input_data.jsonl"
GPT4_URL = RAW + "/input_response_data_gpt4_20231107_145030.jsonl"

SECTION_ID = "detectable_format:multiple_sections"


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
    for (cid, value, spliter, num_req, true_count, exp_num,
         exp_verdict, _note) in CASES:
        if count_sections(value, spliter) != exp_num:
            agg["all_reproduced"] = False
        if corrected_count(value, spliter) != true_count:
            agg["all_reproduced"] = False
        verdict = classify_wrap(value, spliter, num_req, true_count)
        if verdict != exp_verdict:
            agg["all_reproduced"] = False
        agg["n_cases"] += 1
        agg[key[verdict]] += 1
    agg["n_flips"] = agg["n_false_pass"] + agg["n_false_fail"]
    return agg


def classify_wrap(value, spliter, num_req, true_count):
    from section_checker import classify
    return classify(value, spliter, num_req, true_count)


def section_requirement(item):
    """Return (section_spliter, num_sections) for such a prompt, else None."""
    ids = item.get("instruction_id_list") or []
    kwargs = item.get("kwargs") or []
    for i, iid in enumerate(ids):
        if iid == SECTION_ID:
            kw = kwargs[i] if i < len(kwargs) else {}
            kw = kw or {}
            return (kw.get("section_spliter"), kw.get("num_sections"))
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

    sec_prompts = []
    for it in inputs:
        req = section_requirement(it)
        if req is not None and req[0] is not None and req[1] is not None:
            sec_prompts.append((it.get("prompt"), req[0], req[1]))

    present = missing = checker_pass = 0
    n_inline = n_flips = n_errors = 0
    examples = []
    for prompt, spliter, n_required in sec_prompts:
        resp = prompt_to_resp.get(prompt)
        if resp is None:
            missing += 1
            continue
        present += 1
        try:
            upstream = count_sections(resp, spliter)
            passed = check_following(resp, n_required, spliter)
            corrected = corrected_count(resp, spliter)
        except Exception:
            n_errors += 1
            continue
        if passed:
            checker_pass += 1
        inline = upstream > corrected
        if inline:
            n_inline += 1
        corrected_verdict = (corrected >= n_required)
        if passed != corrected_verdict:
            n_flips += 1
            if len(examples) < 25:
                examples.append({
                    "prompt_head": str(prompt)[:90],
                    "spliter": spliter,
                    "num_required": n_required,
                    "upstream_num": upstream,
                    "corrected_count": corrected,
                    "inline_or_substring_match": inline,
                    "checker_pass": passed,
                    "corrected_pass": corrected_verdict,
                })

    return {
        "available": True,
        "n_prompts_total": len(inputs),
        "n_prompts_require_sections": len(sec_prompts),
        "n_responses_present": present,
        "n_responses_missing": missing,
        "n_checker_pass": checker_pass,
        "n_responses_with_inline_match": n_inline,
        "n_verdict_flips_if_corrected": n_flips,
        "n_eval_errors": n_errors,
        "examples": examples,
    }


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    summary = build_corpus()
    assert summary == TARGET, "corpus %r != target %r" % (summary, TARGET)

    exposure = measure_exposure()

    results = {
        "audit": "ifeval-section-hazards",
        "target": "IFEval SectionChecker (detectable_format:multiple_sections)",
        "what": ("IFEval builds the split pattern r'\\s?'+spliter+r'\\s?\\d+\\s?' with no "
                 "re.escape and no line anchoring, sets num_sections = len(split)-1, and "
                 "passes on num_sections >= required. The unbounded pattern counts inline "
                 "cross-references ('see Section 3') and in-word substrings ('subSection3') "
                 "as section boundaries, so too-few-section answers can pass; and because it "
                 "requires a digit, spelled-out numbers ('Section One') match nothing and a "
                 "correct answer fails. Under >= this flips verdicts in both directions."),
        "method": {
            "checker": "verbatim reproduction of SectionChecker.check_following.",
            "corpus": "7 hand-traced cases (spliter 'Section'); verdict = checker >= vs ground truth.",
            "corrected_count": ("count only line-start spliter keyword + a digit OR a spelled-out "
                                "number word (case-insensitive)."),
            "exposure": ("across GPT-4 responses to the section-requiring prompts: how many have "
                         "an upstream count above the corrected line-start count (an inline or "
                         "substring match), and in how many the corrected count flips the >= "
                         "verdict; examples kept for manual review."),
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
        print("prompts_requiring_sections: %d of %d" % (
            exposure["n_prompts_require_sections"], exposure["n_prompts_total"]))
        print("responses_present=%d checker_pass=%d inline_match=%d flips=%d errors=%d" % (
            exposure["n_responses_present"], exposure["n_checker_pass"],
            exposure["n_responses_with_inline_match"],
            exposure["n_verdict_flips_if_corrected"],
            exposure["n_eval_errors"]))
    else:
        print("exposure UNAVAILABLE:", exposure.get("note"))
    print("OK: corpus matches pre-registered target")


if __name__ == "__main__":
    main()
