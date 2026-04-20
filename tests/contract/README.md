# Contract Test Conventions

This folder defines API contract tests. These tests protect endpoint compatibility and must be updated whenever contracts change.

## Goals

- Verify endpoint request/response contracts remain stable.
- Catch breaking API changes early.
- Keep contract behavior explicit and reviewable.

## Folder Layout

```text
tests/contract/
  README.md
  conftest.py
  schemas/
    error_response.json
    housing_unit_response.json
    housing_unit_list_response.json
  test_get_housing_units_contract.py
  test_get_housing_unit_by_id_contract.py
  test_post_housing_unit_contract.py
  test_put_housing_unit_contract.py
  test_delete_housing_unit_contract.py
```

## Naming Rules

- File names: `test_<endpoint>_contract.py`
- Test names: `test_<method>_<endpoint>_<scenario>_contract`

Examples:

- `test_get_housing_units_success_contract`
- `test_post_housing_units_validation_error_contract`
- `test_put_housing_unit_not_found_contract`

## Minimum Required Assertions Per Endpoint

For each endpoint, include tests that verify:

1. Status code contract
2. Response body schema/shape contract
3. Required vs optional field semantics
4. Error schema contract (for at least one 4xx path)

For protected endpoints, also verify:

5. Authorization failure contract (`401`/`403` and error payload shape)

## Schema Strategy

- Store response schema fixtures under `tests/contract/schemas/`.
- Keep schema fixtures readable and versioned in git.
- When contract changes are intentional, update:
  - endpoint implementation
  - contract tests
  - schema fixtures
  - docs (`README.md` + OpenAPI examples)
  in the same change set.

## Implementation Notes

- Prefer black-box API calls using HTTP client fixtures.
- Do not instantiate service classes directly in contract tests.
- Keep assertions strict for field presence and type, loose for non-contract internals.
- Validate error payloads using shared error schema fixture.

## Pull Request Requirement

Any endpoint contract change without matching contract test updates should be treated as incomplete.
