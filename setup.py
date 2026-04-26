# -*- coding: utf-8 -*-
"""
PyLD
====

PyLD_ is a Python JSON-LD_ library.

.. _PyLD: https://github.com/digitalbazaar/pyld
.. _JSON-LD: https://json-ld.org/
"""

from distutils.core import setup
import os

# get meta data
about = {}
with open(os.path.join(
        os.path.dirname(__file__), 'lib', 'pyld', '__about__.py')) as fp:
    exec(fp.read(), about)

with open('README.rst') as fp:
    long_description = fp.read()

setup(
    name='PyLD',
    version=about['__version__'],
    description='Python implementation of the JSON-LD API',
    long_description=long_description,
    long_description_content_type="text/x-rst",
    author='Digital Bazaar',
    author_email='support@digitalbazaar.com',
    url='https://github.com/digitalbazaar/pyld',
    packages=[
        'c14n',
        'pyld',
        'pyld.documentloader',
        'pyld.documentloader.frozen',
    ],
    package_dir={'': 'lib'},
    package_data={
        'pyld.documentloader.frozen': ['bundled/*.jsonld'],
    },
    include_package_data=True,
    license='BSD 3-Clause license',
    classifiers=[
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
    install_requires=[
        'cachetools',
        'frozendict',
        'lxml',
    ],
    extras_require={
        'requests': ['requests'],
        'aiohttp': ['aiohttp'],
        'cachetools': ['cachetools'],
        'frozendict': ['frozendict'],
    }
)
