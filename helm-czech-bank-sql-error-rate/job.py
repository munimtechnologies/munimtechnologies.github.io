#!/usr/bin/env python3
# Audit 115 (pre-registered): HELM CzechBankQA "SQL Error Rate".
# MV2 of Munim, Inc. -- made by AI agents working in MV2's name. Licence: Apache-2.0.
#
# HELM's CzechBankQAMetrics (stanford-crfm/helm main, unchanged since #3222, 2024-12-19) returns one number,
# error_rate = 0 if the model's query runs without an SQLite error, else 1. Its annotator also stores the
# query's result and the gold query's result, but no metric compares them. This job measures:
#   A. what HELM's metric gives fixed queries such as "SELECT 1" on every question (a check, not a prediction);
#   B. the gold side: all gold queries of the config HELM uses, run on HELM's pinned czech_bank.db;
#   C. if the HELM SQL leaderboard (release v0.4.0) can be reached: the published error rate against the
#      execution accuracy of the same stored outputs.
# Standard library only. The database is opened read-only and every query is time-limited.
import argparse
import csv
import hashlib
import json
import os
import sqlite3
import sys
import time
import urllib.parse
import urllib.request

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)
csv.field_size_limit(2 ** 31 - 1)

HF = "https://huggingface.co/datasets/yifanmai/czech_bank_qa/resolve/main/"
DB_URL = HF + "czech_bank.db?download=true"
CONFIG = "berka_queries_1024_2024_12_18"
CSV_URL = HF + CONFIG + ".csv?download=true"
LB_BASES = [
    "https://nlp.stanford.edu/helm/sql/benchmark_output",
    "http://nlp.stanford.edu/helm/sql/benchmark_output",
]
RELEASE = "v0.4.0"
QUERY_SECONDS = 10.0
ROW_CAP = 200000
SOFT_DEADLINE_SECONDS = 110 * 60
UA = {"User-Agent": "mv2-munim-research/1.0 (mv2@munimtech.com)"}
BASELINES = ["SELECT 1", "SELECT NULL", "SELECT * FROM account LIMIT 0", "", "-- no query"]

# Frozen thresholds (see README, pre-registered before any data was read).
MIN_RUNS = 3
MIN_RECORDS = 50


def helm_clean(completion):
    """HELM CzechBankQAAnnotator.annotate: strips code fences only."""
    return completion.replace("```sql", "").replace("```", "")


def error_rate_flag(error):
    """HELM CzechBankQAMetrics: 0.0 if the annotation's error is None, else 1.0."""
    return 0.0 if error is None else 1.0


def run_query(conn, query, seconds=None):
    """HELM CzechBankQAAnnotator.get_result, plus a time limit and a row cap.

    Returns {"result": str(rows) or None, "error": str or None, "rows": list or None, "status": ...}.
    status is ok, error (an SQLite error, as in HELM), timeout, row_cap or other_exception.
    """
    if seconds is None:
        seconds = QUERY_SECONDS
    deadline = time.monotonic() + seconds
    state = {"timed_out": False}

    def handler():
        if time.monotonic() > deadline:
            state["timed_out"] = True
            return 1
        return 0

    out = {"result": None, "error": None, "rows": None, "status": "ok"}
    cursor = None
    conn.set_progress_handler(handler, 1000)
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA query_only = TRUE")
        cursor.execute(query)
        rows = []
        while True:
            chunk = cursor.fetchmany(5000)
            if not chunk:
                break
            rows.extend(chunk)
            if len(rows) > ROW_CAP:
                rows = None
                out["status"] = "row_cap"
                break
        if rows is not None:
            out["rows"] = rows
            out["result"] = str(rows)
    except (sqlite3.DatabaseError, sqlite3.Warning) as e:
        out["error"] = str(e)
        out["status"] = "timeout" if state["timed_out"] else "error"
    except Exception as e:  # HELM would raise here; recorded separately
        out["error"] = "%s: %s" % (type(e).__name__, e)
        out["status"] = "other_exception"
    finally:
        conn.set_progress_handler(None, 0)
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
    return out


def string_match(result, gold_result, gold_error):
    """Execution match on HELM's stored strings: str(rows) equal, both queries ran."""
    return result is not None and gold_error is None and gold_result is not None and result == gold_result


def set_match(rows, gold_rows):
    """BIRD-style execution match: the same set of rows, order and duplicates ignored."""
    return rows is not None and gold_rows is not None and set(rows) == set(gold_rows)


def kendall_tau_b(x, y):
    n = len(x)
    nc = nd = tx = ty = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx = (x[i] > x[j]) - (x[i] < x[j])
            dy = (y[i] > y[j]) - (y[i] < y[j])
            if dx == 0 and dy == 0:
                continue
            if dx == 0:
                tx += 1
            elif dy == 0:
                ty += 1
            elif dx == dy:
                nc += 1
            else:
                nd += 1
    denom = ((nc + nd + tx) * (nc + nd + ty)) ** 0.5
    return (nc - nd) / denom if denom else None


def published_error_rate(stats):
    for e in stats:
        name = e.get("name") or {}
        if name.get("name") == "error_rate" and name.get("split") == "test" and "perturbation" not in name:
            if e.get("mean") is not None:
                return e["mean"]
            if e.get("count"):
                return e["sum"] / e["count"]
    return None


def model_from_run(run_name):
    tail = run_name.split(":", 1)[1] if ":" in run_name else run_name
    for part in tail.split(","):
        if part.startswith("model="):
            return part[len("model="):]
    return tail


def fetch(url, timeout=120, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(), None
        except Exception as e:
            last = "%s: %s" % (type(e).__name__, e)
            time.sleep(3 * (i + 1))
    return None, last


def download(url, path, min_bytes):
    if os.path.exists(path) and os.path.getsize(path) >= min_bytes:
        return None
    raw, err = fetch(url, timeout=600)
    if raw is None:
        return err
    with open(path, "wb") as f:
        f.write(raw)
    return None


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def gold_side(conn, golds):
    cache = {}
    statuses = {}
    empty = 0
    single_value = 0
    for g in golds:
        if g not in cache:
            cache[g] = run_query(conn, g)
        r = cache[g]
        statuses[r["status"]] = statuses.get(r["status"], 0) + 1
        if r["result"] == "[]":
            empty += 1
        if r["rows"] is not None and len(r["rows"]) == 1 and len(r["rows"][0]) == 1:
            single_value += 1
    return cache, {
        "golds": len(golds),
        "unique_gold_queries": len(cache),
        "status_counts": statuses,
        "gold_error_or_timeout": sum(v for k, v in statuses.items() if k != "ok" and k != "row_cap"),
        "empty_results": empty,
        "single_value_results": single_value,
    }


def baselines(conn, golds, cache):
    out = []
    for q in BASELINES:
        r = run_query(conn, helm_clean(q))
        flag = error_rate_flag(r["error"])
        sm = sum(1 for g in golds if string_match(r["result"], cache[g]["result"], cache[g]["error"]))
        st = sum(1 for g in golds if set_match(r["rows"], cache[g]["rows"]))
        out.append({
            "query": q,
            "status": r["status"],
            "error": r["error"],
            "helm_error_rate_on_every_question": flag,
            "string_matches": sm,
            "set_matches": st,
            "questions": len(golds),
        })
    return out


def leaderboard(conn, gold_cache, t0, out_dir):
    info = {"reached": False, "base": None, "errors": [], "runs": []}
    r2s = None
    base = None
    for b in LB_BASES:
        raw, err = fetch("%s/releases/%s/runs_to_run_suites.json" % (b, RELEASE), timeout=60, tries=2)
        if raw is None:
            info["errors"].append("%s: %s" % (b, err))
            continue
        try:
            r2s = json.loads(raw)
            base = b
            break
        except Exception as e:
            info["errors"].append("%s: bad json %s" % (b, e))
    if r2s is None:
        return info, []
    info["reached"] = True
    info["base"] = base
    names = sorted(n for n in r2s if n.startswith("czech_bank_qa"))
    info["czech_runs_listed"] = names
    lb_dir = os.path.join(out_dir, "leaderboard")
    os.makedirs(lb_dir, exist_ok=True)
    for g in ["groups/financial_scenarios.json", "groups/czech_bank_qa.json"]:
        raw, err = fetch("%s/releases/%s/%s" % (base, RELEASE, g), timeout=60, tries=2)
        if raw is not None and len(raw) < 1500000:
            with open(os.path.join(lb_dir, g.replace("/", "_")), "wb") as f:
                f.write(raw)
    rows_out = []
    for name in names:
        suite = r2s[name]
        rb = "%s/runs/%s/%s" % (base, urllib.parse.quote(str(suite), safe=""), urllib.parse.quote(name, safe=":=,._-"))
        run = {"run": name, "model": model_from_run(name), "suite": suite}
        stats_raw, e1 = fetch(rb + "/stats.json")
        dp_raw, e2 = fetch(rb + "/display_predictions.json", timeout=300)
        inst_raw, e3 = fetch(rb + "/instances.json", timeout=300)
        if stats_raw is None or dp_raw is None or inst_raw is None:
            run["fetch_errors"] = [e1, e2, e3]
            info["runs"].append(run)
            continue
        try:
            stats = json.loads(stats_raw)
            dps = json.loads(dp_raw)
            insts = json.loads(inst_raw)
        except Exception as e:
            run["fetch_errors"] = ["bad json %s" % e]
            info["runs"].append(run)
            continue
        gold_by_id = {}
        for ins in insts:
            refs = ins.get("references") or []
            if refs:
                gold_by_id[ins.get("id")] = ((refs[0].get("output") or {}).get("text"))
        run["published_error_rate"] = published_error_rate(stats)
        recs = []
        for d in dps:
            if d.get("train_trial_index", 0) != 0 or d.get("perturbation"):
                continue
            ann = (d.get("annotations") or {}).get("czech_bank_qa")
            pred = d.get("predicted_text") or ""
            cleaned = helm_clean(pred)
            gold = gold_by_id.get(d.get("instance_id"))
            rec = {"run": name, "instance_id": d.get("instance_id"), "has_annotation": ann is not None,
                   "empty_query": cleaned.strip() == ""}
            if ann is not None:
                rec["flag_stored"] = error_rate_flag(ann.get("error"))
                rec["string_match_stored"] = string_match(ann.get("result"), ann.get("gold_result"), ann.get("gold_error"))
                rec["ran_stored"] = ann.get("error") is None
                rec["query_equals_clean"] = ann.get("query") == cleaned
            if time.monotonic() - t0 < SOFT_DEADLINE_SECONDS and gold is not None:
                if gold not in gold_cache:
                    gold_cache[gold] = run_query(conn, gold)
                g = gold_cache[gold]
                o = run_query(conn, cleaned)  # not cached: predicted rows are dropped after matching
                rec["flag_ours"] = error_rate_flag(o["error"])
                rec["status_ours"] = o["status"]
                rec["string_match_ours"] = string_match(o["result"], g["result"], g["error"])
                rec["set_match_ours"] = set_match(o["rows"], g["rows"])
                if ann is not None:
                    rec["gold_result_reproduced"] = ann.get("gold_result") == g["result"]
            recs.append(rec)
        n = len(recs)
        ann_recs = [r for r in recs if r.get("has_annotation")]
        ours = [r for r in recs if "flag_ours" in r]
        run["records"] = n
        run["annotated_records"] = len(ann_recs)
        run["recomputed_error_rate_stored"] = (sum(r["flag_stored"] for r in ann_recs) / len(ann_recs)) if ann_recs else None
        run["exec_acc_string_stored"] = (sum(r["string_match_stored"] for r in ann_recs) / len(ann_recs)) if ann_recs else None
        run["ran_but_wrong_stored"] = sum(1 for r in ann_recs if r["ran_stored"] and not r["string_match_stored"])
        run["ran_stored"] = sum(1 for r in ann_recs if r["ran_stored"])
        run["empty_queries"] = sum(1 for r in recs if r["empty_query"])
        run["empty_queries_scored_no_error"] = sum(1 for r in ann_recs if r["empty_query"] and r["flag_stored"] == 0.0)
        run["records_rerun"] = len(ours)
        run["flag_reproduced"] = sum(1 for r in ours if r.get("has_annotation") and r["flag_ours"] == r["flag_stored"])
        run["gold_result_reproduced"] = sum(1 for r in ours if r.get("gold_result_reproduced"))
        run["string_match_ours"] = sum(1 for r in ours if r["string_match_ours"])
        run["set_match_ours"] = sum(1 for r in ours if r["set_match_ours"])
        run["timeouts_ours"] = sum(1 for r in ours if r["status_ours"] == "timeout")
        info["runs"].append(run)
        rows_out.extend(recs)
    return info, rows_out


def grade(gold_stats, info):
    p = {}
    g = gold_stats
    p["P1"] = {"claim": "every gold query runs without error or timeout", "value": g["gold_error_or_timeout"],
               "held": g["gold_error_or_timeout"] == 0}
    share = g["empty_results"] / g["golds"] if g["golds"] else None
    p["P2"] = {"claim": "at most 5% of gold results are empty", "value": share,
               "held": share is not None and share <= 0.05}
    graded = [r for r in info.get("runs", []) if r.get("annotated_records", 0) >= MIN_RECORDS
              and r.get("published_error_rate") is not None]
    if len(graded) < MIN_RUNS:
        for k in ["P3", "P4", "P5", "P6", "P7", "P8"]:
            p[k] = {"held": None, "note": "not graded: fewer than %d runs with %d+ annotated records reached (%d)"
                    % (MIN_RUNS, MIN_RECORDS, len(graded))}
        return p, graded
    rerun = sum(r["records_rerun"] for r in graded)
    repro = sum(r["flag_reproduced"] for r in graded)
    cells_ok = all(abs(r["recomputed_error_rate_stored"] - r["published_error_rate"]) <= 0.001 for r in graded)
    p["P3"] = {"claim": "our flag = stored flag on >= 99% pooled re-run records, and every run's stored-flag mean is "
                        "within 0.001 of its published error rate",
               "flag_reproduced": repro, "rerun": rerun, "cells_ok": cells_ok,
               "held": rerun > 0 and repro / rerun >= 0.99 and cells_ok}
    gaps = [(1 - r["published_error_rate"]) - r["exec_acc_string_stored"] for r in graded]
    p["P4"] = {"claim": "in every run, execution accuracy <= (1 - error rate) - 0.20", "min_gap": min(gaps),
               "held": all(x >= 0.20 for x in gaps)}
    best_err = min(r["published_error_rate"] for r in graded)
    best_acc = max(r["exec_acc_string_stored"] for r in graded)
    lead_err = {r["run"] for r in graded if r["published_error_rate"] == best_err}
    lead_acc = {r["run"] for r in graded if r["exec_acc_string_stored"] == best_acc}
    p["P5"] = {"claim": "the lowest-error-rate model is not the highest-execution-accuracy model",
               "lead_err": sorted(lead_err), "lead_acc": sorted(lead_acc), "held": not (lead_err & lead_acc)}
    tau = kendall_tau_b([-r["published_error_rate"] for r in graded], [r["exec_acc_string_stored"] for r in graded])
    p["P6"] = {"claim": "Kendall tau-b(-error rate, execution accuracy) < 0.8", "tau_b": tau,
               "held": tau is not None and tau < 0.8}
    s_str = sum(r["string_match_ours"] for r in graded)
    s_set = sum(r["set_match_ours"] for r in graded)
    p["P7"] = {"claim": "set matching credits >= 1.02 x string matching, pooled (our re-run)", "string": s_str,
               "set": s_set, "held": s_str > 0 and s_set >= 1.02 * s_str}
    ran = sum(r["ran_stored"] for r in graded)
    wrong = sum(r["ran_but_wrong_stored"] for r in graded)
    p["P8"] = {"claim": ">= 50% of queries that ran without error return a result different from the gold's",
               "ran": ran, "ran_but_wrong": wrong, "held": ran > 0 and wrong / ran >= 0.5}
    return p, graded


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args()
    t0 = time.monotonic()
    os.makedirs(args.out_dir, exist_ok=True)
    d = os.path.join(args.data_dir, "czech-bank-qa")
    os.makedirs(d, exist_ok=True)
    db_path = os.path.join(d, "czech_bank.db")
    csv_path = os.path.join(d, CONFIG + ".csv")
    errs = [download(DB_URL, db_path, 1000000), download(CSV_URL, csv_path, 1000)]
    if any(errs):
        print("[fatal] download failed:", errs)
        with open(os.path.join(args.out_dir, "results.json"), "w") as f:
            json.dump({"fatal": "download failed", "errors": errs}, f, indent=1)
        return 1
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    header = list(rows[0].keys()) if rows else []
    col = "sql_query" if "sql_query" in header else next((h for h in header if "sql" in h.lower()), None)
    if col is None:
        print("[fatal] no SQL column in", header)
        with open(os.path.join(args.out_dir, "results.json"), "w") as f:
            json.dump({"fatal": "no SQL column", "csv_header": header}, f, indent=1)
        return 1
    golds = [r[col] or "" for r in rows]
    print("[data] db sha256", sha256(db_path), "bytes", os.path.getsize(db_path))
    print("[data] csv rows", len(rows), "header", header)
    conn = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True)
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    table_rows = {t: conn.execute('SELECT count(*) FROM "%s"' % t.replace('"', '""')).fetchone()[0] for t in tables}
    print("[db] tables", table_rows)
    cache, gstats = gold_side(conn, golds)
    print("[gold]", json.dumps(gstats))
    base = baselines(conn, golds, cache)
    for b in base:
        print("[baseline]", json.dumps(b))
    info, recs = leaderboard(conn, cache, t0, args.out_dir)
    print("[leaderboard] reached", info["reached"], "base", info["base"], "errors", info["errors"])
    for r in info.get("runs", []):
        print("[run]", json.dumps(r))
    preds, graded = grade(gstats, info)
    for k in sorted(preds):
        print("[%s]" % k, json.dumps(preds[k]))
    res = {
        "audit": 115,
        "config": CONFIG,
        "db_sha256": sha256(db_path),
        "csv_header": header,
        "db_table_rows": table_rows,
        "gold": gstats,
        "baselines": base,
        "leaderboard": info,
        "graded_runs": [r["run"] for r in graded],
        "predictions": preds,
        "elapsed_seconds": round(time.monotonic() - t0, 1),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w") as f:
        json.dump(res, f, indent=1)
    with open(os.path.join(args.out_dir, "records.json"), "w") as f:
        json.dump(recs, f)
    print("[done] elapsed", res["elapsed_seconds"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
