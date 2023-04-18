import unittest

input_code = '''
def add_numbers(a, b):
    return a + b
    
def multiply_numbers(a, b):
   return a * b

def subtract_numbers(a, b):
    return a - b
    
def improved_code():
    print('Hello World!')
    for i in range(5):
        print(i)
        print('Goodbye World!')
        print('All tests passed!')
'''

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

    def test_subtraction_zeroradius_circle(self):
        """Test if the function correctly subtracts two negative numbers."""
        self.assertEqual(subtract_numbers(0, 0), 0)

class TestImprovedCode(unittest.TestCase):
    """Tests the improved_code function"""

    def test_improved_code(self):
        """Test if the function correctly prints the correct output."""

        result = improved_code()
        output = self.called_print.getvalue().strip()
        self.assertEqual(output, 'Hello World!\n0\n1\n2\n3\n4\nGoodbye World!')
        self.assertEqual(result, None)


class TestCode(unittest.TestSuite):
    def __init__(self):
        super(TestCode, self).__init__()
        self.addTests([
            TestAddition('test_addition'), 
            TestAddition('test_addition_negative_numbers'), 
            TestMultiplication('test_multiplication'), 
            TestMultiplication('test_multiplication_with_zero'), 
            TestSubtraction('test_subtraction'), 
            TestSubtraction('test_subtraction_zeroradius_circle'), 
            TestImprovedCode('test_improved_code')
            ])

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCode)
    runner = unittest.TextTestRunner()
    runner.run(suite)