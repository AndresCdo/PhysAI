"""Core module for PhysAI Neuro-Symbolic Engine."""

from physai.core.types import (
    Variable,
    Attempt,
    AttemptStatus,
    FitResult,
    DiscoveryResult,
    UnitDimension,
)
from physai.core.constants import (
    RESERVED_CONSTANTS,
    PHYSICAL_UNITS,
    MATHEMATICAL_FUNCTIONS,
    normalize_unit,
    get_unit_dimension,
)
from physai.core.researcher import SymbolicResearcher, ResearcherConfig
from physai.core.llm_interface import OllamaInterface
from physai.core.wolfram_evaluator import WolframEvaluator

__all__ = [
    "Variable",
    "Attempt",
    "AttemptStatus",
    "FitResult",
    "DiscoveryResult",
    "UnitDimension",
    "RESERVED_CONSTANTS",
    "PHYSICAL_UNITS",
    "MATHEMATICAL_FUNCTIONS",
    "normalize_unit",
    "get_unit_dimension",
    "SymbolicResearcher",
    "ResearcherConfig",
    "OllamaInterface",
    "WolframEvaluator",
]
