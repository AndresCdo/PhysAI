def evaluate_code(code):
	result = None
	try:
		result = eval(code)
		print(f'Result: {result}')
	except Exception as e:
		print(f'Error: {e}')