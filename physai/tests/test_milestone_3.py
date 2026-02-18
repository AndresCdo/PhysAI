"""Tests for PhysAI Milestone 3: 1D Quantum Well (Schrödinger)."""

import math
from pathlib import Path

import pytest

from physai.core.researcher import SymbolicResearcher, ResearcherConfig


@pytest.fixture
def quantum_well_path():
    """Path to 1D quantum well dataset."""
    return Path(__file__).parent.parent / "data" / "benchmarks" / "quantum_well_1d.csv"


class TestQuantumWellDataset:
    """Tests for the 1D quantum well dataset."""

    def test_dataset_exists(self, quantum_well_path):
        """Verify the quantum well dataset exists."""
        assert quantum_well_path.exists(), f"Dataset not found: {quantum_well_path}"

    def test_dataset_format(self, quantum_well_path):
        """Verify the dataset has the correct columns."""
        import pandas as pd

        df = pd.read_csv(quantum_well_path)

        assert "quantum_number_n" in df.columns
        assert "well_width_nm" in df.columns
        assert "energy_ev" in df.columns

    def test_energy_increases_with_quantum_number(self, quantum_well_path):
        """At fixed well width, energy should increase with n²."""
        import pandas as pd

        df = pd.read_csv(quantum_well_path)

        # For fixed well width, energy should increase with quantum number
        for width in df["well_width_nm"].unique():
            subset = df[df["well_width_nm"] == width].sort_values("quantum_number_n")
            energies = subset["energy_ev"].values

            for i in range(len(energies) - 1):
                assert energies[i] < energies[i + 1], (
                    f"Energy should increase with n at L={width}"
                )

    def test_energy_decreases_with_well_width(self, quantum_well_path):
        """At fixed quantum number, energy should decrease with L²."""
        import pandas as pd

        df = pd.read_csv(quantum_well_path)

        # For fixed n, energy should decrease as well width increases
        for n in df["quantum_number_n"].unique():
            subset = df[df["quantum_number_n"] == n].sort_values("well_width_nm")
            energies = subset["energy_ev"].values

            for i in range(len(energies) - 1):
                assert energies[i] > energies[i + 1], (
                    f"Energy should decrease with L at n={n}"
                )

    def test_energy_scaling_law(self, quantum_well_path):
        """Verify E ∝ n² / L² relationship."""
        import pandas as pd
        import numpy as np

        df = pd.read_csv(quantum_well_path)

        # Check that E * L² / n² is approximately constant
        df["normalized_energy"] = (
            df["energy_ev"] * df["well_width_nm"] ** 2 / df["quantum_number_n"] ** 2
        )

        mean_normalized = df["normalized_energy"].mean()
        std_normalized = df["normalized_energy"].std()

        # Should be within 5% of constant
        relative_std = std_normalized / mean_normalized
        assert relative_std < 0.05, (
            f"Energy scaling law not followed: std/mean = {relative_std:.2%}"
        )


class TestMilestone3Expressions:
    """Tests for expression validation."""

    def test_quantum_well_expression(self):
        """Test that quantum well expression is valid."""
        from physai.utils.parsing import is_valid_expression

        valid, error = is_valid_expression("a * quantum_number_n^2 / well_width_nm^2")
        assert valid, f"Expression should be valid: {error}"

    def test_quantum_well_with_power(self):
        """Test alternative form with Power function."""
        from physai.utils.parsing import is_valid_expression

        valid, error = is_valid_expression(
            "a * Power[quantum_number_n, 2] * Power[well_width_nm, -2]"
        )
        assert valid, f"Expression should be valid: {error}"


@pytest.mark.skip(reason="Requires Ollama + Wolfram")
class TestMilestone3Integration:
    """
    Milestone 3: 1D Quantum Well (Particle in a Box).

    Target: E_n = (n²π²ℏ²) / (2mL²)
    Simplified: E = a × n² / L²

    where a = π²ℏ² / (2m) ≈ 37.6 eV·nm² for an electron.
    """

    def test_quantum_well_discovery(self, quantum_well_path):
        """Run the full discovery process for quantum well."""
        if not quantum_well_path.exists():
            pytest.skip("Quantum well dataset not found")

        config = ResearcherConfig(
            max_iterations=15,
            r2_threshold=0.95,
            llm_temperature=0.3,
            skip_dimension_check=True,
        )

        with SymbolicResearcher(model="granite4:1b", config=config) as researcher:
            result = researcher.discover(
                dataset_path=str(quantum_well_path),
                target="energy_ev",
                inputs=["quantum_number_n", "well_width_nm"],
            )

            assert result.success, f"Discovery failed: {result.error_message}"
            assert result.final_r2 is not None and result.final_r2 >= 0.95, (
                f"R² too low: {result.final_r2}"
            )

            assert result.best_expression is not None

            # Should contain n² (or n^2)
            has_n_squared = (
                "quantum_number_n^2" in result.best_expression
                or "Power[quantum_number_n, 2]" in result.best_expression
            )
            assert has_n_squared, f"Expected n² term, got: {result.best_expression}"

            # Should contain L² in denominator (or L^(-2))
            has_l_denominator = (
                "/" in result.best_expression
                or "well_width_nm^2" in result.best_expression
                or "Power[well_width_nm, -2]" in result.best_expression
                or "Power[well_width_nm, 2]" in result.best_expression
            )
            assert has_l_denominator, (
                f"Expected L² denominator, got: {result.best_expression}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
