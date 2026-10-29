.PHONY: format

format:
	@echo "Formatting Python code with black..."
	python -m black dashboard/ tests/
	@echo "Formatting complete."

format-autopep8:
	@echo "Formatting Python code with autopep8 --in-place --aggressive..."
	python -m autopep8 --in-place --aggressive dashboard/ tests/
	@echo "Formatting complete."
