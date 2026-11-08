"""How often does HELM Lite's MATH scorer grade an answer wrongly, in both directions? Core logic for audit 91.

HELM Lite runs MATH (7 subjects, level 1) with chain of thought and scores it with math_equiv_chain_of_thought: the
contents of the LAST \\boxed{...} of the reference solution and of the model output are normalised by Hendrycks'
_strip_string and compared as strings. Three hazards follow from the code itself:
  * an output with no \\boxed{} scores 0 even when it states the right answer;
  * equal values written differently ('10,001' vs '10001', '1.5' vs '\\frac{3}{2}', '5\\text{cm}' vs '5') score 0;
  * when neither the reference nor the output has an extractable answer, is_equiv(None, None) returns 1.0, so any
    unboxed output is marked correct (HELM issue #4374, which gives no count on archived runs).

Graders applied to every archived prediction:
  H  HELM's is_equiv_chain_of_thought, transcribed (Apache-2.0, stanford-crfm/helm; from hendrycks/math, MIT),
     gated against HELM's recorded score;
  A  the corrected grade: the reference answer is HELM's, or, when HELM extracts none, a '\\boxed 5' / '\\fbox{5}'
     fallback (no gold answer -> 0); the output's answer is HELM's boxed answer, else the same fallback, else the
     unboxed final answer (unboxed_candidate); credit when HELM's is_equiv holds or both sides are the same rational
     number (value_eq).
Standard library only. Apache-2.0. Authored by AI agents working in the name of MV2, Munim, Inc.
"""

import re
from fractions import Fraction

# ----- H: HELM's MATH scorer, transcribed (src/helm/benchmark/scenarios/math_scenario.py) -----


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


# ----- A: the corrected grade -----

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
    """(candidate, source) for an output with no extractable boxed answer. '\\$' is dropped and '$$', '\\[', '\\]',
    '\\(', '\\)' become '$'. If 'answer is' (any case) occurs, the rest of that line after its LAST occurrence: its
    last $...$ segment if it has one, else the line itself ('phrase'). Otherwise the last non-empty $...$ segment of
    the whole output ('math'); ('', 'none') if there is none. Then the text after the last '=', with trailing '.',
    ',' and ';' removed."""
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


def grade(gold, pred):
    """H and A for one prediction, plus what the flip classes need."""
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


UP_CLASSES = ("gold_fallback", "pred_fallback", "value_format", "unboxed", "other")
DOWN_CLASSES = ("both_none", "other")


def flip_class(r):
    """Why A differs from H (None when they agree). Up (H 0, A 1), first rule that applies: the reference answer came
    from the fallback; the output's answer came from the fallback; HELM's boxed answers are the same number written
    differently; the output has no boxed answer and its unboxed final answer is right. Down (H 1, A 0): HELM credited
    the output only because neither side had an extractable answer."""
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


# ----- Ranks and rank agreement (copied unchanged from audit 90, grade90.py) -----

def min_ranks(acc):
    """acc {model: Fraction} -> {model: 1 + number of models with a strictly higher accuracy}."""
    return {m: 1 + sum(1 for o in acc if acc[o] > acc[m]) for m in acc}


def kendall_tau_b(xs, ys):
    """Kendall's tau-b of two equal-length lists; None when either list is constant."""
    conc = disc = tx = ty = 0
    n = len(xs)
    for i in range(n):
        for j in range(i + 1, n):
            dx = (xs[i] > xs[j]) - (xs[i] < xs[j])
            dy = (ys[i] > ys[j]) - (ys[i] < ys[j])
            if dx == 0 and dy == 0:
                continue
            if dx == 0:
                tx += 1
            elif dy == 0:
                ty += 1
            elif dx == dy:
                conc += 1
            else:
                disc += 1
    denom = ((conc + disc + tx) * (conc + disc + ty)) ** 0.5
    return (conc - disc) / denom if denom else None


# ----- Pre-registered verdicts P2-P7 (P1 is decided in job.py; P8 is graded by reading, next run) -----

def predictions91(net, n_pred, unboxed_up, value_up, n_gold_none, moved, up, down, th):
    """net: A-correct minus H-correct over all included predictions (n_pred of them); unboxed_up, value_up: up-flips
    of class unboxed and value_format; n_gold_none: reference solutions with no answer HELM can extract; moved: models
    whose macro-accuracy rank moves by at least th['P6_min_move'] places; up, down: flip counts."""
    return {
        "P2_net_rescues": bool(n_pred > 0 and net * th["P2_den"] >= n_pred * th["P2_num"]),
        "P3_unboxed_rescues": unboxed_up >= th["P3_min_unboxed"],
        "P4_value_rescues": value_up >= th["P4_min_value"],
        "P5_gold_unextractable": n_gold_none >= th["P5_min_gold_none"],
        "P6_rank_moves": moved >= th["P6_min_models"],
        "P7_down_flips_rare": bool(up > 0 and th["P7_ratio"] * down <= up),
    }


# ----- HELM Lite run selection: one run per (model, subject) -----

def _version(s):
    out = []
    for p in (s or "").lstrip("v").split("."):
        try:
            out.append(int(p))
        except ValueError:
            out.append(-1)
    return tuple(out)


def run_part(run, key):
    """'math:subject=algebra,...,model=x_y' -> value of `key` (None if absent)."""
    body = run.split(":", 1)[1] if ":" in run else run
    for part in body.split(","):
        if part.startswith(key + "="):
            return part[len(key) + 1:]
    return None


def select_runs(run_suites, prefix="math:"):
    """One run per (model, subject) among keys starting with `prefix`: the newest suite, then the shortest and
    alphabetically first key (audit 86's rule). Returns ({(model, subject): (run, suite)}, runs dropped)."""
    best, dropped = {}, 0
    for run, suite in run_suites.items():
        if not run.startswith(prefix):
            continue
        m, s = run_part(run, "model"), run_part(run, "subject")
        if m is None or s is None:
            continue
        k, cand = (m, s), (run, suite)
        if k in best:
            dropped += 1
            cur = best[k]
            if (_version(suite), -len(run), [-ord(c) for c in run]) > (_version(cur[1]), -len(cur[0]),
                                                                           [-ord(c) for c in cur[0]]):
                best[k] = cand
        else:
            best[k] = cand
    return best, dropped
