"""
Test to verify hypothesis configuration is working correctly.
This test validates that the hypothesis profiles are properly configured.
"""
import pytest
from hypothesis import given, strategies as st, settings


@pytest.mark.property
def test_hypothesis_configuration():
    """Verify hypothesis is configured and working"""
    # This test will run with the configured profile settings
    # CI profile: 100 iterations
    # Dev profile: 10 iterations
    
    @given(x=st.integers())
    def property_test(x):
        # Simple property: x + 0 should equal x
        assert x + 0 == x
    
    # Run the property test
    property_test()


@pytest.mark.property
def test_hypothesis_profile_settings():
    """Verify the current hypothesis profile has correct settings"""
    current_settings = settings()
    
    # The profile should have max_examples set (either 100 for CI or 10 for dev)
    assert current_settings.max_examples in [10, 100], \
        f"Expected max_examples to be 10 or 100, got {current_settings.max_examples}"
    
    # Verify deadline is disabled
    assert current_settings.deadline is None, \
        "Deadline should be disabled to avoid flaky tests"


@pytest.mark.property
@given(
    a=st.integers(min_value=-1000, max_value=1000),
    b=st.integers(min_value=-1000, max_value=1000)
)
def test_hypothesis_basic_property(a, b):
    """
    Test a basic mathematical property to verify hypothesis is working.
    Property: Addition is commutative (a + b == b + a)
    """
    assert a + b == b + a
