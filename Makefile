.PHONY: install test docs-install docs-build docs-serve docs-deploy docs-export docs-set-default upgrade-submodules download-bundled-contexts

PORT ?= 8000
VERSION ?=
GIT_REF ?=
ALIASES ?=
DEFAULT_VERSION ?= latest
DOCS_ALIAS_TYPE ?= copy
PUSH ?=
DOCS_DEPLOY_BRANCH ?= gh-pages
DOCS_DEPLOY_REMOTE ?= origin
DOCS_EXPORT_DIR ?= site-versioned
DOCS_RETRO_WORKTREE ?= .docs-retro-worktree
MIKE_FLAGS ?=
MIKE_PUSH = $(if $(PUSH),--push,)

install:
	pip install -e .

test:
	pytest --cov=pyld

docs-install:
	python -m pip install --upgrade pip
	pip install -e ".[cli]"
	pip install -r docs/requirements.txt

docs-build:
	mkdocs build --strict

docs-serve:
	mkdocs serve --dev-addr 127.0.0.1:$(PORT)
	
docs-deploy:
	@test -n "$(VERSION)" || (echo "VERSION is required, e.g. VERSION=3.2 make docs-deploy"; exit 1)
	@if [ -n "$(GIT_REF)" ]; then \
		test ! -e "$(DOCS_RETRO_WORKTREE)" || (echo "$(DOCS_RETRO_WORKTREE) already exists"; exit 1); \
		set -e; \
		trap 'git worktree remove --force "$(DOCS_RETRO_WORKTREE)"' EXIT; \
		git worktree add --detach "$(DOCS_RETRO_WORKTREE)" "$(GIT_REF)"; \
		: "Older tags predate Material's mike version selector config, so patch mkdocs.yml."; \
		python -c 'from pathlib import Path; p = Path("$(DOCS_RETRO_WORKTREE)/mkdocs.yml"); s = p.read_text(); b = "extra:\n  version:\n    provider: mike\n\n"; p.write_text(s if "provider: mike" in s else s.replace("extra_css:", b + "extra_css:", 1) if "extra_css:" in s else s.rstrip() + "\n\n" + b)'; \
		python -m pip install -e "$(DOCS_RETRO_WORKTREE)"; \
		mike deploy --config-file "$(DOCS_RETRO_WORKTREE)/mkdocs.yml" --update-aliases --alias-type=$(DOCS_ALIAS_TYPE) --remote $(DOCS_DEPLOY_REMOTE) --branch $(DOCS_DEPLOY_BRANCH) $(MIKE_PUSH) $(MIKE_FLAGS) $(VERSION) $(ALIASES); \
	else \
		mike deploy --update-aliases --alias-type=$(DOCS_ALIAS_TYPE) --remote $(DOCS_DEPLOY_REMOTE) --branch $(DOCS_DEPLOY_BRANCH) $(MIKE_PUSH) $(MIKE_FLAGS) $(VERSION) $(ALIASES); \
	fi

docs-export:
	@test ! -e "$(DOCS_EXPORT_DIR)" || (echo "$(DOCS_EXPORT_DIR) already exists"; exit 1)
	mkdir "$(DOCS_EXPORT_DIR)"
	git archive "$(DOCS_DEPLOY_BRANCH)" | tar -x -C "$(DOCS_EXPORT_DIR)"

docs-set-default:
	mike set-default --remote $(DOCS_DEPLOY_REMOTE) --branch $(DOCS_DEPLOY_BRANCH) $(MIKE_PUSH) $(MIKE_FLAGS) $(DEFAULT_VERSION)

upgrade-submodules:
	git submodule update --remote --init --recursive

download-bundled-contexts:
	python scripts/download_contexts.py

RUFF_TARGET = lib/pyld/*.py lib/pyld/cli/*.py lib/pyld/cli/commands/*.py tests/*.py docs_macros.py

lint:
	ruff check $(RUFF_TARGET)

fmt:
	ruff check --fix $(RUFF_TARGET)
	ruff format $(RUFF_TARGET)
