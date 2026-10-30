"""Does MMLU-Pro's pick-longest shortcut survive translation into MMLU-ProX's 29 languages? (audit 67)

Audits 61-63 found that a question-free "pick the longest option" heuristic scores 18.4% on MMLU-Pro (chance 11.1%)
and about 67% on its STEM-website biology and psychology questions; audits 65-66 found that models' answers follow
that cue. MMLU-ProX (li-lab/MMLU-ProX, MIT) translates MMLU-Pro into 29 languages with the options in the same order.
This job joins every translated test question back to its English MMLU-Pro row and measures, per language and on the
same questions, pick-longest accuracy, its lift over chance relative to English (retention), and how often English's
unique longest option is still the unique longest after translation.

Gates before any prediction is scored: hand-traced fixtures match, and the MMLU-Pro parse reproduces audit 63
exactly. Seven predictions were pre-registered before any MMLU-ProX file was opened.

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
import model_length as ml
import prox

UA = {"User-Agent": "mv2-eval-reliability-audits/1.0 (research; contact mv2@munimtech.com)"}
PARQUET_API = "https://datasets-server.huggingface.co/parquet?dataset=%s"


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
    return rows


def fixtures_ok():
    pro_by_id = {r["question_id"]: r for r in cases.PRO_ROWS}
    best, status = prox.best_key(cases.X_ROWS, pro_by_id)
    ok_join = best == cases.JOIN_TARGET["best"] and status == cases.JOIN_TARGET["status"]
    info, accs = prox.analyse_language(cases.X_ROWS, pro_by_id)
    ok_acc = (accs == cases.ACC_TARGETS and info["joined"] == cases.JOIN_TARGET["joined"]
              and info["duplicates"] == cases.JOIN_TARGET["duplicates"])
    ok_rep = True
    for key, want in cases.REPORT_TARGETS.items():
        got = prox.report(accs[key])
        if set(got) != set(want):
            ok_rep = False
            continue
        for f, v in want.items():
            if abs(got[f] - v) > 1e-12:
                ok_rep = False
    return {"join": ok_join, "accumulate": ok_acc, "report": ok_rep}


def structural_gate(rows):
    fam_n = {}
    src_credit = {}
    for r in rows:
        f = ml.family(r["src"])
        fam_n[f] = fam_n.get(f, 0) + 1
        if r["src"] in cases.EXPECTED["src_pick_longest"]:
            n, c = src_credit.get(r["src"], (0, Fraction(0)))
            src_credit[r["src"]] = (n + 1, c + ml.pick_longest_credit(r["options"], r["answer_index"]))
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

    spec = cases.MMLU_PRO
    pro_index = parquet_index(spec["hf"])
    pro_urls = []
    for split in spec["splits"]:
        pro_urls += pro_index.get((spec["config"], split), [])
    rows = [r for r in read_rows(pro_urls, spec["cols"]) if r["options"] and len(r["options"]) >= 2
            and r["answer_index"] is not None and 0 <= r["answer_index"] < len(r["options"])]
    gate_ok, gate_detail = structural_gate(rows)
    print("[structural-gate] reproduces audit 63 : %s" % gate_ok)
    if not gate_ok:
        for k, d in gate_detail.items():
            if not d["match"]:
                print("[structural-gate][MISMATCH] %s got=%s expected=%s" % (k, d["got"], d["expected"]))
        raise SystemExit("structural gate failed -- aborting")
    pro_by_id = {int(r["question_id"]): r for r in rows}

    x_index = parquet_index(cases.PROX["hf"])
    join_info = {}
    reports = {}
    for lang in cases.LANGS:
        urls = x_index.get((lang, cases.PROX["split"]), [])
        if not urls:
            join_info[lang] = {"status": "no_parquet", "ok_share": 0.0}
            print("[lang] %-3s no parquet files listed" % lang)
            continue
        try:
            xrows = read_rows(urls, cases.PROX["cols"])
        except Exception as e:  # noqa: BLE001 - report unreadable languages, never patch them
            join_info[lang] = {"status": "read_failed", "error": str(e)[:300], "ok_share": 0.0}
            print("[lang] %-3s read failed: %s" % (lang, str(e)[:120]))
            continue
        info, accs = prox.analyse_language(xrows, pro_by_id)
        info["status"] = "analysed" if info["joined"] else "nothing_joined"
        join_info[lang] = info
        del xrows
        if not info["joined"]:
            print("[lang] %-3s nothing joined: %s" % (lang, info["status"]))
            continue
        reports[lang] = {k: prox.report(a) for k, a in sorted(accs.items())}
        a = reports[lang]["ALL"]
        b = reports[lang].get("sub:stemez-biopsy", {})
        print("[lang] %-3s key=%s rows=%d joined=%d ok_share=%.4f | pl=%.4f chance=%.4f en=%.4f retention=%s "
              "agree=%s | stemez-biopsy pl=%s en=%s n=%s"
              % (lang, info["key"], info["rows"], info["joined"], info["ok_share"], a["pick_longest"], a["chance"],
                 a["en_pick_longest"], a["retention"], a["ul_agreement"], b.get("pick_longest"),
                 b.get("en_pick_longest"), b.get("n")))

    preds = prox.predictions(reports, join_info, len(cases.LANGS))
    for name in sorted(p for p in preds if p.startswith("P") and not p.endswith("_detail")):
        print("[prediction] %s = %s" % (name, "HELD" if preds[name] else "FAILED"))
    print("[langs] analysed %d of %d" % (len(reports), len(cases.LANGS)))

    out = {
        "dataset": ("MMLU-Pro (TIGER-Lab/MMLU-Pro 'default' test) joined to MMLU-ProX (li-lab/MMLU-ProX, 29 language "
                    "configs, test split) via the HF datasets-server parquet API on the run date. A translated row "
                    "joins only if its id key finds an MMLU-Pro row with the same answer_index, N/A (or blank) in "
                    "every slot past the English option count k, and non-blank text in the first k slots; the id "
                    "key (question_id_src or question_id) is chosen per language as the one joining more rows. "
                    "Lengths are Unicode code points after str.strip()."),
        "fixtures": fx,
        "structural_gate": {"passed": gate_ok, "detail": gate_detail},
        "languages": join_info,
        "reports": reports,
        "predictions": preds,
        "note": ("pick_longest: tie-aware accuracy of picking the longest option. chance: mean 1/k. lift: "
                 "pick_longest - chance. en_*: the same on the English MMLU-Pro options of the same questions. "
                 "retention: lift / en_lift. ul_agreement: among questions whose English options have a unique "
                 "longest, the share whose translated options have the same unique longest. Construction property "
                 "only; no model is evaluated."),
    }
    path = os.path.join(args.out_dir, "results.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    print("[done] wrote %s" % path)


if __name__ == "__main__":
    main()
