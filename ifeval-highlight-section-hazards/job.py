# Sealed compute job for the ifeval-highlight-section-hazards audit.
#
# 1. Re-derive the pre-registered synthetic corpus and ASSERT it matches the
#    pre-registered target (guards the checker reproduction; non-zero exit if it
#    drifts).
# 2. Measure exposure on IFEval's own released data: how many of the 541 prompts
#    require N highlighted sections (detectable_format:number_highlighted_sections)
#    -- the checker's blast radius -- and, across the released GPT-4 responses to
#    those prompts, how often the upstream count disagrees with a corrected count
#    that treats each '***text***' bold-italic span as ONE highlight, and in how
#    many cases that disagreement FLIPS the pass/fail verdict. Examples are kept
#    for manual inspection (no auto-labelling of real responses).
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

from highlight_checker import (
    count_highlights, count_triple_spans, corrected_count, classify,
)
from cases import CASES, TARGET

OUT_DIR = "/out"
SOURCE_FILES = [
    "highlight_checker.py",
    "cases.py",
    "test_highlight_checker.py",
    "job.py",
    "README.md",
]

RAW = ("https://raw.githubusercontent.com/google-research/google-research/"
       "master/instruction_following_eval/data")
INPUT_URL = RAW + "/input_data.jsonl"
GPT4_URL = RAW + "/input_response_data_gpt4_20231107_145030.jsonl"

HIGHLIGHT_ID = "detectable_format:number_highlighted_sections"


def fetch_lines(url):
    req = urllib.request.Request(url, headers={"User-Agent": "mv2-research-audit"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        text = resp.read().decode("utf-8")
    return [json.loads(ln) for ln in text.splitlines() if ln.strip()]


def build_corpus():
    n_match = n_correct_neg = n_false_pass = n_false_fail = 0
    all_ok = True
    for cid, value, req, intended, exp, note in CASES:
        verdict = classify(value, req, intended)
        if verdict != exp:
            all_ok = False
        if verdict == "match":
            n_match += 1
        elif verdict == "correct_neg":
            n_correct_neg += 1
        elif verdict == "false_pass":
            n_false_pass += 1
        else:
            n_false_fail += 1
    return {
        "n_cases": len(CASES),
        "n_match": n_match,
        "n_correct_neg": n_correct_neg,
        "n_false_pass": n_false_pass,
        "n_false_fail": n_false_fail,
        "n_flips": n_false_pass + n_false_fail,
        "all_reproduced": all_ok,
    }


def required_highlights(item):
    """Pull the num_highlights kwarg for the highlight instruction in `item`,
    joining instruction_id_list to the parallel kwargs list. Returns None if
    absent or malformed."""
    ids = item.get("instruction_id_list") or []
    kwargs = item.get("kwargs") or []
    for i, iid in enumerate(ids):
        if iid == HIGHLIGHT_ID and i < len(kwargs):
            kw = kwargs[i] or {}
            val = kw.get("num_highlights")
            if isinstance(val, int):
                return val
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

    highlight_prompts = [it for it in inputs
                         if HIGHLIGHT_ID in (it.get("instruction_id_list") or [])]

    n_resp_present = 0
    n_resp_missing = 0
    n_checker_pass = 0
    n_with_triple = 0          # response uses at least one '***text***' span
    n_count_inflated = 0       # upstream count > corrected count
    n_verdict_flips = 0        # checker passes but corrected count would fail
    flip_examples = []
    inflate_examples = []

    for it in highlight_prompts:
        req = required_highlights(it)
        resp = prompt_to_resp.get(it.get("prompt"))
        if resp is None:
            n_resp_missing += 1
            continue
        n_resp_present += 1
        up = count_highlights(resp)
        corr = corrected_count(resp)
        triples = count_triple_spans(resp)
        checker_pass = (req is not None) and (up >= req)
        if checker_pass:
            n_checker_pass += 1
        if triples > 0:
            n_with_triple += 1
        if corr < up:
            n_count_inflated += 1
            if len(inflate_examples) < 25:
                inflate_examples.append({
                    "prompt_head": str(it.get("prompt"))[:90],
                    "num_required": req,
                    "upstream_count": up,
                    "corrected_count": corr,
                    "triple_spans": triples,
                })
        if req is not None and checker_pass and corr < req:
            n_verdict_flips += 1
            if len(flip_examples) < 25:
                flip_examples.append({
                    "prompt_head": str(it.get("prompt"))[:90],
                    "num_required": req,
                    "upstream_count": up,
                    "corrected_count": corr,
                    "triple_spans": triples,
                })

    return {
        "available": True,
        "n_prompts_total": len(inputs),
        "n_prompts_require_highlight": len(highlight_prompts),
        "n_responses_present": n_resp_present,
        "n_responses_missing": n_resp_missing,
        "n_checker_pass": n_checker_pass,
        "n_responses_with_triple_span": n_with_triple,
        "n_responses_count_inflated": n_count_inflated,
        "n_verdict_flips_if_corrected": n_verdict_flips,
        "inflate_examples": inflate_examples,
        "flip_examples": flip_examples,
    }


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    summary = build_corpus()
    assert summary == TARGET, "corpus %r != target %r" % (summary, TARGET)

    exposure = measure_exposure()

    results = {
        "audit": "ifeval-highlight-section-hazards",
        "target": "IFEval HighlightSectionChecker (detectable_format:number_highlighted_sections)",
        "what": ("IFEval counts highlighted sections as (single-asterisk matches) + "
                 "(double-asterisk matches); a single '***text***' bold-italic span is "
                 "matched as both a single '*text*' and a double '**text**', so ONE "
                 "visual highlight is counted as 2, and a response can satisfy a "
                 "'highlight at least N sections' quota it did not really meet."),
        "method": {
            "checker": "verbatim reproduction of HighlightSectionChecker.check_following.",
            "corpus": "6 hand-traced cases; verdict = checker pass/fail vs ground-truth span count.",
            "corrected_count": "upstream count minus one per '***text***' span (each span is one visual highlight).",
            "exposure": ("across GPT-4 responses to the highlight-requiring prompts: how many use a "
                         "triple-asterisk span, how many have an inflated count, and in how many the "
                         "inflation would FLIP the pass/fail verdict; examples kept for manual review."),
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
        print("prompts_requiring_highlight: %d of %d" % (
            exposure["n_prompts_require_highlight"], exposure["n_prompts_total"]))
        print("responses_present=%d checker_pass=%d with_triple=%d inflated=%d flips=%d" % (
            exposure["n_responses_present"], exposure["n_checker_pass"],
            exposure["n_responses_with_triple_span"], exposure["n_responses_count_inflated"],
            exposure["n_verdict_flips_if_corrected"]))
    else:
        print("exposure UNAVAILABLE:", exposure.get("note"))
    print("OK: corpus matches pre-registered target")


if __name__ == "__main__":
    main()
