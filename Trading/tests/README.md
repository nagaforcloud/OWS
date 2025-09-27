# Testing Guide for Option Wheel Strategy

This document explains how to run tests for the Option Wheel Strategy project.

## Test Organization

The tests are organized as follows:
- `tests/test_config.py` - Tests for configuration loading
- `tests/test_models.py` - Tests for data models and enums
- `tests/test_strategy.py` - Tests for core strategy logic
- `tests/test_backtesting.py` - Tests for backtesting functionality
- `tests/test_integration.py` - Integration tests for complete workflows

## Running Tests

### Method 1: Using the test runner script

```bash
cd Trading
python run_tests.py
```

This will discover and run all tests in the tests directory.

### Method 2: Running individual test files

```bash
cd Trading
python -m pytest tests/test_config.py -v
python -m pytest tests/test_models.py -v
python -m pytest tests/test_strategy.py -v
python -m pytest tests/test_backtesting.py -v
python -m pytest tests/test_integration.py -v
```

### Method 3: Running all tests with pytest

```bash
cd Trading
python -m pytest tests/ -v
```

## Test Coverage

To run tests with coverage reporting:

```bash
cd Trading
python -m pytest tests/ --cov=option_wheel_strategy --cov-report=html --cov-report=term
```

This will generate an HTML coverage report in the `htmlcov` directory.

## Continuous Integration

For CI/CD pipelines, you can run:

```bash
cd Trading
python -m pytest tests/ --cov=option_wheel_strategy --cov-report=xml
```

This generates an XML coverage report that can be consumed by CI systems.

## Writing New Tests

1. Create a new test file in the `tests/` directory with the naming pattern `test_*.py`
2. Import the necessary modules and classes
3. Create test classes that inherit from `unittest.TestCase`
4. Write test methods that start with `test_`
5. Use assertions to verify expected behavior
6. Mock external dependencies when needed

## Test Categories

### Unit Tests
Test individual functions and methods in isolation.

### Integration Tests
Test the interaction between multiple components.

### End-to-End Tests
Test complete workflows from start to finish.

### Edge Case Tests
Test boundary conditions and error handling.

## Mocking Strategy

- Use `unittest.mock.Mock` and `unittest.mock.patch` for mocking
- Mock external APIs (like KiteConnect) to avoid network calls
- Mock file I/O operations when testing data loading
- Mock time-related functions when testing time-dependent logic

## Test Data

- Use realistic but synthetic data for testing
- Avoid including sensitive data in tests
- Use fixtures for complex test data setup
- Parameterize tests when testing multiple similar scenarios