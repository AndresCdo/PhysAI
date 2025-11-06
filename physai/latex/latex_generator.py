"""Module for generating LaTeX documents from equations."""
import os

from physai.algorithms.equation_generator import EquationGenerator
from physai.algorithms.equation_verifier import EquationVerifier


class LatexGenerator:
    """A class for generating LaTeX documents based on the algorithms module output."""

    def __init__(self, output_dir="latex_documents"):
        """
        Initialize the LatexGenerator class with an output directory.

        Args:
            output_dir: The output directory for the generated LaTeX documents
                (default: 'latex_documents').
        """
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def create_latex_document(self, file_name, equations):
        """
        Create a LaTeX document with the generated equations.

        Args:
            file_name: The file name of the generated LaTeX document.
            equations: A list of equations to include in the LaTeX document.
        """
        output_path = os.path.join(self.output_dir, f"{file_name}.tex")

        template_path = os.path.join(os.path.dirname(__file__), "latex_document_template.tex")
        try:
            with open(template_path, "r", encoding='utf-8') as template_file:
                template_content = template_file.read()
        except FileNotFoundError:
            raise FileNotFoundError(
                f"LaTeX template file not found at '{template_path}'. Please ensure 'latex_document_template.tex' exists."
            )

        equations_section = "\\section{Generated Equations}\n"

        for idx, equation in enumerate(equations, start=1):
            equations_section += f"\\subsection*{{Equation {idx}}}\n"
            equations_section += f"\\begin{{equation}}\n{equation}\n\\end{{equation}}\n"

        content = template_content.replace(
            "\\section{Results}", f"\\section{{Results}}\n{equations_section}"
        )

        with open(output_path, "w", encoding='utf-8') as output_file:
            output_file.write(content)

        print(f"Generated LaTeX document: {output_path}")

if __name__ == "__main__":
    # Instantiate the classes from the algorithms module
    equation_generator = EquationGenerator(data=None)
    equation_verifier = EquationVerifier(data=None)

    # Generate and verify equations (dummy example)
    generated_equations = [
        equation_generator.generate_equation("E = mc^2")[0]
    ]
    verified_result = equation_verifier.verify_equation(generated_equations[0])
    print(f"Verification result: {verified_result}")

    # Instantiate the LatexGenerator class
    latex_generator = LatexGenerator()

    # Create a LaTeX document with the generated equations
    latex_generator.create_latex_document(
        "PhysAI_Generated_Equations", generated_equations
    )

