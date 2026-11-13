"""Audit 113: what does MedHELM's EHRSQL column (EHRSQLExeAcc) measure?

Reads every ehr_sql run of MedHELM release v4.0.0: the gold SQL and template values of each test instance
(instances.json), each stored answer with its stored annotations and per-record scores (display_predictions.json) and
the run means (stats.json). Downloads the pinned eicu.sqlite HELM uses and runs every gold query on it twice: as HELM
does, and after EHRSQL's own post-processing. Gate: every stored per-record execution accuracy and query validity is
reproduced by our transcription of HELM's EhrSqlMetric and the run mean matches stats.json. Then each run is re-scored
(answerable questions only; no template-value substitution; EHRSQL-style), ranks and the eight pre-registered verdicts
follow. Only run names, instance ids, classes, counts, table names and public model names go to results.json; SQL and
answers go to the job log only, for the hand-read.
Usage: python job.py --out-dir /out (network required). Standard library only. Apache-2.0.
"""

import argparse
import hashlib
import json
import os
import sqlite3
import tempfile
import urllib.parse
import urllib.request
from fractions import Fraction

import grade113 as g

HELM_BASE = "https://storage.googleapis.com/crfm-helm-public/medhelm/benchmark_output"
RELEASE = "v4.0.0"
PREFIX = "ehr_sql:"
GROUP = "ehr_sql"
DB_URL = "https://github.com/raulista1997/benchmarkdata/raw/c4c252443fa9c52afb6960f53e51be278639bea2/eicu.sqlite"
UA = {"User-Agent": "mv2-eval-reliability-audits/1.0 (research; contact mv2@munimtech.com)"}
TOL_RUN = 1e-9
TOL_CELL = 1e-6
GAIN = Fraction(3, 100)
PLACES = 3
PRINT_N = 6
LEADER = "openai_gpt-4o-2024-05-13"


def _get(url, tries=4):
    last = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 - retry transient network errors
            last = e
    raise RuntimeError("GET failed after %d tries: %s (%s)" % (tries, url, last))


def _json(url):
    return json.loads(_get(url).decode("utf-8"))


def run_url(run, fname):
    return "%s/runs/%s/%s/%s" % (HELM_BASE, RELEASE, urllib.parse.quote(run, safe=":,=@-_."), fname)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=None)  # unused; data fetched over the network
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # ---- database ----
    blob = _get(DB_URL)
    db_sha = hashlib.sha256(blob).hexdigest()
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "eicu.sqlite")
    with open(db_path, "wb") as fh:
        fh.write(blob)
    conn = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True)
    tables = [r[0] for r in conn.execute("select name from sqlite_master where type='table' order by name")]
    table_rows = {t: conn.execute('select count(*) from "%s"' % t.replace('"', '""')).fetchone()[0] for t in tables}
    db_rows = sum(table_rows.values())
    print("[db] bytes=%d sha256=%s sqlite=%s tables=%s total_rows=%d" % (len(blob), db_sha, sqlite3.sqlite_version,
                                                                         table_rows, db_rows))
    cache = {}

    def exec_off(sql):
        if sql not in cache:
            cache[sql] = g.execute(conn, sql)
        return cache[sql]

    # ---- release ----
    run_suites = _json("%s/releases/%s/runs_to_run_suites.json" % (HELM_BASE, RELEASE))
    chosen = sorted(g.select_runs(run_suites, PREFIX))
    print("[release] %s runs listed=%d" % (RELEASE, len(chosen)))
    try:
        published = g.group_values(_json("%s/releases/%s/groups/%s.json" % (HELM_BASE, RELEASE, GROUP))) or []
        group_err = None
    except Exception as e:  # noqa: BLE001
        published, group_err = [], str(e)[:200]
    print("[group] %s cells published=%d error=%s" % (g.CELL_HEADER, len(published), group_err))

    # ---- gold (from the first run whose instances download) ----
    info, ref_run = {}, None
    for run in chosen:
        try:
            inst = _json(run_url(run, "instances.json"))
        except Exception as e:  # noqa: BLE001
            print("[instances] %s failed: %s" % (run, str(e)[:200]))
            continue
        info = {i.get("id"): g.info_of(i) for i in inst if isinstance(i, dict) and i.get("split") == "test"}
        ref_run = run
        del inst
        break
    test_ids = sorted(info)
    impossible = sorted(i for i in test_ids if g.is_impossible(info[i]))
    imp_set = set(impossible)
    answerable = [i for i in test_ids if i not in imp_set]
    flag_vs_null = sum(1 for i in test_ids if info[i]["impossible"] != (info[i]["gq"].lower() == "null"))
    print("[test] ref=%s ids=%d impossible=%d answerable=%d is_impossible_vs_null_disagree=%d" % (
        ref_run, len(test_ids), len(impossible), len(answerable), flag_vs_null))

    gold_raw, gold_off = {}, {}
    for i in test_ids:
        q = info[i]["gq"]
        gold_raw[i] = g.execute(conn, q)
        gold_off[i] = ("null", None) if q.lower() == "null" else exec_off(g.official_sql(q))
    raw_cls = g.class_counts({i: gold_raw[i][0] for i in answerable}, ("rows", "empty", "error", "timeout"))
    off_cls = g.class_counts({i: gold_off[i][0] for i in answerable}, ("rows", "empty", "error", "timeout"))
    changed = sorted(i for i in answerable if gold_raw[i][0] != gold_off[i][0] or (
        gold_raw[i][0] == "rows" and g.official_key(gold_raw[i][1]) != g.official_key(gold_off[i][1])))
    empty_to_rows = sum(1 for i in changed if gold_raw[i][0] in ("empty", "error") and gold_off[i][0] == "rows")
    print("[gold raw, answerable] %s" % raw_cls)
    print("[gold EHRSQL-style, answerable] %s changed=%d empty_or_error_to_rows=%d" % (off_cls, len(changed),
                                                                                       empty_to_rows))

    # ---- runs ----
    runs_out, inc = {}, {}
    for run in chosen:
        try:
            preds = _json(run_url(run, "display_predictions.json"))
            stats = _json(run_url(run, "stats.json"))
        except Exception as e:  # noqa: BLE001 - recorded, never patched
            runs_out[run] = {"status": "download_failed", "error": str(e)[:300]}
            continue
        s = g.summarize_run(preds, info, gold_raw, gold_off, exec_off)
        st_acc = g.stat_entry(stats, g.ACC)
        ni = g.stat_entry(stats, "num_instances")
        del preds, stats
        reasons = []
        if s["stored_missing"] or s["acc_mismatch"] or s["val_mismatch"] or s["counts"]["no_annotation"]:
            reasons.append("stored")
        if ni is None or ni.get("sum") is None or s["counts"]["kept"] != int(round(ni["sum"])):
            reasons.append("instances")
        pub = g.run_mean(s["trials"], "pub")
        if st_acc is None or st_acc.get("mean") is None or pub is None or abs(float(pub) - st_acc["mean"]) > TOL_RUN:
            reasons.append("mean")
        gc = g.class_counts(s["gclass"], g.GOLD_CLASSES)
        pc = g.class_counts(s["pclass"], g.PRED_CLASSES)
        runs_out[run] = {"status": "included" if not reasons else "excluded", "reasons": reasons,
                         "model": g.model_of(run), "counts": s["counts"], "acc_mismatch": s["acc_mismatch"],
                         "val_mismatch": s["val_mismatch"], "gold_classes": gc, "pred_classes": pc}
        if not reasons:
            s["gc"], s["pc"] = gc, pc
            inc[run] = s
        print("[run] %s %s %s gold=%s pred=%s" % (runs_out[run]["status"], reasons, g.model_of(run), gc, pc))
    order = sorted(inc)
    print("[runs] listed=%d included=%d" % (len(chosen), len(order)))

    ref = inc.get(ref_run) or (inc[order[0]] if order else None)
    slot_golds = sum(1 for i in answerable if ref and ref["gclass"].get(i) == "slot") if ref else 0
    slot_unanswerable = sum(1 for i in impossible if ref and ref["gclass"].get(i) == "slot") if ref else 0
    gold_same = (sum(1 for i in test_ids if len({inc[m]["golds"].get(i) for m in order}) == 1) if order else 0)
    stored_rows = [i for i in test_ids if ref and ref["gclass"].get(i) == "rows"] if ref else []
    rows_rep = sum(1 for i in stored_rows if gold_raw[i][0] == "rows" and set(gold_raw[i][1]) == set(ref["golds"][i]))
    slot_from = g.class_counts({i: gold_raw[i][0] for i in answerable if ref and ref["gclass"].get(i) == "slot"},
                               ("rows", "empty", "error", "timeout"))
    check_c1 = all(inc[m]["slot_credit"] == 0 for m in order) if order else None
    print("[check C1] no credit on a template-value gold in any included run = %s; gold identical across runs for "
          "%d of %d ids" % (check_c1, gold_same, len(test_ids)))
    print("[gold stored, ref run] answerable slot=%d of %d; unanswerable slot=%d; stored rows=%d reproduced=%d; "
          "slot golds by our raw run=%s" % (slot_golds, len(answerable), slot_unanswerable, len(stored_rows),
                                            rows_rep, slot_from))

    cell = {k: {m: g.run_mean(inc[m]["trials"], k) for m in order} for k in g.VARIANTS}
    abstain_major = sorted(m for m in order if inc[m]["abstain_credit"] * 2 > inc[m]["credit"])
    gain3 = sorted(m for m in order if cell["fixed"][m] - cell["pub"][m] >= GAIN)
    rp = g.ranks_high(cell["pub"])
    rk = {k: g.ranks_high(cell[k]) for k in ("sql_only", "fixed", "official")}
    leaders_pub = [m for m in order if rp[m] == 1]
    lead = next((m for m in order if g.model_of(m) == LEADER), None)
    leader_sql_first = None if lead is None else rk["sql_only"][lead] == 1
    taus = {k: (g.kendall_tau_b([cell["pub"][m] for m in order], [cell[k][m] for m in order]) if order else None)
            for k in ("sql_only", "fixed", "official")}
    movers = {k: sorted(m for m in order if abs(rp[m] - rk[k][m]) >= PLACES) for k in rk}
    matched = g.match_cells({m: float(v) for m, v in cell["pub"].items()}, published, TOL_CELL)
    pooled_va = sum(inc[m]["valid_answerable"] for m in order)
    pooled_vae = sum(inc[m]["valid_answerable_empty"] for m in order)
    table = []
    for m in sorted(order, key=lambda k: (rp[k], k)):
        s = inc[m]
        table.append(dict({"run": m, "model": g.model_of(m)}, **{k: float(cell[k][m]) for k in g.VARIANTS},
                          **{"rank_pub": rp[m], "rank_sql_only": rk["sql_only"][m], "rank_fixed": rk["fixed"][m],
                             "rank_official": rk["official"][m], "credit": s["credit"],
                             "abstain_credit": s["abstain_credit"], "valid_answerable": s["valid_answerable"],
                             "valid_answerable_empty": s["valid_answerable_empty"], "gold_classes": s["gc"],
                             "pred_classes": s["pc"]}))
    print("[cells] matched %d of %d (published %d)" % (matched, len(order), len(published)))
    print("[ranks] leaders=%s gpt4o_first_sql_only=%s taus=%s movers3=%s abstain_majority=%d gain3=%d "
          "pooled valid answerable=%d empty_result=%d" % (leaders_pub, leader_sql_first, taus,
                                                          {k: len(v) for k, v in movers.items()},
                                                          len(abstain_major), len(gain3), pooled_va, pooled_vae))
    for row in table:
        print("[cell] %s" % row)

    stats = {"test_ids": len(test_ids), "runs_listed": len(chosen), "runs_included": len(order),
             "cells_matched": matched, "answerable": len(answerable), "slot_golds": slot_golds, "db_rows": db_rows,
             "gold_changed_official": len(changed), "stored_rows_golds": len(stored_rows),
             "rows_reproduced": rows_rep, "runs_abstain_majority": len(abstain_major),
             "runs_fixed_gain3": len(gain3), "leader_sql_only_first": leader_sql_first}
    verdicts = g.verdicts(stats)
    for k, v in sorted(verdicts.items()):
        print("[verdict] %s = %s" % (k, g.verdict_word(v)))

    # ---- hand-read material (job log only) ----
    for cls in ("slot", "other"):
        for i in sorted((i for i in test_ids if ref and ref["gclass"].get(i) == cls),
                        key=lambda x: (g.stable_hash(cls + x), x))[:PRINT_N]:
            print("[read gold %s] id=%s raw=%s official=%s value=%s gq=%r" % (
                cls, i, gold_raw[i][0], gold_off[i][0], info[i]["value"], info[i]["gq"][:300]))
    for i in sorted(changed, key=lambda x: (g.stable_hash("chg" + x), x))[:PRINT_N]:
        print("[read changed] id=%s raw=%s/%s official=%s/%s gq=%r" % (
            i, gold_raw[i][0], str(gold_raw[i][1])[:80], gold_off[i][0], str(gold_off[i][1])[:80],
            info[i]["gq"][:300]))
    shown = 0
    for m in sorted(order, key=lambda x: (g.stable_hash("emp" + x), x)):
        if shown >= PRINT_N:
            break
        ids = [i for i, c in inc[m]["pclass"].items() if c == "empty_result" and i not in imp_set
               and inc[m]["gclass"].get(i) == "slot"]
        if ids:
            i = min(ids, key=lambda x: (g.stable_hash(m + x), x))
            shown += 1
            print("[read empty-on-slot] run=%s id=%s gq=%r pred=%r" % (m, i, info[i]["gq"][:300], inc[m]["texts"][i]))

    out = {
        "audit": 113,
        "slug": "helm-ehrsql-gold",
        "dataset": ("Per-instance outputs of MedHELM release %s (Stanford CRFM): every ehr_sql run listed in "
                    "runs_to_run_suites.json, test split (EHRSQL eICU, Lee et al.). Only run names, instance ids, "
                    "classes, counts, table names and public model names are published." % RELEASE),
        "db": {"url": DB_URL, "bytes": len(blob), "sha256": db_sha, "table_rows": table_rows, "total_rows": db_rows,
               "sqlite_version": sqlite3.sqlite_version},
        "test_ids": len(test_ids), "impossible": len(impossible), "answerable": len(answerable),
        "is_impossible_vs_null_disagree": flag_vs_null,
        "gold_raw_answerable": raw_cls, "gold_official_answerable": off_cls,
        "gold_changed_official": len(changed), "gold_empty_or_error_to_rows": empty_to_rows,
        "slot_golds_answerable": slot_golds, "slot_golds_unanswerable": slot_unanswerable,
        "slot_golds_by_raw_class": slot_from, "stored_rows_golds": len(stored_rows), "rows_reproduced": rows_rep,
        "gold_identical_across_runs": gold_same, "check_c1_no_slot_credit": check_c1,
        "group_error": group_err, "runs_listed": len(chosen), "runs_included": len(order),
        "cells_matched": [matched, len(order)], "published_cells": len(published),
        "runs_abstain_majority": abstain_major, "runs_fixed_gain3": gain3, "leaders_published": leaders_pub,
        "gpt4o_first_sql_only": leader_sql_first, "tau_b_vs_published": taus, "movers_3plus": movers,
        "pooled_valid_answerable": pooled_va, "pooled_valid_answerable_empty": pooled_vae,
        "verdicts": {k: g.verdict_word(v) for k, v in verdicts.items()},
        "table": table,
        "ids_changed_official": changed,
        "ids_slot_answerable": sorted(i for i in answerable if ref and ref["gclass"].get(i) == "slot"),
        "runs": runs_out,
        "note": ("pub: HELM's stored execution accuracy. sql_only: stored credit on answerable questions only (no credit "
                 "for an empty answer to an unanswerable question). fixed: HELM's stored executions, gold = the gold "
                 "query's own result (HELM's stored rows, else our run of the gold query as HELM runs it; an empty "
                 "result matches an empty result; a failed gold query credits nobody), unanswerable questions credit "
                 "an empty answer. official: both queries post-processed as in EHRSQL's evaluate.py and re-run by us on "
                 "the same database, first-100 sorted string comparison."),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    print("[done] wrote results.json")


if __name__ == "__main__":
    main()
