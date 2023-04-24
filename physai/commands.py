"""
commands.py

A module to evaluate code and return the result.
"""

import sys


def evaluate_code(code):
    """
    Evaluates the code and returns the result.

    Args:
        code (str): The code to be evaluated.

    Returns:
        The result of the evaluation or an error message if an exception is raised.
    """
    result = None
    try:
        result = eval(code)
        return f"Result: {result}"
    except SyntaxError as se:
        return f"Error: {se}"
    except NameError as ne:
        return f"Error: {ne}"
    except TypeError as te:
        return f"Error: {te}"
    except ZeroDivisionError as zde:
        return f"Error: {zde}"
    except Exception as e:
        return f"Unexpected error: {e}"


if __name__ == "__main__":
    if len(sys.argv) > 1:
        code = sys.argv[1]
        print(evaluate_code(code))
    else:
        print("Please provide code to evaluate as an argument.")
