"""Deciding whether a model emitted the target law, and not merely something
that the variable names make obvious.

The first version of this instrument scored M2b with the pattern
``sin(angle_deg)``. It matched 30/30 runs — but a column named "angle" makes
``sin`` the obvious thing to write, so the pattern measured the variable name
rather than recall. It also *under*-counted M0, whose pattern demanded
``sqrt(length_m)`` while the model was writing ``2*Pi*Sqrt[length_m/(g*g)]``.

Both failures share a cause: a pattern only measures recall if it demands the
features that separate the target from the answer a model would give from the
variable names alone. So a signature here is a **conjunction** of features, and
every problem ships the positives it must catch and the decoys it must reject.
``test_blind_control_detectors.py`` holds the instrument to both.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Mapping, Sequence, Tuple


def normalise(expression: str) -> str:
    """Fold Wolfram and SymPy spellings onto one form before matching.

    Mirrors the normaliser the contamination guard uses, so "did the model emit
    the answer" and "does the prompt contain the answer" are decided the same
    way.
    """
    text = expression.strip()
    text = text.replace("[", "(").replace("]", ")")
    text = text.replace("**", "^")
    text = re.sub(r"\s+", " ", text)
    return text.lower()


@dataclass(frozen=True)
class Feature:
    """One necessary ingredient of a target law.

    ``template`` is a regex with ``{name}`` placeholders filled from the
    variable mapping, so the same signature works for real and obfuscated runs.
    """

    label: str
    template: str

    def compile_for(self, mapping: Mapping[str, str]) -> re.Pattern:
        """Bind the role placeholders to the names this run actually used."""
        return re.compile(self.template.format(**mapping))


@dataclass(frozen=True)
class Problem:
    """A target law plus the evidence needed to trust its detector."""

    problem_id: str
    dataset: str
    target: Tuple[str, str]
    inputs: Tuple[Tuple[str, str], ...]
    signature: Tuple[Feature, ...]
    positives: Tuple[str, ...]
    decoys: Tuple[str, ...]

    def variable_map(self, obfuscated: bool) -> Dict[str, str]:
        """Map role names used in signatures to the names a run actually uses."""
        roles = {"target": "var_y"} if obfuscated else {"target": self.target[0]}
        for index, (name, _) in enumerate(self.inputs):
            roles[f"in{index}"] = f"var_{chr(ord('a') + index)}" if obfuscated else name
        return roles

    def matches(self, output: str, obfuscated: bool = False) -> bool:
        """True when every feature of the signature is present."""
        text = normalise(output)
        mapping = self.variable_map(obfuscated)
        return all(f.compile_for(mapping).search(text) for f in self.signature)

    def missing_features(self, output: str, obfuscated: bool = False) -> Sequence[str]:
        """Which features are absent — for diagnosing a near miss."""
        text = normalise(output)
        mapping = self.variable_map(obfuscated)
        return [
            f.label for f in self.signature if not f.compile_for(mapping).search(text)
        ]


# `g` is admitted inside the square root because a model reciting the pendulum
# law writes the gravitational constant even when it garbles the denominator.
# Requiring sqrt over the length alone is what made the first version miss it.
_M0 = Problem(
    problem_id="M0-pendulum",
    dataset="pendulum_simple.csv",
    target=("period_s", "Time"),
    inputs=(("length_m", "Length"),),
    signature=(Feature("sqrt-over-length", r"sqrt\([^)]*{in0}"),),
    positives=(
        "a * sqrt(length_m)",
        "a * Sqrt[length_m]",
        "2*Pi*Sqrt[length_m/(g*g)]",
        "2 * pi * sqrt(length_m / g)",
    ),
    decoys=(
        "a * length_m^b",  # the obvious power law, and what condition A produced
        "a * length_m",
        "a + b * length_m",
        "sqrt(a) * length_m",  # sqrt present, but not over the length
    ),
)

_M1 = Problem(
    problem_id="M1-damped",
    dataset="pendulum_damped.csv",
    target=("amplitude_m", "Length"),
    inputs=(("length_m", "Length"), ("time_s", "Time")),
    signature=(
        Feature("sqrt-over-length", r"sqrt\([^)]*{in0}"),
        Feature("exponential-decay", r"exp\( ?-"),
    ),
    positives=(
        "a * sqrt(length_m) * exp(-b * time_s)",
        "a * Sqrt[length_m] * Exp[-b * time_s]",
        "exp(-b*time_s) * a * sqrt(length_m)",
    ),
    decoys=(
        "a * sqrt(length_m)",  # no decay
        "a * exp(-b * time_s)",  # no length dependence
        "a * length_m * exp(-b * time_s)",  # linear, not sqrt
    ),
)

_M2A = Problem(
    problem_id="M2a-drag",
    dataset="projectile_horizontal_drag.csv",
    target=("distance_m", "Length"),
    inputs=(("velocity_m_s", "Speed"), ("time_s", "Time")),
    signature=(Feature("saturating-exponential", r"\( ?1 ?- ?exp\( ?-"),),
    positives=(
        "a * velocity_m_s * (1 - exp(-b * time_s))",
        "a * velocity_m_s * (1 - Exp[-b*time_s])",
    ),
    decoys=(
        "velocity_m_s * time_s",  # the drag-free answer
        "a * velocity_m_s * exp(-b * time_s)",  # decay, not saturation
        "a * velocity_m_s * (1 + exp(-b * time_s))",
    ),
)

# Two features, because a column named "angle" makes a bare `sin` the obvious
# thing to write. Only the square AND the double angle identify the range law.
_M2B = Problem(
    problem_id="M2b-range",
    dataset="projectile_2d_drag.csv",
    target=("range_m", "Length"),
    inputs=(("velocity_m_s", "Speed"), ("angle_deg", "Angle")),
    signature=(
        Feature("velocity-squared", r"{in0} ?\^ ?2"),
        Feature("double-angle", r"sin\( ?2 ?\*"),
    ),
    positives=(
        "a * velocity_m_s^2 * sin(2 * angle_deg * pi / 180)",
        "a * velocity_m_s**2 * sin(2*angle_deg)",
        "velocity_m_s^2 * Sin[2 * angle_deg] / g",
    ),
    decoys=(
        "a * velocity_m_s * sin(angle_deg)",  # what the first pattern accepted
        "a * velocity_m_s^2 * sin(angle_deg)",  # square, but no double angle
        "a * velocity_m_s * sin(2 * angle_deg)",  # double angle, but no square
        "a * sin(angle_deg)",
    ),
)

_M3 = Problem(
    problem_id="M3-well",
    dataset="quantum_well_1d.csv",
    target=("energy_ev", "Energy"),
    inputs=(("quantum_number_n", "Dimensionless"), ("well_width_nm", "Length")),
    signature=(
        Feature("quantum-number-squared", r"{in0} ?\^ ?2"),
        Feature("inverse-square-width", r"/ ?\(?{in1} ?\^ ?2"),
    ),
    positives=(
        "a * quantum_number_n^2 / well_width_nm^2",
        "a * quantum_number_n**2 / (well_width_nm**2)",
    ),
    decoys=(
        "a * quantum_number_n^2 / well_width_nm",  # inverse-linear, not square
        "a * quantum_number_n / well_width_nm^2",
        "energy_ev",  # what condition A produced: echo the target column
    ),
)

PROBLEMS: Tuple[Problem, ...] = (_M0, _M1, _M2A, _M2B, _M3)
BY_ID: Dict[str, Problem] = {p.problem_id: p for p in PROBLEMS}
