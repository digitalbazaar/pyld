#!/usr/bin/env python3
"""Refresh the JSON-LD contexts bundled with FrozenDocumentLoader.

Fetches each URL in :data:`pyld.documentloader.frozen.BUNDLED_CONTEXTS` over
HTTPS and writes the response body to the corresponding bundled file path.
The mapping is the single source of truth — there is no separate manifest
here.

Run from the repo root::

    python scripts/download_contexts.py

Exits non-zero on any HTTP failure or non-JSON response.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / 'lib'))

from pyld.documentloader.frozen import BUNDLED_CONTEXTS  # noqa: E402


def download() -> int:
    headers = {'Accept': 'application/ld+json, application/json'}
    failures: list[str] = []
    for url, target in BUNDLED_CONTEXTS.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            response = requests.get(
                url, headers=headers, timeout=30, allow_redirects=True
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            print(f'FAIL {url}: {exc}', file=sys.stderr)
            failures.append(url)
            continue
        target.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + '\n',
            encoding='utf-8',
        )
        print(f'OK   {url} -> {target.relative_to(REPO_ROOT)}')
    if failures:
        print(
            f'\n{len(failures)} URL(s) failed; bundle may be incomplete.',
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(download())
