"""Expression parsing utilities for Wolfram Language code."""

import re
from typing import List, Set, Tuple

from physai.core.constants import RESERVED_CONSTANTS, MATHEMATICAL_FUNCTIONS


def extract_parameters(expression: str, input_variables: List[str]) -> List[str]:
    """
    Extract free parameters from a Wolfram expression.

    Parameters are single lowercase letters that are:
    - Not in RESERVED_CONSTANTS (g, c, pi, e, etc.)
    - Not in input_variables
    - Not function names

    Args:
        expression: Wolfram Language expression string
        input_variables: List of variable names that are inputs

    Returns:
        Sorted list of unique parameter names

    Examples:
        >>> extract_parameters("a * Sqrt[L / g]", ["L"])
        ['a']
        >>> extract_parameters("a * x^2 + b * x + c", ["x"])
        ['a', 'b', 'c']
    """
    exclude: Set[str] = (
        RESERVED_CONSTANTS
        | set(input_variables)
        | MATHEMATICAL_FUNCTIONS
        | {"True", "False", "None", "List", "Rule", "Association"}
    )

    single_letter_pattern = r"\b([a-zA-Z])\b"
    candidates = set(re.findall(single_letter_pattern, expression))

    word_pattern = r"\b([a-zA-Z][a-zA-Z0-9]*)\s*\("
    function_names = set(re.findall(word_pattern, expression))
    exclude.update(function_names)

    pattern_with_subscript = r"\b([a-zA-Z])(?:_\{[^}]+\})?\b"
    subscript_vars = re.findall(pattern_with_subscript, expression)
    candidates.update(subscript_vars)

    parameters = [p for p in candidates if p not in exclude]

    return sorted(parameters)


def is_valid_expression(expression: str) -> Tuple[bool, str]:
    """
    Basic validation of Wolfram expression syntax.

    This is a lightweight check for common issues before sending to Wolfram.
    It does NOT guarantee the expression is valid Wolfram code.

    Args:
        expression: Wolfram Language expression string

    Returns:
        Tuple of (is_valid, error_message)

    Examples:
        >>> is_valid_expression("a * Sqrt[x]")
        (True, "")
        >>> is_valid_expression("a * Sqrt[x")
        (False, "Unbalanced brackets: 1 unclosed")
    """
    if not expression or not expression.strip():
        return False, "Empty expression"

    square_open = expression.count("[")
    square_close = expression.count("]")
    curly_open = expression.count("{")
    curly_close = expression.count("}")
    paren_open = expression.count("(")
    paren_close = expression.count(")")

    errors = []

    if square_open != square_close:
        diff = square_open - square_close
        if diff > 0:
            errors.append(f"{diff} unclosed square bracket(s)")
        else:
            errors.append(f"{-diff} extra closing square bracket(s)")

    if curly_open != curly_close:
        diff = curly_open - curly_close
        if diff > 0:
            errors.append(f"{diff} unclosed curly brace(s)")
        else:
            errors.append(f"{-diff} extra closing curly brace(s)")

    if paren_open != paren_close:
        diff = paren_open - paren_close
        if diff > 0:
            errors.append(f"{diff} unclosed parenthesis(es)")
        else:
            errors.append(f"{-diff} extra closing parenthesis(es)")

    quote_count = expression.count('"')
    if quote_count % 2 != 0:
        errors.append("Unbalanced string quotes")

    known_functions = MATHEMATICAL_FUNCTIONS | {
        "FindFit",
        "NonlinearModelFit",
        "LinearModelFit",
        "Fit",
        "Solve",
        "NSolve",
        "Reduce",
        "Simplify",
        "FullSimplify",
        "Expand",
        "Factor",
        "Together",
        "Apart",
        "Collect",
        "D",
        "Integrate",
        "NIntegrate",
        "Sum",
        "NSum",
        "Plot",
        "ListPlot",
        "Show",
        "Graphics",
        "Table",
        "Range",
        "Array",
        "ConstantArray",
        "Quantity",
        "UnitConvert",
        "UnitDimensions",
        "CompatibleUnitQ",
        "Mean",
        "StandardDeviation",
        "Variance",
        "Total",
        "First",
        "Last",
        "Rest",
        "Most",
        "Take",
        "Drop",
        "Select",
        "Cases",
        "Position",
        "Count",
        "Map",
        "Apply",
        "Fold",
        "Nest",
        "If",
        "Which",
        "Switch",
        "Piecewise",
        "Module",
        "Block",
        "With",
        "Function",
        "Rule",
        "RuleDelayed",
        "Replace",
        "ReplaceAll",
        "Part",
        "Extract",
        "Insert",
        "Delete",
        "Append",
        "Prepend",
    }

    func_pattern = r"\b([A-Z][a-zA-Z0-9]*)\s*\["
    found_functions = set(re.findall(func_pattern, expression))
    unknown_functions = found_functions - known_functions

    if unknown_functions:
        pass

    if errors:
        return False, "; ".join(errors)

    return True, ""


def normalize_expression(expression: str) -> str:
    """
    Normalize a Wolfram expression for comparison.

    Removes extra whitespace and standardizes formatting.

    Args:
        expression: Wolfram Language expression string

    Returns:
        Normalized expression string
    """
    normalized = re.sub(r"\s+", " ", expression.strip())
    normalized = re.sub(r"\s*([\[\]\{\}\(\)\+\-\*\/\^])\s*", r"\1", normalized)
    normalized = re.sub(r"(\d)\s+(\d)", r"\1 \2", normalized)

    return normalized


def expression_complexity(expression: str) -> int:
    """
    Estimate the complexity of an expression for Occam's Razor.

    Higher values indicate more complex expressions.

    Args:
        expression: Wolfram Language expression string

    Returns:
        Complexity score (higher = more complex)
    """
    score = 0

    score += len(re.findall(r"[+\-*/^]", expression))
    score += len(re.findall(r"\b(?:Sin|Cos|Tan|Log|Exp|Sqrt)\b", expression)) * 2
    score += len(re.findall(r"\[", expression))
    score += len(extract_parameters(expression, []))
    score += len(re.findall(r"\d+\.\d+", expression))

    return score


def suggest_simplification(expression: str) -> List[str]:
    """
    Suggest potential simplifications for an expression.

    Args:
        expression: Wolfram Language expression string

    Returns:
        List of suggestion strings
    """
    suggestions = []

    if expression_complexity(expression) > 10:
        suggestions.append("Consider simplifying the expression")

    params = extract_parameters(expression, [])
    if len(params) > 4:
        suggestions.append(
            f"Expression has {len(params)} parameters. "
            "Consider reducing to improve generalization."
        )

    nested_sqrt = re.search(r"Sqrt\s*\[\s*Sqrt", expression, re.IGNORECASE)
    if nested_sqrt:
        suggestions.append("Nested square roots can be simplified to a single power")

    double_negative = re.search(r"-\s*-", expression)
    if double_negative:
        suggestions.append("Double negative detected; simplify to positive")

    return suggestions
