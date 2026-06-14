.PHONY: all install install-dev test lint format clean build distclean

PACKAGE = edai

all: install-dev

## install ............. Install the package in editable mode
install:
	pip install -e .

## install-dev ........ Install package + dev dependencies
install-dev:
	pip install -e ".[dev]"

## test ............... Run the test suite
test:
	python -m pytest $(PYTEST_ARGS)

## test-cov ........... Run tests with coverage report
test-cov:
	python -m pytest --cov=$(PACKAGE) --cov-report=term-missing $(PYTEST_ARGS)

## lint ............... Run ruff linter + mypy
lint:
	ruff check src/ tests/
	mypy src/ tests/

## format ............. Auto-format code with ruff
format:
	ruff format src/ tests/

## clean .............. Remove build artifacts
clean:
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .ruff_cache/ .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

## dist ............... Build source and wheel distributions
dist:
	python -m build

## distclean .......... Remove everything that isn't tracked by git
distclean: clean
	rm -rf .venv/
