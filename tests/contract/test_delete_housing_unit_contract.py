"""Contract tests for DELETE /housing-units/{id}."""

import pytest


@pytest.mark.skip(reason="Implement once API client fixture is available.")
def test_delete_housing_unit_success_contract() -> None:
    """Verify success contract for deleting a unit."""


@pytest.mark.skip(reason="Implement once API client fixture is available.")
def test_delete_housing_unit_auth_error_contract() -> None:
    """Verify auth failure contract for protected write route."""


@pytest.mark.skip(reason="Implement once API client fixture is available.")
def test_delete_housing_unit_not_found_contract() -> None:
    """Verify not-found error contract for missing ids."""
