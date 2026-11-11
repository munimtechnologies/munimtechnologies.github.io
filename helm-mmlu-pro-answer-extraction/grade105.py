"""Audit 105 helpers: does HELM Capabilities' MMLU-Pro column read the answer each model actually stated?

HELM Capabilities scores MMLU-Pro (and GPQA) with GPQAChainOfThoughtMetric (gpqa_chain_of_thought_metric.py). Its
extract_answer() tries four regexes in order and returns the FIRST match of the first regex that matches:
  1. "answer is \\(?([A-J])\\)?"                  (first occurrence anywhere in the output)
  2. "\\.*\\[aA\\]nswer:\\s*\\(?([A-J])\\)?"         (escaped brackets: matches only the literal text "[aA]nswer:";
                                                  HELM PR #4323, open, proposes the unescaped "[aA]nswer:")
  3. "correct answer is [^A-Za-z]*([A-J])"        (added by HELM PR #3420, 2025-03-10)
  4. "correct answer is [^A-Z]*([A-J])"           (added by HELM PR #3445, 2025-03-18)
The prompt asks the model to finish with 'The correct answer is (insert answer here)'. An answer written as
"The final answer is $\\boxed{C}$", "**Answer:** C" or "Answer: C" matches none of the four and is scored 0 even when
C is the gold; an earlier "answer is X" in the reasoning wins over the final statement; and regex 1 also reads the
first capital of a word ("the answer is Because ..." -> B).

This module transcribes the scorer (versions v2 = regexes 1-2, v3 = 1-3, v4 = 1-4 as on HELM main, and pr4323 = v4
with regex 2 unescaped) and a "stated answer" grade: the LAST explicit answer statement in the output, either
"answer is X" / "answer: X" (letter A-J not followed by a letter or digit; optional "option"/"choice", "(", "**")
or "\\boxed{X}" (optionally "\\text{...}" / "\\textbf{...}" and a parenthesis inside).
Standard library only. Apache-2.0. Authored by AI agents working in the name of MV2, Munim, Inc.
"""

import hashlib
import math
import re

# ----- HELM's extract_answer, transcribed (gpqa_chain_of_thought_metric.py) -----

R1 = r"answer is \(?([A-J])\)?"
R2_ESCAPED = r"\.*\[aA\]nswer:\s*\(?([A-J])\)?"
R2_FIXED = r"\.*[aA]nswer:\s*\(?([A-J])\)?"
R3 = r"correct answer is [^A-Za-z]*([A-J])"
R4 = r"correct answer is [^A-Z]*([A-J])"

VERSIONS = {
    "v2": [R1, R2_ESCAPED],
    "v3": [R1, R2_ESCAPED, R3],
    "v4": [R1, R2_ESCAPED, R3, R4],
    "pr4323": [R1, R2_FIXED, R3, R4],
}
# Versions HELM may have scored a release with, newest first (ties in reproduction go to the newest).
SCORER_VERSIONS = ("v4", "v3", "v2")


def helm_extract(text, version="v4"):
    """(letter, rule, spurious): HELM's extracted letter (None if no regex matches), the 1-based index of the regex
    that matched (0 if none), and whether regex 1 took the first capital of a word (the letter is followed by a
    lowercase letter, e.g. 'answer is Because')."""
    text = text or ""
    for i, pat in enumerate(VERSIONS[version], 1):
        m = re.search(pat, text)
        if m:
            nxt = text[m.end(1)] if m.end(1) < len(text) else ""
            return m.group(1), i, (i == 1 and nxt.islower())
    return None, 0, False


# ----- The stated-answer grade: the last explicit answer statement -----

# Possessive quantifiers (Python 3.11+) keep long runs of spaces or asterisks from backtracking.
STATED_PATTERNS = (
    ("boxed", re.compile(r"\\boxed\s*+\{\s*+(?:\\text(?:bf)?\s*+\{\s*+)?\(?\s*+([A-J])(?![A-Za-z0-9])")),
    ("phrase", re.compile(r"\b(?:[Aa]nswer|ANSWER)(?:\s+(?:is|IS)|[\*_]*\s*:)[\s\*_:]*+"
                          r"(?:(?:[Oo]ption|[Cc]hoice)\s+)?\(?[\*_]*+([A-J])(?![A-Za-z0-9])")),
)


def stated_answer(text):
    """(letter, form) of the last explicit answer statement (largest start position), or (None, None)."""
    best = None
    for form, pat in STATED_PATTERNS:
        for m in pat.finditer(text or ""):
            if best is None or m.start() > best[0]:
                best = (m.start(), m.group(1), form)
    return (best[1], best[2]) if best else (None, None)


# ----- One record -----


def gold_letter(references):
    """Letter of the first reference tagged 'correct' (HELM: chr(65 + index)); None if none."""
    for i, r in enumerate(references or []):
        if isinstance(r, dict) and "correct" in (r.get("tags") or []):
            return chr(65 + i)
    return None


def record_class(h_letter, h_rule, h_spur, s_letter, s_form, gold):
    """Class of one record from HELM's extraction (h_*) and the stated answer (s_*)."""
    h = h_letter is not None and h_letter == gold
    s = s_letter is not None and s_letter == gold
    if h and s:
        return "both_right"
    if not h and not s:
        return "both_wrong"
    if s:
        return ("up_" + s_form) if h_letter is None else "up_other_letter"
    if h_spur:
        return "down_spurious_capital"
    if h_rule in (3, 4):
        return "down_fallback"
    if s_letter is None:
        return "down_no_statement"
    return "down_other_letter"


def grade_record(text, gold):
    """Everything the audit needs about one output: HELM's letter under each version, the stated answer, credits."""
    ext = {v: helm_extract(text, v) for v in VERSIONS}
    s_letter, s_form = stated_answer(text)
    return {"gold": gold, "ext": ext, "s_letter": s_letter, "s_form": s_form,
            "credit": {v: 1 if ext[v][0] is not None and ext[v][0] == gold else 0 for v in VERSIONS},
            "stated_credit": 1 if s_letter is not None and s_letter == gold else 0}


# ----- One run -----


def golds_by_id(instances):
    """{instance id: gold letter} from a HELM instances.json list (unperturbed instances only)."""
    out = {}
    for inst in instances or []:
        if not isinstance(inst, dict) or inst.get("perturbation") is not None:
            continue
        iid = inst.get("id")
        if iid is not None and iid not in out:
            out[iid] = gold_letter(inst.get("references"))
    return out


def _num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def summarize_run(predictions, golds, tail_chars=160):
    """Grade every unperturbed display prediction (first per (instance id, trial)).
    counts: request bookkeeping; records: compact per-record dicts (key, gold, ext, stated, stored, tail);
    mismatch: per scorer version, records whose stored chain_of_thought_correctness differs from that version's credit;
    stored_n: records with a stored score."""
    counts = {"predictions": 0, "perturbed": 0, "duplicate": 0, "no_gold": 0, "kept": 0}
    seen, records = set(), []
    mismatch = {v: 0 for v in VERSIONS}
    stored_n = 0
    for p in predictions or []:
        if not isinstance(p, dict):
            continue
        counts["predictions"] += 1
        if p.get("perturbation") is not None:
            counts["perturbed"] += 1
            continue
        key = (p.get("instance_id"), p.get("train_trial_index", 0))
        if key in seen:
            counts["duplicate"] += 1
            continue
        seen.add(key)
        gold = golds.get(key[0])
        if gold is None:
            counts["no_gold"] += 1
            continue
        text = p.get("predicted_text") or ""
        g = grade_record(text, gold)
        stored = _num(((p.get("stats") or {}).get("chain_of_thought_correctness")))
        if stored is not None:
            stored_n += 1
            for v in VERSIONS:
                if abs(g["credit"][v] - stored) > 1e-9:
                    mismatch[v] += 1
        counts["kept"] += 1
        g.update({"key": key, "stored": stored, "tail": text[-tail_chars:], "chars": len(text)})
        records.append(g)
    return {"counts": counts, "records": records, "mismatch": mismatch, "stored_n": stored_n}


def choose_version(mismatch):
    """The scorer version with the fewest mismatches against the stored scores (ties -> newest)."""
    return min(SCORER_VERSIONS, key=lambda v: (mismatch.get(v, math.inf), SCORER_VERSIONS.index(v)))


def run_mean(records, credit_of):
    """HELM's run value: mean over trials of each trial's mean credit (None without records)."""
    trials = {}
    for r in records:
        t = trials.setdefault(r["key"][1], [0, 0])
        t[0] += credit_of(r)
        t[1] += 1
    vs = [a / n for a, n in (trials[k] for k in sorted(trials)) if n]
    return sum(vs) / len(vs) if vs else None


def class_counts(records, version):
    out = {}
    for r in records:
        h_letter, h_rule, h_spur = r["ext"][version]
        c = record_class(h_letter, h_rule, h_spur, r["s_letter"], r["s_form"], r["gold"])
        out[c] = out.get(c, 0) + 1
    return out


def pr_up(records, version):
    """Records PR #4323's scorer credits that the reproducing version does not (and the reverse)."""
    up = sum(1 for r in records if r["credit"]["pr4323"] == 1 and r["credit"][version] == 0)
    down = sum(1 for r in records if r["credit"]["pr4323"] == 0 and r["credit"][version] == 1)
    return up, down


# ----- Run names and HELM files -----


def is_mmlu_pro(run):
    return run.startswith("mmlu_pro:")


def model_part(name):
    i = name.find("model=")
    return name[i + len("model="):] if i >= 0 else ""


def select_runs(run_suites):
    return {r: s for r, s in (run_suites or {}).items() if is_mmlu_pro(r)}


def stat_entry(stats, name, split):
    """{count, sum, mean} of the unperturbed stat `name` on `split` in a HELM stats.json list (None when absent)."""
    for s in stats or []:
        if not isinstance(s, dict):
            continue
        nm = s.get("name") or {}
        if (nm.get("name") == name and nm.get("split") == split and nm.get("perturbation") is None
                and nm.get("sub_split") is None):
            return {"count": s.get("count"), "sum": s.get("sum"), "mean": s.get("mean")}
    return None


def group_values(group_doc, prefix):
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
        if isinstance(row, list) and len(row) > col and isinstance(row[col], dict):
            v = row[col].get("value")
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out.append(float(v))
    return out


# ----- Ranks, matching, summaries -----


def ranks_high(values):
    """Higher is better: rank = 1 + the number of entries strictly higher."""
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


# ----- Verdicts -----

FLASH_LITE = "google_gemini-2.5-flash-lite"


def verdicts(s):
    """The eight pre-registered predictions (True = HELD) from the job's pooled statistics `s`."""
    return {
        "P1": (bool(s["fixtures"]) and s["runs_listed"] > 0 and s["runs_included"] * 10 >= 9 * s["runs_listed"]
               and s["cells"] > 0 and s["matched"] * 10 >= 9 * s["cells"]),
        "P2": s["flash_lite_gain"] is not None and s["flash_lite_gain"] >= 0.10 - 1e-12,
        "P3": s["gainers_other"] >= 3,
        "P4": s["up"] > 0 and s["up"] >= 3 * s["down"],
        "P5": s["up_boxed"] > s["up_phrase"] and s["up_boxed"] > s["up_other_letter"],
        "P6": s["up"] > 0 and 4 * s["pr_up"] < s["up"],
        "P7": s["movers"] >= 3 and s["tau"] is not None and s["tau"] >= 0.9,
        "P8": s["gemini_other_gainers"] >= 2,
    }
