# Integration Test Conventions

This folder holds integration tests that exercise the app with real infrastructure dependencies, especially PostgreSQL.

## Scope

- database session and transaction behavior
- repository queries against a real Postgres schema
- migration-applied test database flows
- API behavior that depends on real persistence

## Boundaries

- Prefer real database interactions over mocks.
- These tests should stay narrower than end-to-end tests.
- When DB-backed features land, add fixtures here for migration setup and seeded data.
