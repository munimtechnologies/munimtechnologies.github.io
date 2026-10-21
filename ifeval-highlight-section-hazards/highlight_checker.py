# Faithful reproduction of IFEval's HighlightSectionChecker
# (detectable_format:number_highlighted_sections) from
# google-research/instruction_following_eval (instructions.py). The checker
# verifies a response highlights at least `num_highlights` sections in markdown,
# "such as *highlighted section*".
#
# Reproduced verbatim in behaviour (confirmed against upstream instructions.py):
#   singles = re.findall(r"\*[^\n\*]*\*", value)  -> count each whose
#             highlight.strip("*").strip() is non-empty;
#   doubles = re.findall(r"\*\*[^\n\*]*\*\*", value) -> count each whose
#             removeprefix("**").removesuffix("**").strip() is non-empty;
#   num_highlights = (counted singles) + (counted doubles);
#   pass iff num_highlights >= self._num_highlights.
#
# The hazard this audit isolates: a SINGLE markdown bold-italic span written
# with three asterisks, "***text***", is ONE visual highlighted section, but it
# is matched BOTH as a single "*text*" (once the leading "**" is consumed as an
# empty "**") AND as a double "**text**", so the checker credits it as 2. A
# response that highlights one span with "***...***" therefore satisfies a
# "highlight at least 2 sections" instruction it did not really meet
# (an over-count false pass).
#
# No network, no live system. Audit code by AI agents working in MV2's name
# (Munim, Inc.). Apache-2.0.

import re

_SINGLE = re.compile(r"\*[^\n\*]*\*")
_DOUBLE = re.compile(r"\*\*[^\n\*]*\*\*")
# A single markdown bold-italic span: exactly three asterisks, inner content
# with no asterisk or newline, three asterisks. Each such span is ONE visual
# highlight but is counted twice by the upstream checker.
_TRIPLE = re.compile(r"\*\*\*[^\n\*]+\*\*\*")


def count_highlights(value):
    """Reproduce the upstream num_highlights count for `value`."""
    num = 0
    for highlight in re.findall(_SINGLE, value):
        if highlight.strip("*").strip():
            num += 1
    for highlight in re.findall(_DOUBLE, value):
        if highlight.removeprefix("**").removesuffix("**").strip():
            num += 1
    return num


def count_triple_spans(value):
    """Number of '***text***' bold-italic spans: each inflates the checker count
    by exactly 1 (counted once as a single and once as a double)."""
    return len(re.findall(_TRIPLE, value))


def corrected_count(value):
    """A count that treats each '***text***' span as ONE highlight instead of
    two. corrected = upstream count - (one excess per triple span)."""
    return count_highlights(value) - count_triple_spans(value)


def check_following(value, num_required):
    """Upstream pass condition: num_highlights >= num_required."""
    return count_highlights(value) >= num_required


def classify(value, num_required, intended_true_count):
    """Compare the checker's pass/fail with the ground-truth number of
    deliberately highlighted sections. Returns:
    'match'       -- checker passes and the response really meets the quota;
    'correct_neg' -- checker fails and the response really does not meet it;
    'false_pass'  -- checker passes but the response does NOT really meet the
                     quota (over-count let it through);
    'false_fail'  -- checker fails but the response really meets the quota."""
    checker_pass = check_following(value, num_required)
    true_pass = intended_true_count >= num_required
    if checker_pass and true_pass:
        return "match"
    if (not checker_pass) and (not true_pass):
        return "correct_neg"
    if checker_pass and not true_pass:
        return "false_pass"
    return "false_fail"
