"""Audit 101 helpers: does HELM Classic's GSM8K column score right answers 0 because it compares only the last token?

HELM's GSM8K scenario (gsm_scenario.py) builds each gold as the worked solution with "####" replaced by "The answer is"
and a "." appended, e.g. "... The answer is 72.". HELM Classic's published GSM8K column ("EM") is
exact_match_indicator (src/helm/benchmark/metrics/evaluate_reference_metrics.py), which keeps only the text after the
LAST space in gold and prediction and compares them literally. So only "72." is compared: "The answer is 72" (no
period), "The answer is $72.", "The answer is 1,000." (gold "1000.") or "The answer is 72 apples." all score 0, and so
does a right answer followed by more text. HELM Lite scores GSM8K with final_number_exact_match instead (the last
number in each text, commas removed).

This module transcribes exact_match, exact_match_indicator and final_number_exact_match, adds a stated-answer grade
(CORR: the number right after the first "the answer is" in the prediction, or, without one, the prediction's last
number, compared by value with the gold's answer), classes every disagreement between HELM's indicator and CORR, and
provides census, cell, rank, tau and verdict helpers. Apache-2.0 (exact_match, exact_match_indicator and
final_number_exact_match are transcribed from stanford-crfm/helm, Apache-2.0).
"""

import hashlib
import math
import re
from fractions import Fraction

STAT = "exact_match_indicator"
UNDER_CLASSES = ("continued", "words_after", "no_period", "number_form", "no_phrase")
PHRASE = re.compile(r"the answer is", re.IGNORECASE)
NUM_AFTER = re.compile(r"\s*:?\s*\$?\s*(-?[\d,]*\.?\d+)")
NUM_ANY = re.compile(r"-?\d[\d,]*(?:\.\d+)?")
HELM_FINAL = re.compile(r"-?[\d,]+(?:.\d+)?")  # HELM's regex, unescaped "." included on purpose


# ---------------- HELM transcriptions ----------------
def exact_match(gold, pred):
    if not pred:
        return 0
    return 1 if gold.strip() == pred.strip() else 0


def exact_match_indicator(gold, pred, indicator=" "):
    """HELM: exact match of the text after the last indicator (default: a single space) in gold and prediction."""
    pred = pred.split(indicator)[-1].strip()
    gold = gold.split(indicator)[-1].strip()
    return exact_match(gold, pred)


def helm_final_number(x):
    """HELM's get_final_number: the last regex match with commas removed ("" when there is none)."""
    matches = HELM_FINAL.findall(x)
    if not matches:
        return ""
    return matches[-1].replace(",", "")


def final_number_exact_match(gold, pred):
    """HELM: 1 iff the final number in gold and prediction match (as strings, commas removed)."""
    return exact_match(helm_final_number(gold), helm_final_number(pred))


def lone_comma(pred):
    """True when the prediction has a digit but HELM's final-number regex ends on a match made only of commas, so
    final_number_exact_match sees an empty number (the case of HELM issue #4337)."""
    m = HELM_FINAL.findall(pred or "")
    return bool(m) and m[-1].replace(",", "") == "" and any(ch.isdigit() for ch in pred)


# ---------------- Our stated-answer grade ----------------
def to_value(s):
    """Exact value of a number string with commas removed (None when it is not a number)."""
    try:
        return Fraction(s.replace(",", ""))
    except (ValueError, ZeroDivisionError):
        return None


def stated(text, last=False):
    """(value, end) of the number right after the first (or last) "the answer is" in text; (None, None) when the
    phrase is absent or no number follows it directly (an optional ':' and '$' are allowed)."""
    ms = list(PHRASE.finditer(text or ""))
    if not ms:
        return None, None
    m = ms[-1] if last else ms[0]
    n = NUM_AFTER.match(text, m.end())
    if not n:
        return None, None
    return to_value(n.group(1)), n.end()


def last_number(text):
    ms = NUM_ANY.findall(text or "")
    return to_value(ms[-1]) if ms else None


def gold_value(gold):
    """The gold's answer: the number after its last "the answer is" (HELM appends one), else its last number."""
    v, _ = stated(gold, last=True)
    return v if v is not None else last_number(gold)


def corr_grade(gold, pred):
    """(grade, source, end): source 'stated' when the prediction states an answer after "the answer is", else 'last'
    (its last number); grade 1 when that value equals the gold's answer."""
    gv = gold_value(gold)
    sv, end = stated(pred)
    if sv is not None:
        v, source = sv, "stated"
    else:
        v, source, end = last_number(pred), "last", None
    return (1 if (v is not None and gv is not None and v == gv) else 0), source, end


def under_class(pred, source, end):
    """Class of a right answer HELM's indicator scored 0: no_phrase (no stated answer; the last number is right), or,
    by the text after the stated number: continued (it goes on to another line), no_period (nothing follows),
    number_form (only '.' follows, so the number is written differently from the gold's, e.g. '$72' or '1,000'),
    words_after (other text on the same line)."""
    if source != "stated":
        return "no_phrase"
    rest = pred[end:].strip()
    if "\n" in rest:
        return "continued"
    if rest == "":
        return "no_period"
    if rest == ".":
        return "number_form"
    return "words_after"


def grade_record(golds, pred_text):
    """HELM strips the completion and keeps the max over correct references. Returns ind (HELM's indicator), fnem
    (HELM's final_number_exact_match), corr (our stated-answer grade), and cls: an under-credit class when corr is 1
    and ind 0, 'changed' when ind is 1 and corr 0 (the stated answer differs from the gold's), else None."""
    pred = (pred_text or "").strip()
    ind = max((exact_match_indicator(g, pred) for g in golds), default=0)
    fnem = max((final_number_exact_match(g, pred) for g in golds), default=0)
    grades = [corr_grade(g, pred) for g in golds]
    corr = max((x[0] for x in grades), default=0)
    cls = None
    if corr == 1 and ind == 0:
        _, source, end = next(x for x in grades if x[0] == 1)
        cls = under_class(pred, source, end)
    elif ind == 1 and corr == 0:
        cls = "changed"
    return {"ind": ind, "fnem": fnem, "corr": corr, "cls": cls, "lone_comma": lone_comma(pred)}


# ---------------- Run names and release ----------------
def model_of(run_name):
    """Text after 'model=' up to the next comma."""
    i = run_name.find("model=")
    return run_name[i + len("model="):].split(",")[0] if i >= 0 else ""


def select_runs(run_suites, prefix):
    return {r: s for r, s in (run_suites or {}).items() if r.startswith(prefix)}


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


def is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and not (isinstance(v, float) and math.isnan(v))


# ---------------- Run census ----------------
def summarize_run(instances, preds, cap):
    """Grade every test-split record of one run (all trials, unperturbed, first record per (instance, trial)).

    trials: {trial: {n, ind, fnem, corr}}; classes: counts of under-credits by class; over: ind 1 and corr 0;
    keys: the (instance id, trial) of each class and of 'changed'; fnem_gain / fnem_loss: records where HELM's
    final_number_exact_match is 1 / 0 and its indicator 0 / 1; lone_comma: records with the #4337 empty final number;
    cap_records / cap_under: records, and under-credits, whose stored num_output_tokens reached max_tokens `cap`.
    """
    gold = {}
    for inst in instances or []:
        if isinstance(inst, dict) and inst.get("split") == "test":
            gold[inst.get("id")] = [((r.get("output") or {}).get("text") or "")
                                    for r in inst.get("references") or []
                                    if isinstance(r, dict) and "correct" in (r.get("tags") or [])]
    counts = {"n_records": 0, "perturbed": 0, "not_test": 0, "duplicate": 0, "kept": 0}
    trials, seen = {}, set()
    classes = {c: 0 for c in UNDER_CLASSES}
    keys = {c: [] for c in UNDER_CLASSES + ("changed",)}
    stat_missing = stat_mismatch = under = over = fnem_gain = fnem_loss = lone = cap_records = cap_under = 0
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
        gr = grade_record(gold[iid], r.get("predicted_text"))
        acc = trials.setdefault(t, {"n": 0, "ind": 0, "fnem": 0, "corr": 0})
        acc["n"] += 1
        for k in ("ind", "fnem", "corr"):
            acc[k] += gr[k]
        st = r.get("stats") or {}
        stored = st.get(STAT)
        if not is_number(stored):
            stat_missing += 1
        elif int(round(stored)) != gr["ind"]:
            stat_mismatch += 1
        if gr["fnem"] == 1 and gr["ind"] == 0:
            fnem_gain += 1
        if gr["fnem"] == 0 and gr["ind"] == 1:
            fnem_loss += 1
        if gr["lone_comma"]:
            lone += 1
        nout = st.get("num_output_tokens")
        at_cap = is_number(nout) and nout >= cap
        if at_cap:
            cap_records += 1
        if gr["cls"] == "changed":
            over += 1
            keys["changed"].append((iid, t))
        elif gr["cls"] is not None:
            under += 1
            classes[gr["cls"]] += 1
            keys[gr["cls"]].append((iid, t))
            if at_cap:
                cap_under += 1
    return {"counts": counts, "trials": trials, "stat_missing": stat_missing, "stat_mismatch": stat_mismatch,
            "classes": classes, "keys": keys, "under": under, "over": over, "fnem_gain": fnem_gain,
            "fnem_loss": fnem_loss, "lone_comma": lone, "cap_records": cap_records, "cap_under": cap_under}


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


def group_em_values(group_doc):
    """Numeric values of the 'EM' column of a group page's first table (None when there is no such column)."""
    if not isinstance(group_doc, list) or not group_doc or not isinstance(group_doc[0], dict):
        return None
    t = group_doc[0]
    header = t.get("header") or []
    col = next((j for j, h in enumerate(header) if isinstance(h, dict) and h.get("value") == "EM"), None)
    if col is None:
        return None
    out = []
    for row in t.get("rows") or []:
        if isinstance(row, list) and len(row) > col and isinstance(row[col], dict) and is_number(row[col].get("value")):
            out.append(float(row[col]["value"]))
    return out


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
    """The seven pre-registered predictions (True = HELD) from the job's pooled statistics `s`."""
    cl = s.get("under_classes") or {}
    cont = cl.get("continued", 0)
    p7 = s["under"] > 0 and all(cont > v for k, v in cl.items() if k != "continued")
    return {
        "P1": bool(s["fixtures"]) and s["runs_listed"] >= 60 and s["runs_included"] * 10 >= 9 * s["runs_listed"]
        and s["runs_included"] > 0 and s["cells_matched"] * 10 >= 9 * s["runs_included"],
        "P2": s["ind_credits"] > 0 and s["under"] * 100 >= s["ind_credits"],
        "P3": s["over"] < s["under"],
        "P4": s["max_rise"] is not None and s["max_rise"] >= Fraction(1, 100),
        "P5": s["movers"] >= 5,
        "P6": s["tau"] is not None and s["tau"] >= 0.9,
        "P7": p7,
    }
