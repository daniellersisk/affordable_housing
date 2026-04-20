# End-to-End Test Conventions

This folder holds system-level tests that exercise the running API over HTTP.

## Scope

- full request/response flows against the containerized stack
- startup, health, and routing verification
- CRUD flows once persistence and auth are implemented
- regression checks that cross multiple layers

## Boundaries

- Treat these as black-box tests.
- Do not call service or repository classes directly.
- Favor a small number of high-signal scenarios over broad duplication of lower-level coverage.
