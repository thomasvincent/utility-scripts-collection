# Contributing to Utility Scripts Collection

Thank you for considering contributing to the Utility Scripts Collection! This document outlines the process for contributing to this project.

## Code of Conduct

By participating in this project, you agree to abide by our code of conduct. Please be respectful and considerate of others.

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with the following information:

1. A clear, descriptive title
2. Steps to reproduce the issue
3. Expected behavior
4. Actual behavior
5. Any relevant logs or error messages
6. Your environment (OS, Python version, etc.)

### Suggesting Enhancements

We welcome suggestions for new features or improvements. To suggest an enhancement:

1. Create an issue with a clear, descriptive title
2. Describe the enhancement in detail
3. Explain why this enhancement would be useful
4. If possible, suggest an implementation approach

### Pull Requests

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification for commit messages. This makes the commit history more readable and allows for automatic versioning and changelog generation.

Each commit message should have a structured format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Types include:
- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation changes
- `style`: Changes that do not affect code functionality (formatting, etc.)
- `refactor`: Code changes that neither fix a bug nor add a feature
- `perf`: Performance improvements
- `test`: Adding or fixing tests
- `build`: Changes to build system or dependencies
- `ci`: Changes to CI configuration

Example commit messages:
- `feat: add support for DNS zone transfers`
- `fix: correct timeout handling in HTTP checker`
- `docs: improve installation instructions`

#### Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Install and run pre-commit hooks to ensure code quality
   ```bash
   pip install pre-commit
   pre-commit install
   pre-commit install --hook-type commit-msg  # For commit message validation
   ```
5. Run the tests to ensure they pass
   ```bash
   pytest
   ```
6. Commit your changes with conventional commit messages
   ```bash
   git commit -m "feat: add amazing feature"
   ```
7. Push to your branch
   ```bash
   git push origin feature/amazing-feature
   ```
8. Create a pull request

#### Pull Request Guidelines

- Keep your changes focused on a single issue
- Write comprehensive tests for your changes
- Update documentation as needed
- Follow the code style of the project

## Development Environment

To set up a development environment:

1. Clone the repository
   ```bash
   git clone https://github.com/thomasvincent/utility-scripts-collection.git
   cd utility-scripts-collection
   ```

2. Create a virtual environment
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use: venv\Scripts\activate
   ```

3. Install development dependencies
   ```bash
   pip install -e ".[dev]"
   ```

4. Install pre-commit hooks
   ```bash
   pre-commit install
   pre-commit install --hook-type commit-msg
   ```

## Running Tests

We use pytest for testing. To run the tests:

```bash
pytest
```

To run tests with coverage:

```bash
pytest --cov=utility_scripts
```

## Code Style

This project uses:
- Black for code formatting
- isort for import sorting
- Flake8 for linting
- mypy for type checking

You can run all style checks with:

```bash
# Format code
black src tests
isort src tests

# Check code
flake8 src tests
mypy src
```

## License

By contributing to this project, you agree that your contributions will be licensed under the project's MIT License.