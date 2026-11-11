"""Audit 102 helpers: how often do HELM Classic's two MATH columns grade an answer wrongly?

HELM Classic (release v0.4.0) publishes two MATH columns over the same 437 level-1 questions (7 subjects):
  * "MATH" (group math_regular): use_official_examples=True, no chain of thought. The prompt shows answers as
    'Answer: $5$', generation stops at '$' (max 20 tokens) and the output is scored with math_equiv: Hendrycks'
    _strip_string on gold and output, then string equality.
  * "MATH (chain-of-thoughts)" (group math_chain_of_thought): 400 tokens, stop at '###', scored with
    math_equiv_chain_of_thought: the contents of the LAST \\boxed{...} of the reference solution and of the output.
Hazards that follow from the code: equal values written differently ('1,000' vs '1000', '0.25' vs '\\frac{1}{4}')
score 0 in both columns; in the chain-of-thought column an output with no \\boxed{} scores 0 even when it states the
right answer (audit 91 measured this on HELM Lite); and in runs where HELM replaced the stop sequence with '#'
(run names with stop=hash), a short answer can keep its closing '$', which _strip_string does not remove.

Graders, per test record and trial:
  H  HELM's metric, transcribed (Apache-2.0, stanford-crfm/helm; from hendrycks/math, MIT) and gated against the
     score HELM stored for every record;
  A  the corrected grade. Chain of thought: audit 91's grade, unchanged (boxed answer, else a '\\boxed 5' / '\\fbox{5}'
     fallback, else the unboxed final answer; credit when HELM's is_equiv holds or both sides are the same rational
     number). Regular: the output up to its first unescaped '$', credited when HELM's is_equiv holds or both sides are
     the same rational number.
Standard library only. Apache-2.0. Authored by AI agents working in the name of MV2, Munim, Inc.
"""

import hashlib
import math
import re
from fractions import Fraction

# ----- H: HELM's MATH scorer, transcribed (src/helm/benchmark/scenarios/math_scenario.py); copied from audit 91 -----


def remove_boxed(string):
    left = "\\boxed{"
    try:
        assert string[: len(left)] == left
        assert string[-1] == "}"
        return string[len(left): -1]
    except Exception:  # noqa: BLE001 - transcribed as is
        return None


def last_boxed_only_string(string):
    idx = string.rfind("\\boxed")
    if idx < 0:
        idx = string.rfind("\\fbox")
        if idx < 0:
            return None
    i = idx
    right_brace_idx = None
    num_left_braces_open = 0
    while i < len(string):
        if string[i] == "{":
            num_left_braces_open += 1
        if string[i] == "}":
            num_left_braces_open -= 1
            if num_left_braces_open == 0:
                right_brace_idx = i
                break
        i += 1
    if right_brace_idx is None:
        retval = None
    else:
        retval = string[idx: right_brace_idx + 1]
    return retval


def get_answer(solution):
    if solution is None:
        return None
    last_boxed = last_boxed_only_string(solution)
    if last_boxed is None:
        return None
    answer = remove_boxed(last_boxed)
    if answer is None:
        return None
    return answer


def _fix_fracs(string):
    substrs = string.split("\\frac")
    new_str = substrs[0]
    if len(substrs) > 1:
        substrs = substrs[1:]
        for substr in substrs:
            new_str += "\\frac"
            if substr[0] == "{":
                new_str += substr
            else:
                try:
                    assert len(substr) >= 2
                except Exception:  # noqa: BLE001 - transcribed as is
                    return string
                a = substr[0]
                b = substr[1]
                if b != "{":
                    if len(substr) > 2:
                        post_substr = substr[2:]
                        new_str += "{" + a + "}{" + b + "}" + post_substr
                    else:
                        new_str += "{" + a + "}{" + b + "}"
                else:
                    if len(substr) > 2:
                        post_substr = substr[2:]
                        new_str += "{" + a + "}" + b + post_substr
                    else:
                        new_str += "{" + a + "}" + b
    string = new_str
    return string


def _fix_a_slash_b(string):
    if len(string.split("/")) != 2:
        return string
    a_str = string.split("/")[0]
    b_str = string.split("/")[1]
    try:
        a = int(a_str)
        b = int(b_str)
        assert string == "{}/{}".format(a, b)
        new_string = "\\frac{" + str(a) + "}{" + str(b) + "}"
        return new_string
    except Exception:  # noqa: BLE001 - transcribed as is
        return string


def _remove_right_units(string):
    if "\\text{ " in string:
        splits = string.split("\\text{ ")
        assert len(splits) == 2
        return splits[0]
    else:
        return string


def _fix_sqrt(string):
    if "\\sqrt" not in string:
        return string
    splits = string.split("\\sqrt")
    new_string = splits[0]
    for split in splits[1:]:
        if split[0] != "{":
            a = split[0]
            new_substr = "\\sqrt{" + a + "}" + split[1:]
        else:
            new_substr = "\\sqrt" + split
        new_string += new_substr
    return new_string


def _strip_string(string):
    string = string.replace("\n", "")
    string = string.replace("\\!", "")
    string = string.replace("\\\\", "\\")
    string = string.replace("tfrac", "frac")
    string = string.replace("dfrac", "frac")
    string = string.replace("\\left", "")
    string = string.replace("\\right", "")
    string = string.replace("^{\\circ}", "")
    string = string.replace("^\\circ", "")
    string = string.replace("\\$", "")
    string = _remove_right_units(string)
    string = string.replace("\\%", "")
    string = string.replace(r"\%", "")
    string = string.replace(" .", " 0.")
    string = string.replace("{.", "{0.")
    if len(string) == 0:
        return string
    if string[0] == ".":
        string = "0" + string
    if len(string.split("=")) == 2:
        if len(string.split("=")[0]) <= 2:
            string = string.split("=")[1]
    string = _fix_sqrt(string)
    string = string.replace(" ", "")
    string = _fix_fracs(string)
    if string == "0.5":
        string = "\\frac{1}{2}"
    string = _fix_a_slash_b(string)
    return string


def is_equiv(str1, str2):
    if str1 is None and str2 is None:
        return 1.0  # HELM prints "WARNING: Both None" here
    if str1 is None or str2 is None:
        return 0.0
    try:
        ss1 = _strip_string(str1)
        ss2 = _strip_string(str2)
        return float(ss1 == ss2)
    except Exception:  # noqa: BLE001 - transcribed as is
        return float(str1 == str2)


def is_equiv_chain_of_thought(str1, str2):
    ans1 = get_answer(str1)
    ans2 = get_answer(str2)
    return is_equiv(ans1, ans2)


# ----- A: the corrected grade (copied unchanged from audit 91, grade91.py) -----

_BOXED_BARE = re.compile(r"\\boxed ([^\s${}]+)")


def fallback_answer(s):
    """An answer HELM cannot extract: the contents of a last \\fbox{...}, else the token after the last '\\boxed '
    written without braces; None otherwise."""
    s = s or ""
    lb = last_boxed_only_string(s)
    if lb is not None and lb.startswith("\\fbox{") and lb.endswith("}"):
        return lb[len("\\fbox{"): -1]
    m = _BOXED_BARE.findall(s)
    if m:
        return m[-1]
    return None


def strip_safe(s):
    try:
        return _strip_string(s)
    except Exception:  # noqa: BLE001 - HELM's own fallback is the raw string
        return s


_TEXT_TAIL = re.compile(r"\\(?:text|mbox|mathrm)\{[A-Za-z .]*\}$")
_THOUSANDS = re.compile(r"^-?\d{1,3}(?:,\d{3})+(?:\.\d+)?$")
_DEC = re.compile(r"^-?\d+(?:\.\d+)?$")
_FRAC = re.compile(r"^(-?)\\frac\{(-?\d+)\}\{(-?\d+)\}$")
_SLASH = re.compile(r"^(-?\d+)/(\d+)$")


def value(s):
    """The rational number an answer string denotes, or None: HELM's normalisation, then LaTeX thin spaces and
    '{,}' removed, trailing \\text{...} / \\mbox{...} / \\mathrm{...} unit groups removed, a trailing '.' removed,
    thousands commas removed; then an integer or decimal, \\frac{a}{b} (optionally negated) or a/b."""
    if s is None:
        return None
    t = strip_safe(s)
    t = t.replace("\\,", "").replace("{,}", "").replace("\\;", "").replace("\\ ", "")
    prev = None
    while prev != t:
        prev = t
        t = _TEXT_TAIL.sub("", t).strip()
    t = t.rstrip(".")
    if _THOUSANDS.match(t):
        t = t.replace(",", "")
    if _DEC.match(t):
        return Fraction(t)
    m = _FRAC.match(t)
    if m:
        den = int(m.group(3))
        if den == 0:
            return None
        v = Fraction(int(m.group(2)), den)
        return -v if m.group(1) else v
    m = _SLASH.match(t)
    if m:
        den = int(m.group(2))
        return Fraction(int(m.group(1)), den) if den else None
    return None


def value_eq(a, b):
    va, vb = value(a), value(b)
    return va is not None and vb is not None and va == vb


_ANS_IS = re.compile(r"answer is", re.I)


def unboxed_candidate(pred):
    """(candidate, source) for an output with no extractable boxed answer (audit 91's rule, unchanged)."""
    t = (pred or "").replace("\\$", "")
    for a in ("$$", "\\[", "\\]", "\\(", "\\)"):
        t = t.replace(a, "$")
    ms = list(_ANS_IS.finditer(t))
    if ms:
        line = t[ms[-1].end():].split("\n", 1)[0]
        segs = [x.strip() for x in line.split("$")[1::2] if x.strip()]
        cand = segs[-1] if segs else line.strip().strip(":").strip()
        src = "phrase"
    else:
        segs = [x.strip() for x in t.split("$")[1::2] if x.strip()]
        if not segs:
            return "", "none"
        cand = segs[-1]
        src = "math"
    if "=" in cand:
        cand = cand.rsplit("=", 1)[1]
    cand = cand.strip().rstrip(".,;").strip()
    return cand, src


def grade_cot(gold, pred):
    """H and A for one chain-of-thought prediction (audit 91's grade, unchanged)."""
    g_helm, p_helm = get_answer(gold), get_answer(pred)
    h = 1 if is_equiv(g_helm, p_helm) == 1.0 else 0
    both_none = g_helm is None and p_helm is None
    g, g_src = g_helm, "boxed"
    if g is None:
        g = fallback_answer(gold)
        g_src = "fallback" if g is not None else "none"
    cand, route = "", ""
    if g is None:
        a, route = 0, "no_gold"
    else:
        p = p_helm
        route = "boxed"
        if p is None:
            p = fallback_answer(pred)
            route = "fallback"
        if p is not None:
            cand = p
            a = 1 if (is_equiv(g, p) == 1.0 or value_eq(g, p)) else 0
        else:
            cand, usrc = unboxed_candidate(pred)
            route = "unboxed_" + usrc
            a = 1 if (cand and (is_equiv(g, cand) == 1.0 or value_eq(g, cand))) else 0
    return {"h": h, "a": a, "both_none": both_none, "gold_src": g_src, "route": route, "gold_answer": g,
            "helm_pred_answer": p_helm, "candidate": cand}


COT_UP = ("gold_fallback", "pred_fallback", "value_format", "unboxed", "other")
COT_DOWN = ("both_none", "other")


def cot_flip_class(r):
    """Audit 91's flip classes (None when H and A agree)."""
    if r["h"] == r["a"]:
        return None
    if r["a"] == 1:
        if r["gold_src"] == "fallback":
            return "gold_fallback"
        if r["route"] == "fallback":
            return "pred_fallback"
        if r["route"] == "boxed":
            return "value_format"
        if r["route"].startswith("unboxed"):
            return "unboxed"
        return "other"
    if r["both_none"]:
        return "both_none"
    return "other"


# ----- The regular (no chain of thought) column -----

REG_UP = ("dollar_tail", "value_format")
REG_DOWN = ("other",)


def reg_candidate(pred):
    """(text before the first '$' not preceded by a backslash, stripped; True) or (pred, False) without one."""
    for i, ch in enumerate(pred):
        if ch == "$" and (i == 0 or pred[i - 1] != "\\"):
            return pred[:i].strip(), True
    return pred, False


def grade_reg(gold, pred):
    """H (HELM's math_equiv) and A for one regular prediction. Up-flip classes: dollar_tail (the output kept a closing
    '$' and the text before it is right), value_format (the same number written differently). Down: other."""
    pred = (pred or "").strip()
    h = 1 if is_equiv(gold, pred) == 1.0 else 0
    cand, cut = reg_candidate(pred)
    a = 1 if (cand and (is_equiv(gold, cand) == 1.0 or value_eq(gold, cand))) else 0
    cls = None
    if a == 1 and h == 0:
        cls = "dollar_tail" if cut else "value_format"
    elif h == 1 and a == 0:
        cls = "other"
    return {"h": h, "a": a, "cls": cls, "cut": cut, "candidate": cand}


MODES = ("reg", "cot")
STAT = {"reg": "math_equiv", "cot": "math_equiv_chain_of_thought"}
UP = {"reg": REG_UP, "cot": COT_UP}
DOWN = {"reg": REG_DOWN, "cot": COT_DOWN}


def grade_one(mode, gold, pred):
    if mode == "reg":
        return grade_reg(gold, pred)
    r = grade_cot(gold, pred)
    r["cls"] = cot_flip_class(r)
    return r


def grade_record(mode, golds, pred_text):
    """HELM strips the completion and keeps the max over references. cls: 'up:<class>' when A is 1 and H 0,
    'down:<class>' when H is 1 and A 0, else None."""
    pred = (pred_text or "").strip()
    rs = [grade_one(mode, g, pred) for g in golds]
    h = max((r["h"] for r in rs), default=0)
    a = max((r["a"] for r in rs), default=0)
    cls = None
    if a == 1 and h == 0:
        cls = "up:" + next(r for r in rs if r["a"] == 1)["cls"]
    elif h == 1 and a == 0:
        cls = "down:" + next(r for r in rs if r["h"] == 1)["cls"]
    return {"h": h, "a": a, "cls": cls}


# ----- Run names -----

def _parts(run):
    return run.split(":", 1)[1].split(",") if ":" in run else run.split(",")


def run_mode(run):
    """'reg' for math runs with official examples and no chain of thought, 'cot' for chain-of-thought runs without
    official examples, None otherwise."""
    if not run.startswith("math:"):
        return None
    p = _parts(run)
    if "use_chain_of_thought=False" in p and "use_official_examples=True" in p:
        return "reg"
    if "use_chain_of_thought=True" in p and "use_official_examples=False" in p:
        return "cot"
    return None


def subject_of(run):
    for p in _parts(run):
        if p.startswith("subject="):
            return p[len("subject="):]
    return None


def adapter_of(run):
    """The run name without its subject= part: one HELM table row per adapter."""
    head = run.split(":", 1)[0] if ":" in run else ""
    return head + ":" + ",".join(p for p in _parts(run) if not p.startswith("subject="))


def model_part(name):
    """Everything after 'model=' (keeps later parts such as stop=hash); '' when absent."""
    i = name.find("model=")
    return name[i + len("model="):] if i >= 0 else ""


def select_runs(run_suites):
    """{run: (mode, suite)} for every math run of either column."""
    out = {}
    for r, s in (run_suites or {}).items():
        m = run_mode(r)
        if m is not None:
            out[r] = (m, s)
    return out


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


# ----- Run census -----

def golds_of(instances):
    gold = {}
    for inst in instances or []:
        if isinstance(inst, dict) and inst.get("split") == "test":
            gold[inst.get("id")] = [((r.get("output") or {}).get("text") or "")
                                    for r in inst.get("references") or []
                                    if isinstance(r, dict) and "correct" in (r.get("tags") or [])]
    return gold


def summarize_run(mode, instances, preds, cap):
    """Grade every test-split record of one run (all trials, unperturbed, first record per (instance, trial)).
    trials {trial: {n, h, a}}; up / down: flip counts by class; keys: (instance id, trial) per 'up:'/'down:' class;
    stat_missing / stat_mismatch: records whose stored HELM score is absent / differs from H; cap_records / cap_up:
    records, and up-flips, whose stored num_output_tokens reached max_tokens `cap`."""
    gold = golds_of(instances)
    counts = {"n_records": 0, "perturbed": 0, "not_test": 0, "duplicate": 0, "kept": 0}
    trials, seen = {}, set()
    up = {c: 0 for c in UP[mode]}
    down = {c: 0 for c in DOWN[mode]}
    keys = {"up:" + c: [] for c in UP[mode]}
    keys.update({"down:" + c: [] for c in DOWN[mode]})
    stat_missing = stat_mismatch = cap_records = cap_up = 0
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
        gr = grade_record(mode, gold[iid], r.get("predicted_text"))
        acc = trials.setdefault(t, {"n": 0, "h": 0, "a": 0})
        acc["n"] += 1
        acc["h"] += gr["h"]
        acc["a"] += gr["a"]
        st = r.get("stats") or {}
        stored = st.get(STAT[mode])
        if not is_number(stored):
            stat_missing += 1
        elif int(round(stored)) != gr["h"]:
            stat_mismatch += 1
        nout = st.get("num_output_tokens")
        at_cap = is_number(nout) and nout >= cap
        if at_cap:
            cap_records += 1
        if gr["cls"] is not None:
            kind, c = gr["cls"].split(":", 1)
            (up if kind == "up" else down)[c] += 1
            keys[gr["cls"]].append((iid, t))
            if kind == "up" and at_cap:
                cap_up += 1
    return {"counts": counts, "trials": trials, "stat_missing": stat_missing, "stat_mismatch": stat_mismatch,
            "up": up, "down": down, "keys": keys, "cap_records": cap_records, "cap_up": cap_up}


def run_mean(trials, key):
    """HELM's run-level mean: the mean over trials of each trial's mean (exact Fraction; None without trials)."""
    ms = [Fraction(v[key], v["n"]) for _, v in sorted(trials.items()) if v["n"]]
    return sum(ms, Fraction(0)) / len(ms) if ms else None


def build_cells(runs, subjects):
    """runs {run: {mode, adapter, subject, trials}} (included runs only) -> {(mode, adapter): {'h': F, 'a': F}}: the
    mean over subjects of each run's mean, only for adapters that have an included run for every subject."""
    by = {}
    for r in runs.values():
        by.setdefault((r["mode"], r["adapter"]), {})[r["subject"]] = r["trials"]
    cells = {}
    for key, subj in by.items():
        if any(s not in subj for s in subjects):
            continue
        cells[key] = {k: sum((run_mean(subj[s], k) for s in subjects), Fraction(0)) / len(subjects)
                      for k in ("h", "a")}
    return cells


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


def group_values(group_doc, prefix="Equivalent"):
    """Numeric values of the first column whose header starts with `prefix` in a group page's first table."""
    if not isinstance(group_doc, list) or not group_doc or not isinstance(group_doc[0], dict):
        return None
    t = group_doc[0]
    header = t.get("header") or []
    col = next((j for j, h in enumerate(header)
                if isinstance(h, dict) and str(h.get("value") or "").startswith(prefix)), None)
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


# ----- Verdicts -----

def verdicts(s):
    """The eight pre-registered predictions (True = HELD) from the job's pooled statistics `s`."""
    cl = s.get("cot_up_classes") or {}
    unb = cl.get("unboxed", 0)
    return {
        "P1": (bool(s["fixtures"]) and s["runs_listed"] > 0 and s["runs_included"] * 10 >= 9 * s["runs_listed"]
               and s["cells_reg"] >= 60 and s["cells_cot"] >= 60
               and s["matched_reg"] * 10 >= 9 * s["cells_reg"] and s["matched_cot"] * 10 >= 9 * s["cells_cot"]),
        "P2": s["cot_n"] > 0 and s["cot_net"] * 100 >= s["cot_n"],
        "P3": unb > 0 and all(unb > v for k, v in cl.items() if k != "unboxed"),
        "P4": s["cot_movers"] >= 5,
        "P5": s["cot_tau"] is not None and s["cot_tau"] >= 0.9,
        "P6": s["reg_n"] > 0 and s["reg_up"] * 1000 >= 2 * s["reg_n"],
        "P7": bool(s["hash_rise"]),
        "P8": s["cot_n"] > 0 and s["reg_n"] > 0 and s["cot_net"] * s["reg_n"] > s["reg_net"] * s["cot_n"],
    }
