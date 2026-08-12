"""Tests for PhysAI Neuro-Symbolic Engine."""

from pathlib import Path

import pytest

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
    normalize_unit,
    get_unit_dimension,
)
from physai.utils.parsing import (
    extract_parameters,
    is_valid_expression,
    expression_complexity,
)
from physai.utils.feedback import (
    extract_wolfram_expression,
    generate_qualitative_feedback,
)
from physai.utils.serialization import data_to_wolfram_string


class TestVariable:
    """Tests for Variable dataclass."""

    def test_variable_creation(self):
        v = Variable(name="length", unit="Meters", description="Pendulum length")
        assert v.name == "length"
        assert v.unit == "Meters"
        assert v.symbol == "length"

    def test_variable_with_custom_symbol(self):
        v = Variable(name="length_m", unit="Meters", symbol="L")
        assert v.symbol == "L"

    def test_variable_repr(self):
        v = Variable(name="length", unit="Meters")
        assert "length" in repr(v)
        assert "Meters" in repr(v)


class TestUnitDimension:
    """Tests for UnitDimension."""

    def test_dimensionless(self):
        d = UnitDimension()
        assert "dimensionless" in repr(d).lower() or repr(d) == ""

    def test_length(self):
        d = UnitDimension(length=1)
        assert "L" in repr(d)

    def test_velocity(self):
        v = UnitDimension(length=1, time=-1)
        assert v.length == 1
        assert v.time == -1

    def test_multiply(self):
        d1 = UnitDimension(length=1)
        d2 = UnitDimension(time=-2)
        result = d1.multiply(d2)
        assert result.length == 1
        assert result.time == -2

    def test_divide(self):
        d1 = UnitDimension(length=1)
        d2 = UnitDimension(time=1)
        result = d1.divide(d2)
        assert result.length == 1
        assert result.time == -1

    def test_equality(self):
        d1 = UnitDimension(length=1, time=-2)
        d2 = UnitDimension(length=1, time=-2)
        d3 = UnitDimension(length=2, time=-2)
        assert d1 == d2
        assert d1 != d3


class TestConstants:
    """Tests for physical constants."""

    def test_reserved_constants_contains_common(self):
        assert "g" in RESERVED_CONSTANTS
        assert "pi" in RESERVED_CONSTANTS
        assert "c" in RESERVED_CONSTANTS

    def test_physical_units_contains_si(self):
        assert "Meters" in PHYSICAL_UNITS
        assert "Seconds" in PHYSICAL_UNITS
        assert "Kilograms" in PHYSICAL_UNITS

    def test_get_unit_dimension(self):
        d = get_unit_dimension("Meters")
        assert d.length == 1
        assert d.time == 0

    def test_normalize_unit(self):
        assert normalize_unit("meter") == "Meters"
        assert normalize_unit("Meters") == "Meters"


class TestParsing:
    """Tests for expression parsing utilities."""

    def test_extract_parameters_simple(self):
        params = extract_parameters("a * x + b", ["x"])
        assert "a" in params
        assert "b" in params
        assert "x" not in params

    def test_extract_parameters_with_constants(self):
        params = extract_parameters("a * Sqrt[L / g]", ["L"])
        assert "a" in params
        assert "g" not in params
        assert "L" not in params

    def test_extract_parameters_no_params(self):
        params = extract_parameters("x + y", ["x", "y"])
        assert len(params) == 0

    def test_is_valid_expression_balanced(self):
        valid, _ = is_valid_expression("a * Sqrt[x]")
        assert valid

    def test_is_valid_expression_unbalanced_brackets(self):
        valid, error = is_valid_expression("a * Sqrt[x")
        assert not valid
        assert "bracket" in error.lower()

    def test_is_valid_expression_empty(self):
        valid, _ = is_valid_expression("")
        assert not valid

    def test_expression_complexity(self):
        simple = expression_complexity("a * x")
        complex_expr = expression_complexity("a * Sin[b * x] + c * Exp[d * y]")
        assert complex_expr > simple


class TestFeedback:
    """Tests for feedback generation utilities."""

    def test_extract_wolfram_expression_simple(self):
        output = "a * Sqrt[length_m]"
        result = extract_wolfram_expression(output)
        assert result == "a * Sqrt[length_m]"

    def test_extract_wolfram_expression_with_markdown(self):
        output = (
            "Sure! Here's your equation:\n```wolfram\na * Sqrt[x]\n```\nHope it helps!"
        )
        result = extract_wolfram_expression(output)
        assert "Sqrt" in result

    def test_extract_wolfram_expression_multiline(self):
        output = "Here it is:\na * x + b"
        result = extract_wolfram_expression(output)
        assert "a * x + b" in result

    def test_generate_qualitative_feedback_good_fit(self):
        result = FitResult(
            expression="a * Sqrt[x]",
            parameters={"a": 2.0},
            adjusted_r2=0.98,
            aic=-50,
            bic=-45,
            residuals_rmse=0.05,
            converged=True,
        )
        feedback = generate_qualitative_feedback(result)
        assert len(feedback) > 0

    def test_generate_qualitative_feedback_poor_fit(self):
        result = FitResult(
            expression="a * x",
            parameters={"a": 1.0},
            adjusted_r2=0.3,
            aic=100,
            bic=105,
            residuals_rmse=0.5,
            converged=True,
        )
        feedback = generate_qualitative_feedback(result)
        assert "different" in feedback.lower() or "partial" in feedback.lower()


class TestSerialization:
    """Tests for data serialization utilities."""

    def test_data_to_wolfram_string_simple(self):
        import pandas as pd

        df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
        result = data_to_wolfram_string(df)
        assert result.startswith("{")
        assert result.endswith("}")
        assert "1" in result
        assert "4" in result

    def test_data_to_wolfram_string_floats(self):
        import pandas as pd

        df = pd.DataFrame({"length": [0.1, 0.5, 1.0], "period": [0.63, 1.42, 2.01]})
        result = data_to_wolfram_string(df)
        assert "0.1" in result or "1e-01" in result.lower()


class TestAttempt:
    """Tests for Attempt dataclass."""

    def test_attempt_feedback_string_success(self):
        attempt = Attempt(
            expression="a * Sqrt[x]",
            status=AttemptStatus.SUCCESS,
            adjusted_r2=0.99,
            iteration=1,
        )
        feedback = attempt.to_feedback_string()
        assert "a * Sqrt[x]" in feedback
        assert "0.99" in feedback or "Success" in feedback

    def test_attempt_feedback_string_error(self):
        attempt = Attempt(
            expression="a * x[",
            status=AttemptStatus.SYNTAX_ERROR,
            error_message="Unbalanced bracket",
            iteration=1,
        )
        feedback = attempt.to_feedback_string()
        assert "Syntax" in feedback or "error" in feedback.lower()


class TestFitResult:
    """Tests for FitResult dataclass."""

    def test_is_good_fit(self):
        result = FitResult(
            expression="a * x",
            parameters={"a": 2.0},
            adjusted_r2=0.97,
            aic=-100,
            bic=-95,
            residuals_rmse=0.02,
            converged=True,
        )
        assert result.is_good_fit()

    def test_is_poor_fit(self):
        result = FitResult(
            expression="a * x",
            parameters={"a": 2.0},
            adjusted_r2=0.5,
            aic=100,
            bic=105,
            residuals_rmse=0.5,
            converged=True,
        )
        assert not result.is_good_fit()

    def test_combined_score(self):
        good_result = FitResult(
            expression="a * x",
            parameters={"a": 2.0},
            adjusted_r2=0.99,
            aic=-100,
            bic=-95,
            residuals_rmse=0.02,
            converged=True,
        )
        poor_result = FitResult(
            expression="a * x",
            parameters={"a": 2.0},
            adjusted_r2=0.5,
            aic=100,
            bic=105,
            residuals_rmse=0.5,
            converged=True,
        )
        assert good_result.combined_score() > poor_result.combined_score()


class TestDiscoveryResult:
    """Tests for DiscoveryResult dataclass."""

    def test_success_summary(self):
        result = FitResult(
            expression="a * Sqrt[x]",
            parameters={"a": 2.0},
            adjusted_r2=0.98,
            aic=-50,
            bic=-45,
            residuals_rmse=0.05,
            converged=True,
        )
        discovery = DiscoveryResult(
            success=True,
            best_expression="a * Sqrt[x]",
            best_result=result,
            total_iterations=5,
        )
        summary = discovery.summary()
        assert "successful" in summary.lower()
        assert "a * Sqrt[x]" in summary

    def test_failure_summary(self):
        discovery = DiscoveryResult(
            success=False, error_message="Did not converge", total_iterations=20
        )
        summary = discovery.summary()
        assert "failed" in summary.lower()


@pytest.fixture
def pendulum_data_path():
    """Path to pendulum benchmark dataset."""
    return Path(__file__).parent.parent / "data" / "benchmarks" / "pendulum_simple.csv"


class TestIntegration:
    """Integration tests (require external dependencies)."""

    @pytest.mark.skip(reason="Requires Wolfram Kernel")
    def test_wolfram_evaluator_connection(self):
        """Test that we can connect to Wolfram Kernel."""
        from physai.core.wolfram_evaluator import WolframEvaluator

        with WolframEvaluator() as evaluator:
            # Asserting on the live kernel session is the point of this test.
            assert evaluator._session is not None  # pylint: disable=protected-access

    @pytest.mark.skip(reason="Requires Ollama server")
    def test_ollama_connection(self):
        """Test that we can connect to Ollama."""
        from physai.core.llm_interface import OllamaInterface

        interface = OllamaInterface(model="granite4:1b")
        assert interface.check_connection()

    @pytest.mark.skip(reason="Requires full stack")
    def test_milestone_0_pendulum(self, pendulum_data_path):
        """
        Milestone 0: Rediscover T = 2π√(L/g) from pendulum data.

        This test requires:
        - Ollama running with granite4:1b model
        - Wolfram Kernel with valid license
        """
        from physai.core.researcher import SymbolicResearcher

        if not pendulum_data_path.exists():
            pytest.skip("Pendulum dataset not found")

        with SymbolicResearcher(model="granite4:1b") as researcher:
            result = researcher.discover(
                dataset_path=str(pendulum_data_path),
                target="period_s",
                inputs=["length_m"],
            )

            assert result.success, f"Discovery failed: {result.error_message}"
            assert result.final_r2 is not None and result.final_r2 >= 0.90, (
                f"R² too low: {result.final_r2}"
            )

            assert result.best_expression is not None
            assert "Sqrt" in result.best_expression or "Power" in result.best_expression


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
