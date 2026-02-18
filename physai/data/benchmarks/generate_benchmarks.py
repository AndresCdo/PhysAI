"""Benchmark dataset generator for PhysAI."""

from typing import List, Optional, Union

import math
import random
from pathlib import Path


def generate_pendulum_dataset(
    output_path: Union[str, Path],
    lengths: Optional[List[float]] = None,
    g: float = 9.81,
    noise_std: float = 0.02,
    seed: int = 42,
) -> str:
    """
    Generate a pendulum dataset with T = 2π√(L/g) + noise.

    Args:
        output_path: Path to save the CSV file.
        lengths: List of pendulum lengths in meters.
        g: Gravitational acceleration (default 9.81 m/s²).
        noise_std: Standard deviation of Gaussian noise.
        seed: Random seed for reproducibility.

    Returns:
        Path to the generated file.
    """
    random.seed(seed)

    if lengths is None:
        lengths = [
            0.10,
            0.15,
            0.20,
            0.25,
            0.30,
            0.40,
            0.50,
            0.60,
            0.70,
            0.80,
            0.90,
            1.00,
            1.20,
            1.50,
            1.80,
            2.00,
            2.50,
            3.00,
        ]

    rows = ["length_m,period_s"]
    for L in lengths:
        T_theoretical = 2 * math.pi * math.sqrt(L / g)
        T_noisy = T_theoretical + random.gauss(0, noise_std)
        rows.append(f"{L:.2f},{T_noisy:.2f}")

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        f.write("\n".join(rows))

    return str(path)


def generate_freefall_dataset(
    output_path: Union[str, Path],
    times: Optional[List[float]] = None,
    g: float = 9.81,
    noise_std: float = 0.1,
    seed: int = 42,
) -> str:
    """
    Generate a freefall dataset with s = 0.5 * g * t² + noise.

    Args:
        output_path: Path to save the CSV file.
        times: List of times in seconds.
        g: Gravitational acceleration (default 9.81 m/s²).
        noise_std: Standard deviation of Gaussian noise.
        seed: Random seed for reproducibility.

    Returns:
        Path to the generated file.
    """
    random.seed(seed)

    if times is None:
        times = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]

    rows = ["time_s,distance_m"]
    for t in times:
        s_theoretical = 0.5 * g * t**2
        s_noisy = s_theoretical + random.gauss(0, noise_std)
        rows.append(f"{t:.1f},{s_noisy:.2f}")

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        f.write("\n".join(rows))

    return str(path)


def generate_ohms_law_dataset(
    output_path: Union[str, Path],
    resistances: Optional[List[float]] = None,
    voltages: Optional[List[float]] = None,
    noise_std: float = 0.01,
    seed: int = 42,
) -> str:
    """
    Generate an Ohm's Law dataset with I = V/R + noise.

    Args:
        output_path: Path to save the CSV file.
        resistances: List of resistances in Ohms.
        voltages: List of voltages in Volts.
        noise_std: Standard deviation of Gaussian noise (relative).
        seed: Random seed for reproducibility.

    Returns:
        Path to the generated file.
    """
    random.seed(seed)

    if resistances is None:
        resistances = [100, 200, 300, 500, 1000]
    if voltages is None:
        voltages = [1, 2, 3, 5, 10, 12]

    rows = ["voltage_v,resistance_ohm,current_a"]
    for V in voltages:
        for R in resistances:
            I_theoretical = V / R
            I_noisy = I_theoretical * (1 + random.gauss(0, noise_std))
            rows.append(f"{V},{R},{I_noisy:.6f}")

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        f.write("\n".join(rows))

    return str(path)


if __name__ == "__main__":
    benchmarks_dir = Path(__file__).parent

    print("Generating benchmark datasets...")

    pendulum_path = generate_pendulum_dataset(
        benchmarks_dir / "pendulum_simple.csv", noise_std=0.02, seed=42
    )
    print(f"  Created: {pendulum_path}")

    freefall_path = generate_freefall_dataset(
        benchmarks_dir / "freefall.csv", noise_std=0.1, seed=42
    )
    print(f"  Created: {freefall_path}")

    ohms_path = generate_ohms_law_dataset(
        benchmarks_dir / "ohms_law.csv", noise_std=0.01, seed=42
    )
    print(f"  Created: {ohms_path}")

    print("Done!")
