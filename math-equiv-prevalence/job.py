# Run the pre-registered math-equiv exposure study over all 12,500 MATH problems.
#
# Reads openai/prm800k math_splits train.jsonl + test.jsonl (MIT) from --data-dir
# (downloading them if absent), extracts each gold the way lm-evaluation-harness
# does, and writes results.json with M0-M6, the graded predictions P1-P6, the
# original-test-split breakdown and the exploratory answer-field comparison.
#
# Apache-2.0. Made with AI by MV2 of Munim, Inc.

import argparse
import hashlib
import json
import os
import sys
import tempfile
import urllib.request

import math_equiv as me
import prevalence as pv

URLS = {
    "train.jsonl": "https://media.githubusercontent.com/media/openai/prm800k/main/prm800k/math_splits/train.jsonl",
    "test.jsonl": "https://media.githubusercontent.com/media/openai/prm800k/main/prm800k/math_splits/test.jsonl",
    "math_equiv.py": "https://raw.githubusercontent.com/munimtechnologies/munimtechnologies.github.io/main/math-equiv-hazards/math_equiv.py",
}


def find_or_fetch(name, data_dir, tmp_dir):
    for root, _, files in os.walk(data_dir):
        for f in files:
            if f == name or f.endswith("_" + name) or f.endswith("-" + name):
                return os.path.join(root, f)
    os.makedirs(tmp_dir, exist_ok=True)
    path = os.path.join(tmp_dir, name)
    try:
        urllib.request.urlretrieve(URLS[name], path)
    except Exception as e:
        print("could not fetch %s: %s" % (name, e))
        return None
    return path


def load_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line.startswith("version https://git-lfs"):
                raise SystemExit("%s is a Git LFS pointer, not data" % path)
            if line:
                rows.append(json.loads(line))
    return rows


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args()
    tmp = tempfile.mkdtemp(prefix="fetch-")

    local = os.path.abspath(me.__file__)
    published = find_or_fetch("math_equiv.py", args.data_dir, tmp)
    checker = {"local_sha256": sha256(local)}
    if published:
        checker["published_sha256"] = sha256(published)
        checker["byte_identical"] = checker["local_sha256"] == checker["published_sha256"]
        with open(local, encoding="utf-8") as a, open(published, encoding="utf-8") as b:
            checker["identical_ignoring_trailing_whitespace"] = a.read().rstrip() == b.read().rstrip()
    print("checker:", json.dumps(checker))

    rows, sources = [], {}
    for name in ("train.jsonl", "test.jsonl"):
        path = find_or_fetch(name, args.data_dir, tmp)
        if not path:
            raise SystemExit("missing %s" % name)
        part = load_jsonl(path)
        sources[name] = {"rows": len(part), "sha256": sha256(path)}
        rows.extend(part)

    seen, golds, no_gold, answers = set(), [], [], {}
    for row in rows:
        uid = row["unique_id"]
        if uid in seen:
            continue
        seen.add(uid)
        g = pv.extract_gold(row["solution"])
        if g is None:
            no_gold.append(uid)
            continue
        golds.append((uid, g))
        answers[uid] = row.get("answer")

    res = {"study": "math-equiv-prevalence", "prereg": "prereg.md", "checker": checker,
           "sources": sources, "n_rows": len(rows), "n_unique": len(seen),
           "n_no_gold": len(no_gold), "no_gold_ids": no_gold}
    res["all"] = pv.measure(golds)
    res["predictions"] = pv.grade(res["all"])
    res["original_test"] = pv.measure([x for x in golds if x[0].startswith("test/")])

    mism = [{"id": uid, "gold": g, "answer": answers[uid]} for uid, g in golds
            if answers[uid] is not None and not me.is_equiv(answers[uid], g)]
    res["exploratory_answer_field_mismatch"] = {"count": len(mism), "items": mism}

    os.makedirs(args.out_dir, exist_ok=True)
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, ensure_ascii=False)

    a = res["all"]
    print("rows %d unique %d gold %d no_gold %d" % (len(rows), len(seen), a["n_gold"], len(no_gold)))
    for part in ("all", "original_test"):
        m = res[part]
        print("[%s] n=%d M0=%s M1 L=%d C=%d (L only %d) M2=%d a=%d b=%d c=%d M3 L=%d C=%d "
              "M4 L=%d C=%d M5=%s M6 pos=%s neg=%s" % (
                  part, m["n_gold"], m["M0"], m["M1"]["L"]["count"], m["M1"]["C"]["count"],
                  len(m["M1_L_only"]), m["M2"]["count"], m["M2"]["M2a"], m["M2"]["M2b"],
                  m["M2"]["M2c"], m["M3"]["L"]["count"], m["M3"]["C"]["count"],
                  m["M4"]["L"]["count"], m["M4"]["C"]["count"], m["M5"],
                  m["M6"]["pos"], m["M6"]["neg"]))
    for k, v in res["predictions"].items():
        print(k, "HIT" if v["hit"] else "MISS", json.dumps({x: y for x, y in v.items() if x != "hit"}))
    print("M2b tails:", json.dumps([(i["id"], i["gold"]) for i in a["M2"]["items"]
                                    if i["connective"]], ensure_ascii=False))
    print("M1 L-only:", json.dumps(a["M1_L_only"], ensure_ascii=False))
    print("exploratory answer-field mismatches:", len(mism))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
