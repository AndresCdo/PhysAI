"""Guards against the evaluation answers leaking into the prompt.

An LLM that is shown the target expression in its own few-shot examples will
reproduce it, and the run will look like a discovery. Every component
downstream — the fitter, the CAS, the refinement loop — can be broken without
the result changing. These tests make that failure mode detectable
automatically instead of by inspection.
"""

import csv
import re
from pathlib import Path

import pytest

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "system_prompt.txt"
BENCHMARK_DIR = Path(__file__).parent.parent / "data" / "benchmarks"

EXAMPLE_PATTERN = re.compile(
    r"### Example (\d+)\s*\nTarget:\s*(\S+).*?\nInputs:\s*(.*?)\nOutput:\s*(.*)"
)


def normalise(expression: str) -> str:
    """Reduce an expression to a syntax-independent form before matching.

    The forbidden-form patterns below must keep working if the candidate
    language changes. Written against Wolfram syntax alone they go blind the
    moment the same expression arrives as `a * sqrt(x)` instead of
    `a * Sqrt[x]`, which would silently retire the guard. Normalising folds
    both dialects — and any future one with the same operators — onto one
    spelling.
    """
    text = expression.strip()
    text = text.replace("[", "(").replace("]", ")")  # Wolfram calls -> Python calls
    text = text.replace("**", "^")  # Python powers -> one spelling
    text = re.sub(r"\s+", " ", text)
    # Function names are case-insensitive across the dialects we accept.
    for name in ("sqrt", "exp", "sin", "cos", "tan", "log"):
        text = re.sub(name, name, text, flags=re.IGNORECASE)
    return text.lower()


# Functional forms the evaluation sets ask the system to recover, matched
# against normalise() output. An example matching one of these hands over the
# answer even when it uses different variable names or a different dialect.
FORBIDDEN_FORMS = {
    "sqrt-of-single-input": re.compile(r"^a \* sqrt\( ?\w+ ?\)$"),
    "sqrt-times-decay": re.compile(r"sqrt\( ?\w+ ?\) \* exp\( ?-"),
    "saturating-exponential": re.compile(r"\( ?1 - exp\( ?-"),
    "range-with-double-angle": re.compile(r"sin\( ?2 \*"),
    "inverse-square-quantum": re.compile(r"\w+\^2 ?/ ?\w+\^2"),
}


def parse_examples():
    """Return [(number, target, [inputs], output)] from the prompt template."""
    return [
        (int(n), target, [v.split(" ")[0] for v in inputs.split(", ")], output.strip())
        for n, target, inputs, output in EXAMPLE_PATTERN.findall(
            PROMPT_PATH.read_text(encoding="utf-8")
        )
    ]


def benchmark_columns():
    """Return {column_name: [files it appears in]} across every benchmark."""
    columns = {}
    for path in sorted(BENCHMARK_DIR.glob("*.csv")):
        with open(path, encoding="utf-8") as handle:
            for column in next(csv.reader(handle)):
                columns.setdefault(column, []).append(path.name)
    return columns


def test_prompt_template_exists():
    assert PROMPT_PATH.exists(), f"Prompt template not found: {PROMPT_PATH}"


def test_prompt_has_examples():
    assert parse_examples(), "No few-shot examples parsed; the guard would be vacuous"


def test_benchmarks_are_discoverable():
    assert benchmark_columns(), "No benchmark columns found; the guard would be vacuous"


def test_no_example_uses_a_benchmark_column():
    """No few-shot variable name may appear as a column in any evaluation set."""
    columns = benchmark_columns()
    leaks = []
    for number, target, inputs, _ in parse_examples():
        for name in [target] + inputs:
            if name in columns:
                leaks.append(f"Example {number} uses '{name}' from {columns[name]}")

    assert not leaks, (
        "Few-shot examples share variable names with evaluation data, which hands "
        "the model the variable mapping:\n  " + "\n  ".join(leaks)
    )


@pytest.mark.parametrize("label,pattern", sorted(FORBIDDEN_FORMS.items()))
def test_no_example_reproduces_an_evaluation_form(label, pattern):
    """No few-shot output may have the shape of an evaluation target."""
    offenders = [
        f"Example {number}: {output}"
        for number, _, _, output in parse_examples()
        if pattern.search(normalise(output))
    ]

    assert not offenders, (
        f"Few-shot examples reproduce the '{label}' evaluation form:\n  "
        + "\n  ".join(offenders)
    )


# The five evaluation answers, written in each dialect the project may emit.
# Wolfram is what the prompt used; SymPy is what a move off the Wolfram kernel
# would produce. Both must be caught, or switching dialect retires the guard.
KNOWN_ANSWERS = [
    ("wolfram", "a * Sqrt[length_m]"),
    ("wolfram", "a * Sqrt[length_m] * Exp[-b * time_s]"),
    ("wolfram", "a * velocity_m_s * (1 - Exp[-b * time_s])"),
    ("wolfram", "a * velocity_m_s^2 * Sin[2 * angle_deg * Pi / 180]"),
    ("wolfram", "a * quantum_number_n^2 / well_width_nm^2"),
    ("sympy", "a * sqrt(length_m)"),
    ("sympy", "a * sqrt(length_m) * exp(-b * time_s)"),
    ("sympy", "a * velocity_m_s * (1 - exp(-b * time_s))"),
    ("sympy", "a * velocity_m_s**2 * sin(2 * angle_deg * pi / 180)"),
    ("sympy", "a * quantum_number_n**2 / well_width_nm**2"),
]


@pytest.mark.parametrize("dialect,answer", KNOWN_ANSWERS)
def test_guard_catches_known_answers_in_any_dialect(dialect, answer):
    """The guard must not depend on which expression language is in use."""
    matched = [
        label
        for label, pattern in FORBIDDEN_FORMS.items()
        if pattern.search(normalise(answer))
    ]

    assert matched, (
        f"A known evaluation answer written in {dialect} syntax passes every "
        f"forbidden-form pattern: {answer!r} normalises to "
        f"{normalise(answer)!r}. The guard is blind to this dialect."
    )


def test_instructions_do_not_hint_an_evaluation_form():
    """Prose outside the examples must not hand over a target form either."""
    text = PROMPT_PATH.read_text(encoding="utf-8")
    body = EXAMPLE_PATTERN.sub("", text)

    hints = [
        hint for hint in ("T ∝ √L", "T = 2", "sqrt(L/g)", "Sqrt[L/g]") if hint in body
    ]

    assert not hints, f"Prompt prose hints at an evaluation target: {hints}"
