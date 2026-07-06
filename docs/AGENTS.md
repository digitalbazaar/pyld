# Documentation guidance

- Review documentation diffs with the same rigor as code diffs; apply the
  project documentation conventions whenever docs files are touched.
- Keep reference pages centered on the API or object named by the page; do not
  add examples for unrelated loaders or implementation escape hatches.
- Put the primary API autodoc or mkdocstrings block near the top of reference
  pages, after any prerequisite admonition and before explanatory prose; do not
  add a separate `API Reference` heading before it.
- On the first prose mention of an external software product on a docs page,
  link to the official product or package page and include the relevant MkDocs
  Material icon; do not force links inside code spans, Python object names,
  filenames, options, or generated example output.
- When a docs page is influenced by an ADR, add a bottom-of-page collapsed
  admonition named `Decisions` that links to the relevant decision document.
- This file is excluded from MkDocs publishing through `exclude_docs` in
  `mkdocs.yml`.
