"""Does the pick-longest shortcut flip on NOT / EXCEPT questions? MMLU-Pro, MedMCQA and MedQA-USMLE (audit 68).

Audits 61-67 found that a question-free "pick the longest option" heuristic scores 18.4% on MMLU-Pro (chance 11.1%).
This job measures the same heuristic, and its mirror "pick the shortest", on the two medical multiple-choice sets
most medical LLM papers report (MedMCQA, openlifescienceai/medmcqa, Apache-2.0; MedQA-USMLE 4-option,
GBaker/MedQA-USMLE-4-options, CC BY 4.0) and on MMLU-Pro, split by whether the question's last sentence is
negatively worded (not / except / false / incorrect / untrue / least / n't).

Gates before any prediction is scored: hand-traced fixtures match, and the MMLU-Pro parse reproduces audit 63
exactly. Eight predictions were pre-registered before any count on the medical files was computed.

Usage: python job.py --out-dir /out   (network required)
Apache-2.0.
"""

import argparse
import io
import json
import os
import urllib.request
from fractions import Fraction

import pyarrow.parquet as pq

import cases
import polarity as pol

UA = {"User-Agent": "mv2-eval-reliability-audits/1.0 (research; contact mv2@munimtech.com)"}
PARQUET_API = "https://datasets-server.huggingface.co/parquet?dataset=%s"
LETTERS = "ABCD"


def _get(url, tries=4):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 - retry transient network errors
            last = e
    raise RuntimeError("GET failed after %d tries: %s (%s)" % (tries, url, last))


def parquet_index(hf_dataset):
    data = json.loads(_get(PARQUET_API % hf_dataset).decode("utf-8"))
    out = {}
    for f in data["parquet_files"]:
        out.setdefault((f["config"], f["split"]), []).append(f["url"])
    return {k: sorted(v) for k, v in out.items()}


def read_rows(urls, cols):
    rows = []
    for url in urls:
        table = pq.read_table(io.BytesIO(_get(url)), columns=cols)
        data = {c: table.column(c).to_pylist() for c in cols}
        for i in range(len(data[cols[0]])):
            rows.append({c: data[c][i] for c in cols})
        del table, data
    return rows


def load(spec):
    index = parquet_index(spec["hf"])
    out = {}
    for split in spec["splits"]:
        out[split] = read_rows(index.get((spec["config"], split), []), spec["cols"])
    return out


def fixtures_ok():
    ok_pol = all(pol.polarity(q) == w for q, w in cases.POLARITY_CASES)
    ok_meta = all(pol.is_meta(o) == w for o, w in cases.META_CASES)
    ok_credit = all(pol.longest_credit(o, g) == lc and pol.shortest_credit(o, g) == sc
                    for o, g, lc, sc in cases.CREDIT_CASES)
    accs = pol.accumulate(cases.ROWS)
    ok_acc = accs == cases.ACC_TARGETS
    ok_rep = True
    for key, want in cases.REPORT_TARGETS.items():
        got = pol.report(accs[key])
        if set(got) != set(want) or any(abs(got[f] - v) > 1e-12 for f, v in want.items()):
            ok_rep = False
    return {"polarity": ok_pol, "meta": ok_meta, "credit": ok_credit, "accumulate": ok_acc, "report": ok_rep}


def structural_gate(rows):
    fam_n = {}
    src_credit = {}
    for r in rows:
        f = pol.family(r["src"])
        fam_n[f] = fam_n.get(f, 0) + 1
        if r["src"] in cases.EXPECTED["src_pick_longest"]:
            n, c = src_credit.get(r["src"], (0, Fraction(0)))
            src_credit[r["src"]] = (n + 1, c + pol.longest_credit(r["options"], r["answer_index"]))
    detail = {"n_valid": {"got": len(rows), "expected": cases.EXPECTED["n_valid"],
                          "match": len(rows) == cases.EXPECTED["n_valid"]},
              "family_n": {"got": fam_n, "expected": cases.EXPECTED["family_n"],
                           "match": fam_n == cases.EXPECTED["family_n"]}}
    for src, (n_exp, acc_exp) in sorted(cases.EXPECTED["src_pick_longest"].items()):
        n, c = src_credit.get(src, (0, Fraction(0)))
        got = float(c / n) if n else None
        detail["src:" + src] = {"got": [n, got], "expected": [n_exp, acc_exp],
                                "match": n == n_exp and got is not None and abs(got - acc_exp) < 1e-12}
    return all(d["match"] for d in detail.values()), detail


def norm_mmlu_pro(raw):
    out = []
    for r in raw:
        out.append({"dataset": "mmlu_pro", "split": "test", "question": r["question"], "options": r["options"],
                    "gold": r["answer_index"],
                    "groups": ["cat=" + str(r["category"]), "fam=" + pol.family(r["src"])]})
    return out


def norm_medmcqa(split, raw, excluded):
    out = []
    for r in raw:
        opts = [r["opa"], r["opb"], r["opc"], r["opd"]]
        cop = r["cop"]
        if any(o is None for o in opts) or not isinstance(cop, int) or not 0 <= cop < 4:
            excluded[split] = excluded.get(split, 0) + 1
            continue
        out.append({"dataset": "medmcqa", "split": split, "question": r["question"], "options": opts, "gold": cop,
                    "groups": ["subject=" + str(r["subject_name"]), "choice_type=" + str(r["choice_type"])]})
    return out


def norm_medqa(split, raw, excluded, inconsistent):
    out = []
    for r in raw:
        o = r["options"] or {}
        opts = [o.get(l) for l in LETTERS]
        a = str(r["answer_idx"] or "").strip().upper()
        if any(x is None for x in opts) or len(a) != 1 or a not in LETTERS:
            excluded[split] = excluded.get(split, 0) + 1
            continue
        gold = LETTERS.index(a)
        if str(r["answer"] or "").strip() != str(opts[gold]).strip():
            inconsistent[split] = inconsistent.get(split, 0) + 1
            continue
        out.append({"dataset": "medqa", "split": split, "question": r["question"], "options": opts, "gold": gold,
                    "groups": ["step=" + str(r["meta_info"])]})
    return out


def trigger_counts(rows):
    """Which negation word fired, per dataset (lower-cased first match in the last sentence)."""
    out = {}
    for r in rows:
        m = pol.NEG_RE.search(pol.last_sentence(r["question"]))
        if m:
            w = m.group(0).lower().replace("’", "'")
            d = out.setdefault(r["dataset"], {})
            d[w] = d.get(w, 0) + 1
    return {k: dict(sorted(v.items(), key=lambda kv: -kv[1])) for k, v in out.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=None)  # unused; data fetched over the network
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    fx = fixtures_ok()
    print("[fixture] %s" % fx)
    if not all(fx.values()):
        raise SystemExit("fixture mismatch -- aborting before real data")

    pro_raw = load(cases.MMLU_PRO)["test"]
    pro_rows = [r for r in pro_raw if r["options"] and len(r["options"]) >= 2
                and r["answer_index"] is not None and 0 <= r["answer_index"] < len(r["options"])]
    gate_ok, gate_detail = structural_gate(pro_rows)
    print("[structural-gate] reproduces audit 63 : %s" % gate_ok)
    if not gate_ok:
        for k, d in gate_detail.items():
            if not d["match"]:
                print("[structural-gate][MISMATCH] %s got=%s expected=%s" % (k, d["got"], d["expected"]))
        raise SystemExit("structural gate failed -- aborting")
    rows = norm_mmlu_pro(pro_rows)
    del pro_raw, pro_rows

    sizes = {}
    excluded = {"medmcqa": {}, "medqa": {}}
    inconsistent = {}
    for split, raw in load(cases.MEDMCQA).items():
        sizes.setdefault("medmcqa", {})[split] = len(raw)
        rows += norm_medmcqa(split, raw, excluded["medmcqa"])
    for split, raw in load(cases.MEDQA).items():
        sizes.setdefault("medqa", {})[split] = len(raw)
        rows += norm_medqa(split, raw, excluded["medqa"], inconsistent)
    size_check = {d: {s: {"got": sizes.get(d, {}).get(s), "expected": n, "match": sizes.get(d, {}).get(s) == n}
                      for s, n in sp.items()} for d, sp in cases.EXPECTED_SIZES.items()}
    print("[sizes] %s" % json.dumps(size_check))
    print("[excluded] %s | medqa answer text != keyed option: %s" % (excluded, inconsistent))

    accs = pol.accumulate(rows)
    reports = {k: pol.report(a) for k, a in sorted(accs.items())}
    triggers = trigger_counts(rows)
    del rows, accs

    for key in sorted(reports):
        parts = key.split("|")
        if len(parts) <= 3 and not parts[1].startswith(("subject=", "cat=", "choice_type=")) or \
                parts[1].startswith(("fam=", "step=", "choice_type=")):
            r = reports[key]
            print("[r] %-44s n=%6d pl=%.4f ps=%.4f chance=%.4f lift=%+.4f se=%s meta=%.3f"
                  % (key, r["n"], r["pick_longest"], r["pick_shortest"], r["chance"], r["lift"],
                     "%.4f" % r["se_lift"] if r["se_lift"] is not None else "-", r["meta_share"]))
    contrasts = {}
    for key in sorted(reports):
        if key.endswith("|pol=neg"):
            base = key[: -len("|pol=neg")]
            pos = reports.get(base + "|pol=pos")
            if pos:
                contrasts[base] = pol.contrast(reports[key], pos)
    for d in pol.DATASETS:
        c = contrasts.get(d, {})
        print("[contrast] %-10s neg-pos lift=%s z=%s" % (d, c.get("lift_diff"), c.get("z")))
    print("[triggers] %s" % json.dumps(triggers))

    preds = pol.predictions(reports)
    for name in sorted(p for p in preds if p.startswith("P") and not p.endswith("_detail")):
        print("[prediction] %s = %s" % (name, "HELD" if preds[name] else "FAILED"))

    out = {
        "dataset": ("MMLU-Pro (TIGER-Lab/MMLU-Pro 'default' test), MedMCQA (openlifescienceai/medmcqa train + "
                    "validation; the unlabelled test split is not used) and MedQA-USMLE 4-option "
                    "(GBaker/MedQA-USMLE-4-options train + test), read via the HF datasets-server parquet API on the "
                    "run date. Stem polarity: 'neg' when the question's last sentence (split after . ? ! + "
                    "whitespace) matches not|except|false|incorrect|untrue|least or n't as a whole word, "
                    "case-insensitive. Meta option: first word all|none|both|neither and at most 6 words. Lengths "
                    "are Unicode code points after str.strip()."),
        "fixtures": fx,
        "structural_gate": {"passed": gate_ok, "detail": gate_detail},
        "sizes": size_check,
        "excluded": excluded,
        "medqa_answer_text_mismatch_excluded": inconsistent,
        "negation_triggers": triggers,
        "reports": reports,
        "contrasts": contrasts,
        "predictions": preds,
        "note": ("pick_longest / pick_shortest: tie-aware accuracy of picking the longest / shortest option without "
                 "reading the question. chance: mean 1/k. lift: pick_longest - chance; se_lift: its standard error "
                 "over questions. contrasts: negative-stem lift minus positive-stem lift with a two-sample z. "
                 "meta_share: share of questions with an all/none/both-style option. Construction property only; "
                 "no model is evaluated."),
    }
    path = os.path.join(args.out_dir, "results.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    print("[done] wrote %s" % path)


if __name__ == "__main__":
    main()
