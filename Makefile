.PHONY: install test upgrade-submodules download-bundled-contexts

install:
	pip install -e .

test:
	pytest --cov=pyld

upgrade-submodules:
	git submodule update --remote --init --recursive

download-bundled-contexts:
	python scripts/download_contexts.py

RUFF_TARGET = lib/pyld/*.py tests/*.py

lint:
	ruff check $(RUFF_TARGET)

fmt:
	ruff check --fix $(RUFF_TARGET)
	ruff format $(RUFF_TARGET)
