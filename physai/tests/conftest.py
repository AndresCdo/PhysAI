"""Test configuration and fixtures."""
import pytest

from physai.algorithms.equation_generator import EquationGenerator
from physai.algorithms.equation_verifier import EquationVerifier
from physai.data_processing.data_collector import DataCollector
from physai.data_processing.data_preprocessor import DataPreprocessor
from physai.data_processing.data_validator import DataValidator
from physai.latex.latex_generator import LatexGenerator


@pytest.fixture
def equation_generator():
    """Fixture for EquationGenerator."""
    return EquationGenerator(data=None)


@pytest.fixture
def equation_verifier():
    """Fixture for EquationVerifier."""
    return EquationVerifier(data=None)


@pytest.fixture
def data_collector():
    """Fixture for DataCollector."""
    return DataCollector()


@pytest.fixture
def data_preprocessor():
    """Fixture for DataPreprocessor."""
    return DataPreprocessor()


@pytest.fixture
def data_validator():
    """Fixture for DataValidator."""
    return DataValidator()


@pytest.fixture
def latex_generator():
    """Fixture for LatexGenerator."""
    return LatexGenerator()


