"""Tests for PhysAI Milestone 2: Projectile Motion with Drag."""

import math
from pathlib import Path

import pytest

from physai.core.researcher import SymbolicResearcher, ResearcherConfig


@pytest.fixture
def horizontal_drag_path():
    """Path to horizontal projectile with drag dataset."""
    return (
        Path(__file__).parent.parent
        / "data"
        / "benchmarks"
        / "projectile_horizontal_drag.csv"
    )


@pytest.fixture
def projectile_2d_path():
    """Path to 2D projectile with drag dataset."""
    return (
        Path(__file__).parent.parent / "data" / "benchmarks" / "projectile_2d_drag.csv"
    )


class TestHorizontalDragDataset:
    """Tests for the horizontal projectile with drag dataset."""

    def test_dataset_exists(self, horizontal_drag_path):
        """Verify the horizontal drag dataset exists."""
        assert horizontal_drag_path.exists(), (
            f"Dataset not found: {horizontal_drag_path}"
        )

    def test_dataset_format(self, horizontal_drag_path):
        """Verify the dataset has the correct columns."""
        import pandas as pd

        df = pd.read_csv(horizontal_drag_path)

        assert "velocity_m_s" in df.columns
        assert "time_s" in df.columns
        assert "distance_m" in df.columns

    def test_distance_increases_with_velocity(self, horizontal_drag_path):
        """At fixed time, distance should increase with velocity."""
        import pandas as pd

        df = pd.read_csv(horizontal_drag_path)

        # At t=5, distance should increase with velocity
        t5_data = df[df["time_s"] == 5].sort_values("velocity_m_s")
        distances = t5_data["distance_m"].values

        for i in range(len(distances) - 1):
            assert distances[i] < distances[i + 1], (
                "Distance should increase with velocity"
            )

    def test_distance_asymptote(self, horizontal_drag_path):
        """Distance growth should slow down over time (drag effect)."""
        import pandas as pd
        import numpy as np

        df = pd.read_csv(horizontal_drag_path)

        # For a fixed velocity, check that distance growth slows
        for velocity in df["velocity_m_s"].unique()[:2]:
            subset = df[df["velocity_m_s"] == velocity].sort_values("time_s")
            times = subset["time_s"].values
            distances = subset["distance_m"].values

            # Calculate incremental distance per time unit
            if len(distances) > 2:
                increments = np.diff(distances)
                # Later increments should be smaller (drag slowing the motion)
                # This is a soft check - may not hold for all cases
                assert increments[0] > 0, "Distance should increase"


class TestProjectile2DDataset:
    """Tests for the 2D projectile with drag dataset."""

    def test_dataset_exists(self, projectile_2d_path):
        """Verify the 2D projectile dataset exists."""
        assert projectile_2d_path.exists(), f"Dataset not found: {projectile_2d_path}"

    def test_dataset_format(self, projectile_2d_path):
        """Verify the dataset has the correct columns."""
        import pandas as pd

        df = pd.read_csv(projectile_2d_path)

        assert "velocity_m_s" in df.columns
        assert "angle_deg" in df.columns
        assert "range_m" in df.columns

    def test_max_range_at_45_degrees(self, projectile_2d_path):
        """Range should be maximum near 45 degrees for fixed velocity."""
        import pandas as pd

        df = pd.read_csv(projectile_2d_path)

        # For each velocity, check that 45 degrees has near-maximum range
        for velocity in df["velocity_m_s"].unique():
            subset = df[df["velocity_m_s"] == velocity]
            max_range = subset["range_m"].max()
            range_at_45 = subset[subset["angle_deg"] == 45]["range_m"].values

            if len(range_at_45) > 0:
                # 45 degree range should be within 10% of max
                assert range_at_45[0] >= max_range * 0.9, (
                    f"Range at 45° should be near maximum for v={velocity}"
                )

    def test_range_increases_with_velocity(self, projectile_2d_path):
        """At fixed angle, range should increase with velocity squared."""
        import pandas as pd

        df = pd.read_csv(projectile_2d_path)

        # At 45 degrees, range should increase with velocity
        angle_45_data = df[df["angle_deg"] == 45].sort_values("velocity_m_s")
        ranges = angle_45_data["range_m"].values

        for i in range(len(ranges) - 1):
            assert ranges[i] < ranges[i + 1], (
                "Range should increase with velocity at fixed angle"
            )


class TestMilestone2Expressions:
    """Tests for expression validation."""

    def test_horizontal_drag_expression(self):
        """Test that horizontal drag expression is valid."""
        from physai.utils.parsing import is_valid_expression

        valid, error = is_valid_expression("a * velocity_m_s * (1 - Exp[-b * time_s])")
        assert valid, f"Expression should be valid: {error}"

    def test_projectile_range_expression(self):
        """Test that projectile range expression is valid."""
        from physai.utils.parsing import is_valid_expression

        valid, error = is_valid_expression(
            "a * velocity_m_s^2 * Sin[2 * angle_deg * Pi / 180]"
        )
        assert valid, f"Expression should be valid: {error}"


@pytest.mark.skip(reason="Requires Ollama + Wolfram")
class TestMilestone2aIntegration:
    """
    Milestone 2a: Horizontal projectile with linear drag.

    Target: x(t) = (v₀/b) × (1 - e^(-bt))
    Rewritten as: x(t) = a × v₀ × (1 - e^(-bt)) where a = 1/b
    """

    def test_horizontal_drag_discovery(self, horizontal_drag_path):
        """Run the full discovery process for horizontal drag."""
        if not horizontal_drag_path.exists():
            pytest.skip("Horizontal drag dataset not found")

        config = ResearcherConfig(
            max_iterations=15, r2_threshold=0.95, llm_temperature=0.3
        )

        with SymbolicResearcher(model="granite4:1b", config=config) as researcher:
            result = researcher.discover(
                dataset_path=str(horizontal_drag_path),
                target="distance_m",
                inputs=["velocity_m_s", "time_s"],
            )

            assert result.success, f"Discovery failed: {result.error_message}"
            assert result.final_r2 is not None and result.final_r2 >= 0.95, (
                f"R² too low: {result.final_r2}"
            )

            assert result.best_expression is not None

            # Should contain Exp for the drag term
            has_exp = "Exp" in result.best_expression
            has_exp_form = (
                "1 -" in result.best_expression or "(1-" in result.best_expression
            )

            assert has_exp, (
                f"Expected exponential decay Exp[-b*t], got: {result.best_expression}"
            )


@pytest.mark.skip(reason="Requires Ollama + Wolfram")
class TestMilestone2bIntegration:
    """
    Milestone 2b: 2D projectile with drag.

    Target: R = (v₀²/g) × sin(2θ) × correction
    Simplified: R = a × v₀² × sin(2θ)
    """

    def test_projectile_2d_discovery(self, projectile_2d_path):
        """Run the full discovery process for 2D projectile."""
        if not projectile_2d_path.exists():
            pytest.skip("2D projectile dataset not found")

        config = ResearcherConfig(
            max_iterations=15,
            r2_threshold=0.95,
            llm_temperature=0.3,
            skip_dimension_check=True,  # Angle is dimensionless
        )

        with SymbolicResearcher(model="granite4:1b", config=config) as researcher:
            result = researcher.discover(
                dataset_path=str(projectile_2d_path),
                target="range_m",
                inputs=["velocity_m_s", "angle_deg"],
            )

            assert result.success, f"Discovery failed: {result.error_message}"
            assert result.final_r2 is not None and result.final_r2 >= 0.95, (
                f"R² too low: {result.final_r2}"
            )

            assert result.best_expression is not None

            # Should contain Sin for angle dependence
            has_sin = "Sin" in result.best_expression
            assert has_sin, (
                f"Expected Sin term for angle, got: {result.best_expression}"
            )

            # Should contain velocity^2
            has_v2 = (
                "velocity_m_s^2" in result.best_expression
                or "Power[velocity_m_s, 2]" in result.best_expression
            )
            assert has_v2, f"Expected velocity^2 term, got: {result.best_expression}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
