# :material-file-code-outline: Open a JSON-LD file

For a local `.jsonld` file that already contains its `@context`, use Python's
standard `json` module first. PyLD processes Python objects, so the usual order
is:

```bash
pip install PyLD
```

1. Read the file with `pathlib.Path`.
2. Parse it with `json.loads()` or `json.load()`.
3. Pass the parsed object to `jsonld.expand()`, `jsonld.compact()`,
   `jsonld.to_rdf()`, or another PyLD API.

{{ example('open_jsonld_file.py', 'json') }}

After parsing the file, use any PyLD operation. For example, convert the local
JSON-LD file to N-Quads:

{{ example('open_jsonld_file_to_rdf.py') }}

That is enough for local files with inline contexts. Choose a document loader
only when PyLD must dereference a URL during processing.

If the document uses remote contexts, install and pass
`RequestsDocumentLoader`:

```bash
pip install "PyLD[requests]"
```

If PyLD should load the JSON-LD document itself from a `file:` URL, use
[`FileDocumentLoader`](../reference/document-loaders/file.md) and pass it with
`documentLoader` in the operation `options`. Direct `json.load()` is simpler
when you already know the file path and only need to process that one file.
