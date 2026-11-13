"""Audit 113 helpers: what MedHELM's EHRSQL column measures.

HELM's EhrSqlAnnotator (src/helm/benchmark/annotation/ehr_sql_annotator.py, Stanford CRFM, Apache-2.0) runs the gold
SQL of each EHRSQL (eICU) question on a pinned eicu.sqlite. When the gold query returns no rows or fails, it uses the
question's extra_data["value"] as the gold result instead. In EHRSQL that field holds the values that were filled into
the question template (a patient id, a drug or lab name), not an answer, so the "gold result" becomes a list of plain
strings such as [<patient id>, <lab name>]. EhrSqlMetric then compares set(predicted rows) with set(gold); a row is a tuple
and can never equal a string, so on those questions no SQL query can be credited. HELM also runs the gold SQL without
EHRSQL's own post-processing (glee4810/EHRSQL evaluate.py: 'current_time' and 'now' anchored at 2105-12-31 23:59:00,
'%y' -> '%Y', vital-sign bounds), and an empty answer earns credit when the gold result is empty (the unanswerable
questions, whose gold query is the string 'null').

This module holds the stdlib-only parts of the audit: HELM's scoring, validity and SQL extraction (transcribed), the
gold and answer classes, an EHRSQL-style post-processing and comparison, safe execution, the run census, run means,
ranks, Kendall tau-b, the group-page column and the verdicts. Apache-2.0.
"""

import hashlib
import math
import re
import time
from fractions import Fraction

ACC = "ehr_sql_execution_accuracy"
VAL = "ehr_sql_query_validity"
CELL_HEADER = "EHRSQLExeAcc"
N_TEST = 1000
ANCHOR = "2105-12-31 23:59:00"
VARIANTS = ("pub", "sql_only", "fixed", "official")
GOLD_CLASSES = ("rows", "slot", "empty", "other")
PRED_CLASSES = ("abstain", "error", "rows", "empty_result")

SQL_TAG = re.compile(r"<\s*sql\s*>(.*?)<\/?\s*sql\s*>", re.DOTALL | re.IGNORECASE)
LOWER_RE = re.compile(r"[ \n]+([a-zA-Z0-9_]+_lower)")
UPPER_RE = re.compile(r"[ \n]+([a-zA-Z0-9_]+_upper)")
VITALS = {"temperature": (35.5, 38.1), "sao2": (95.0, 100.0), "heart rate": (60.0, 100.0),
          "respiration": (12.0, 18.0), "systolic bp": (90.0, 120.0), "diastolic bp": (60.0, 90.0),
          "mean bp": (60.0, 110.0)}


# ---------------- HELM (transcribed from EhrSqlMetric and EhrSqlAnnotator) ----------------
def hashable(x):
    """JSON turns result rows (tuples) into lists; turn them back so set() behaves as it did inside HELM."""
    if isinstance(x, list):
        return tuple(hashable(v) for v in x)
    return x


def helm_exec_acc(prediction, gt_query, gt_result, pred_result):
    """EhrSqlMetric's execution accuracy for one record."""
    prediction = (prediction or "").strip()
    gq = (gt_query or "").strip()
    acc = 0
    if gq:
        if gt_result and pred_result:
            acc = int(set(hashable(r) for r in pred_result) == set(hashable(r) for r in gt_result))
        elif not gt_result and not pred_result and not prediction:
            acc = 1
    return acc


def helm_validity(prediction, query_error):
    """EhrSqlMetric's query validity: 0 for an empty answer, 1 if the query ran, else 0."""
    if not (prediction or "").strip():
        return 0
    return 1 if query_error is None else 0


def helm_extract_sql(text):
    """EhrSqlAnnotator's reading of the answer: <sql> tags if any, backticks removed, a leading 'sql' line dropped."""
    t = (text or "").strip()
    m = SQL_TAG.search(t)
    s = m.group(1).strip() if m else t.strip()
    s = s.replace("`", "").strip()
    return re.sub(r"^sql\n", "", s, flags=re.MULTILINE)


# ---------------- Classes ----------------
def gold_class(gt_result, value):
    """rows: a list of result rows; slot: exactly the template values HELM substitutes; empty: []; other."""
    if not gt_result:
        return "empty"
    if all(isinstance(r, list) for r in gt_result):
        return "rows"
    if list(gt_result) == list((value or {}).values()):
        return "slot"
    return "other"


def pred_class(prediction, query_error, pred_result):
    if not (prediction or "").strip():
        return "abstain"
    if query_error is not None:
        return "error"
    return "rows" if pred_result else "empty_result"


def is_impossible(info):
    return bool(info.get("impossible")) or (info.get("gq") or "").strip().lower() == "null"


# ---------------- EHRSQL-style post-processing and comparison ----------------
def official_sql(q, anchor=ANCHOR):
    """Following glee4810/EHRSQL evaluate.py post_process_sql: lower-case; anchor current_time; vital-sign bounds when
    exactly one vital placeholder name is used; "''" -> "'"; '< =' -> '<='; '%y' -> '%Y'; '%j' -> '%J'; 'now' anchored."""
    q = (q or "").lower()
    if "current_time" in q:
        q = q.replace("current_time", "'%s'" % anchor)
    lo, up = LOWER_RE.findall(q), UPPER_RE.findall(q)
    if lo and up:
        lo_e, up_e = lo[0], up[0]
        names = set(re.findall(r"([a-zA-Z0-9_]+)_lower", lo_e)) | set(re.findall(r"([a-zA-Z0-9_]+)_upper", up_e))
        if len(names) == 1:
            name = names.pop().replace("_", " ")
            if name in VITALS:
                q = q.replace(lo_e, str(VITALS[name][0])).replace(up_e, str(VITALS[name][1]))
    q = q.replace("''", "'").replace("< =", "<=")
    q = q.replace("%y", "%Y").replace("%j", "%J")
    return q.replace("'now'", "'%s'" % anchor)


def official_key(rows):
    """EHRSQL's comparison key: the first 100 rows as strings, sorted (duplicates kept)."""
    return str(sorted([str(r) for r in list(rows)[:100]]))


def execute(conn, sql, limit_s=5.0):
    """(class, rows or message): rows / empty / error / timeout. One statement, wall-clock limit via progress handler."""
    start = time.monotonic()
    conn.set_progress_handler(lambda: 1 if time.monotonic() - start > limit_s else 0, 1000)
    try:
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        return ("rows" if rows else "empty"), rows
    except Exception as e:  # noqa: BLE001 - any failure is a failed query
        cls = "timeout" if time.monotonic() - start > limit_s else "error"
        return cls, "%s: %s" % (type(e).__name__, str(e)[:80])
    finally:
        conn.set_progress_handler(None, 0)


def ran(res):
    return res[0] in ("rows", "empty")


def fixed_acc(info, prediction, query_error, pred_result, gold):
    """HELM's stored execution, no template-value substitution, EHRSQL-style empty == empty.
    gold: (class, rows) where class rows / empty / error / timeout. Unanswerable: credit an empty answer only."""
    p = (prediction or "").strip()
    if is_impossible(info):
        return 1 if not p else 0
    if not p or query_error is not None or not ran(gold):
        return 0
    g = set(hashable(r) for r in gold[1]) if gold[0] == "rows" else set()
    return int(set(hashable(r) for r in (pred_result or [])) == g)


def official_acc(info, prediction, gold_off, exec_off):
    """EHRSQL-style: both queries post-processed and run; first-100 sorted string comparison. An empty (or 'null')
    extracted query is an abstention: credited on unanswerable questions only. exec_off(sql) -> (class, rows)."""
    sql = helm_extract_sql(prediction)
    abstain = (not sql) or sql.strip().lower() == "null"
    if is_impossible(info):
        return 1 if abstain else 0
    if abstain or not ran(gold_off):
        return 0
    po = exec_off(official_sql(sql))
    if not ran(po):
        return 0
    return int(official_key(po[1] if po[0] == "rows" else []) == official_key(gold_off[1] if gold_off[0] == "rows"
                                                                               else []))


# ---------------- Release, stats, census ----------------
def model_of(run_name):
    i = run_name.find("model=")
    return run_name[i + len("model="):].split(",")[0] if i >= 0 else ""


def select_runs(run_suites, prefix):
    return {r: s for r, s in (run_suites or {}).items() if r.startswith(prefix)}


def is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and not (isinstance(v, float) and math.isnan(v))


def stat_entry(stats, name, split="test"):
    for s in stats or []:
        if not isinstance(s, dict):
            continue
        nm = s.get("name") or {}
        if (nm.get("name") == name and nm.get("split") == split and nm.get("perturbation") is None
                and nm.get("sub_split") is None):
            return {"count": s.get("count"), "sum": s.get("sum"), "mean": s.get("mean")}
    return None


def info_of(instance):
    """{gq, value, impossible} of one HELM instance (gold = first reference tagged 'correct')."""
    gq = None
    for ref in (instance or {}).get("references") or []:
        if isinstance(ref, dict) and "correct" in (ref.get("tags") or []):
            gq = (ref.get("output") or {}).get("text")
            break
    ed = (instance or {}).get("extra_data") or {}
    return {"gq": (gq or "").strip(), "value": ed.get("value") or {}, "impossible": bool(ed.get("is_impossible"))}


def summarize_run(preds, info, gold_raw, gold_off, exec_off):
    """Census of one run's display_predictions (unperturbed, test ids only, first record per (instance, trial)).

    info: {id: info_of(...)}; gold_raw / gold_off: {id: (class, rows)} from running the gold as HELM does / EHRSQL-style;
    exec_off(sql) -> (class, rows). trials: {t: {n, pub, sql_only, fixed, official}} with pub = stored accuracy."""
    counts = {"n_records": 0, "perturbed": 0, "not_test": 0, "duplicate": 0, "kept": 0, "no_annotation": 0}
    tally = {"stored_missing": 0, "acc_mismatch": 0, "val_mismatch": 0, "credit": 0, "abstain_credit": 0,
             "slot_credit": 0, "valid_answerable": 0, "valid_answerable_empty": 0}
    trials, gclass, pclass, golds, texts, seen = {}, {}, {}, {}, {}, set()
    for r in preds or []:
        if not isinstance(r, dict):
            continue
        counts["n_records"] += 1
        if r.get("perturbation") is not None:
            counts["perturbed"] += 1
            continue
        iid, t = r.get("instance_id"), r.get("train_trial_index", 0)
        if iid not in info:
            counts["not_test"] += 1
            continue
        if (iid, t) in seen:
            counts["duplicate"] += 1
            continue
        seen.add((iid, t))
        counts["kept"] += 1
        inf = info[iid]
        pred = (r.get("predicted_text") or "").strip()
        ann = (r.get("annotations") or {}).get("ehr_sql")
        if not isinstance(ann, dict):
            counts["no_annotation"] += 1
            ann = {}
        gt = ann.get("ground_truth_result") or []
        pr = ann.get("predicted_result") or []
        qe = ann.get("query_error")
        st = r.get("stats") or {}
        v = st.get(ACC)
        if not is_number(v):
            tally["stored_missing"] += 1
            stored = 0
        else:
            stored = v
            if abs(v - helm_exec_acc(pred, inf["gq"], gt, pr)) > 1e-9:
                tally["acc_mismatch"] += 1
        vv = st.get(VAL)
        if is_number(vv) and abs(vv - helm_validity(pred, qe)) > 1e-9:
            tally["val_mismatch"] += 1
        gc, pc = gold_class(gt, inf["value"]), pred_class(pred, qe, pr)
        if stored >= 1:
            tally["credit"] += 1
            if not pred:
                tally["abstain_credit"] += 1
            if gc == "slot":
                tally["slot_credit"] += 1
        if not is_impossible(inf) and pc in ("rows", "empty_result"):
            tally["valid_answerable"] += 1
            if pc == "empty_result":
                tally["valid_answerable_empty"] += 1
        gold_fix = ("rows", gt) if gc == "rows" else gold_raw.get(iid, ("error", "missing"))
        acc = trials.setdefault(t, dict({"n": 0}, **{k: Fraction(0) for k in VARIANTS}))
        acc["n"] += 1
        acc["pub"] += Fraction(stored).limit_denominator(10 ** 6)
        acc["sql_only"] += Fraction(stored).limit_denominator(10 ** 6) if not is_impossible(inf) else 0
        acc["fixed"] += fixed_acc(inf, pred, qe, pr, gold_fix)
        acc["official"] += official_acc(inf, pred, gold_off.get(iid, ("error", "missing")), exec_off)
        if t == 0:
            gclass[iid], pclass[iid] = gc, pc
            golds[iid] = hashable(gt)
            texts[iid] = pred[:200]
    return dict({"counts": counts, "trials": trials, "gclass": gclass, "pclass": pclass, "golds": golds,
                 "texts": texts}, **tally)


def run_mean(trials, key):
    ms = [Fraction(v[key]) / v["n"] for _, v in sorted(trials.items()) if v["n"]]
    return sum(ms, Fraction(0)) / len(ms) if ms else None


def class_counts(classes, names):
    out = {c: 0 for c in names}
    for c in classes.values():
        out[c] = out.get(c, 0) + 1
    return out


def ranks_high(values):
    return {k: 1 + sum(1 for w in values.values() if w > v) for k, v in values.items()}


def kendall_tau_b(xs, ys):
    n = len(xs)
    c = d = tx = ty = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx = (xs[i] > xs[j]) - (xs[i] < xs[j])
            dy = (ys[i] > ys[j]) - (ys[i] < ys[j])
            if dx == 0:
                tx += 1
            if dy == 0:
                ty += 1
            if dx and dy:
                if dx == dy:
                    c += 1
                else:
                    d += 1
    n0 = n * (n - 1) // 2
    den = (n0 - tx) * (n0 - ty)
    return (c - d) / math.sqrt(den) if den > 0 else None


def group_values(doc, header_name=CELL_HEADER):
    tables = doc if isinstance(doc, list) else [doc]
    for t in tables:
        if not isinstance(t, dict):
            continue
        header = t.get("header") or []
        col = next((j for j, h in enumerate(header) if isinstance(h, dict) and h.get("value") == header_name), None)
        if col is None:
            continue
        out = []
        for row in t.get("rows") or []:
            if (isinstance(row, list) and len(row) > col and isinstance(row[col], dict)
                    and is_number(row[col].get("value"))):
                out.append(float(row[col]["value"]))
        return out
    return None


def match_cells(ours, published, tol):
    pub = sorted(published)
    used = [False] * len(pub)
    hit = 0
    for v in sorted(ours.values()):
        for j, p in enumerate(pub):
            if not used[j] and abs(p - v) <= tol:
                used[j] = True
                hit += 1
                break
    return hit


def stable_hash(text):
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:12], 16)


# ---------------- Verdicts ----------------
def verdicts(s):
    """The eight pre-registered predictions (True = HELD, False = FAILED, None = not gradable)."""
    inc = s["runs_included"]
    ans = s["answerable"]
    return {
        "P1": (s["test_ids"] == N_TEST and s["runs_listed"] >= 13 and inc >= 12
               and s["cells_matched"] * 10 >= 9 * inc),
        "P2": None if not ans else s["slot_golds"] * 4 >= ans,
        "P3": None if s["db_rows"] is None else s["db_rows"] < 10000,
        "P4": None if not ans else s["gold_changed_official"] * 10 >= ans,
        "P5": None if not s["stored_rows_golds"] else s["rows_reproduced"] * 20 >= 19 * s["stored_rows_golds"],
        "P6": s["runs_abstain_majority"] >= 7,
        "P7": s["runs_fixed_gain3"] >= 10,
        "P8": None if s["leader_sql_only_first"] is None else not s["leader_sql_only_first"],
    }


def verdict_word(v):
    return "NOT GRADED" if v is None else ("HELD" if v else "FAILED")
