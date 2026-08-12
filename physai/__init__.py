"""
PhysAI - Neuro-Symbolic Framework for Physics Equation Discovery

PhysAI combines Large Language Models with symbolic computation to discover
physical equations from experimental data.

Main Components:
- SymbolicResearcher: Orchestrates the discovery process
- OllamaInterface: LLM interface for hypothesis generation
- WolframEvaluator: Symbolic validation and fitting

Quick Start:
    >>> from physai import SymbolicResearcher, ResearcherConfig
    >>>
    >>> config = ResearcherConfig(max_iterations=20, r2_threshold=0.95)
    >>> with SymbolicResearcher(model="granite4:1b", config=config) as researcher:
    ...     result = researcher.discover(
    ...         dataset_path="data/pendulum.csv",
    ...         target="period_s",
    ...         inputs=["length_m"]
    ...     )
    >>> print(result.summary())

Legacy Components (deprecated):
- EquationGenerator: Old text-based equation generation (use SymbolicResearcher)
- EquationVerifier: Stub implementation (use WolframEvaluator)
"""

__version__ = "0.1.0"

from physai.core import (
    SymbolicResearcher,
    ResearcherConfig,
    OllamaInterface,
    WolframEvaluator,
    Variable,
    FitResult,
    DiscoveryResult,
    Attempt,
    AttemptStatus,
)

__all__ = [
    "__version__",
    "SymbolicResearcher",
    "ResearcherConfig",
    "OllamaInterface",
    "WolframEvaluator",
    "Variable",
    "FitResult",
    "DiscoveryResult",
    "Attempt",
    "AttemptStatus",
]

try:
    from physai.algorithms.equation_generator import EquationGenerator
    from physai.algorithms.equation_verifier import EquationVerifier
    from physai.data_processing.data_collector import DataCollector
    from physai.data_processing.data_preprocessor import DataPreprocessor
    from physai.data_processing.data_validator import DataValidator

    __all__.extend(
        [
            "EquationGenerator",
            "EquationVerifier",
            "DataCollector",
            "DataPreprocessor",
            "DataValidator",
        ]
    )
except ImportError:
    pass
