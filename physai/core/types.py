"""Type definitions for PhysAI Neuro-Symbolic Engine."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class AttemptStatus(Enum):
    """Status of a hypothesis attempt."""

    PENDING = "pending"
    SYNTAX_ERROR = "syntax_error"
    DIMENSION_MISMATCH = "dimension_mismatch"
    FIT_FAILED = "fit_failed"
    SUCCESS = "success"


@dataclass
class Variable:
    """Represents a physical variable with its metadata."""

    name: str
    unit: str
    description: str = ""
    symbol: str = ""

    def __post_init__(self):
        if not self.symbol:
            self.symbol = self.name

    def __repr__(self) -> str:
        return f"Variable({self.name}, [{self.unit}])"


@dataclass
class Attempt:
    """Represents a single hypothesis attempt in the discovery loop."""

    expression: str
    status: AttemptStatus = AttemptStatus.PENDING
    error_message: str = ""
    adjusted_r2: Optional[float] = None
    aic: Optional[float] = None
    parameters: Optional[Dict[str, float]] = None
    iteration: int = 0

    def to_feedback_string(self) -> str:
        """Generate a human-readable feedback string for LLM context."""
        parts = [f"Iteration {self.iteration}: {self.expression}"]

        if self.status == AttemptStatus.SYNTAX_ERROR:
            parts.append(f"  Error: Syntax error - {self.error_message}")
        elif self.status == AttemptStatus.DIMENSION_MISMATCH:
            parts.append(f"  Error: Dimensional mismatch - {self.error_message}")
        elif self.status == AttemptStatus.FIT_FAILED:
            parts.append(f"  Error: Fitting failed - {self.error_message}")
        elif self.status == AttemptStatus.SUCCESS:
            parts.append(f"  Success! R² = {self.adjusted_r2:.4f}")
        else:
            parts.append(f"  R² = {self.adjusted_r2:.4f}, AIC = {self.aic:.2f}")

        return "\n".join(parts)


@dataclass
class FitResult:
    """Result of a symbolic fit operation."""

    expression: str
    parameters: Dict[str, float]
    adjusted_r2: float
    aic: float
    bic: float
    residuals_rmse: float
    converged: bool = True

    def is_good_fit(self, r2_threshold: float = 0.95) -> bool:
        """Check if the fit meets quality threshold."""
        return self.adjusted_r2 >= r2_threshold and self.converged

    def complexity_score(self) -> int:
        """Estimate equation complexity for Occam's Razor."""
        return len(self.parameters)

    def combined_score(self, r2_weight: float = 0.7, aic_weight: float = 0.3) -> float:
        """
        Combined score for ranking hypotheses.
        Higher is better.
        """
        normalized_r2 = self.adjusted_r2
        normalized_aic = 1.0 / (1.0 + abs(self.aic) / 100.0)
        return r2_weight * normalized_r2 + aic_weight * normalized_aic


@dataclass
class DiscoveryResult:
    """Final result of a discovery process."""

    success: bool
    best_expression: Optional[str] = None
    best_result: Optional[FitResult] = None
    attempts: List[Attempt] = field(default_factory=list)
    total_iterations: int = 0
    target_variable: Optional[Variable] = None
    input_variables: List[Variable] = field(default_factory=list)
    error_message: str = ""

    @property
    def final_r2(self) -> Optional[float]:
        """Return R² of best result."""
        return self.best_result.adjusted_r2 if self.best_result else None

    def summary(self) -> str:
        """Generate a human-readable summary."""
        if self.success:
            return (
                f"Discovery successful!\n"
                f"  Expression: {self.best_expression}\n"
                f"  R² = {self.final_r2:.4f}\n"
                f"  Iterations: {self.total_iterations}"
            )
        return (
            f"Discovery failed after {self.total_iterations} iterations.\n"
            f"  Error: {self.error_message}"
        )


@dataclass
class UnitDimension:
    """Represents dimensional analysis of a physical quantity."""

    length: int = 0
    mass: int = 0
    time: int = 0
    current: int = 0
    temperature: int = 0
    amount: int = 0
    luminosity: int = 0

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, UnitDimension):
            return False
        return (
            self.length == other.length
            and self.mass == other.mass
            and self.time == other.time
            and self.current == other.current
            and self.temperature == other.temperature
            and self.amount == other.amount
            and self.luminosity == other.luminosity
        )

    def __repr__(self) -> str:
        dims = []
        if self.length:
            dims.append(f"L^{self.length}" if self.length != 1 else "L")
        if self.mass:
            dims.append(f"M^{self.mass}" if self.mass != 1 else "M")
        if self.time:
            dims.append(f"T^{self.time}" if self.time != 1 else "T")
        if self.current:
            dims.append(f"I^{self.current}" if self.current != 1 else "I")
        if self.temperature:
            dims.append(f"Θ^{self.temperature}" if self.temperature != 1 else "Θ")
        if self.amount:
            dims.append(f"N^{self.amount}" if self.amount != 1 else "N")
        if self.luminosity:
            dims.append(f"J^{self.luminosity}" if self.luminosity != 1 else "J")
        return " ".join(dims) if dims else "dimensionless"

    def multiply(self, other: "UnitDimension") -> "UnitDimension":
        """Multiply dimensions."""
        return UnitDimension(
            length=self.length + other.length,
            mass=self.mass + other.mass,
            time=self.time + other.time,
            current=self.current + other.current,
            temperature=self.temperature + other.temperature,
            amount=self.amount + other.amount,
            luminosity=self.luminosity + other.luminosity,
        )

    def divide(self, other: "UnitDimension") -> "UnitDimension":
        """Divide dimensions."""
        return UnitDimension(
            length=self.length - other.length,
            mass=self.mass - other.mass,
            time=self.time - other.time,
            current=self.current - other.current,
            temperature=self.temperature - other.temperature,
            amount=self.amount - other.amount,
            luminosity=self.luminosity - other.luminosity,
        )

    def power(self, exponent: float) -> "UnitDimension":
        """Raise dimension to a power."""
        if exponent == int(exponent):
            exp = int(exponent)
            return UnitDimension(
                length=self.length * exp,
                mass=self.mass * exp,
                time=self.time * exp,
                current=self.current * exp,
                temperature=self.temperature * exp,
                amount=self.amount * exp,
                luminosity=self.luminosity * exp,
            )
        raise ValueError(f"Non-integer power {exponent} not supported for dimensions")
