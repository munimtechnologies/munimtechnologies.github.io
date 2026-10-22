# gsm8k_socratic_steps.py -- census of whether GSM8K's socratic solutions keep the SAME
# reasoning steps and the SAME <<expr=result>> calculator annotations as the main solutions.
#
# Each socratic line has the form "<sub-question>? ** <step text>". If the socratic file is
# the main file with sub-questions inserted (as the GSM8K paper describes), then removing
# the "<sub-question>? ** " prefix from each socratic line should give back the main lines,
# and the two files should carry the same annotation sequence. This census pairs rows by
# exact question text and counts where that holds and where it does not. It also re-runs
# the calculator-annotation arithmetic check (calc_eval.py, audit 19) on both files.
#
# Authored by AI agents working in MV2's name (Munim, Inc.). Apache-2.0.
# The GSM8K corpus keeps its own licence (Cobbe et al. 2021, openai/grade-school-math, MIT).

from calc_eval import classify_annotation, find_annotations

SEPARATOR = " ** "
CLASSES = ("match", "rounded", "mismatch", "unparseable_expr", "unparseable_result")


def reasoning_lines(answer_text):
    """Return the stripped, non-empty lines before the last '####' marker."""
    head = answer_text.rsplit("####", 1)[0] if "####" in answer_text else answer_text
    return [line.strip() for line in head.split("\n") if line.strip()]


def strip_subquestion(line):
    """Return (step_text, had_separator): the text after the first ' ** ', or the
    whole line unchanged when the line has no separator."""
    if SEPARATOR in line:
        return line.split(SEPARATOR, 1)[1].strip(), True
    return line, False


def _build(rows, question_key, answer_key):
    """{question -> answer} for rows whose question and answer are strings; first wins."""
    mapping = {}
    for r in rows:
        q = r.get(question_key)
        a = r.get(answer_key)
        if isinstance(q, str) and isinstance(a, str):
            mapping.setdefault(q, a)
    return mapping


def annotation_classes(answers):
    """Count calc_eval classes over every annotation in an iterable of answer texts."""
    counts = {c: 0 for c in CLASSES}
    for a in answers:
        for expr, result in find_annotations(a):
            counts[classify_annotation(expr, result)] += 1
    return counts


def census(main_rows, socratic_rows, question_key="question", answer_key="answer",
           max_examples=50):
    main_map = _build(main_rows, question_key, answer_key)
    soc_map = _build(socratic_rows, question_key, answer_key)
    paired = sorted(main_map.keys() & soc_map.keys())

    soc_lines = 0
    soc_lines_with_sep = 0
    step_count_equal = 0
    steps_identical = 0
    annotations_identical = 0
    annotations_differ = 0
    annotation_examples = []
    step_examples = []

    for q in paired:
        main_lines = reasoning_lines(main_map[q])
        stripped = []
        for line in reasoning_lines(soc_map[q]):
            step, had_sep = strip_subquestion(line)
            stripped.append(step)
            soc_lines += 1
            soc_lines_with_sep += 1 if had_sep else 0
        if len(main_lines) == len(stripped):
            step_count_equal += 1
        if main_lines == stripped:
            steps_identical += 1
        elif len(step_examples) < max_examples:
            step_examples.append({"question": q, "main_steps": main_lines,
                                  "socratic_steps": stripped})
        main_ann = find_annotations(main_map[q])
        soc_ann = find_annotations(soc_map[q])
        if main_ann == soc_ann:
            annotations_identical += 1
        else:
            annotations_differ += 1
            if len(annotation_examples) < max_examples:
                annotation_examples.append({
                    "question": q,
                    "main_annotations": ["<<%s=%s>>" % a for a in main_ann],
                    "socratic_annotations": ["<<%s=%s>>" % a for a in soc_ann],
                })

    main_classes = annotation_classes(main_map.values())
    soc_classes = annotation_classes(soc_map.values())
    return {
        "pairs": len(paired),
        "only_in_main": len(main_map.keys() - soc_map.keys()),
        "only_in_socratic": len(soc_map.keys() - main_map.keys()),
        "socratic_lines_in_pairs": soc_lines,
        "socratic_lines_with_separator": soc_lines_with_sep,
        "step_count_equal": step_count_equal,
        "steps_identical": steps_identical,
        "annotations_identical": annotations_identical,
        "annotations_differ": annotations_differ,
        "main_annotations_total": sum(main_classes.values()),
        "socratic_annotations_total": sum(soc_classes.values()),
        "main_annotation_classes": main_classes,
        "socratic_annotation_classes": soc_classes,
        "annotation_diff_examples": annotation_examples,
        "step_diff_examples": step_examples,
    }


def public_summary(result):
    """Integer-only subset compared against the pre-registered TARGET."""
    keys = ("pairs", "only_in_main", "only_in_socratic", "socratic_lines_in_pairs",
            "socratic_lines_with_separator", "step_count_equal", "steps_identical",
            "annotations_identical", "annotations_differ", "main_annotations_total",
            "socratic_annotations_total")
    out = {k: result[k] for k in keys}
    out["main_annotation_classes"] = dict(result["main_annotation_classes"])
    out["socratic_annotation_classes"] = dict(result["socratic_annotation_classes"])
    return out
