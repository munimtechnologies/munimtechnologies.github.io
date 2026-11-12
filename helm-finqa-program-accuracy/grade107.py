"""Audit 107 helpers: does HELM Finance's FinQA "Program Accuracy" score right programs 0 for how they are written?

HELM Finance v1.0.0 (Stanford CRFM) publishes one FinQA column, Program Accuracy (FinQAMetric in
src/helm/benchmark/metrics/fin_qa_metrics.py, main_name program_accuracy). It tokenises the model's program and the
gold program with FinQA's own evaluate.py (vendored by HELM as fin_qa_metrics_helper.py), maps every literal argument
of the GOLD program to a symbol and compares the two programs symbolically. An argument of the prediction that is not
written exactly like one of the gold's is not in the symbol map, and the program scores 0. Three ways a right program
can be written differently follow from HELM's prompt:
  * the prompt names the table operations "table-max, table-min, table-sum, table-average" (hyphens), while the
    scorer accepts only "table_max" and so on (underscores);
  * the prompt says the table operations "take arguments of table row names", while gold programs and the scorer
    need a second argument "none" (e.g. "table_max(net revenue, none)");
  * the prompt never mentions constants, while gold programs write 100 as "const_100" (and -1 as "const_m1"); and a
    number written as "5,829", "5829.0", "14.1%" or "$12" is a different symbol from the gold's spelling.

This module holds the stdlib-only parts of the audit: the argument-normalised program text and tokens (ANPA), the
up-flip classes, the run census, run means, ranks, Kendall tau-b, the group-page column and the verdicts. FinQA's
helper (MIT, Zhiyu Chen) is NOT copied here: the job downloads HELM's vendored copy at a pinned commit at run time and
passes it in. Apache-2.0.
"""

import hashlib
import math
import re
from fractions import Fraction

HYPHEN_RE = re.compile(r"\btable-(max|min|sum|average)\b")
ONEARG_RE = re.compile(r"(table_(?:max|min|sum|average)\()([^(),]*)\)")
UP_CLASSES = ("table_name", "table_none", "const", "number_form", "combined")
KEY_CLASSES = UP_CLASSES + ("exec_only", "down")
# Each single fix: (hyphen names -> underscores, add ", none" to one-argument table ops, numeric-argument mode)
SINGLE_FIXES = (
    ("table_name", (True, False, None)),
    ("table_none", (False, True, None)),
    ("const", (False, False, "const")),
    ("number_form", (False, False, "number")),
)
CELL_HEADER = "Program Accuracy"


# ---------------- Normalisation (ours) ----------------
def norm_text(text, hyphen=True, none=True):
    """Strip; optionally rename hyphenated table operations to FinQA's underscore names, and give a one-argument
    table operation the second argument 'none' that FinQA's programs and scorer expect."""
    t = (text or "").strip()
    if hyphen:
        t = HYPHEN_RE.sub(lambda m: "table_" + m.group(1), t)
    if none:
        t = ONEARG_RE.sub(lambda m: m.group(1) + m.group(2) + ", none)", t)
    return t


def to_number(arg):
    """Value of an argument as FinQA's executor reads it (commas removed, 'N%' = N/100, const_N = N, const_m1 = -1),
    after also dropping '$'. None when it is not a number."""
    a = (arg or "").strip().replace("$", "").strip().replace(",", "")
    if not a:
        return None
    try:
        return float(a)
    except ValueError:
        pass
    if "%" in a:
        try:
            return float(a.replace("%", "")) / 100.0
        except ValueError:
            return None
    if a.startswith("const_"):
        r = a[len("const_"):]
        if r == "m1":
            return -1.0
        try:
            return float(r)
        except ValueError:
            return None
    return None


def canon_arg(arg, mode="all", fmt="%.12g"):
    """Canonical spelling of a numeric argument (mode 'all'; 'const' = only const_N arguments; 'number' = only the
    other numeric arguments). '#n' step references, 'none' and non-numbers are returned unchanged. fmt None = repr."""
    a = (arg or "").strip()
    if not a or a.startswith("#") or a == "none":
        return arg
    is_const = a.startswith("const_")
    if mode == "const" and not is_const:
        return arg
    if mode == "number" and is_const:
        return arg
    v = to_number(a)
    if v is None:
        return arg
    return repr(v) if fmt is None else fmt % v


def norm_tokens(tokens, mode="all", fmt="%.12g"):
    """Canonicalise the numeric arguments of a FinQA token list ([op(, arg1, arg2, ), ..., 'EOF']). Arguments of table
    steps (row names) are left alone; a list that is not a whole number of 4-token steps is returned unchanged."""
    toks = list(tokens or [])
    body = toks[:-1] if toks and toks[-1] == "EOF" else toks
    if mode is None or len(body) % 4 != 0:
        return toks
    out = []
    for i in range(0, len(body), 4):
        op, a1, a2, close = body[i:i + 4]
        if not op.endswith("(") or close != ")" or "table" in op:
            out.extend([op, a1, a2, close])
        else:
            out.extend([op, canon_arg(a1, mode, fmt), canon_arg(a2, mode, fmt), close])
    return out + toks[len(body):]


def up_class(flips):
    """Class of an up-flip (HELM 0, ANPA 1): the first single fix that alone gives credit, else 'combined'."""
    for c, _ in SINGLE_FIXES:
        if flips.get(c):
            return c
    return "combined"


# ---------------- Release, stats, census ----------------
def model_of(run_name):
    i = run_name.find("model=")
    return run_name[i + len("model="):].split(",")[0] if i >= 0 else ""


def select_runs(run_suites, prefix):
    return {r: s for r, s in (run_suites or {}).items() if r.startswith(prefix)}


def is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and not (isinstance(v, float) and math.isnan(v))


def stat_entry(stats, name, split="test"):
    """{count, sum, mean} of the unperturbed stat `name` on `split` in a HELM stats.json list (None when absent)."""
    for s in stats or []:
        if not isinstance(s, dict):
            continue
        nm = s.get("name") or {}
        if (nm.get("name") == name and nm.get("split") == split and nm.get("perturbation") is None
                and nm.get("sub_split") is None):
            return {"count": s.get("count"), "sum": s.get("sum"), "mean": s.get("mean")}
    return None


def stored_exec(per_instance_stats):
    """{(instance id, trial): stored execution_accuracy} from a HELM per_instance_stats.json list (unperturbed)."""
    out = {}
    for p in per_instance_stats or []:
        if not isinstance(p, dict) or p.get("perturbation") is not None:
            continue
        key = (p.get("instance_id"), p.get("train_trial_index", 0))
        for s in p.get("stats") or []:
            nm = (s or {}).get("name") or {}
            if nm.get("name") == "execution_accuracy" and nm.get("perturbation") is None and key not in out:
                v = s.get("mean")
                out[key] = v if is_number(v) else s.get("sum")
    return out


def summarize_run(instances, preds, pis, grade):
    """Grade every test record of one run (unperturbed, first record per (instance, trial)).

    grade(gold_program, exe_ans, table_text, iid, pred_text) -> {pa, ea, anpa, anea, cls, hyphen, onearg, invalid,
    err}. trials: {t: {n, pa, ea, anpa, anea}}; up/down: ANPA 1 and HELM 0 / the reverse; classes: up-flips by class;
    exec_only: execution 1 and ANPA 0; keys: (instance id, trial) per class, 'exec_only' and 'down'."""
    gold = {}
    for inst in instances or []:
        if isinstance(inst, dict) and inst.get("split") == "test":
            refs = inst.get("references") or []
            if len(refs) == 3:
                gold[inst.get("id")] = tuple(((r or {}).get("output") or {}).get("text") or "" for r in refs)
    ea_st = stored_exec(pis)
    counts = {"n_records": 0, "perturbed": 0, "not_test": 0, "duplicate": 0, "kept": 0}
    trials, seen = {}, set()
    classes = {c: 0 for c in UP_CLASSES}
    keys = {c: [] for c in KEY_CLASSES}
    tally = {"up": 0, "down": 0, "exec_only": 0, "anea_up": 0, "anea_down": 0, "hyphen": 0, "onearg": 0,
             "invalid": 0, "errors": 0, "pa_missing": 0, "pa_mismatch": 0, "ea_missing": 0, "ea_mismatch": 0}
    for r in preds or []:
        if not isinstance(r, dict):
            continue
        counts["n_records"] += 1
        if r.get("perturbation") is not None:
            counts["perturbed"] += 1
            continue
        iid, t = r.get("instance_id"), r.get("train_trial_index", 0)
        if iid not in gold:
            counts["not_test"] += 1
            continue
        if (iid, t) in seen:
            counts["duplicate"] += 1
            continue
        seen.add((iid, t))
        counts["kept"] += 1
        prog, exe, table = gold[iid]
        g = grade(prog, exe, table, iid, r.get("predicted_text"))
        acc = trials.setdefault(t, {"n": 0, "pa": 0, "ea": 0, "anpa": 0, "anea": 0})
        acc["n"] += 1
        for k in ("pa", "ea", "anpa", "anea"):
            acc[k] += g[k]
        stored = (r.get("stats") or {}).get("program_accuracy")
        if not is_number(stored):
            tally["pa_missing"] += 1
        elif int(round(stored)) != g["pa"]:
            tally["pa_mismatch"] += 1
        se = ea_st.get((iid, t))
        if not is_number(se):
            tally["ea_missing"] += 1
        elif int(round(se)) != g["ea"]:
            tally["ea_mismatch"] += 1
        for k in ("hyphen", "onearg", "invalid"):
            if g.get(k):
                tally[k] += 1
        if g.get("err"):
            tally["errors"] += 1
        if g["anpa"] == 1 and g["pa"] == 0:
            tally["up"] += 1
            cls = g.get("cls") or "combined"
            classes[cls] += 1
            keys[cls].append((iid, t))
        elif g["anpa"] == 0 and g["pa"] == 1:
            tally["down"] += 1
            keys["down"].append((iid, t))
        if g["ea"] == 1 and g["anpa"] == 0:
            tally["exec_only"] += 1
            keys["exec_only"].append((iid, t))
        if g["anea"] == 1 and g["ea"] == 0:
            tally["anea_up"] += 1
        elif g["anea"] == 0 and g["ea"] == 1:
            tally["anea_down"] += 1
    return {"counts": counts, "trials": trials, "classes": classes, "keys": keys, **tally}


def run_mean(trials, key):
    """HELM's run-level mean: the mean over trials of each trial's mean (exact Fraction; None without trials)."""
    ms = [Fraction(v[key], v["n"]) for _, v in sorted(trials.items()) if v["n"]]
    return sum(ms, Fraction(0)) / len(ms) if ms else None


def ranks_high(values):
    """Higher is better: rank = 1 + the number of entries strictly higher (exact values)."""
    return {k: 1 + sum(1 for w in values.values() if w > v) for k, v in values.items()}


def kendall_tau_b(xs, ys):
    """Kendall's tau-b of two equal-length sequences (None when either is constant or shorter than 2)."""
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
    """Numeric values of the column `header_name` in a HELM group page: either a list of tables (the first table
    that has the column is used) or a single table."""
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
    """How many of our cell values find a distinct published value within tol (greedy, both sorted)."""
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


def pick(lst, salt):
    """One element of a list of (instance id, trial) keys, chosen by a stable hash (None for an empty list)."""
    if not lst:
        return None
    return min(lst, key=lambda k: (stable_hash("%s|%s|%s" % (salt, k[0], k[1])), str(k)))


# ---------------- Verdicts ----------------
def verdicts(s):
    """The eight pre-registered predictions (True = HELD) from the job's pooled statistics `s`."""
    cl = s.get("up_classes") or {}
    const = cl.get("const", 0)
    p3 = s["up"] > 0 and all(const > v for k, v in cl.items() if k != "const")
    inc = s["runs_included"]
    return {
        "P1": bool(s["fixtures"]) and s["runs_listed"] >= 22 and inc >= 20
        and s["cells_matched"] * 10 >= 9 * inc,
        "P2": s["records"] > 0 and s["up"] * 100 >= s["records"],
        "P3": p3,
        "P4": s["hyphen"] >= 20,
        "P5": s["max_rise"] is not None and s["max_rise"] >= Fraction(1, 50),
        "P6": s["tau"] is not None and s["tau"] >= 0.85,
        "P7": bool(s["leader_ok"]),
        "P8": inc > 0 and s["ea_gap_runs"] * 2 >= inc,
    }
