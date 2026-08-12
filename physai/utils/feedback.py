"""Feedback generation utilities for LLM context."""

import re
from typing import List, Optional
from physai.core.types import FitResult, Attempt, AttemptStatus


def generate_qualitative_feedback(
    result: FitResult, previous_attempts: Optional[List[Attempt]] = None
) -> str:
    """
    Translate statistical metrics into actionable hints for a small LLM.

    Small models (1B parameters) cannot interpret raw residuals or AIC values.
    This function converts numerical results into natural language hints
    that guide the LLM toward better hypotheses.

    Args:
        result: FitResult from Wolfram evaluation
        previous_attempts: List of previous attempts for pattern analysis

    Returns:
        Human-readable feedback string
    """
    hints: List[str] = []

    if result.adjusted_r2 < 0.3:
        hints.append(
            "The equation does not capture the trend at all. "
            "Try a completely different functional form."
        )
    elif result.adjusted_r2 < 0.6:
        hints.append(
            "Partial fit. The equation captures some but not all of the behavior. "
            "Consider adding a non-linear term or a different power."
        )
    elif result.adjusted_r2 < 0.8:
        hints.append(
            "Moderate fit. You are on the right track. "
            "Try fine-tuning the functional form or adding a correction term."
        )
    elif result.adjusted_r2 < 0.95:
        hints.append(
            "Good fit! The equation is close. "
            "Consider minor adjustments or simplification."
        )

    if not result.converged:
        hints.append(
            "The fitting algorithm did not converge. "
            "The equation may be too complex or have numerical issues."
        )

    if result.complexity_score() > 4:
        hints.append(
            "The equation has many parameters. "
            "A simpler expression with fewer terms might generalize better."
        )

    if previous_attempts and len(previous_attempts) >= 2:
        recent_r2 = [a.adjusted_r2 for a in previous_attempts[-3:] if a.adjusted_r2]
        if len(recent_r2) >= 2:
            if all(recent_r2[i] < recent_r2[i + 1] for i in range(len(recent_r2) - 1)):
                hints.append("Progress is improving! Continue in this direction.")
            elif all(
                recent_r2[i] >= recent_r2[i + 1] - 0.05
                for i in range(len(recent_r2) - 1)
            ):
                hints.append(
                    "Results are stagnant. Try a fundamentally different approach."
                )

    if not hints:
        if result.adjusted_r2 >= 0.95:
            return "Excellent fit! The equation accurately models the data."
        return "Continue exploring variations of this expression."

    return " ".join(hints)


def generate_error_feedback(attempt: Attempt) -> str:
    """
    Generate feedback for failed attempts.

    Args:
        attempt: Failed Attempt object

    Returns:
        Human-readable error feedback
    """
    if attempt.status == AttemptStatus.SYNTAX_ERROR:
        return (
            f"Syntax error in your expression: {attempt.error_message}. "
            "Ensure all brackets are balanced and functions are spelled correctly."
        )

    if attempt.status == AttemptStatus.DIMENSION_MISMATCH:
        return (
            f"Dimensional inconsistency: {attempt.error_message}. "
            "Check that your expression has the correct units."
        )

    if attempt.status == AttemptStatus.FIT_FAILED:
        return (
            f"Fitting failed: {attempt.error_message}. "
            "The equation may be too complex or unsuitable for this data."
        )

    return f"Unknown error: {attempt.error_message}"


def extract_wolfram_expression(llm_output: str) -> str:
    """
    Extract the largest balanced-bracket expression from potentially chatty LLM output.

    Small LLMs often add conversational text or markdown formatting.
    This function extracts the actual Wolfram expression from:
    - Markdown code blocks
    - Conversational prefixes like "Sure! Here's your equation:"
    - Multiple lines with only one being the actual expression

    Args:
        llm_output: Raw output from LLM

    Returns:
        Clean Wolfram Language expression string

    Examples:
        >>> extract_wolfram_expression("Sure!\\n```wolfram\\na * Sqrt[x]\\n```")
        'a * Sqrt[x]'
        >>> extract_wolfram_expression("Here it is:\\na * x + b")
        'a * x + b'
    """
    cleaned = llm_output.strip()

    code_block_pattern = r"```[\w]*\n?(.*?)```"
    code_blocks = re.findall(code_block_pattern, cleaned, re.DOTALL)
    if code_blocks:
        cleaned = code_blocks[0].strip()

    cleaned = re.sub(
        r"^\s*(Sure!?\s*|Here('s| is)?[:!]?\s*|Output:?|Result:?|Answer:?)\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    lines = [line.strip() for line in cleaned.split("\n") if line.strip()]

    wolfram_like_lines = []
    for line in lines:
        if re.search(r"[a-zA-Z]", line) and (
            re.search(r"[+\-*/^=]", line)
            or re.search(r"\[.*\]", line)
            or re.search(r"\b(Sqrt|Sin|Cos|Tan|Log|Exp|Power)\b", line)
            or re.search(r"^[a-z]\s*[*+-]\s*", line)
        ):
            cleaned_line = re.sub(r"^.*?:\s*", "", line)
            wolfram_like_lines.append(cleaned_line)

    if wolfram_like_lines:
        cleaned = wolfram_like_lines[-1]
    elif lines:
        cleaned = lines[-1]
    else:
        return ""

    bracket_depth = 0
    best_match = ""
    last_valid_end = 0

    for i, char in enumerate(cleaned):
        if char in "[{(":
            bracket_depth += 1
        elif char in "]})":
            bracket_depth = max(0, bracket_depth - 1)
            if bracket_depth == 0:
                last_valid_end = i + 1

    if last_valid_end > 0:
        best_match = cleaned[:last_valid_end].strip()
    else:
        best_match = cleaned.strip()

    best_match = re.sub(r"^[`\s]+|[`\s]+$", "", best_match)

    return best_match


def format_error_history(attempts: List[Attempt], max_entries: int = 5) -> str:
    """
    Format recent attempts as a feedback string for the LLM prompt.

    Args:
        attempts: List of previous attempts
        max_entries: Maximum number of attempts to include

    Returns:
        Formatted string of recent attempts and their outcomes
    """
    if not attempts:
        return "No previous attempts."

    recent = attempts[-max_entries:]
    lines = ["Previous attempts:"]

    for attempt in recent:
        if attempt.status == AttemptStatus.SUCCESS:
            lines.append(f"  ✓ {attempt.expression} (R² = {attempt.adjusted_r2:.3f})")
        elif attempt.status == AttemptStatus.SYNTAX_ERROR:
            lines.append(f"  ✗ {attempt.expression} - Syntax error")
        elif attempt.status == AttemptStatus.DIMENSION_MISMATCH:
            lines.append(f"  ✗ {attempt.expression} - Wrong units")
        elif attempt.status == AttemptStatus.FIT_FAILED:
            lines.append(f"  ✗ {attempt.expression} - Fit failed")
        else:
            r2_str = (
                f"R² = {attempt.adjusted_r2:.3f}" if attempt.adjusted_r2 else "pending"
            )
            lines.append(f"  ? {attempt.expression} ({r2_str})")

    return "\n".join(lines)
