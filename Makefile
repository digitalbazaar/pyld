.PHONY: install test upgrade-submodules

install:
	pip install -e .

test:
	pytest

upgrade-submodules:
	git submodule update --remote --init --recursive