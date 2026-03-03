.PHONY: install test upgrade-submodules

install:
	pip install -e .

test:
	pytest --cov=pyld

upgrade-submodules:
	git submodule update --remote --init --recursive

# TODO: Expand to lib/ and tests/ as linting issues are resolved.
RUFF_TARGET = lib/pyld/*.py tests/*.py

lint:
	ruff check $(RUFF_TARGET)

fmt:
	ruff check --fix $(RUFF_TARGET)
	ruff format $(RUFF_TARGET)
