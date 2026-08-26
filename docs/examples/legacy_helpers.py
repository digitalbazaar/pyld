import json

from pyld.util import from_legacy_dataset, to_legacy_dataset

legacy_dataset = [
    {
        'http://example.org': [
            {
                'subject': {'type': 'blank node', 'value': '_:s1'},
                'predicate': {'type': 'IRI', 'value': 'p1'},
                'object': {'type': 'literal', 'value': 'o1'},
            }
        ]
    }
]

rdflib_dataset = from_legacy_dataset(legacy_dataset)
print(rdflib_dataset.serialize(format="nquads"))

legacy_dataset = to_legacy_dataset(rdflib_dataset)
print(json.dumps(legacy_dataset, indent=2))
