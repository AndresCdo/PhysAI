"""Test suite for PhysAI basic functionality."""
import unittest


def add_numbers(a, b):
    """Add two numbers."""
    return a + b


def multiply_numbers(a, b):
    """Multiply two numbers."""
    return a * b


def subtract_numbers(a, b):
    """Subtract two numbers."""
    return a - b


def improved_code():
    """Sample function for testing."""
    print('Hello World!')
    for i in range(5):
        print(i)
    print('Goodbye World!')
    print('All tests passed!')


class TestAddition(unittest.TestCase):
    """Tests the addition function"""

    def test_addition(self):
        """Test if the function correctly adds two positive numbers."""
        self.assertEqual(add_numbers(2, 3), 5)

    def test_addition_negative_numbers(self):
        """Test if the function correctly adds two negative numbers."""
        self.assertEqual(add_numbers(-2, -3), -5)


class TestMultiplication(unittest.TestCase):
    """Tests the multiplication function"""

    def test_multiplication(self):
        """Test if the function correctly multiplies two positive numbers."""
        self.assertEqual(multiply_numbers(2, 3), 6)

    def test_multiplication_with_zero(self):
        """Test if the function correctly multiplies a number by zero."""
        self.assertEqual(multiply_numbers(0, 3), 0)


class TestSubtraction(unittest.TestCase):
    """Tests the subtraction function"""

    def test_subtraction(self):
        """Test if the function correctly subtracts two positive numbers."""
        self.assertEqual(subtract_numbers(2, 3), -1)

    def test_subtraction_zero(self):
        """Test if the function correctly subtracts two zeros."""
        self.assertEqual(subtract_numbers(0, 0), 0)


if __name__ == "__main__":
    unittest.main()

