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
- JSON-LD API reference pages use **function autodoc + matching `*Options` TypedDict autodoc** under a `## Options` heading. Option key prose lives on the TypedDict fields in `lib/pyld/options.py`, not in nested `:param options:` continuations on the function docstring. TypedDict types are typing/documentation only — no runtime validation of `options` dicts.
- Reference pages omit duplicate prose: set `show_docstring_description: false` on **function** autodoc blocks only. On `*Options` blocks use `show_bases: false` but keep descriptions enabled so field docstrings render. Do not use Sphinx `:func:` roles in TypedDict docstrings (they render literally). Wrap literals in single backticks (e.g. `True`, `False`).

### Documentation validation

- **No in-repo Playwright.** Do not add `@playwright/test`, `playwright.config.js`, or e2e test dependencies. Live browser checks use **only** the Playwright MCP server (`user-playwright`).
- After doc changes, run `make docs-build` (strict). For interactive checks, run `make docs-serve` and validate with Playwright MCP: `browser_navigate`, `browser_snapshot`, `browser_click`, `browser_wait_for`. Prefer `browser_run_code_unsafe` with `page.screenshot({ animations: 'disabled', timeout: 60000 })` over `browser_take_screenshot` (font load timeouts).

## Committing

- Prefer one file per commit
- Base the commit message on the diff of the file that you are going to commit
- Prefer one line commit messages
- Do not co-author commits
