# :simple-pypi: Installation

Install PyLD from PyPI:

```bash
pip install PyLD
```

PyLD's core package does not install `requests` or `aiohttp` automatically. If
your application needs one of the built-in remote document loaders, install the
matching extra:

```bash
pip install "PyLD[requests]"
pip install "PyLD[aiohttp]"
pip install "PyLD[requests-cache]"
pip install "PyLD[cli]"
```

`PyLD[cli]` installs [:simple-typer: Typer](https://typer.tiangolo.com/) and
[:simple-pypi: `requests-cache`](https://pypi.org/project/requests-cache/), and
registers the [`pyld`](cli/index.md) console script.

You can also depend on `requests` or `aiohttp` directly if your project already
manages those dependencies.

## Development Install

From a local checkout:

```bash
pip install -e .
```

Run the project tests with:

```bash
pytest
```

The JSON-LD specification test suites are stored under `specifications/` and are
usually initialized as git submodules:

```bash
git submodule init
git submodule update
```
