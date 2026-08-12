"""Symbolic Researcher orchestrator for equation discovery."""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict

import pandas as pd

from physai.core.types import (
    Variable,
    Attempt,
    AttemptStatus,
    FitResult,
    DiscoveryResult,
)
from physai.core.llm_interface import OllamaInterface, OllamaInterfaceError
from physai.core.wolfram_evaluator import (
    WolframEvaluator,
    WolframFitError,
)
from physai.utils.feedback import generate_qualitative_feedback, generate_error_feedback
from physai.utils.parsing import is_valid_expression

logger = logging.getLogger(__name__)


@dataclass
class ResearcherConfig:
    """Configuration for SymbolicResearcher."""

    max_iterations: int = 20
    r2_threshold: float = 0.95
    max_history_for_llm: int = 5
    wolfram_timeout: int = 30
    llm_temperature: float = 0.7
    llm_max_retries: int = 3
    skip_dimension_check: bool = False
    skip_syntax_check: bool = False


class SymbolicResearcher:
    """
    Orchestrates the neuro-symbolic equation discovery process.

    This class manages the feedback loop between:
    1. Ollama LLM (hypothesis generation)
    2. Wolfram Evaluator (validation and fitting)

    The discovery process:
    1. Load data and variable metadata
    2. Ask LLM for a hypothesis (Wolfram expression)
    3. Validate syntax and dimensions
    4. Fit parameters to data
    5. If R² < threshold, generate feedback and retry
    6. Return the best-fitting expression

    Usage:
        >>> researcher = SymbolicResearcher(model="granite4:1b")
        >>> result = researcher.discover(
        ...     dataset_path="data/pendulum.csv",
        ...     target="period_s",
        ...     inputs=["length_m"]
        ... )
        >>> print(result.summary())
    """

    def __init__(
        self,
        model: str = "granite4:1b",
        ollama_url: str = "http://localhost:11434",
        wolfram_kernel_path: Optional[str] = None,
        config: Optional[ResearcherConfig] = None,
    ):
        """
        Initialize the Symbolic Researcher.

        Args:
            model: Name of the Ollama model to use.
            ollama_url: URL of the Ollama server.
            wolfram_kernel_path: Path to WolframKernel executable.
            config: ResearcherConfig with discovery parameters.
        """
        self.config = config or ResearcherConfig()

        self.llm = OllamaInterface(
            model=model, base_url=ollama_url, temperature=self.config.llm_temperature
        )

        self.evaluator = WolframEvaluator(
            kernel_path=wolfram_kernel_path,
            timeout=self.config.wolfram_timeout,
            auto_start=False,
        )

        self._history: List[Attempt] = []
        self._best_result: Optional[FitResult] = None

    # Public entry point: every parameter is domain-meaningful and the loop
    # is one coherent algorithm. Splitting it to satisfy a counter would
    # scatter the discovery flow across helpers.
    # pylint: disable=too-many-positional-arguments,too-many-locals,too-many-statements
    def discover(
        self,
        dataset_path: str,
        target: str,
        inputs: List[str],
        target_unit: Optional[str] = None,
        input_units: Optional[Dict[str, str]] = None,
        descriptions: Optional[Dict[str, str]] = None,
    ) -> DiscoveryResult:
        """
        Run the equation discovery process.

        Args:
            dataset_path: Path to CSV file with data.
            target: Name of the target variable column.
            inputs: List of input variable column names.
            target_unit: Unit of the target variable.
            input_units: Dict mapping input names to units.
            descriptions: Dict mapping variable names to descriptions.

        Returns:
            DiscoveryResult with the best-found expression.
        """
        self._history = []
        self._best_result = None

        data = self._load_data(dataset_path)

        target_var = Variable(
            name=target,
            unit=target_unit or self._infer_unit(target),
            description=(descriptions or {}).get(target, ""),
        )

        input_vars = [
            Variable(
                name=inp,
                unit=(input_units or {}).get(inp, self._infer_unit(inp)),
                description=(descriptions or {}).get(inp, ""),
            )
            for inp in inputs
        ]

        logger.info(f"Starting discovery for {target} as function of {inputs}")
        logger.info(f"Data shape: {data.shape}")

        try:
            # no public API to force a connection; tracked with the evaluator refactor
            self.evaluator._ensure_connection()  # pylint: disable=protected-access
        # foreign boundary: wolframclient surfaces undocumented types from a subprocess link
        except Exception as e:  # pylint: disable=broad-exception-caught
            return DiscoveryResult(
                success=False,
                error_message=f"Failed to connect to Wolfram: {e}",
                attempts=self._history,
                target_variable=target_var,
                input_variables=input_vars,
            )

        for iteration in range(self.config.max_iterations):
            logger.info(f"Iteration {iteration + 1}/{self.config.max_iterations}")

            hypothesis = self._generate_hypothesis(target_var, input_vars)

            if hypothesis is None:
                continue

            attempt = Attempt(
                expression=hypothesis, iteration=iteration, status=AttemptStatus.PENDING
            )

            # Check that expression uses correct variable names
            var_check = self._validate_variable_names(hypothesis, inputs)
            if not var_check[0]:
                attempt.status = AttemptStatus.SYNTAX_ERROR
                attempt.error_message = var_check[1]
                self._history.append(attempt)
                logger.warning(f"Variable name error: {var_check[1]}")
                continue

            if not self.config.skip_syntax_check:
                is_valid, error = self._validate_syntax(hypothesis)
                if not is_valid:
                    attempt.status = AttemptStatus.SYNTAX_ERROR
                    attempt.error_message = error
                    self._history.append(attempt)
                    logger.warning(f"Syntax error: {error}")
                    continue

            if not self.config.skip_dimension_check:
                is_dimensionally_valid, dim_error = self._validate_dimensions(
                    hypothesis, target_var, input_vars
                )
                if not is_dimensionally_valid:
                    attempt.status = AttemptStatus.DIMENSION_MISMATCH
                    attempt.error_message = dim_error
                    self._history.append(attempt)
                    logger.warning(f"Dimension error: {dim_error}")
                    continue

            result = self._fit_expression(hypothesis, data, target, inputs)

            if result is None:
                attempt.status = AttemptStatus.FIT_FAILED
                attempt.error_message = "Fitting failed"
                self._history.append(attempt)
                continue

            attempt.adjusted_r2 = result.adjusted_r2
            attempt.aic = result.aic
            attempt.parameters = result.parameters

            if (
                self._best_result is None
                or result.combined_score() > self._best_result.combined_score()
            ):
                self._best_result = result

            if result.is_good_fit(self.config.r2_threshold):
                attempt.status = AttemptStatus.SUCCESS
                self._history.append(attempt)

                logger.info(f"Discovery successful! R² = {result.adjusted_r2:.4f}")
                logger.info(f"Expression: {hypothesis}")

                return DiscoveryResult(
                    success=True,
                    best_expression=hypothesis,
                    best_result=result,
                    attempts=self._history,
                    total_iterations=iteration + 1,
                    target_variable=target_var,
                    input_variables=input_vars,
                )

            self._history.append(attempt)
            logger.info(f"Iteration {iteration + 1}: R² = {result.adjusted_r2:.4f}")

        logger.warning(
            f"Discovery did not converge after {self.config.max_iterations} iterations"
        )

        return DiscoveryResult(
            success=False,
            best_expression=self._best_result.expression if self._best_result else None,
            best_result=self._best_result,
            error_message=f"Did not reach R² threshold of {self.config.r2_threshold}",
            attempts=self._history,
            total_iterations=self.config.max_iterations,
            target_variable=target_var,
            input_variables=input_vars,
        )

    def _load_data(self, dataset_path: str) -> pd.DataFrame:
        """Load data from CSV file."""
        path = Path(dataset_path)
        if not path.exists():
            raise FileNotFoundError(f"Dataset not found: {dataset_path}")

        data = pd.read_csv(path)

        if data.isna().any().any():
            logger.warning("Data contains NaN values, dropping rows with NaN")
            data = data.dropna()

        return data

    # Dispatch table: one return per physical quantity. See issue #12 for the
    # ordering defect in this function.
    # pylint: disable=too-many-return-statements
    def _infer_unit(self, variable_name: str) -> str:
        """Infer unit from variable name using common patterns."""
        name_lower = variable_name.lower()

        unit_hints = {
            "_m": "Meters",
            "_s": "Seconds",
            "_kg": "Kilograms",
            "_n": "Newtons",
            "_j": "Joules",
            "_w": "Watts",
            "_v": "Volts",
            "_a": "Amperes",
            "_k": "Kelvins",
            "_hz": "Hertz",
            "_pa": "Pascals",
        }

        for suffix, unit in unit_hints.items():
            if name_lower.endswith(suffix):
                return unit

        if "length" in name_lower or "distance" in name_lower:
            return "Meters"
        if "time" in name_lower or "period" in name_lower:
            return "Seconds"
        if "mass" in name_lower:
            return "Kilograms"
        if "velocity" in name_lower or "speed" in name_lower:
            return "MetersPerSecond"
        if "force" in name_lower:
            return "Newtons"
        if "energy" in name_lower:
            return "Joules"
        if "power" in name_lower:
            return "Watts"
        if "pressure" in name_lower:
            return "Pascals"

        return "Unknown"

    def _generate_hypothesis(
        self, target: Variable, inputs: List[Variable]
    ) -> Optional[str]:
        """Generate a hypothesis from the LLM."""
        try:
            # feedback is computed and never forwarded to generate_with_retry. See issue #13
            feedback = None  # pylint: disable=unused-variable
            if self._history:
                last_attempt = self._history[-1]
                if (
                    last_attempt.adjusted_r2 is not None
                    and last_attempt.adjusted_r2 < 0.95
                ):
                    mock_result = FitResult(
                        expression=last_attempt.expression,
                        parameters=last_attempt.parameters or {},
                        adjusted_r2=last_attempt.adjusted_r2,
                        aic=last_attempt.aic or 0,
                        bic=0,
                        residuals_rmse=0,
                        converged=True,
                    )
                    feedback = generate_qualitative_feedback(mock_result, self._history)
                elif last_attempt.status != AttemptStatus.PENDING:
                    feedback = generate_error_feedback(last_attempt)

            hypothesis = self.llm.generate_with_retry(
                target=target,
                inputs=inputs,
                error_history=self._history,
                max_retries=self.config.llm_max_retries,
            )

            return hypothesis

        except OllamaInterfaceError as e:
            logger.error(f"LLM generation failed: {e}")
            return None

    def _validate_syntax(self, expression: str) -> tuple:
        """Validate expression syntax."""
        is_valid, error = is_valid_expression(expression)
        if not is_valid:
            return False, error

        try:
            return self.evaluator.syntax_check(expression)
        # foreign boundary: wolframclient surfaces undocumented types from a subprocess link
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"Wolfram syntax check failed, using local: {e}")
            return is_valid, error

    def _validate_variable_names(
        self, expression: str, input_variables: List[str]
    ) -> tuple:
        """Validate that expression uses the correct variable names."""
        for var in input_variables:
            # Check if the exact variable name appears in the expression
            pattern = r"\b" + re.escape(var) + r"\b"
            if not re.search(pattern, expression):
                # Variable name not found - provide helpful error
                return False, (
                    f"Variable '{var}' not found in expression. "
                    f"You must use EXACT variable names. "
                    f"Expected: {var}, Expression uses different name."
                )

        return True, ""

    def _validate_dimensions(
        self, expression: str, target: Variable, inputs: List[Variable]
    ) -> tuple:
        """Validate dimensional consistency."""
        input_units = {v.name: v.unit for v in inputs}

        try:
            return self.evaluator.is_dimensionally_sound(
                expression=expression, target_unit=target.unit, input_units=input_units
            )
        # FAILS OPEN: reports success on kernel error. See issue #12
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"Dimension check failed: {e}")
            return True, ""

    def _fit_expression(
        self, expression: str, data: pd.DataFrame, target: str, inputs: List[str]
    ) -> Optional[FitResult]:
        """Fit the expression to data."""
        try:
            return self.evaluator.fit_and_score(
                expression=expression,
                data=data,
                target_variable=target,
                input_variables=inputs,
            )
        except WolframFitError as e:
            logger.error(f"Fitting failed: {e}")
            return None
        # foreign boundary: wolframclient surfaces undocumented types from a subprocess link
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Unexpected fitting error: {e}")
            return None

    def close(self) -> None:
        """Clean up resources."""
        self.evaluator.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
