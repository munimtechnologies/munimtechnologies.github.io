#!/usr/bin/env python3
# Audit 116 check job: HELM's KPI-EDGAR adjusted_macro_f1_score on the real test split.
# MV2 of Munim, Inc. -- made by AI agents working in MV2's name. Licence: Apache-2.0.
#
# A check, not a pre-registration: the floors are code-certain (see README). This job only puts numbers on them
# for HELM's own test split, built the way HELM's KPIEDGARScenario builds it from the same pinned file, and
# scores fixed reference answers (no model outputs are used; HELM publishes none for this scenario).
# Standard library only.
import argparse
import hashlib
import json
import os
import statistics
import urllib.request

import kpi_edgar_check as k

URL = ("https://raw.githubusercontent.com/tobideusser/kpi-edgar/"
       "2ec7084dcd55b4979bbe288d4aa1e962c685c9ab/data/kpi_edgar.json")
UA = {"User-Agent": "mv2-munim-research/1.0 (mv2@munimtech.com)"}
MAX_TOKENS = 100  # HELM's kpi_edgar run spec


def escape(text):
    """KPIEDGARScenario.escape_parenthesis: square brackets become round ones."""
    return text.replace("[", "(").replace("]", ")")


def build(dataset):
    """KPIEDGARScenario.get_sentences + sentences_to_instances + get_output_text."""
    out = {"train": [], "valid": [], "test": []}
    notes = {"split_none": 0, "split_other": 0, "no_tagged_entity": 0, "entities_anno_none": 0}
    for document in dataset:
        for segment in document["segments"]:
            for sentence in segment["sentences"] or []:
                split = sentence["split_type"]
                if split is None:
                    notes["split_none"] += 1
                    continue
                if split not in out:
                    notes["split_other"] += 1
                    continue
                words = [w["value"] for w in sentence["words"]]
                passage = escape(" ".join(words))
                annos = sentence["entities_anno"]
                if annos is None:
                    notes["entities_anno_none"] += 1
                    annos = []
                ents = []
                for a in annos:
                    if a["type_"] not in k.TAGS:
                        continue
                    ents.append((escape(" ".join(words[a["start"]:a["end"]])), a["type_"]))
                gold = ", ".join("%s [%s]" % e for e in ents)
                if not gold:
                    notes["no_tagged_entity"] += 1
                    continue
                out[split].append({"passage": passage, "gold": gold, "ents": ents})
    return out, notes


def first_words(ents):
    parts = []
    for phrase, tag in ents:
        w = phrase.split()
        if w:
            parts.append("%s [%s]" % (w[0], tag))
    return ", ".join(parts)


def one_word_per_tag(test):
    """For each tag, the first word of its first gold entity in the first test sentence that has one; all
    other answers empty."""
    answers = [[] for _ in test]
    for tag in k.TAGS:
        for i, inst in enumerate(test):
            hit = [p for p, t in inst["ents"] if t == tag and p.split()]
            if hit:
                answers[i].append("%s [%s]" % (hit[0].split()[0], tag))
                break
    return [(inst["gold"], ", ".join(a)) for inst, a in zip(test, answers)]


def evaluate(records):
    res = {}
    for o in ("helm", "fixed"):
        s = k.score(records, o)
        res[o] = {"adjusted_macro_f1_score": round(s["adjusted_macro_f1_score"], 6),
                  "word_macro_f1_score": round(s["word_macro_f1_score"], 6),
                  "per_tag": {t: {kk: (round(v, 6) if isinstance(v, float) else v) for kk, v in d.items()}
                              for t, d in k.tag_scores(records, o).items()}}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    req = urllib.request.Request(URL, headers=UA)
    with urllib.request.urlopen(req, timeout=300) as r:
        raw = r.read()
    sha = hashlib.sha256(raw).hexdigest()
    print("[data] %d bytes sha256 %s" % (len(raw), sha))
    data, notes = build(json.loads(raw.decode("utf-8")))
    sizes = {s: len(v) for s, v in data.items()}
    print("[data] instances %s notes %s" % (sizes, notes))
    test = data["test"]

    tag_sentences = {t: sum(1 for i in test if any(tt == t for _, tt in i["ents"])) for t in k.TAGS}
    print("[data] test sentences with each tag %s" % tag_sentences)

    strategies = {
        "gold": [(i["gold"], i["gold"]) for i in test],
        "empty": [(i["gold"], "") for i in test],
        "copy_sentence_all_tags": [(i["gold"], k.copy_answer(i["passage"])) for i in test],
        "first_word_of_each_gold_entity": [(i["gold"], first_words(i["ents"])) for i in test],
        "one_word_per_tag_in_whole_split": one_word_per_tag(test),
    }
    results = {"source": URL, "sha256": sha, "instances": sizes, "notes": notes,
               "test_sentences_with_tag": tag_sentences, "strategies": {}}
    for name, recs in strategies.items():
        try:
            results["strategies"][name] = evaluate(recs)
        except Exception as e:  # report, do not hide
            results["strategies"][name] = {"error": "%s: %s" % (type(e).__name__, e)}
        r = results["strategies"][name]
        if "error" in r:
            print("[%s] ERROR %s" % (name, r["error"]))
        else:
            print("[%s] HELM adjusted %.6f | PR #4350 order adjusted %.6f | word F1 %.6f" % (
                name, r["helm"]["adjusted_macro_f1_score"], r["fixed"]["adjusted_macro_f1_score"],
                r["fixed"]["word_macro_f1_score"]))

    lens = [len(i["passage"].split()) for i in test]
    copy_words = [4 * n + 4 for n in lens]
    lens_sorted = sorted(lens)
    length = {
        "passage_words_median": statistics.median(lens) if lens else None,
        "passage_words_p90": lens_sorted[int(0.9 * (len(lens_sorted) - 1))] if lens else None,
        "passage_words_max": max(lens) if lens else None,
        "copy_answers_within_%d_whitespace_words" % MAX_TOKENS: sum(1 for c in copy_words if c <= MAX_TOKENS),
    }
    results["length"] = length
    print("[length] %s (whitespace words; model tokens are usually more, so this is an upper bound on fits)"
          % length)

    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1, sort_keys=True)
    print("[done] wrote results.json")


if __name__ == "__main__":
    main()
