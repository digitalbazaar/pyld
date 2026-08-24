# :material-code-json: Inject a JSON-LD `@context`

JSON-LD property names only become RDF terms when a context maps them to IRIs.
If the input JSON has no `@context`, and the source cannot provide one through
an HTTP `Link` header, pass the context with `expandContext`.

Use this for JSON already loaded from a file, queue, database, or API client:

1. Load or receive the plain JSON document.
2. Define the context your application wants to apply.
3. Pass that context in the operation `options` as `expandContext`.
4. Run `jsonld.expand()` or another API that expands internally.

PyLD processes `expandContext` before expansion. If the document also has its
own `@context`, that document context is processed later and can refine or
override term definitions for the document body.

{{ example('inject_context.py', 'json') }}

The same option works with APIs that expand internally, including
`jsonld.compact()`, `jsonld.flatten()`, and `jsonld.frame()`:

{{ example('inject_context_compact.py', 'json') }}

Use an in-document `@context` when you control the JSON. Use `expandContext`
when the context is application policy or transport metadata.
