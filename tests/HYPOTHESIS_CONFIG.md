# Hypothesis Configuration for Property-Based Testing

This document describes the hypothesis configuration for property-based testing in the test suite.

## Overview

Hypothesis is configured with two profiles to support different testing scenarios:

### CI Profile (Default)
- **Max Examples**: 100 iterations per property test
- **Verbosity**: Verbose output for detailed test results
- **Deadline**: Disabled to avoid flaky tests in CI environments
- **Health Checks**: `too_slow` check suppressed for complex tests

This profile is used by default and ensures thorough testing with minimum 100 iterations per property test as required by the specification.

### Dev Profile
- **Max Examples**: 10 iterations per property test
- **Verbosity**: Normal output
- **Deadline**: Disabled

This profile provides faster feedback during development while still validating properties.

## Usage

### Running Tests with Default (CI) Profile

```bash
# Run all property-based tests with 100 iterations
pytest tests/property/ -v

# Run specific property test
pytest tests/property/test_auth_properties.py -v

# Show hypothesis statistics
pytest tests/property/ -v --hypothesis-show-statistics
```

### Running Tests with Dev Profile

```bash
# Run with dev profile (10 iterations for faster feedback)
HYPOTHESIS_PROFILE=dev pytest tests/property/ -v
```

### Running Tests with Custom Settings

You can override settings for individual tests using the `@settings` decorator:

```python
from hypothesis import given, settings, strategies as st

@given(x=st.integers())
@settings(max_examples=200)  # Override to run 200 iterations
def test_custom_iterations(x):
    assert x + 0 == x
```

## Configuration Location

The hypothesis configuration is defined in `tests/conftest.py`:

```python
from hypothesis import settings, Verbosity, HealthCheck

# CI profile: 100 iterations with verbose output
settings.register_profile(
    "ci",
    max_examples=100,
    verbosity=Verbosity.verbose,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow]
)

# Development profile: 10 iterations for faster feedback
settings.register_profile(
    "dev",
    max_examples=10,
    verbosity=Verbosity.normal,
    deadline=None
)

# Load profile based on environment variable (defaults to "ci")
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "ci"))
```

## Property Test Markers

Property-based tests should be marked with the `@pytest.mark.property` decorator:

```python
import pytest
from hypothesis import given, strategies as st

@pytest.mark.property
@given(x=st.integers(), y=st.integers())
def test_addition_commutative(x, y):
    """Property: Addition is commutative"""
    assert x + y == y + x
```

This allows filtering property tests:

```bash
# Run only property-based tests
pytest -m property

# Run all tests except property-based tests
pytest -m "not property"
```

## Hypothesis Statistics

When running tests with `--hypothesis-show-statistics`, you'll see detailed information about:
- Number of examples generated
- Number of passing/failing/invalid examples
- Runtime statistics
- Why the test stopped (e.g., reached max_examples)

Example output:
```
Hypothesis Statistics:
tests/property/test_auth_properties.py::test_valid_credentials:
  - during generate phase (0.15 seconds):
    - Typical runtimes: < 1ms, of which < 1ms in data generation
    - 100 passing examples, 0 failing examples, 0 invalid examples
  - Stopped because settings.max_examples=100
```

## Best Practices

1. **Use CI profile for final validation**: Always run tests with the CI profile (100 iterations) before committing
2. **Use dev profile during development**: Use the dev profile for faster iteration during test development
3. **Tag property tests**: Always use `@pytest.mark.property` for property-based tests
4. **Document properties**: Include clear docstrings explaining what property is being tested
5. **Reference requirements**: Link property tests to requirements using comments (e.g., `# Validates: Requirements 7.1`)

## Troubleshooting

### Tests are too slow
- Use the dev profile during development: `HYPOTHESIS_PROFILE=dev pytest`
- Consider if your test strategy is generating overly complex examples
- Use `@settings(suppress_health_check=[HealthCheck.too_slow])` if needed

### Flaky tests in CI
- The deadline is already disabled to prevent timeout-related flakiness
- Check if your test has non-deterministic behavior
- Use `hypothesis.seed()` to reproduce specific failures

### Need more examples for thorough testing
- Override max_examples for specific tests: `@settings(max_examples=500)`
- Consider if your test strategy is too narrow

## References

- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [Hypothesis Settings](https://hypothesis.readthedocs.io/en/latest/settings.html)
- [Hypothesis Strategies](https://hypothesis.readthedocs.io/en/latest/data.html)
