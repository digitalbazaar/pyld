from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR / 'lib'))


def define_env(env):
    @env.macro
    def bundled_contexts_table():
        from pyld import BUNDLED_CONTEXTS

        rows = [
            '| Context URL | Bundled file |',
            '| --- | --- |',
        ]
        for url, path in sorted(BUNDLED_CONTEXTS.items()):
            relative_path = Path(path).relative_to(ROOT_DIR)
            rows.append(f'| `{url}` | `{relative_path}` |')
        return '\n'.join(rows)
