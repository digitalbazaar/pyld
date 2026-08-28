"""The ``pyld cache`` commands."""

from __future__ import annotations

from pyld.cli.input import configured_cache_file
from pyld.cli.output import console


def cache_clear() -> None:
    """Clear the CLI HTTP cache."""
    path = configured_cache_file()
    if path.exists():
        path.unlink()
    console.print('Cache cleared.', style='green')
