Contributing to PyLD
====================

Want to contribute to PyLD? Great! Here are a few notes:

Code
----

* In general, follow the common `PEP 8 Style Guide`_.
* Try to make the code pass flake8_ checks.

  * ``flake8 lib/pyld/jsonld.py``

* Use version X.Y.Z-dev in dev mode.
* Use version X.Y.Z for releases.

Versioning
----------

* Follow the `Semantic Versioning`_ guidelines.

Release Process
---------------

* ``$EDITOR CHANGELOG.md``: update CHANGELOG with new notes, version, and date.
* commit changes
* ``$EDITOR lib/pyld/__about__.py``: update to release version and remove ``-dev``
  suffix.
* ``git commit CHANGELOG.md lib/pyld/__about__.py -m "Release {version}."``
* ``git tag {version}``
* ``$EDITOR lib/pyld/__about__.py``: update to next version and add ``-dev`` suffix.
* ``git commit lib/pyld/__about__.py -m "Start {next-version}."``
* ``git push --tags``

To ensure a clean `package <https://pypi.org/project/PyLD/>`_ upload to PyPI_,
use a clean checkout, and run the following:

* ``git checkout {version}``
* ``python setup.py sdist upload``

Implementation Report Process
-----------------------------

As of early 2020, the process to generate an EARL report for the official
`JSON-LD 1.1 Processor Conformance`_ page is:

* Run the tests on the ``json-ld-api`` and ``json-ld-framing`` test repos to
  generate a ``.jsonld`` test report:

  * ``python tests/runtests.py ../json-ld-api/tests/ ../json-ld-framing/tests/ -e pyld-earl.jsonld``

* Use the rdf_ tool to generate a ``.ttl``:

  * ``rdf serialize pyld-earl.jsonld --output-format turtle -o pyld-earl.ttl``

* Optionally follow the `report instructions`_ to generate the HTML report for
  inspection.
* Submit a PR to the `json-ld-api repository`_ with at least the ``.ttl``:

.. _JSON-LD 1.1 Processor Conformance: https://w3c.github.io/json-ld-api/reports/
.. _PEP 8 Style Guide: https://www.python.org/dev/peps/pep-0008/
.. _Semantic Versioning: https://semver.org/
.. _flake8: https://pypi.python.org/pypi/flake8
.. _json-ld-api repository: https://github.com/w3c/json-ld-api/pulls
.. _rdf: https://rubygems.org/gems/rdf
.. _report instructions: https://github.com/w3c/json-ld-api/tree/master/reports
.. _PyPI: https://pypi.org/
