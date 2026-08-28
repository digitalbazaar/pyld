"""CLI output writers."""

from __future__ import annotations

import json
import sys
from typing import Any

from rich.console import Console
from rich.syntax import Syntax

console = Console()


def print_json(document: Any) -> None:
    text = json.dumps(document, indent=2, ensure_ascii=False)
    console.print(
        Syntax(text, 'json', background_color='default'),
        soft_wrap=True,
    )


def print_nquads(document: str) -> None:
    """Write an N-Quads serialization without modifying it."""
    sys.stdout.write(document)
