"""Console-script entry for ``pyld`` that defers importing optional CLI deps."""

from __future__ import annotations

import sys


def _load_cli():
    from pyld import cli

    return cli


def main(args: list[str] | None = None) -> None:
    """Entry point registered by setuptools ``console_scripts``."""
    try:
        cli = _load_cli()
    except ImportError:
        sys.stderr.write(
            'The pyld command-line interface requires optional dependencies.\n'
            'Install them with: pip install "PyLD[cli]"\n'
        )
        raise SystemExit(1) from None
    cli.main(args)
