# SPDX-License-Identifier: Apache-2.0
# Audit 117 (desk check) by MV2 of Munim, Inc.: HELM ConvFinQACalc scoring.
# Made with AI agents working in MV2's name.
#
# _strip_string and float_equiv are transcribed from HELM's
# src/helm/benchmark/metrics/conv_fin_qa_calc_metrics.py at commit 0d02c1b
# (2025-08-27, the last commit to touch the file). HELM is Apache-2.0
# (Stanford CRFM). The hwarn() call is left out; it does not change the result.
"""HELM ConvFinQACalc: the scorer and the token budget it is paired with.

HELM's run spec get_conv_fin_qa_calc_spec() calls get_generation_adapter_spec()
without max_tokens, so every answer is cut at the default of 5 tokens (stop
sequence "\\n", 5 in-context examples). float_equiv() reads only the FIRST number
in the answer and the gold and credits a difference below 1e-6. ConvFinQA's gold
exe_ans is rounded to 5 decimals, so a fraction such as 0.14136 must be written
in full. A tokenizer that gives every digit its own token (LLaMA 1 and Llama 2:
Touvron et al. 2023) needs at least 6 tokens for ".14136".
"""
import re

MAX_TOKENS = 5  # get_generation_adapter_spec() default; the ConvFinQACalc run spec does not set it
EPS = 1e-6


# ---- transcribed from HELM (Apache-2.0) ----
def _strip_string(str):  # noqa: A002 (name kept as in HELM)
    # from https://stackoverflow.com/a/4703508
    numeric_const_pattern = r"[-+]?(?:(?:\d*\.\d+)|(?:\d+\.?))(?:[Ee][+-]?\d+)?"
    match = re.search(numeric_const_pattern, str)
    if match:
        try:
            return float(str[match.start() : match.end()])
        except Exception:
            return None
    return None


def float_equiv(str1, str2, eps=EPS):
    try:
        ss1 = _strip_string(str1)
        ss2 = _strip_string(str2)

        if ss1 is None or ss2 is None:
            # HELM: hwarn("float_equiv returning 1.0 because both values are non-floats")
            return 0.0
        return float(abs(ss1 - ss2) < eps)
    except Exception:
        return float(str1 == str2)


# ---- audit helpers (ours) ----
def natural_form(gold):
    """The gold as a model would naturally write it: str(exe_ans) without a trailing '.0'."""
    if re.fullmatch(r"-?\d+\.0", gold):
        return gold[:-2]
    return gold


def shortest_form(gold):
    """Shortest fixed-point decimal that float_equiv credits for this gold, with the
    leading zero of 0.x dropped (HELM's pattern reads '.14136' and '-.5').
    None when the gold holds no number (then nothing can ever be credited)."""
    g = _strip_string(gold)
    if g is None:
        return None
    for d in range(0, 13):
        c = f"{g:.{d}f}"
        if float_equiv(c, gold) == 1.0:
            break
    else:
        return None
    if float(c) == 0.0:
        return "0"
    if c.startswith("0."):
        c = c[1:]
    elif c.startswith("-0."):
        c = "-" + c[2:]
    return c


def digit_split_min_tokens(s):
    """Lower bound on the token count of s for a tokenizer that gives every digit its
    own token: each digit is one token, and a run of non-digit characters between
    digits is at least one more (it cannot merge across a digit)."""
    digits = len(re.findall(r"[0-9]", s))
    runs = len(re.findall(r"[^0-9]+", s))
    return digits + runs


def digit_split_truncate(s, k=MAX_TOKENS):
    """Best case for a digit-splitting tokenizer: one token per digit, each run of
    non-digits merged into one token; keep the first k tokens."""
    tokens = re.findall(r"[0-9]|[^0-9]+", s)
    return "".join(tokens[:k])


def reachable_digit_split(gold, k=MAX_TOKENS):
    """Can a digit-splitting model be credited at all within k tokens?"""
    s = shortest_form(gold)
    return s is not None and digit_split_min_tokens(s) <= k


EXAMPLES = [
    # (answer, gold, what it shows)
    ("0.14136", "0.14136", "the gold written in full"),
    ("0.141", "0.14136", "a digit-splitting model's 5-token cut of 0.14136"),
    ("14.136%", "0.14136", "the same ratio written as a percent"),
    ("1,234", "1234.0", "a thousands separator: only the 1 is read"),
    ("In 2009 it was 0.5", "0.5", "a sentence: the year is read"),
    ("-.5", "-0.5", "leading zero dropped"),
    ("yes", "yes", "a yes/no gold: never credited"),
]


def main():
    print("max_tokens:", MAX_TOKENS)
    for answer, gold, why in EXAMPLES:
        print(f"{answer!r:24} gold {gold!r:10} -> {float_equiv(answer, gold):.1f}   ({why})")
    for gold in ["0.14136", "14.1", "1234.5", "12345.0", "206588.0", "-0.0368", "yes"]:
        s = shortest_form(gold)
        lb = None if s is None else digit_split_min_tokens(s)
        print(f"gold {gold!r:10} shortest {s!r:10} digit-split tokens >= {lb}  reachable in 5: {reachable_digit_split(gold)}")


if __name__ == "__main__":
    main()
