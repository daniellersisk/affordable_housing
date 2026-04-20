"""Contract tests for PUT /housing-units/{id}."""

import pytest


@pytest.mark.skip(reason="Implement once API client fixture is available.")
def test_put_housing_unit_success_contract() -> None:
    """Verify success contract for updating a unit."""


@pytest.mark.skip(reason="Implement once API client fixture is available.")
def test_put_housing_unit_auth_error_contract() -> None:
    """Verify auth failure contract for protected write route."""


@pytest.mark.skip(reason="Implement once API client fixture is available.")
def test_put_housing_unit_not_found_contract() -> None:
    """Verify not-found error contract for missing ids."""
