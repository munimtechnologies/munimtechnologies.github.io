# Sealed compute job for the ifeval-bullet-list-hazards audit.
#
# 1. Re-derive the pre-registered synthetic corpus and ASSERT it matches TARGET
#    (guards the checker reproduction; non-zero exit if it drifts).
# 2. Measure exposure on IFEval's own released data: how many of the 541 prompts
#    require an exact number of bullet points (detectable_format:number_bullet_lists),
#    and across their released GPT-4 responses how often the checker counts a
#    marker line that CommonMark would NOT render as a bullet (a dash or asterisk
#    with no following space), whether that inflates the count, and whether the
#    inflation FLIPS the exact-equality verdict. Examples are kept for manual review.
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

from bullet_checker import count_bullets, corrected_count, check_following
from cases import CASES, TARGET

OUT_DIR = "/out"
SOURCE_FILES = [
    "bullet_checker.py",
    "cases.py",
    "test_bullet_checker.py",
    "job.py",
    "README.md",
]

RAW = ("https://raw.githubusercontent.com/google-research/google-research/"
       "master/instruction_following_eval/data")
INPUT_URL = RAW + "/input_data.jsonl"
GPT4_URL = RAW + "/input_response_data_gpt4_20231107_145030.jsonl"

BULLET_ID = "detectable_format:number_bullet_lists"


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
    from bullet_checker import classify
    for cid, value, num_req, true_count, exp_count, exp_verdict, _note in CASES:
        if count_bullets(value) != exp_count:
            agg["all_reproduced"] = False
        verdict = classify(value, num_req, true_count)
        if verdict != exp_verdict:
            agg["all_reproduced"] = False
        agg["n_cases"] += 1
        agg[key[verdict]] += 1
    agg["n_flips"] = agg["n_false_pass"] + agg["n_false_fail"]
    return agg


def bullet_requirement(item):
    """Return the required num_bullets for a bullet-list prompt, else None."""
    ids = item.get("instruction_id_list") or []
    kwargs = item.get("kwargs") or []
    for i, iid in enumerate(ids):
        if iid == BULLET_ID:
            kw = kwargs[i] if i < len(kwargs) else {}
            return (kw or {}).get("num_bullets")
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

    bullet_prompts = []
    for it in inputs:
        n = bullet_requirement(it)
        if n is not None:
            bullet_prompts.append((it.get("prompt"), n))

    present = missing = checker_pass = 0
    n_with_suspicious = n_inflated = n_flips = 0
    examples = []
    for prompt, n_required in bullet_prompts:
        resp = prompt_to_resp.get(prompt)
        if resp is None:
            missing += 1
            continue
        present += 1
        upstream = count_bullets(resp)
        corrected = corrected_count(resp)
        suspicious = upstream - corrected
        if check_following(resp, n_required):
            checker_pass += 1
        if suspicious > 0:
            n_with_suspicious += 1
            n_inflated += 1
            checker_verdict = (upstream == n_required)
            corrected_verdict = (corrected == n_required)
            if checker_verdict != corrected_verdict:
                n_flips += 1
            if len(examples) < 25:
                examples.append({
                    "prompt_head": str(prompt)[:90],
                    "num_required": n_required,
                    "upstream_count": upstream,
                    "corrected_count": corrected,
                    "suspicious_lines": suspicious,
                    "checker_pass": checker_verdict,
                    "corrected_pass": corrected_verdict,
                    "flips": checker_verdict != corrected_verdict,
                })

    return {
        "available": True,
        "n_prompts_total": len(inputs),
        "n_prompts_require_bullets": len(bullet_prompts),
        "n_responses_present": present,
        "n_responses_missing": missing,
        "n_checker_pass": checker_pass,
        "n_responses_with_suspicious_line": n_with_suspicious,
        "n_responses_count_inflated": n_inflated,
        "n_verdict_flips_if_corrected": n_flips,
        "examples": examples,
    }


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    summary = build_corpus()
    assert summary == TARGET, "corpus %r != target %r" % (summary, TARGET)

    exposure = measure_exposure()

    results = {
        "audit": "ifeval-bullet-list-hazards",
        "target": "IFEval BulletListChecker (detectable_format:number_bullet_lists)",
        "what": ("IFEval counts bullet points with '^\\s*\\*[^\\*].*$' and '^\\s*-.*$' "
                 "(re.MULTILINE) and passes only on EXACT equality with the required "
                 "count. The dash pattern needs no space after '-', so a negative "
                 "number, a '---' rule or a stray dash line is counted as a bullet; "
                 "the asterisk pattern counts a '*italic*' line as a bullet. Under "
                 "exact equality this flips verdicts in both directions."),
        "method": {
            "checker": "verbatim reproduction of BulletListChecker.check_following.",
            "corpus": "7 hand-traced cases; verdict = checker exact-equality vs ground truth.",
            "corrected_count": ("count only marker lines followed by a space and content "
                                "(a rendered CommonMark list item)."),
            "exposure": ("across GPT-4 responses to the bullet-requiring prompts: how many "
                         "contain a counted-but-unrendered marker line, how many have an "
                         "inflated count, and in how many the inflation flips the "
                         "exact-equality verdict; examples kept for manual review."),
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
        print("prompts_requiring_bullets: %d of %d" % (
            exposure["n_prompts_require_bullets"], exposure["n_prompts_total"]))
        print("responses_present=%d checker_pass=%d with_suspicious=%d inflated=%d flips=%d" % (
            exposure["n_responses_present"], exposure["n_checker_pass"],
            exposure["n_responses_with_suspicious_line"],
            exposure["n_responses_count_inflated"],
            exposure["n_verdict_flips_if_corrected"]))
    else:
        print("exposure UNAVAILABLE:", exposure.get("note"))
    print("OK: corpus matches pre-registered target")


if __name__ == "__main__":
    main()
