"""Algorithms package initialization."""

from physai.algorithms.equation_generator import EquationGenerator
from physai.algorithms.equation_verifier import EquationVerifier

__all__ = ["EquationGenerator", "EquationVerifier"]

# Note: LSTM and GAN modules removed in favor of Neuro-Symbolic approach
# See: core/wolfram_evaluator.py and core/llm_interface.py
