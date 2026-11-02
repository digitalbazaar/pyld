"""YAML parsing for YAML-LD documents."""

from math import isfinite


def parse_yaml(document):
    """Construct a mapping, sequence, or null from one YAML 1.2 document."""
    from ruamel.yaml import YAML
    from ruamel.yaml.constructor import SafeConstructor

    class YamlLdConstructor(SafeConstructor):
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

    ancestors = set()

    def validate_no_cycles(value):
        if not isinstance(value, (dict, list)):
            return
        identity = id(value)
        if identity in ancestors:
            raise ValueError('YAML-LD documents must not contain cycles.')
        ancestors.add(identity)
        for child in value.values() if isinstance(value, dict) else value:
            validate_no_cycles(child)
        ancestors.remove(identity)

    validate_no_cycles(parsed_document)
    return parsed_document
