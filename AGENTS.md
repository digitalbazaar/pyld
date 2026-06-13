# Agent guidelines

Read [CONTRIBUTING.md](CONTRIBUTING.md) for code style, linting (e.g. `make lint`, `make fmt`), and release process.

## Testing

- When adding tests to a file that already uses class-based pytest structure (e.g. `tests/test_jsonld.py`), add them as methods on the appropriate existing class — do not introduce a parallel standalone function-based test. A repo-wide refactor to function-based tests is planned but not yet landed; until then, match each file's existing structure.
- For brand-new test files, prefer function-based pytest tests (module-level `def test_...`) over class-based tests.
- Use descriptive test names that reflect behavior (e.g. `test_remote_context_via_link_alternate`).

## Documentation

- Put docs-specific CSS in `docs/stylesheets/extra.css` and register it via `extra_css` in `mkdocs.yml`.
- Put runnable doc examples in `docs/examples/` and embed them with the `example()` macro in `docs_macros.py`.
- One page = one idea — do not combine unrelated topics on a single doc page.
- Python object names in docs must always use backticks — in prose, headings, and card link text (not `__bold__`).
- Doc examples must not use `set_document_loader()`; pass `documentLoader` per operation via `options`.
- Do not use or mention function-based document loaders (`requests_document_loader`, `aiohttp_document_loader`, or plain callables) in docs; use `*DocumentLoader` classes or a `DocumentLoader` subclass.
- Doc page H1 headers should use icons that match their card icons (e.g. `# :material-cloud-download: \`RequestsDocumentLoader\``).
- Custom document-loader docs should illustrate subclassing `DocumentLoader`, not a bare callable.

## Committing

- Prefer one file per commit
- Base the commit message on the diff of the file that you are going to commit
- Prefer one line commit messages
- Do not co-author commits
