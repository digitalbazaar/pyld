"""YAML parsing for YAML-LD documents."""

from math import isfinite


class YamlLdError(ValueError):
    """YAML-LD syntax error with a processing error code."""

    code = 'mapping-key-error'


def parse_yaml(document):
    """Construct a mapping, sequence, or null from one YAML 1.2 document."""
    from ruamel.yaml import YAML
    from ruamel.yaml.constructor import SafeConstructor
    from ruamel.yaml.nodes import ScalarNode

    class YamlLdConstructor(SafeConstructor):
        def construct_mapping(self, node, deep=False):
            for key_node, _ in node.value:
                if (
                    not isinstance(key_node, ScalarNode)
                    or key_node.tag != 'tag:yaml.org,2002:str'
                ):
                    raise YamlLdError('YAML-LD mapping keys must be strings.')
            return super().construct_mapping(node, deep=deep)

        def construct_yaml_float(self, node):
            value = super().construct_yaml_float(node)
            if not isfinite(value):
                raise ValueError('YAML-LD numbers must be finite.')
            return value

    YamlLdConstructor.add_constructor(
        'tag:yaml.org,2002:float', YamlLdConstructor.construct_yaml_float
    )

    parser = YAML(typ='safe', pure=True)
    parser.Constructor = YamlLdConstructor
    parser.version = (1, 2)
    parsed_document = parser.load(document)
    if parsed_document is not None and not isinstance(parsed_document, (dict, list)):
        raise ValueError('YAML-LD document root must be a mapping, sequence, or null.')

    return parsed_document
