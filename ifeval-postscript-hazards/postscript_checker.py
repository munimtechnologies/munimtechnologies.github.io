# Postscript checkers for the ifeval-postscript-hazards audit.
#
# `shipped_check` transcribes IFEval's PostscriptChecker.check_following exactly
# (google-research/instruction_following_eval/instructions.py, class
# PostscriptChecker). That upstream code is Apache-2.0 and keeps its own licence.
# `intended_check` is MV2's proposed line-anchored, dot-tolerant variant, used
# only to decide, per case, whether the shipped verdict is a false pass or a
# false fail. Nothing here is run against any live system.
#
# Audit code by AI agents working in MV2's name (Munim, Inc.). Apache-2.0.

import re


def shipped_check(value: str, marker: str) -> bool:
    """IFEval's PostscriptChecker, transcribed verbatim.

    No `^` anchor: `\\s*` matches whitespace anywhere, so the marker is found
    even mid-line. The P.S./P.P.S branches hard-code literal dots, so common
    spellings ("PS", "P.S", "P.S:") never match.
    """
    value = value.lower()
    if marker == "P.P.S":
        postscript_pattern = r"\s*p\.\s?p\.\s?s.*$"
    elif marker == "P.S.":
        postscript_pattern = r"\s*p\.\s?s\..*$"
    else:
        postscript_pattern = r"\s*" + marker.lower() + r".*$"
    postscript = re.findall(postscript_pattern, value, flags=re.MULTILINE)
    return True if postscript else False


def intended_check(value: str, marker: str) -> bool:
    """MV2's proposed fix: anchor to line start, make dots optional, guard
    against a letter immediately after (so "Psychology" is not a postscript).
    """
    value = value.lower()
    if marker == "P.P.S":
        postscript_pattern = r"^\s*p\.?\s?p\.?\s?s\.?(?![a-z])"
    elif marker == "P.S.":
        postscript_pattern = r"^\s*p\.?\s?s\.?(?![a-z])"
    else:
        postscript_pattern = r"^\s*" + re.escape(marker.lower())
    postscript = re.findall(postscript_pattern, value, flags=re.MULTILINE)
    return True if postscript else False
