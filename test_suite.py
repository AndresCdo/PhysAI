import unittest

input_code = 'def add_numbers(a, b):\n    return a + b\ndef multiply_numbers(a, b):\n    return a * b\ndef subtract_numbers(a, b):\n    return a - b\ndef improved_code():\n    print('Hello World!')\n    for i in range(5):\n        print(i)\n    print('Goodbye World!')\n    print('All tests passed!')\n
test_addition = """class TestAddition(unittest.TestCase):
    def test_addition(self):
        self.assertEqual(add_numbers(2, 3), 5)
    def test_addition_negative_numbers(self):
        self.assertEqual(add_numbers(-2, -3), -5)
"""

test_multiplication = """class TestMultiplication(unittest.TestCase):
    def test_multiplication(self):
        self.assertEqual(multiply_numbers(2, 3), 6)
    def test_multiplication_with_zero(self):
        self.assertEqual(multiply_numbers(0, 3), 0)
"""

test_subtraction = """class TestSubtraction(unittest.TestCase):
    def test_subtraction(self):
        self.assertEqual(subtract_numbers(2, 3), -1)
    def test_subtraction_zeroradius_circle(self):
        self.assertEqual(subtract_numbers(0, 0), 0)
"""

class TestImprovedCode(unittest.TestCase):
    def test_improved_code(self):
        result = improved_code()
        output = self.called_print.getvalue().strip()
        self.assertEqual(output, 'Hello World!\n0\n1\n2\n3\n4\nGoodbye World!')
        self.assertEqual(result, None)


class TestCode(unittest.TestSuite):
    def __init__(self):
        super(TestCode, self).__init__()
        self.addTests([TestAddition('test_addition'), TestAddition('test_addition_negative_numbers'), TestMultiplication('test_multiplication'), TestMultiplication('test_multiplication_with_zero'), TestSubtraction('test_subtraction'), TestSubtraction('test_subtraction_zeroradius_circle'), TestImprovedCode('test_improved_code')])
if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCode)
    runner = unittest.TextTestRunner()
    runner.run(suite)