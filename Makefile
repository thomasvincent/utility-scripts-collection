.PHONY: clean clean-test clean-pyc clean-build test coverage lint format type help
.DEFAULT_GOAL := help

help:
	@echo "Commands:"
	@echo "  clean      - remove all build, test, coverage, and Python artifacts"
	@echo "  clean-build - remove build artifacts"
	@echo "  clean-pyc  - remove Python file artifacts"
	@echo "  clean-test - remove test and coverage artifacts"
	@echo "  lint       - check style with flake8"
	@echo "  format     - format code with black and isort"
	@echo "  test       - run tests quickly with pytest"
	@echo "  coverage   - check code coverage quickly with pytest"
	@echo "  type       - run type checking with mypy"
	@echo "  dist       - build source and wheel distributions"
	@echo "  install    - install the package to the active Python's site-packages"
	@echo "  dev-install - install development dependencies"

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

lint:
	flake8 src tests
	isort --check-only --profile black src tests
	black --check src tests

format:
	isort src tests
	black src tests

test:
	pytest

coverage:
	pytest --cov=utility_scripts tests/
	coverage report -m
	coverage html

type:
	mypy src tests

dist: clean
	python -m build
	ls -l dist

install: clean
	pip install .

dev-install:
	pip install -e ".[dev]"
	pre-commit install
	pre-commit install --hook-type commit-msg