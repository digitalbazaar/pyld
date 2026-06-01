import ast
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
BUNDLED_CONTEXTS_SOURCE = (
    ROOT_DIR / 'lib' / 'pyld' / 'documentloader' / 'frozen' / '__init__.py'
)
BUNDLED_CONTEXTS_DIR = (
    ROOT_DIR / 'lib' / 'pyld' / 'documentloader' / 'frozen' / 'bundled'
)


def _bundled_contexts():
    module = ast.parse(BUNDLED_CONTEXTS_SOURCE.read_text(encoding='utf-8'))
    for statement in module.body:
        if not isinstance(statement, ast.AnnAssign):
            continue
        if not isinstance(statement.target, ast.Name):
            continue
        if statement.target.id != 'BUNDLED_CONTEXTS':
            continue
        if not isinstance(statement.value, ast.Dict):
            break
        contexts = {}
        for key_node, value_node in zip(statement.value.keys, statement.value.values):
            if (
                not isinstance(key_node, ast.Constant)
                or not isinstance(key_node.value, str)
            ):
                continue
            contexts[key_node.value] = _bundled_context_path(value_node)
        return contexts
    raise RuntimeError(f'Could not find BUNDLED_CONTEXTS in {BUNDLED_CONTEXTS_SOURCE}')


def _bundled_context_path(value_node):
    if (
        isinstance(value_node, ast.BinOp)
        and isinstance(value_node.op, ast.Div)
        and isinstance(value_node.left, ast.Name)
        and value_node.left.id == '_BUNDLED_DIR'
        and isinstance(value_node.right, ast.Constant)
        and isinstance(value_node.right.value, str)
    ):
        return BUNDLED_CONTEXTS_DIR / value_node.right.value
    raise RuntimeError('Unsupported BUNDLED_CONTEXTS value shape')


def define_env(env):
    @env.macro
    def bundled_contexts_table():
        rows = [
            '| Context URL | Bundled file |',
            '| --- | --- |',
        ]
        for url, path in sorted(_bundled_contexts().items()):
            relative_path = Path(path).relative_to(ROOT_DIR)
            rows.append(f'| `{url}` | `{relative_path}` |')
        return '\n'.join(rows)
