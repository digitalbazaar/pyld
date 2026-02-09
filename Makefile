.PHONY: install test upgrade-submodules

install:
	pip install -e .

test:
	pytest

upgrade-submodules:
	git submodule update --remote --init --recursive

# TODO: Expand to lib/ and tests/ as linting issues are resolved.
RUFF_TARGET = lib/pyld/context_resolver.py lib/pyld/identifier_issuer.py lib/pyld/iri_resolver.py lib/pyld/nquads.py

lint:
	ruff check $(RUFF_TARGET)

fmt:
	ruff check --fix $(RUFF_TARGET)
	ruff format $(RUFF_TARGET)
