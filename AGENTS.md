# Agent guidelines

Read [CONTRIBUTING.rst](CONTRIBUTING.rst) for code style, linting (e.g. `make lint`, `make fmt`), and release process.

## Testing

- Prefer **function-based** pytest tests (module-level `def test_...`) over class-based tests (`class Test...`).
- Use descriptive test names that reflect behavior (e.g. `test_remote_context_via_link_alternate`).
