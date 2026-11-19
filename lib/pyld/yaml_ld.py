"""YAML parsing for YAML-LD documents."""


def parse_yaml(document):
    """Construct a mapping, sequence, or null from one YAML 1.2 document."""
    from ruamel.yaml import YAML

    parser = YAML(typ='safe', pure=True)
    parser.version = (1, 2)
    parsed_document = parser.load(document)
    if parsed_document is not None and not isinstance(parsed_document, (dict, list)):
        raise ValueError('YAML-LD document root must be a mapping, sequence, or null.')
    return parsed_document
