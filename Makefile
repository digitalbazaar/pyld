upgrade-submodules:
	git submodule update --remote --init --recursive

test:
	python tests/runtests.py
