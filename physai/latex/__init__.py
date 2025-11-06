"""LaTeX package initialization."""
from physai.latex.latex_generator import LatexGenerator
from physai.latex.latex_utils import (
    label_equation,
    latex_escape,
    wrap_in_align_environment,
    wrap_in_equation_environment,
)

__all__ = [
    "LatexGenerator",
    "latex_escape",
    "wrap_in_equation_environment",
    "wrap_in_align_environment",
    "label_equation",
]

