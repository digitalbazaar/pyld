"""YAML parsing for YAML-LD documents."""


def parse_yaml(document):
    """Construct a Python value from one YAML 1.2 document."""
    from ruamel.yaml import YAML

    parser = YAML(typ='safe', pure=True)
    parser.version = (1, 2)
    return parser.load(document)
