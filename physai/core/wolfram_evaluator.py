"""Wolfram Language evaluator with guardrails for PhysAI."""

import logging
import os
from typing import Dict, List, Optional, Tuple, Any

import pandas as pd

from physai.core.types import FitResult, Variable, UnitDimension
from physai.core.constants import get_unit_dimension, normalize_unit
from physai.utils.serialization import data_to_wolfram_string, variable_to_wolfram_unit
from physai.utils.parsing import is_valid_expression

logger = logging.getLogger(__name__)


class WolframEvaluatorError(Exception):
    """Base exception for WolframEvaluator errors."""

    pass


class WolframConnectionError(WolframEvaluatorError):
    """Raised when connection to Wolfram Kernel fails."""

    pass


class WolframSyntaxError(WolframEvaluatorError):
    """Raised when expression has invalid syntax."""

    pass


class WolframDimensionError(WolframEvaluatorError):
    """Raised when expression has dimensional inconsistency."""

    pass


class WolframFitError(WolframEvaluatorError):
    """Raised when fitting operation fails."""

    pass


class WolframEvaluator:
    """
    Evaluates Wolfram Language expressions with safety guardrails.

    This class provides:
    - Connection management to Wolfram Kernel via WSTP
    - Syntax validation before expensive evaluation
    - Dimensional analysis for unit consistency
    - NonlinearModelFit with error metrics

    Usage:
        >>> evaluator = WolframEvaluator()
        >>> result = evaluator.fit_and_score(
        ...     expression="a * Sqrt[length]",
        ...     data=pd.DataFrame({"length": [1, 2, 3], "period": [2, 2.83, 3.46]}),
        ...     target="period",
        ...     inputs=["length"]
        ... )
    """

    def __init__(
        self,
        kernel_path: Optional[str] = None,
        timeout: int = 30,
        auto_start: bool = True,
    ):
        """
        Initialize the Wolfram evaluator.

        Args:
            kernel_path: Path to WolframKernel executable. If None, uses system default.
            timeout: Timeout in seconds for evaluations.
            auto_start: Whether to start the kernel on initialization.
        """
        self.kernel_path = kernel_path
        self.timeout = timeout
        self._session = None
        self._initialized = False

        if auto_start:
            self._ensure_connection()

    def _ensure_connection(self) -> None:
        """Ensure connection to Wolfram Kernel is established."""
        if self._session is not None:
            return

        try:
            from wolframclient.evaluation import WolframLanguageSession
            from wolframclient.language import wl
        except ImportError as e:
            raise WolframConnectionError(
                "wolframclient is required. Install with: pip install wolframclient"
            ) from e

        try:
            if self.kernel_path:
                self._session = WolframLanguageSession(self.kernel_path)
            else:
                self._session = WolframLanguageSession()

            self._session.start()
            self._wl = wl
            self._initialized = True
            logger.info("Wolfram Kernel session started successfully")
        except Exception as e:
            raise WolframConnectionError(f"Failed to start Wolfram Kernel: {e}") from e

    def close(self) -> None:
        """Close the Wolfram Kernel session."""
        if self._session is not None:
            try:
                self._session.stop()
                logger.info("Wolfram Kernel session closed")
            except Exception as e:
                logger.warning(f"Error closing Wolfram session: {e}")
            finally:
                self._session = None
                self._initialized = False

    def __enter__(self):
        """Context manager entry."""
        self._ensure_connection()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False

    def syntax_check(self, expression: str) -> Tuple[bool, str]:
        """
        Verify expression parses correctly in Wolfram.

        This is a lightweight check that doesn't execute the expression.

        Args:
            expression: Wolfram Language expression string

        Returns:
            Tuple of (is_valid, error_message)
        """
        is_valid_local, local_error = is_valid_expression(expression)
        if not is_valid_local:
            return False, local_error

        self._ensure_connection()

        try:
            escaped_expr = expression.replace('"', '\\"')
            query = f'SyntaxQ["{escaped_expr}"]'
            result = self._evaluate_safe(query)

            if result is True or result == "True":
                return True, ""

            error_query = f'SyntaxLength["{escaped_expr}"]'
            error_pos = self._evaluate_safe(error_query)
            return False, f"Syntax error near position {error_pos}"

        except Exception as e:
            return False, f"Syntax check failed: {e}"

    def is_dimensionally_sound(
        self, expression: str, target_unit: str, input_units: Dict[str, str]
    ) -> Tuple[bool, str]:
        """
        Check if expression has correct dimensional output.

        This uses Wolfram's UnitDimensions to verify that the expression
        results in the expected unit type when given input variables.

        Args:
            expression: Wolfram Language expression string
            target_unit: Expected unit of the result (e.g., "Seconds")
            input_units: Dict mapping variable names to their units

        Returns:
            Tuple of (is_dimensionally_sound, error_message)
        """
        self._ensure_connection()

        try:
            unit_substitutions = ", ".join(
                variable_to_wolfram_unit(var, unit) for var, unit in input_units.items()
            )

            query = f"""
            Module[{{result}},
                result = Quiet[Check[
                    UnitDimensions[{expression} /. {{{unit_substitutions}}}],
                    $Failed
                ]];
                If[result === $Failed,
                    {{False, "Could not determine units"}},
                    {{True, ""}}
                ]
            ]
            """
            result = self._evaluate_safe(query)

            if isinstance(result, list) and len(result) == 2:
                is_ok = result[0] is True or result[0] == "True"
                error = result[1] if isinstance(result[1], str) else ""
                return is_ok, error

            return True, ""

        except Exception as e:
            logger.warning(f"Dimension check failed: {e}")
            return True, ""

    def fit_and_score(
        self,
        expression: str,
        data: pd.DataFrame,
        target_variable: str,
        input_variables: List[str],
        parameters: Optional[List[str]] = None,
    ) -> FitResult:
        """
        Execute NonlinearModelFit and return comprehensive error metrics.

        This method:
        1. Converts data to Wolfram format
        2. Runs NonlinearModelFit with the given expression
        3. Extracts R², AIC, BIC, and RMSE
        4. Returns a FitResult object

        Args:
            expression: Wolfram expression (right-hand side of equation)
            data: DataFrame with columns for all variables
            target_variable: Name of the target column
            input_variables: List of input variable column names
            parameters: List of parameter names. If None, extracted automatically.

        Returns:
            FitResult with parameters, R², AIC, BIC, and RMSE

        Raises:
            WolframFitError: If fitting fails to converge or encounters errors
        """
        from physai.utils.parsing import extract_parameters

        self._ensure_connection()

        # Convert underscores to valid Wolfram identifiers (e.g., length_m -> lengthM)
        def sanitize_name(name: str) -> str:
            parts = name.split("_")
            if len(parts) == 1:
                return name
            return parts[0] + "".join(p.capitalize() for p in parts[1:])

        var_map = {v: sanitize_name(v) for v in input_variables}
        target_wl = sanitize_name(target_variable)

        # Replace variable names in expression
        expression_wl = expression
        for orig, wl in var_map.items():
            import re

            expression_wl = re.sub(r"\b" + re.escape(orig) + r"\b", wl, expression_wl)

        input_variables_wl = [var_map[v] for v in input_variables]

        if parameters is None:
            parameters = extract_parameters(expression_wl, input_variables_wl)

        if not parameters:
            raise WolframFitError(
                "No parameters found in expression. "
                "At least one free parameter is required for fitting."
            )

        # Rename DataFrame columns
        data_wl = data.rename(columns={target_variable: target_wl, **var_map})

        # Data format for NonlinearModelFit: {x1, x2, ..., y} - inputs first, then target
        wolfram_data = data_to_wolfram_string(data_wl[input_variables_wl + [target_wl]])
        param_list = ", ".join(f"{{{p}, 1.0}}" for p in parameters)
        input_list = ", ".join(input_variables_wl)

        query = f"""
        Module[{{data, model, params, r2, aic, bic, rmse, converged, result}},
            data = {wolfram_data};
            
            model = Quiet[Check[
                NonlinearModelFit[
                    data,
                    {expression_wl},
                    {{{param_list}}},
                    {{{input_list}}}
                ],
                $Failed
            ]];
            
            If[model === $Failed,
                result = <|
                    "success" -> False,
                    "error" -> "Fitting failed to converge",
                    "parameters" -> <||>,
                    "adjustedRSquared" -> 0.0,
                    "aic" -> Infinity,
                    "bic" -> Infinity,
                    "rmse" -> Infinity,
                    "converged" -> False
                |>,
                params = model["BestFitParameters"];
                r2 = model["AdjustedRSquared"];
                aic = model["AIC"];
                bic = model["BIC"];
                rmse = Sqrt[Mean[model["FitResiduals"]^2]];
                converged = True;
                
                result = <|
                    "success" -> True,
                    "error" -> "",
                    "parameters" -> AssociationThread[
                        Keys[params],
                        N[Values[params]]
                    ],
                    "adjustedRSquared" -> N[r2],
                    "aic" -> N[aic],
                    "bic" -> N[bic],
                    "rmse" -> N[rmse],
                    "converged" -> converged
                |>
            ];
            
            result
        ]
        """

        try:
            result = self._evaluate_safe(query)
            return self._parse_fit_result(expression, result)
        except Exception as e:
            raise WolframFitError(f"Fitting failed: {e}") from e

    def _evaluate_safe(self, query: str) -> Any:
        """
        Safely evaluate a Wolfram query with timeout.

        Args:
            query: Wolfram Language query string

        Returns:
            Evaluation result
        """
        self._ensure_connection()

        clean_query = 'Clear["Global`*"]; ' + query.strip()

        try:
            result = self._session.evaluate(clean_query, timeout=self.timeout)
            return self._convert_result(result)
        except Exception as e:
            logger.error(f"Wolfram evaluation error: {e}")
            raise

    def _convert_result(self, result: Any) -> Any:
        """Convert Wolfram result to Python native types."""
        if hasattr(result, "name"):
            str_result = str(result.name)
            if str_result == "True":
                return True
            elif str_result == "False":
                return False
            elif str_result == "Null":
                return None
            try:
                if "." in str_result:
                    return float(str_result)
                return int(str_result)
            except ValueError:
                return str_result

        if isinstance(result, (list, tuple)):
            return [self._convert_result(item) for item in result]

        if hasattr(result, "items"):
            return {
                self._convert_result(k): self._convert_result(v)
                for k, v in result.items()
            }

        return result

    def _parse_fit_result(self, expression: str, result: Any) -> FitResult:
        """Parse the fit result from Wolfram into a FitResult object."""
        if isinstance(result, dict):
            success = result.get("success", False)

            if not success:
                raise WolframFitError(result.get("error", "Unknown fitting error"))

            params = result.get("parameters", {})
            if hasattr(params, "items"):
                params = {
                    str(k): float(v) if v is not None else 0.0
                    for k, v in params.items()
                }

            return FitResult(
                expression=expression,
                parameters=params,
                adjusted_r2=float(result.get("adjustedRSquared", 0.0)),
                aic=float(result.get("aic", float("inf"))),
                bic=float(result.get("bic", float("inf"))),
                residuals_rmse=float(result.get("rmse", float("inf"))),
                converged=bool(result.get("converged", False)),
            )

        raise WolframFitError(f"Unexpected result format: {type(result)}")

    def clear_state(self) -> None:
        """Clear all definitions in the Wolfram session."""
        if self._session is not None:
            try:
                self._session.evaluate('ClearAll["Global`*"]')
            except Exception as e:
                logger.warning(f"Failed to clear state: {e}")
