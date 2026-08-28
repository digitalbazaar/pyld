"""Runtime state for one CLI invocation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class State:
    """Per-invocation CLI state."""

    traceback: bool = False
    cache_file: Path | None = None


current = State()
