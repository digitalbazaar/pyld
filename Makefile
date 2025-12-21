.PHONY: install test upgrade-submodules

install:
	pip install -e .

test:
	pytest

upgrade-submodules:
	git submodule update --remote --init --recursive

# At this stage, we are limiting our formatting efforts to one file. We need to ensure that:
# * our formatting rules are sane,
# * we are not introducing conflicts with currently open PRs,
# * and the PR introducing `ruff` is not too large.
RUFF_TARGET = lib/pyld/context_resolver.py

lint:
	ruff check $(RUFF_TARGET)

fmt:
	ruff check --fix $(RUFF_TARGET)
	ruff format $(RUFF_TARGET)
