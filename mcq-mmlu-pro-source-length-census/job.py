"""MMLU-Pro answer-length shortcut by SOURCE (audit 63).

Audit 61 found that MMLU-Pro's 10-option expansion more than doubled MMLU's pick-longest answer-length shortcut.
Audit 62 traced it to MMLU-Pro's new-source questions (src stemez- / theoremQA- / scibench-): they carry 88.8% of
the pooled excess, while the questions inherited from MMLU stay at MMLU's 1.12x chance. Audit 62 inferred by
subtraction that new-source biology and psychology questions must score about 56% and 61% for pick-longest. This
audit measures that directly: the audit-51 length census keyed by source family, by (category, provenance), by
(category, family) and by full src value.

Gates before any prediction is scored: the hand-traced fixtures must match exactly, and the census must reproduce
audit 61 (pooled n, unique-longest, pick-longest; biology and psychology totals) and audit 62 (pick-longest by
provenance) exactly. Six predictions were pre-registered before any real number was seen.

Usage: python job.py --out-dir /out   (network required to fetch the parquet listing and file)
Apache-2.0.
"""

import argparse
import io
import json
import os
import urllib.request

import pyarrow.parquet as pq

import cases
import gold_length as gl
import source as sl

UA = {"User-Agent": "mv2-eval-reliability-audits/1.0 (research; contact mv2@munimtech.com)"}
PARQUET_API = "https://datasets-server.huggingface.co/parquet?dataset=%s"


def _get(url, tries=4):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 - retry transient network errors
            last = e
    raise RuntimeError("GET failed after %d tries: %s (%s)" % (tries, url, last))


def parquet_files(hf_dataset, config, wanted_splits):
    data = json.loads(_get(PARQUET_API % hf_dataset).decode("utf-8"))
    out = []
    for f in data["parquet_files"]:
        if f["config"] == config and f["split"] in wanted_splits:
            out.append((f["split"], f["url"]))
    return sorted(out)


def read_columns(spec):
    """Read the spec's columns from every wanted split. Returns (list of row dicts, split_counts)."""
    rows = []
    counts = {}
    cols = spec["cols"]
    for split, url in parquet_files(spec["hf"], spec["config"], set(spec["splits"])):
        table = pq.read_table(io.BytesIO(_get(url)), columns=cols)
        for c in cols:
            if c not in table.column_names:
                raise RuntimeError("%s parquet missing column %r: %s" % (spec["hf"], c, table.column_names))
        data = {c: table.column(c).to_pylist() for c in cols}
        n = len(data[cols[0]])
        counts[split] = counts.get(split, 0) + n
        for i in range(n):
            rows.append({c: data[c][i] for c in cols})
    return rows, counts


def report(rows, key_fn):
    return gl.to_report(gl.run_census(sl.census_rows(rows, key_fn)))


def fmt(key, e):
    if not e["n_valid"]:
        return "%-34s n=0" % key
    c = e["char"]
    return ("%-34s n=%5d chance=%.4f pick_longest=%.4f lift=%+.4f uniq_long=%.4f uniq_short=%.4f gold/dist=%.1f/%.1f"
            % (key, e["n_valid"], e["chance_accuracy"], c["longest_accuracy"], sl.lift(e),
               c["unique_longest_rate"], c["unique_shortest_rate"], c["mean_gold_len"],
               c["mean_distractor_len"] or 0.0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=None)  # unused; data fetched over the network
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # 1) Hand-traced fixtures must match exactly before any real data is read.
    core_ok = gl.run_census(cases.FIXTURE_ROWS) == cases.TARGET
    fam_ok = sl.digest(gl.run_census(sl.census_rows(cases.KEY_ROWS, lambda r: sl.family(r["src"])))) \
        == cases.KEY_TARGET_FAMILY
    prov_ok = sl.digest(gl.run_census(sl.census_rows(cases.KEY_ROWS, lambda r: sl.provenance(r["src"])))) \
        == cases.KEY_TARGET_PROV
    cp_ok = sl.digest(gl.run_census(sl.census_rows(
        cases.KEY_ROWS, lambda r: r["category"] + "|" + sl.provenance(r["src"])))) == cases.KEY_TARGET_CATPROV
    print("[fixture] core=%s family=%s provenance=%s category|provenance=%s" % (core_ok, fam_ok, prov_ok, cp_ok))
    if not (core_ok and fam_ok and prov_ok and cp_ok):
        raise SystemExit("fixture mismatch -- aborting before real data")

    # 2) Real data.
    rows, counts = read_columns(cases.MMLU_PRO)
    print("[load] mmlu-pro %s" % counts)

    # 3) Census under every key; structural gate vs audits 61/62.
    pooled = report(rows, lambda r: "ALL")["ALL"]
    by_prov = report(rows, lambda r: sl.provenance(r["src"]))
    by_cat = report(rows, lambda r: r["category"])
    gate_ok, gate_detail = sl.structural_gate(pooled, by_prov, by_cat, cases.EXPECTED)
    print("[structural-gate] reproduces audits 61/62 : %s" % gate_ok)
    for k, d in gate_detail.items():
        if not d["match"]:
            print("[structural-gate][MISMATCH] %s got=%s expected=%s" % (k, d["got"], d["expected"]))
    if not gate_ok:
        raise SystemExit("structural gate failed -- aborting")

    by_family = report(rows, lambda r: sl.family(r["src"]))
    by_cat_prov = report(rows, lambda r: r["category"] + "|" + sl.provenance(r["src"]))
    by_cat_family = report(rows, lambda r: r["category"] + "|" + sl.family(r["src"]))
    by_src = report(rows, lambda r: r["src"] or "")

    preds = sl.predictions(by_family, by_cat_prov)

    for k in sorted(by_family):
        print("[family] " + fmt(k, by_family[k]))
    for k in sorted(by_cat_prov):
        print("[cat|prov] " + fmt(k, by_cat_prov[k]))
    for k in sorted(by_cat_family):
        print("[cat|family] " + fmt(k, by_cat_family[k]))
    for name in sorted(p for p in preds if not p.endswith("_detail")):
        print("[prediction] %s = %s" % (name, "HELD" if preds[name] else "FAILED"))

    out = {
        "dataset": ("MMLU-Pro (TIGER-Lab/MMLU-Pro config 'default', test split) read from the HuggingFace "
                    "auto-converted parquet via the datasets-server parquet API. Source family = the src prefix "
                    "before the first '-' (ori_mmlu, stemez, theoremQA, scibench); provenance = ori_mmlu vs new "
                    "(every other src). Lengths are characters after str.strip() (whitespace tokens alongside). "
                    "This is a construction property of the benchmark, not a model's behaviour."),
        "split_counts": counts,
        "fixtures": {"core": core_ok, "family": fam_ok, "provenance": prov_ok, "category_provenance": cp_ok},
        "structural_gate": {"passed": gate_ok, "detail": gate_detail},
        "pooled": pooled,
        "by_provenance": by_prov,
        "by_category": by_cat,
        "by_family": by_family,
        "by_category_provenance": by_cat_prov,
        "by_category_family": by_cat_family,
        "by_src": by_src,
        "predictions": preds,
        "note": ("P1/P2: new-source biology / psychology questions score at least 50% for pick-longest (audit 62 "
                 "implied ~56% / ~61% by subtraction). P3: every new-source family with n >= 100 has a larger "
                 "pick-longest lift over chance than the MMLU-derived questions. P4: stemez has the largest lift "
                 "of those families. P5: among categories with >= 50 valid questions of both provenances, the "
                 "new-source lift exceeds the MMLU-derived lift in a strict majority. P6: in every new-source "
                 "family with n >= 100 the gold is the unique shortest option in under 5% of questions. Each is "
                 "a finding either way. Measures agreement with a length heuristic, not correctness of any model."),
    }
    path = os.path.join(args.out_dir, "results.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    print("[done] wrote %s" % path)


if __name__ == "__main__":
    main()
