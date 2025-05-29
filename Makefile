.PHONY: clean clean-test clean-pyc clean-build test coverage lint format type check all help
.DEFAULT_GOAL := help

# Variables
PYTHON := python3
PIP := pip3
BLACK_LINE_LENGTH := 80
TEST_PATH := tests/
SRC_PATHS := src/ DNSScript/dns_manager.py WhoisScript/main.py NagiosPlugins/check_http500/check_http500_clean.py

help:
	@echo "Utility Scripts Collection - Makefile Commands"
	@echo "============================================="
	@echo ""
	@echo "Development Commands:"
	@echo "  make dev-install  - install development dependencies"
	@echo "  make format       - format code with black and isort"
	@echo "  make lint         - check style with flake8 and pylint"
	@echo "  make type         - run type checking with mypy"
	@echo "  make test         - run tests quickly with pytest"
	@echo "  make coverage     - check code coverage with pytest"
	@echo "  make check        - run all checks (lint, type, test)"
	@echo "  make all          - format code and run all checks"
	@echo ""
	@echo "Cleanup Commands:"
	@echo "  make clean        - remove all artifacts"
	@echo "  make clean-build  - remove build artifacts"
	@echo "  make clean-pyc    - remove Python file artifacts"
	@echo "  make clean-test   - remove test and coverage artifacts"
	@echo ""
	@echo "Distribution Commands:"
	@echo "  make dist         - build source and wheel distributions"
	@echo "  make install      - install the package"

clean: clean-build clean-pyc clean-test

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -rf {} +

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test:
	rm -fr .pytest_cache/
	rm -fr .coverage
	rm -fr htmlcov/
	rm -fr .mypy_cache/
	rm -fr .tox/

format:
	@echo "Formatting code with isort..."
	$(PYTHON) -m isort $(SRC_PATHS) $(TEST_PATH)
	@echo "Formatting code with black..."
	$(PYTHON) -m black --line-length=$(BLACK_LINE_LENGTH) $(SRC_PATHS) $(TEST_PATH)

lint:
	@echo "Running flake8..."
	$(PYTHON) -m flake8 $(SRC_PATHS) $(TEST_PATH)
	@echo "Running pylint..."
	$(PYTHON) -m pylint $(SRC_PATHS) || true

type:
	@echo "Running mypy type checker..."
	$(PYTHON) -m mypy $(SRC_PATHS)

test:
	@echo "Running pytest..."
	$(PYTHON) -m pytest -v $(TEST_PATH)

coverage:
	@echo "Running tests with coverage..."
	$(PYTHON) -m pytest --cov=src --cov=DNSScript --cov=WhoisScript --cov=NagiosPlugins \
		--cov-report=term-missing --cov-report=html $(TEST_PATH)
	@echo "Coverage report generated in htmlcov/"

check: lint type test
	@echo "All checks passed!"

all: format check
	@echo "Code formatted and all checks passed!"

dist: clean
	@echo "Building distribution packages..."
	$(PYTHON) -m build
	ls -l dist

install: clean
	@echo "Installing package..."
	$(PIP) install .

dev-install:
	@echo "Installing development dependencies..."
	$(PIP) install -e ".[dev]"
	@echo "Installing pre-commit hooks..."
	pre-commit install
	pre-commit install --hook-type commit-msg
	@echo "Development environment setup complete!"

# Run the comprehensive test script
test-all:
	$(PYTHON) run_tests.py