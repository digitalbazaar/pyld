# -*- coding: utf-8 -*-
"""
PyLD
====

PyLD_ is a Python JSON-LD_ library.

.. _PyLD: http://github.com/digitalbazaar/pyld
.. _JSON-LD: http://json-ld.org/
"""

from distutils.core import setup
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))
from pyld import jsonld

with open('README.rst') as file:
    long_description = file.read()

setup(
    name = 'PyLD',
    version = jsonld.__version__,
    description = 'Python implementation of the JSON-LD API',
    long_description=long_description,
    author = 'Digital Bazaar',
    author_email = 'support@digitalbazaar.com',
    url = 'http://github.com/digitalbazaar/pyld',
    packages = ['pyld'],
    package_dir = {'': 'lib'},
    license = 'BSD 3-Clause license',
    classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet',
        'Topic :: Software Development :: Libraries',
    ],
)
