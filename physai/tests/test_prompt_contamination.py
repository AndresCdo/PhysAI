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

# Functional forms the evaluation sets ask the system to recover, normalised to
# bare operator sequences. An example matching one of these hands over the
# answer even when it uses different variable names.
FORBIDDEN_FORMS = {
    "sqrt-of-single-input": re.compile(r"^a\s*\*\s*Sqrt\[\s*\w+\s*\]$"),
    "sqrt-times-decay": re.compile(r"Sqrt\[\s*\w+\s*\]\s*\*\s*Exp\[\s*-"),
    "saturating-exponential": re.compile(r"\(\s*1\s*-\s*Exp\[\s*-"),
    "range-with-double-angle": re.compile(r"Sin\[\s*2\s*\*"),
    "inverse-square-quantum": re.compile(r"\w+\^2\s*/\s*\w+\^2"),
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
        if pattern.search(output)
    ]

    assert not offenders, (
        f"Few-shot examples reproduce the '{label}' evaluation form:\n  "
        + "\n  ".join(offenders)
    )


def test_instructions_do_not_hint_an_evaluation_form():
    """Prose outside the examples must not hand over a target form either."""
    text = PROMPT_PATH.read_text(encoding="utf-8")
    body = EXAMPLE_PATTERN.sub("", text)

    hints = [
        hint for hint in ("T ∝ √L", "T = 2", "sqrt(L/g)", "Sqrt[L/g]") if hint in body
    ]

    assert not hints, f"Prompt prose hints at an evaluation target: {hints}"
