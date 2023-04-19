import pytest
from algorithms.equation_generation import EquationGenerator
from algorithms.equation_verification import EquationVerifier
from data_processing.data_collection import DataCollector
from data_processing.data_preprocessor import DataPreprocessor
from data_processing.data_validator import DataValidator
from latex.latex_generation import LatexGeneration

@pytest.fixture
def equation_generator():
    return EquationGenerator()

@pytest.fixture
def equation_verifier():
    return EquationVerifier()

@pytest.fixture
def data_collector():
    return DataCollector()

@pytest.fixture
def data_preprocessor():
    return DataPreprocessor()

@pytest.fixture
def data_validator():
    return DataValidator()

@pytest.fixture
def latex_generator():
    return LatexGeneration()

