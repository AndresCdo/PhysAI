"""Data serialization utilities for Wolfram Language compatibility."""

from typing import List, Union
import pandas as pd
import numpy as np


def data_to_wolfram_string(df: pd.DataFrame, precision: int = 10) -> str:
    """
    Serialize pandas DataFrame to Wolfram Language nested list string.

    Efficient O(n) serialization for small to medium datasets.
    For large datasets, consider using data_to_wolfram() with wolframclient.

    Args:
        df: DataFrame with columns corresponding to variables
        precision: Number of significant digits for floats

    Returns:
        Wolfram-compatible string like "{{0.1, 0.63}, {0.25, 1.0}}"

    Example:
        >>> df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        >>> data_to_wolfram_string(df)
        "{{1, 3}, {2, 4}}"
    """
    rows: List[str] = []

    for _, row in df.iterrows():
        values: List[str] = []
        for val in row:
            if pd.isna(val):
                values.append("Indeterminate")
            elif isinstance(val, (int, np.integer)):
                values.append(str(val))
            elif isinstance(val, (float, np.floating)):
                values.append(f"{val:.{precision}g}")
            else:
                values.append(str(val))
        rows.append("{" + ", ".join(values) + "}")

    return "{" + ", ".join(rows) + "}"


def data_to_wolfram(df: pd.DataFrame):
    """
    Serialize pandas DataFrame to Wolfram NumericArray.

    Requires wolframclient library. Returns a Wolfram Language expression
    that can be directly evaluated.

    Args:
        df: DataFrame with numeric columns only

    Returns:
        wl.NumericArray expression

    Raises:
        ImportError: If wolframclient is not installed
        ValueError: If DataFrame contains non-numeric data
    """
    try:
        from wolframclient.language import wl
    except ImportError as e:
        raise ImportError(
            "wolframclient is required for data_to_wolfram(). "
            "Install with: pip install wolframclient"
        ) from e

    if df.isna().any().any():
        raise ValueError(
            "DataFrame contains NaN values; clean data before serialization"
        )

    numeric_types = {"int64", "float64", "int32", "float32"}
    for col in df.columns:
        if df[col].dtype not in numeric_types:
            raise ValueError(
                f"Column '{col}' has non-numeric type {df[col].dtype}. "
                "Use data_to_wolfram_string() for mixed types."
            )

    arr = df.values.tolist()
    return wl.NumericArray(arr, "Real64")


def variable_to_wolfram_unit(variable_name: str, unit: str) -> str:
    """
    Create a Wolfram Language Quantity expression for a variable.

    Args:
        variable_name: Name of the variable
        unit: Unit string (e.g., "Meters", "Seconds")

    Returns:
        Wolfram expression like "length -> Quantity[1, \"Meters\"]"
    """
    return f'{variable_name} -> Quantity[1, "{unit}"]'


def dict_to_wolfram(d: dict) -> str:
    """
    Convert a Python dict to Wolfram Association syntax.

    Args:
        d: Dictionary with string keys

    Returns:
        Wolfram Association string like "<|\"a\" -> 1, \"b\" -> 2|>"
    """
    pairs = [f'"{k}" -> {repr(v)}' for k, v in d.items()]
    return "<|" + ", ".join(pairs) + "|>"


def list_to_wolfram(lst: List) -> str:
    """
    Convert a Python list to Wolfram List syntax.

    Args:
        lst: List of values

    Returns:
        Wolfram List string like "{1, 2, 3}"
    """
    elements = []
    for item in lst:
        if isinstance(item, str):
            elements.append(f'"{item}"')
        elif isinstance(item, (int, float)):
            elements.append(str(item))
        elif isinstance(item, list):
            elements.append(list_to_wolfram(item))
        else:
            elements.append(str(item))
    return "{" + ", ".join(elements) + "}"
