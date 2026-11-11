"""Audit 104 helpers: is HELM Classic's BoolQ calibration (ECE) computed from the answer's probability?

HELM Classic (release v0.4.0) publishes "ECE (10-bin)" for BoolQ. Its per-record confidence is
max_prob = exp(logprob of the top completion) (basic_metrics.py), and ECE is the equal-mass 10-bin expected
calibration error of max_prob against exact_match (uncertainty-calibration's get_ece_em), once per trial over the
unperturbed records, then averaged over trials.

Some providers return the answer text cut at the stop sequence ("\\n") but a token list, and a summed log probability,
that run past it up to max_tokens (for example " Yes", "\\n", "\\n", "Pass", "age"). HELM's client-side
truncate_sequence leaves such a completion unchanged: the returned text has no stop sequence left to find, and
byte-level token strings ("\\u010a" for a newline) never start with "\\n". The confidence that enters ECE is then the
probability of the answer AND the tokens generated after it.

Per record:  P = HELM's max_prob (exp of the stored completion log probability; reproduces the published ECE);
             T = exp(sum of the log probabilities of the tokens before the first one whose decoded text reaches a
                 stop sequence), i.e. the probability of the answer that was scored. T = P when nothing is past the
                 stop.
Standard library only. Apache-2.0. Authored by AI agents working in the name of MV2, Munim, Inc.
"""

import bisect
import hashlib
import math
import re

# ----- Token text -> bytes (GPT-2 byte-level BPE, SentencePiece, AI21 newline token) -----


def _bytes_to_unicode():
    """GPT-2's byte <-> printable-character table (openai/gpt-2 encoder.py), returned as char -> byte."""
    bs = list(range(ord("!"), ord("~") + 1)) + list(range(ord("\xa1"), ord("\xac") + 1)) + \
        list(range(ord("\xae"), ord("\xff") + 1))
    cs = bs[:]
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b)
            cs.append(256 + n)
            n += 1
    return {chr(c): b for b, c in zip(bs, cs)}


BYTE_DECODER = _bytes_to_unicode()
_BYTE_TOKEN = re.compile(r"<0x([0-9A-Fa-f]{2})>")


def token_bytes(t):
    """Bytes of one token string as HELM stored it: '<0xHH>' byte tokens, '<|newline|>' -> newline, SentencePiece
    '\\u2581' -> space, GPT-2 byte characters ('\\u0120' space, '\\u010a' newline) -> their byte, anything else -> UTF-8."""
    m = _BYTE_TOKEN.fullmatch(t or "")
    if m:
        return bytes([int(m.group(1), 16)])
    out = bytearray()
    for ch in (t or "").replace("<|newline|>", "\n"):
        if ch == "▁":
            out += b" "
        elif ch in BYTE_DECODER:
            out.append(BYTE_DECODER[ch])
        else:
            out += ch.encode("utf-8")
    return bytes(out)


def decode_tokens(texts):
    return b"".join(token_bytes(t) for t in texts).decode("utf-8", "replace")


def keep_count(texts, stops):
    """Number of leading tokens kept: the largest k whose decoded prefix contains no stop sequence."""
    stops = [s for s in (stops or []) if s]
    if not stops:
        return len(texts)
    for k in range(1, len(texts) + 1):
        d = decode_tokens(texts[:k])
        if any(s in d for s in stops):
            return k - 1
    return len(texts)


# ----- HELM's exact_match and one record -----


def exact_match(gold, pred):
    if not pred:
        return 0
    return 1 if gold.strip() == pred.strip() else 0


def golds_of_instance(inst):
    return [((r.get("output") or {}).get("text") or "") for r in (inst or {}).get("references") or []
            if isinstance(r, dict) and "correct" in (r.get("tags") or [])]


def _num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else 0.0


def top_completion(rs):
    """HELM's scored completion (stable sort by -logprob): {text, logprob, tokens [(text, logprob)]}; None if none."""
    comps = [c for c in (((rs or {}).get("result") or {}).get("completions") or []) if isinstance(c, dict)]
    if not comps:
        return None
    c = sorted(comps, key=lambda x: -_num(x.get("logprob")))[0]
    toks = [((t or {}).get("text") or "", _num((t or {}).get("logprob"))) for t in (c.get("tokens") or [])]
    return {"text": c.get("text") or "", "logprob": _num(c.get("logprob")), "tokens": toks}


def score_record(golds, comp, stops):
    """None without golds or completion. em = HELM's exact_match of the stripped top completion (max over golds);
    p = HELM's max_prob; t = the answer-only probability; overrun = tokens past the stop; excess = stored log
    probability minus the answer-only one (0.0 without overrun); consistent = the kept tokens decode to the stored
    text (both stripped); kept / n_tokens = token counts."""
    if not golds or comp is None:
        return None
    pred = comp["text"].strip()
    em = max(exact_match(g, pred) for g in golds)
    p = min(1.0, math.exp(comp["logprob"]))
    texts = [t for t, _ in comp["tokens"]]
    k = keep_count(texts, stops)
    overrun = k < len(texts)
    if overrun:
        tl = sum(lp for _, lp in comp["tokens"][:k])
        t = min(1.0, math.exp(tl))
        excess = comp["logprob"] - tl
    else:
        t, excess = p, 0.0
    return {"em": em, "p": p, "t": t, "overrun": overrun, "excess": excess,
            "consistent": decode_tokens(texts[:k]).strip() == pred, "kept": k, "n_tokens": len(texts)}


# ----- One run -----

EVAL_SPLITS = ("valid", "test")
REC_KEYS = ("overrun", "consistent", "overrun_consistent", "tokens")


def stops_of(state):
    return list(((state or {}).get("adapter_spec") or {}).get("stop_sequences") or [])


def summarize_run(state, cap_samples=2):
    """Score every unperturbed eval-split request state of one run (first per (instance id, trial)).
    trials {trial: {p: [...], t: [...], y: [...]}}; rec: record counts; excess: per overrun record; splits: kept
    records per split; samples: up to cap_samples overrun records (for the job log only)."""
    stops = stops_of(state)
    counts = {"request_states": 0, "perturbed": 0, "not_eval": 0, "duplicate": 0, "no_result": 0, "kept": 0}
    rec = {k: 0 for k in REC_KEYS}
    trials, seen, excess, splits, samples = {}, set(), [], {}, []
    for rs in (state or {}).get("request_states") or []:
        if not isinstance(rs, dict):
            continue
        counts["request_states"] += 1
        inst = rs.get("instance") or {}
        if inst.get("perturbation") is not None:
            counts["perturbed"] += 1
            continue
        if inst.get("split") not in EVAL_SPLITS:
            counts["not_eval"] += 1
            continue
        key = (inst.get("id"), rs.get("train_trial_index", 0))
        if key in seen:
            counts["duplicate"] += 1
            continue
        seen.add(key)
        comp = top_completion(rs)
        s = score_record(golds_of_instance(inst), comp, stops)
        if s is None:
            counts["no_result"] += 1
            continue
        counts["kept"] += 1
        splits[inst.get("split")] = splits.get(inst.get("split"), 0) + 1
        acc = trials.setdefault(key[1], {"p": [], "t": [], "y": []})
        acc["p"].append(s["p"])
        acc["t"].append(s["t"])
        acc["y"].append(s["em"])
        rec["tokens"] += s["n_tokens"]
        rec["consistent"] += 1 if s["consistent"] else 0
        if s["overrun"]:
            rec["overrun"] += 1
            rec["overrun_consistent"] += 1 if s["consistent"] else 0
            excess.append(s["excess"])
            if len(samples) < cap_samples:
                samples.append({"key": key, "text": comp["text"], "tokens": [t for t, _ in comp["tokens"]],
                                "kept": s["kept"], "stored_lp": comp["logprob"], "p": s["p"], "t": s["t"],
                                "em": s["em"]})
    return {"counts": counts, "trials": trials, "rec": rec, "excess": excess, "splits": splits, "samples": samples,
            "stops": stops}


def run_class(overrun, n):
    """'overrun' when at least half of the records carry tokens past the stop, else 'clean'; None without records."""
    if not n:
        return None
    return "overrun" if 2 * overrun >= n else "clean"


# ----- Equal-mass ECE (uncertainty-calibration get_ece_em, p=1, top-label on 1-D probabilities), transcribed -----


def equal_mass_bins(probs, num_bins=10):
    """get_equal_bins: sort, np.array_split into min(num_bins, n) chunks (the first n % k one longer), boundaries at
    the midpoints between chunks, then 1.0; de-duplicated and sorted."""
    s = sorted(probs)
    n = len(s)
    k = min(num_bins, n)
    q, r = divmod(n, k)
    chunks, i = [], 0
    for j in range(k):
        size = q + (1 if j < r else 0)
        chunks.append(s[i:i + size])
        i += size
    bins = [(chunks[j][-1] + chunks[j + 1][0]) / 2.0 for j in range(k - 1)]
    bins.append(1.0)
    return sorted(set(bins))


def ece_em(probs, labels, num_bins=10):
    """Bin-size-weighted mean of |mean prob - mean label| over equal-mass bins (bin = np.searchsorted left)."""
    n = len(probs)
    if not n:
        return None
    bins = equal_mass_bins(probs, num_bins)
    acc = {}
    for p, y in zip(probs, labels):
        b = min(bisect.bisect_left(bins, p), len(bins) - 1)
        a = acc.setdefault(b, [0.0, 0.0])
        a[0] += p
        a[1] += y
    return sum(abs(acc[b][0] - acc[b][1]) for b in sorted(acc)) / n


def run_ece(trials, key, num_bins=10):
    """HELM's run value: the mean over trials of each trial's ECE (None without trials)."""
    vs = [ece_em(v[key], v["y"], num_bins) for _, v in sorted(trials.items()) if v["y"]]
    return sum(vs) / len(vs) if vs else None


def run_em(trials):
    vs = [sum(v["y"]) / len(v["y"]) for _, v in sorted(trials.items()) if v["y"]]
    return sum(vs) / len(vs) if vs else None


# ----- Run names and HELM files -----

def _parts(run):
    return run.split(":", 1)[1].split(",") if ":" in run else run.split(",")


def is_boolq_canonical(run):
    return run.startswith("boolq:") and "data_augmentation=canonical" in _parts(run)


def adapter_of(run):
    """The run name's parts without data_augmentation=canonical: one HELM table row per adapter."""
    return ",".join(p for p in _parts(run) if p != "data_augmentation=canonical")


def model_part(name):
    i = name.find("model=")
    return name[i + len("model="):] if i >= 0 else ""


def select_runs(run_suites):
    return {r: s for r, s in (run_suites or {}).items() if is_boolq_canonical(r)}


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


def slim_hook(d):
    """json object_hook that drops what the audit never reads (prompts, instance inputs, top_logprobs)."""
    d.pop("prompt", None)
    d.pop("top_logprobs", None)
    if "references" in d and "input" in d:
        d.pop("input")
    return d


# ----- Ranks, matching, summaries -----


def ranks_low(values):
    """Lower is better: rank = 1 + the number of entries strictly lower."""
    return {k: 1 + sum(1 for w in values.values() if w < v) for k, v in values.items()}


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


def group_values(group_doc, name):
    """Numeric values of the column whose header is exactly `name` in a group page's first table."""
    if not isinstance(group_doc, list) or not group_doc or not isinstance(group_doc[0], dict):
        return None
    t = group_doc[0]
    header = t.get("header") or []
    col = next((j for j, h in enumerate(header) if isinstance(h, dict) and str(h.get("value") or "") == name), None)
    if col is None:
        return None
    out = []
    for row in t.get("rows") or []:
        if isinstance(row, list) and len(row) > col and isinstance(row[col], dict):
            v = row[col].get("value")
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out.append(float(v))
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


def median(xs):
    s = sorted(xs)
    n = len(s)
    if not n:
        return None
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def stable_hash(text):
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:12], 16)


# ----- Verdicts -----

def verdicts(s):
    """The eight pre-registered predictions (True = HELD) from the job's pooled statistics `s`."""
    oa = s["overrun_adapters"]
    return {
        "P1": (bool(s["fixtures"]) and s["runs_with_ece"] > 0 and s["runs_included"] * 10 >= 9 * s["runs_with_ece"]
               and s["cells"] >= 55 and s["matched"] * 10 >= 9 * s["cells"]),
        "P2": oa >= 8,
        "P3": oa > 0 and 2 * s["excess_hits"] >= oa,
        "P4": oa > 0 and 2 * s["delta_hits"] >= oa,
        "P5": s["overrun_records"] > 0 and s["overrun_consistent"] * 20 >= 19 * s["overrun_records"],
        "P6": s["movers"] >= 3,
        "P7": s["tau"] is not None and s["tau"] >= 0.8,
        "P8": s["better"] > s["worse"],
    }
