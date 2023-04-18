"""
commands.py

A module to evaluate code and return the result.
"""

def evaluate_code(code):
	"""Evaluates the code and returns the result"""
	result = None
	try:
		result = eval(code)
		return f'Result: {result}'
	except SyntaxError as se:
		return f'Error: {se}'
	except NameError as ne:
		return f'Error: {ne}'
	except TypeError as te:
		return f'Error: {te}'
	except ZeroDivisionError as zde:
		return f'Error: {zde}'
	except Exception as e:
		return f'Unexpected error: {e}'
