# Sealed compute job for the ifeval-title-hazards audit.
#
# 1. Re-derive the pre-registered synthetic corpus and ASSERT it matches the
#    pre-registered target (guards the checker reproduction; non-zero exit if it
#    drifts).
# 2. Measure exposure on IFEval's own released data: how many of the 541 prompts
#    require a title (detectable_format:title) -- the checker's blast radius --
#    and, across every released GPT-4 response, how often the <<...>> marker
#    matches at all, with examples kept for manual inspection of whether any
#    match is an operator/heredoc conflation rather than a real title.
# 3. Copy every source file into /out so the artifact is reproducible straight
#    from the compute output, independent of the purged run folder.
#
# Pure stdlib. IFEval data is downloaded over the network from the public
# google-research release; missing/failed files are recorded honestly.
# Audit by AI agents working in MV2's name (Munim, Inc.). Apache-2.0.

import json
import os
import re
import shutil
import urllib.request

from title_checker import check_title, classify
from cases import CASES, TARGET

OUT_DIR = "/out"
SOURCE_FILES = [
    "title_checker.py",
    "cases.py",
    "test_title_checker.py",
    "job.py",
    "README.md",
]

RAW = ("https://raw.githubusercontent.com/google-research/google-research/"
       "master/instruction_following_eval/data")
INPUT_URL = RAW + "/input_data.jsonl"
GPT4_URL = RAW + "/input_response_data_gpt4_20231107_145030.jsonl"

TITLE_ID = "detectable_format:title"
MARKER = re.compile(r"<<[^\n]+>>")


def fetch_lines(url):
    req = urllib.request.Request(url, headers={"User-Agent": "mv2-research-audit"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        text = resp.read().decode("utf-8")
    return [json.loads(ln) for ln in text.splitlines() if ln.strip()]


def build_corpus():
    n_true = n_false_pass = n_false_fail = 0
    all_ok = True
    for cid, value, intended, exp, note in CASES:
        if check_title(value):
            n_true += 1
        verdict = classify(value, intended)
        if verdict != exp:
            all_ok = False
        if verdict == "false_pass":
            n_false_pass += 1
        elif verdict == "false_fail":
            n_false_fail += 1
    return {
        "n_cases": len(CASES),
        "n_checker_true": n_true,
        "n_flips": n_false_pass + n_false_fail,
        "n_false_pass": n_false_pass,
        "n_false_fail": n_false_fail,
        "all_reproduced": all_ok,
    }


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

    title_prompts = [it for it in inputs
                     if TITLE_ID in (it.get("instruction_id_list") or [])]

    # Checker verdict on the GPT-4 responses to the title-requiring prompts.
    title_resp_true = title_resp_false = title_resp_missing = 0
    for it in title_prompts:
        resp = prompt_to_resp.get(it.get("prompt"))
        if resp is None:
            title_resp_missing += 1
            continue
        if check_title(resp):
            title_resp_true += 1
        else:
            title_resp_false += 1

    # Marker occurrences across ALL released GPT-4 responses, with examples kept
    # for manual inspection (operator/heredoc conflation vs genuine title).
    title_prompt_set = set(it.get("prompt") for it in title_prompts)
    n_marker_responses = 0
    examples = []
    for p, resp in prompt_to_resp.items():
        matches = re.findall(MARKER, resp)
        nonempty = [m for m in matches if m.lstrip("<").rstrip(">").strip()]
        if nonempty:
            n_marker_responses += 1
            if len(examples) < 25:
                examples.append({
                    "prompt_head": str(p)[:90],
                    "is_title_prompt": p in title_prompt_set,
                    "marker_matches": nonempty[:5],
                })

    return {
        "available": True,
        "n_prompts_total": len(inputs),
        "n_prompts_require_title": len(title_prompts),
        "title_prompt_responses": {
            "checker_true": title_resp_true,
            "checker_false": title_resp_false,
            "response_missing": title_resp_missing,
        },
        "n_responses_total": len(prompt_to_resp),
        "n_responses_with_marker": n_marker_responses,
        "marker_examples": examples,
    }


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    summary = build_corpus()
    assert summary == TARGET, "corpus %r != target %r" % (summary, TARGET)

    exposure = measure_exposure()

    results = {
        "audit": "ifeval-title-hazards",
        "target": "IFEval TitleChecker (detectable_format:title)",
        "what": ("IFEval accepts a title via re.findall(r'<<[^\\n]+>>', value); that "
                 "marker is also ordinary left-shift/right-shift operator and shell "
                 "heredoc/redirect syntax, so a single line containing 'a << b >> c' "
                 "is credited with a title that was never written (false pass)."),
        "method": {
            "checker": "verbatim reproduction of TitleChecker.check_following.",
            "corpus": "5 hand-traced cases; verdict = checker vs intended semantic.",
            "exposure": ("count of prompts requiring a title; checker verdicts on their "
                         "GPT-4 responses; marker occurrences across all responses with "
                         "examples for manual inspection (no auto-labelling of real data)."),
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
        print("prompts_requiring_title: %d of %d" % (
            exposure["n_prompts_require_title"], exposure["n_prompts_total"]))
        print("title-prompt GPT-4 responses:", json.dumps(exposure["title_prompt_responses"]))
        print("responses_with_marker: %d of %d" % (
            exposure["n_responses_with_marker"], exposure["n_responses_total"]))
    else:
        print("exposure UNAVAILABLE:", exposure.get("note"))
    print("OK: corpus matches pre-registered target")


if __name__ == "__main__":
    main()
