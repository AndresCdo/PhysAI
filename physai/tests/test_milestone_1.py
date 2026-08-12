"""Tests for PhysAI Milestone 1: Damped Pendulum."""

from pathlib import Path

import pytest

from physai.core.researcher import SymbolicResearcher, ResearcherConfig


@pytest.fixture
def damped_pendulum_path():
    """Path to damped pendulum benchmark dataset."""
    return Path(__file__).parent.parent / "data" / "benchmarks" / "pendulum_damped.csv"


class TestDampedPendulumData:
    """Tests for the damped pendulum dataset."""

    def test_dataset_exists(self, damped_pendulum_path):
        """Verify the damped pendulum dataset exists."""
        assert damped_pendulum_path.exists(), (
            f"Dataset not found: {damped_pendulum_path}"
        )

    def test_dataset_format(self, damped_pendulum_path):
        """Verify the dataset has the correct columns."""
        import pandas as pd

        df = pd.read_csv(damped_pendulum_path)

        assert "length_m" in df.columns, "Missing length_m column"
        assert "time_s" in df.columns, "Missing time_s column"
        assert "amplitude_m" in df.columns, "Missing amplitude_m column"

    def test_dataset_values(self, damped_pendulum_path):
        """Verify the dataset follows the expected formula."""
        import pandas as pd
        df = pd.read_csv(damped_pendulum_path)

        # Expected formula: A = a * sqrt(L) * exp(-b*t)
        # where a ≈ 2π/√g ≈ 2.006 and b ≈ 0.05. Those constants are not
        # asserted here; see issue #10.

        # Check that amplitude decreases with time for same length
        for length in df["length_m"].unique():
            subset = df[df["length_m"] == length].sort_values("time_s")
            amplitudes = subset["amplitude_m"].values

            # Amplitude should decrease with time
            for i in range(len(amplitudes) - 1):
                assert amplitudes[i] > amplitudes[i + 1], (
                    f"Amplitude should decrease with time at L={length}"
                )

    def test_amplitude_increases_with_length(self, damped_pendulum_path):
        """At fixed time, amplitude should increase with length."""
        import pandas as pd

        df = pd.read_csv(damped_pendulum_path)

        # At t=0, amplitude should be proportional to sqrt(L)
        t0_data = df[df["time_s"] == 0].sort_values("length_m")
        amplitudes = t0_data["amplitude_m"].values
        lengths = t0_data["length_m"].values

        # Check amplitude increases with length
        for i in range(len(amplitudes) - 1):
            assert amplitudes[i] < amplitudes[i + 1], (
                f"Amplitude at t=0 should increase with length: "
                f"L={lengths[i]} gives {amplitudes[i]}, "
                f"L={lengths[i + 1]} gives {amplitudes[i + 1]}"
            )


class TestDampedPendulumUnits:
    """Unit tests for damped pendulum components."""

    def test_exp_function_in_constants(self):
        """Verify Exp is available as a mathematical function."""
        from physai.core.constants import MATHEMATICAL_FUNCTIONS

        assert "Exp" in MATHEMATICAL_FUNCTIONS

    def test_exponential_expression_validation(self):
        """Test that exponential expressions are valid."""
        from physai.utils.parsing import is_valid_expression

        valid, error = is_valid_expression("a * Sqrt[x] * Exp[-b * t]")
        assert valid, f"Expression should be valid: {error}"

    def test_extract_parameters_with_exp(self):
        """Test parameter extraction with exponential expression."""
        from physai.utils.parsing import extract_parameters

        params = extract_parameters(
            "a * Sqrt[length_m] * Exp[-b * time_s]", ["length_m", "time_s"]
        )
        assert "a" in params
        assert "b" in params
        assert "length_m" not in params
        assert "time_s" not in params


@pytest.mark.skip(reason="Requires Ollama + Wolfram")
class TestMilestone1Integration:
    """
    Milestone 1: Discover A = a × √L × e^(-bt) from damped pendulum data.

    This test requires:
    - Ollama running with granite4:1b model
    - Wolfram Kernel with valid license
    """

    def test_damped_pendulum_discovery(self, damped_pendulum_path):
        """Run the full discovery process for damped pendulum."""
        if not damped_pendulum_path.exists():
            pytest.skip("Damped pendulum dataset not found")

        config = ResearcherConfig(
            max_iterations=25, r2_threshold=0.90, llm_temperature=0.6
        )

        with SymbolicResearcher(model="granite4:1b", config=config) as researcher:
            result = researcher.discover(
                dataset_path=str(damped_pendulum_path),
                target="amplitude_m",
                inputs=["length_m", "time_s"],
            )

            assert result.success, f"Discovery failed: {result.error_message}"
            assert result.final_r2 is not None and result.final_r2 >= 0.85, (
                f"R² too low: {result.final_r2}"
            )

            assert result.best_expression is not None

            # The expression should contain both Sqrt (for length) and Exp (for time)
            has_sqrt = "Sqrt" in result.best_expression
            has_exp = "Exp" in result.best_expression
            has_power = "Power" in result.best_expression and "^" in str(
                result.best_expression
            )

            assert has_sqrt or has_power, (
                f"Expected √L dependence, got: {result.best_expression}"
            )
            assert has_exp, (
                f"Expected exponential decay Exp[-b*t], got: {result.best_expression}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
