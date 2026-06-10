# Agent guidelines

Read [CONTRIBUTING.md](CONTRIBUTING.md) for code style, linting (e.g. `make lint`, `make fmt`), and release process.

## Testing

- When adding tests to a file that already uses class-based pytest structure (e.g. `tests/test_jsonld.py`), add them as methods on the appropriate existing class — do not introduce a parallel standalone function-based test. A repo-wide refactor to function-based tests is planned but not yet landed; until then, match each file's existing structure.
- For brand-new test files, prefer function-based pytest tests (module-level `def test_...`) over class-based tests.
- Use descriptive test names that reflect behavior (e.g. `test_remote_context_via_link_alternate`).

## Documentation

- When adding or promoting public top-level API exports, reflect them in the project documentation, especially the Sphinx API reference under `docs/`.

## Committing

- Prefer one file per commit
- Base the commit message on the diff of the file that you are going to commit
- Prefer one line commit messages
- Do not co-author commits
