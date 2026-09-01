from pyld import jsonld

doc = {
    "@type": "http://schema.org/Person",
    "http://schema.org/name": "Manu Sporny",
    "http://schema.org/url": {"@id": "http://manu.sporny.org/"},
    "http://schema.org/image": {
        "@id": "http://manu.sporny.org/images/manu.png"
    },
}

normalized = jsonld.normalize(
    doc,
    {"algorithm": "URDNA2015", "format": "application/n-quads"},
)

print(normalized)
