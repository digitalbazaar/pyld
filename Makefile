.PHONY: install test docs-install docs-build docs-serve upgrade-submodules download-bundled-contexts

PORT ?= 8000

install:
	pip install -e .

test:
	pytest --cov=pyld

docs-install:
	python -m pip install --upgrade pip
	pip install -r docs/requirements.txt

docs-build:
	mkdocs build --strict

docs-serve:
	mkdocs serve --dev-addr 127.0.0.1:$(PORT)

upgrade-submodules:
	git submodule update --remote --init --recursive

download-bundled-contexts:
	python scripts/download_contexts.py

RUFF_TARGET = lib/pyld/*.py tests/*.py docs_macros.py

lint:
	ruff check $(RUFF_TARGET)

fmt:
	ruff check --fix $(RUFF_TARGET)
	ruff format $(RUFF_TARGET)
