def latex_escape(text):
    """
    Escape special characters in the text for use in LaTeX.

    Args:
        text: The input text to escape.

    Returns:
        The escaped text.
    """
    latex_special_chars = {
        '&': '\\&',
        '%': '\\%',
        '$': '\\$',
        '#': '\\#',
        '_': '\\_',
        '{': '\\{',
        '}': '\\}',
        '~': '\\textasciitilde{}',
        '^': '\\^{}',
        '\\': '\\textbackslash{}',
    }
    return ''.join(latex_special_chars.get(c, c) for c in text)


def wrap_in_equation_environment(equation):
    """
    Wrap an equation string in the LaTeX equation environment.

    Args:
        equation: The equation string to wrap.

    Returns:
        The wrapped equation.
    """
    return f"\\begin{{equation}}\n{equation}\n\\end{{equation}}"


def wrap_in_align_environment(equations):
    """
    Wrap a list of equations in the LaTeX align environment.

    Args:
        equations: A list of equation strings to wrap.

    Returns:
        The wrapped equations.
    """
    equations_str = "\\\\\n".join(equations)
    return f"\\begin{{align}}\n{equations_str}\n\\end{{align}}"


def label_equation(equation, label):
    """
    Add a label to an equation in the LaTeX equation environment.

    Args:
        equation: The equation string to label.
        label: The label to add to the equation.

    Returns:
        The labeled equation.
    """
    return f"\\begin{{equation}}\n{equation} \\label{{{label}}}\n\\end{{equation}}"
