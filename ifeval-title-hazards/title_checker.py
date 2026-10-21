# Faithful reproduction of IFEval's TitleChecker marker test
# (detectable_format:title) from google-research/instruction_following_eval
# (instructions.py). The checker verifies that a response "contains a title,
# wrapped in double angular brackets, such as <<poem of joy>>".
#
# Reproduced verbatim in behaviour: it compiles r"<<[^\n]+>>", findall's every
# match on the value, and returns True as soon as one match has non-empty
# content after stripping angle brackets and whitespace.
#
# The hazard this audit isolates: the marker pattern <<...>> on a single line
# is ALSO ordinary left-shift/right-shift (<<, >>) operator and shell heredoc/
# redirect syntax, so a response that merely contains `a << b >> c` on one line
# is credited with a title it never wrote (a false pass).
#
# No network, no live system. Audit code by AI agents working in MV2's name
# (Munim, Inc.). Apache-2.0.

import re

_PATTERN = re.compile(r"<<[^\n]+>>")


def check_title(value):
    """Return True iff IFEval's TitleChecker would accept `value` as containing
    a double-angle-bracket title. Faithful to the upstream check_following."""
    titles = re.findall(_PATTERN, value)
    for title in titles:
        if title.lstrip("<").rstrip(">").strip():
            return True
    return False


def classify(value, intended_is_title):
    """Compare the checker's verdict with the intended semantic (does the text
    actually present a deliberate title?). Returns one of:
    'match'      -- checker True  and a real title is present;
    'correct_neg'-- checker False and no title is present;
    'false_pass' -- checker True  but no title is present (marker came from
                    shift/redirect operators or similar);
    'false_fail' -- checker False but a real title is present."""
    verdict = check_title(value)
    if verdict and intended_is_title:
        return "match"
    if (not verdict) and (not intended_is_title):
        return "correct_neg"
    if verdict and not intended_is_title:
        return "false_pass"
    return "false_fail"
