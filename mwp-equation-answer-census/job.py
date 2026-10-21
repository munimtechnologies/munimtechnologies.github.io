# Sealed compute job for the mwp-equation-answer-census audit.
#
# 1. Re-derive the pre-registered synthetic corpus and ASSERT it matches the
#    pre-registered target (guards the evaluators; non-zero exit if it drifts).
# 2. Measure annotation consistency on three public MWP datasets: for every
#    problem, evaluate the dataset's OWN annotated equation and check it equals
#    the dataset's OWN annotated numeric answer. Report, per dataset, how many
#    annotations are internally inconsistent (equation does not produce the
#    stated answer), evaluable, or unevaluable.
# 3. Copy every source file into /out so the artifact is reproducible straight
#    from the compute output, independent of the purged run folder.
#
# Pure stdlib. Datasets are downloaded over the network (compete job) from the
# public arkilpatel/SVAMP release; missing/failed files are recorded honestly.
# Audit by AI agents working in MV2's name (Munim, Inc.). Apache-2.0.

import csv
import io
import json
import os
import shutil
import urllib.request

from mwp_eval import classify
from cases import CASES, TARGET

OUT_DIR = "/out"
SOURCE_FILES = [
    "mwp_eval.py",
    "cases.py",
    "test_mwp_eval.py",
    "job.py",
    "README.md",
]

RAW = "https://raw.githubusercontent.com/arkilpatel/SVAMP/main"
SVAMP_URL = RAW + "/SVAMP.json"
ASDIV_URLS = [RAW + "/data/cv_asdiv-a/fold%d/dev.csv" % i for i in range(5)]
MAWPS_URLS = [RAW + "/data/cv_mawps/fold%d/dev.csv" % i for i in range(5)]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "mv2-research-audit"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8")


def build_corpus():
    n_match = n_mismatch = n_uneval = 0
    all_ok = True
    for cid, notation, eq, nums, ans, exp, note in CASES:
        verdict, _ = classify(notation, eq, nums, ans)
        if verdict != exp:
            all_ok = False
        if verdict == "match":
            n_match += 1
        elif verdict == "mismatch":
            n_mismatch += 1
        else:
            n_uneval += 1
    return {
        "n_cases": len(CASES),
        "n_match": n_match,
        "n_mismatch": n_mismatch,
        "n_unevaluable": n_uneval,
        "all_reproduced": all_ok,
    }


def census(records):
    """records: list of (key, notation, equation, numbers, answer, head).
    Deduplicates by key, classifies each, aggregates."""
    seen = set()
    n_match = n_mismatch = n_uneval = 0
    mismatch_ex = []
    uneval_ex = []
    n_total = 0
    for key, notation, eq, nums, ans, head in records:
        if key in seen:
            continue
        seen.add(key)
        n_total += 1
        verdict, val = classify(notation, eq, nums, ans)
        if verdict == "match":
            n_match += 1
        elif verdict == "mismatch":
            n_mismatch += 1
            if len(mismatch_ex) < 25:
                mismatch_ex.append({
                    "head": head[:90],
                    "equation": eq,
                    "numbers": nums,
                    "annotated_answer": ans,
                    "computed": val,
                })
        else:
            n_uneval += 1
            if len(uneval_ex) < 15:
                uneval_ex.append({
                    "head": head[:90],
                    "equation": eq,
                    "numbers": nums,
                    "annotated_answer": ans,
                })
    n_eval = n_match + n_mismatch
    return {
        "available": True,
        "n_total": n_total,
        "n_evaluable": n_eval,
        "n_unevaluable": n_uneval,
        "n_match": n_match,
        "n_mismatch": n_mismatch,
        "mismatch_rate_of_evaluable": (n_mismatch / n_eval) if n_eval else None,
        "mismatch_examples": mismatch_ex,
        "unevaluable_examples": uneval_ex,
    }


def load_svamp():
    try:
        data = json.loads(fetch(SVAMP_URL))
    except Exception as e:
        return {"available": False, "note": "SVAMP.json fetch/parse failed: %r" % e}
    recs = []
    for item in data:
        eq = str(item.get("Equation", ""))
        ans = item.get("Answer")
        body = str(item.get("Body", "")) + " " + str(item.get("Question", ""))
        key = "svamp:" + str(item.get("ID", "")) + "|" + eq + "|" + str(ans)
        recs.append((key, "infix", eq, [], ans, body))
    out = census(recs)
    out["source_files"] = [SVAMP_URL]
    return out


def load_csv_dataset(urls, prefix):
    recs = []
    got = []
    for url in urls:
        try:
            text = fetch(url)
        except Exception:
            continue
        got.append(url)
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            eq = (row.get("Equation") or "").strip()
            nums_raw = (row.get("Numbers") or "").strip()
            try:
                nums = [float(x) for x in nums_raw.split()]
            except ValueError:
                nums = []
            ans = row.get("Answer")
            q = (row.get("Question") or row.get("Body") or "").strip()
            key = prefix + ":" + eq + "|" + nums_raw + "|" + str(ans) + "|" + q
            recs.append((key, "prefix", eq, nums, ans, q))
    if not got:
        return {"available": False, "note": "no fold files fetched"}
    out = census(recs)
    out["source_files"] = got
    return out


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    summary = build_corpus()
    assert summary == TARGET, "corpus %r != target %r" % (summary, TARGET)

    datasets = {
        "SVAMP": load_svamp(),
        "ASDiv-A": load_csv_dataset(ASDIV_URLS, "asdiv"),
        "MAWPS": load_csv_dataset(MAWPS_URLS, "mawps"),
    }

    results = {
        "audit": "mwp-equation-answer-census",
        "what": ("For each public MWP problem, evaluate its own annotated equation and "
                 "check it equals its own annotated numeric answer. Mismatch = the "
                 "released annotation is internally inconsistent."),
        "method": {
            "infix": "ast-based numeric eval over +,-,*,/ (no python eval); SVAMP.json.",
            "prefix": "stack machine over number tokens + Numbers column; ASDiv-A/MAWPS CV release.",
            "tolerance": "match if |computed - answer| <= 1e-3 absolute or relative.",
            "dedup": "within each dataset by (equation|numbers|answer|question).",
        },
        "synthetic_corpus": summary,
        "datasets": datasets,
    }
    with open(os.path.join(OUT_DIR, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)

    here = os.path.dirname(os.path.abspath(__file__))
    for name in SOURCE_FILES:
        src = os.path.join(here, name)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(OUT_DIR, name))

    print("synthetic_corpus:", json.dumps(summary))
    for name, d in datasets.items():
        if d.get("available"):
            print("%s: total=%d evaluable=%d mismatch=%d unevaluable=%d rate=%s" % (
                name, d["n_total"], d["n_evaluable"], d["n_mismatch"],
                d["n_unevaluable"], d["mismatch_rate_of_evaluable"]))
        else:
            print("%s: UNAVAILABLE (%s)" % (name, d.get("note")))
    print("OK: corpus matches pre-registered target")


if __name__ == "__main__":
    main()
