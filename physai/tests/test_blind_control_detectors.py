"""Tests for the blind-control instrument itself.

The first version of this detector both under-counted M0 and produced false
positives on M2b, and neither showed up until the raw traces were read by hand.
An instrument that decides an experiment's outcome needs its own tests, so each
problem ships the expressions it must catch and the near-misses it must reject.
"""

import pytest

from physai.benchmarks.blind_control.detectors import BY_ID, PROBLEMS, normalise


def test_every_problem_declares_evidence():
    """A signature with no positives or no decoys cannot be trusted."""
    for problem in PROBLEMS:
        assert problem.positives, f"{problem.problem_id} declares no positives"
        assert problem.decoys, f"{problem.problem_id} declares no decoys"
        assert problem.signature, f"{problem.problem_id} declares no signature"


@pytest.mark.parametrize(
    "problem_id,expression",
    [(p.problem_id, e) for p in PROBLEMS for e in p.positives],
)
def test_positives_are_detected(problem_id, expression):
    problem = BY_ID[problem_id]
    assert problem.matches(expression), (
        f"{problem_id} failed to detect a genuine recall: {expression!r} "
        f"(missing {list(problem.missing_features(expression))})"
    )


@pytest.mark.parametrize(
    "problem_id,expression",
    [(p.problem_id, e) for p in PROBLEMS for e in p.decoys],
)
def test_decoys_are_rejected(problem_id, expression):
    problem = BY_ID[problem_id]
    assert not problem.matches(expression), (
        f"{problem_id} counted a non-answer as recall: {expression!r}. "
        "A pattern this loose measures the variable name, not the model."
    )


def test_m2b_requires_both_discriminating_features():
    """The regression that motivated this module.

    A column named "angle" makes a bare `sin` the obvious thing to write, so
    neither the square nor the double angle is sufficient alone.
    """
    problem = BY_ID["M2b-range"]
    square_only = "a * velocity_m_s^2 * sin(angle_deg)"
    angle_only = "a * velocity_m_s * sin(2 * angle_deg)"

    assert not problem.matches(square_only)
    assert "double-angle" in problem.missing_features(square_only)
    assert not problem.matches(angle_only)
    assert "velocity-squared" in problem.missing_features(angle_only)
    assert problem.matches("a * velocity_m_s^2 * sin(2 * angle_deg)")


def test_m0_detects_a_garbled_recitation():
    """The under-count that motivated re-scoring.

    A model reciting the pendulum law writes the constant even when it garbles
    the denominator. Demanding sqrt over the bare length missed 30/30 runs.
    """
    problem = BY_ID["M0-pendulum"]
    for observed in (
        "2*Pi*Sqrt[length_m/(g*accel_m_s2)]",
        "2*Pi*Sqrt[length_m/(g*length_m)]",
        "2 * Pi * Sqrt[length_m / (g * g)]",
    ):
        assert problem.matches(observed), f"missed a recitation: {observed!r}"


def test_detection_is_dialect_independent():
    """Wolfram and SymPy spellings of the same law must score identically."""
    for problem in PROBLEMS:
        for expression in problem.positives:
            wolfram = expression.replace("**", "^")
            sympy_style = expression.replace("[", "(").replace("]", ")")
            assert problem.matches(wolfram) == problem.matches(sympy_style)


def test_obfuscated_names_do_not_match_real_signatures():
    """A real-name answer must not count when the run obfuscated the names."""
    problem = BY_ID["M0-pendulum"]
    assert problem.matches("a * sqrt(length_m)", obfuscated=False)
    assert not problem.matches("a * sqrt(length_m)", obfuscated=True)
    assert problem.matches("a * sqrt(var_a)", obfuscated=True)


def test_latex_recitation_is_recognised():
    """Larger models answer in LaTeX unprompted; a miss there is a false zero.

    qwen3.5:2b replies to the pendulum problem with
    ``T = 2\\pi \\sqrt{\\frac{L}{g}}`` — a verbatim recitation that scores as a
    miss under a Wolfram-and-SymPy-only normaliser.
    """
    problem = BY_ID["M0-pendulum"]
    observed = r"T = 2\pi \sqrt{\frac{L}{g}}"

    assert not problem.matches(observed), "generic symbols are not usable output"
    assert problem.recites(observed), "but the law was plainly recalled"


def test_recites_is_strictly_looser_than_matches():
    """Anything usable is also a recitation; the converse need not hold."""
    for problem in PROBLEMS:
        for expression in problem.positives:
            if problem.matches(expression):
                assert problem.recites(expression)


def test_recites_still_rejects_decoys():
    """Accepting textbook symbols must not accept non-answers."""
    for problem in PROBLEMS:
        for decoy in problem.decoys:
            assert not problem.recites(decoy), (
                f"{problem.problem_id} recited a decoy: {decoy!r}"
            )


def test_recites_equals_matches_when_obfuscated():
    """Obfuscated runs supply no meaningful symbol, so the loosening cannot apply."""
    problem = BY_ID["M0-pendulum"]
    for expression in ("a * sqrt(var_a)", "a * sqrt(l)", "2*pi*sqrt(l/g)"):
        assert problem.recites(expression, obfuscated=True) == problem.matches(
            expression, obfuscated=True
        )


def test_normalise_handles_latex():
    assert "sqrt(" in normalise(r"\sqrt{x}")
    assert normalise(r"\frac{a}{b}") == "((a)/(b))"
    assert "pi" in normalise(r"2\pi")
    assert normalise(r"\text{period\_s}") == r"period\_s"


def test_normalise_folds_both_dialects():
    assert normalise("a * Sqrt[x]") == normalise("a * sqrt(x)")
    assert normalise("x**2") == normalise("x^2")
    assert normalise("  a  *   b ") == "a * b"
