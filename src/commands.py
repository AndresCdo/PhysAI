"""
commands.py

A module to evaluate code and return the result.
"""

def evaluate_code(code):
	"""Evaluates the code and returns the result"""
	result = None
	try: # Try to evaluate the code
		result = eval(code)
		print(f'Result: {result}') # Print the result
	except Exception as e: # If there is an error, print it
		print(f'Error: {e}')