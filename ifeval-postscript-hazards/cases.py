# Pre-registered labelled corpus for the ifeval-postscript-hazards audit.
#
# Every case uses the postscript marker "P.S." (IFEval's most common postscript
# marker). `shipped_expected` / `intended_expected` were hand-traced against the
# two regexes in postscript_checker.py BEFORE any code was run; the sealed
# compute job re-derives them and asserts the aggregate corpus matches the
# pre-registered target in job.py.
#
# Labelled corpus by AI agents working in MV2's name (Munim, Inc.). CC BY 4.0.

MARKER = "P.S."

# id, text, shipped_expected, intended_expected, kind, note
CASES = [
    (
        "P1-inline-false-pass",
        "I think p.s. stands for postscript in formal writing.",
        True,
        False,
        "false_pass",
        "Inline 'p.s.' mid-sentence. No ^ anchor, so the shipped pattern finds "
        "it and passes a response that contains no actual postscript.",
    ),
    (
        "P2-PS-no-dots-false-fail",
        "PS I forgot to mention the meeting is at noon.",
        False,
        True,
        "false_fail",
        "'PS' with no dots is a legitimate postscript spelling, but the shipped "
        "pattern hard-codes 'p.' and 's.' literal dots, so it fails.",
    ),
    (
        "P3-one-dot-false-fail",
        "P.S I will call you tomorrow afternoon.",
        False,
        True,
        "false_fail",
        "'P.S' (no trailing dot) is a legitimate spelling; the shipped pattern "
        "requires 's.' so it fails.",
    ),
    (
        "P4-colon-false-fail",
        "P.S: remember to bring the signed documents.",
        False,
        True,
        "false_fail",
        "'P.S:' with a colon is a legitimate spelling; the shipped pattern "
        "requires 's.' so it fails.",
    ),
    (
        "P5-canonical-control",
        "P.S. Thanks again for all your help.",
        True,
        True,
        "control_pass",
        "Canonical 'P.S.' at line start. Both pass; control.",
    ),
    (
        "P6-psychology-control",
        "Psychology is a fascinating field of study.",
        False,
        False,
        "control_fail",
        "'Psychology' starts with 'ps'. Both fail; the intended guard "
        "(?![a-z]) keeps it from matching. Control.",
    ),
]
