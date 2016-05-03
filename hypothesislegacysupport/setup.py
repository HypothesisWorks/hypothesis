from __future__ import division, print_function, absolute_import

import os
import sys

from setuptools import setup, find_packages


def local_file(name):
    return os.path.relpath(os.path.join(os.path.dirname(__file__), name))

SOURCE = local_file('src')
README = local_file('README.rst')


# Assignment to placate pyflakes. The actual version is from the exec that
# follows.
__version__ = None


with open(local_file('src/hypothesislegacysupport/version.py')) as o:
    exec(o.read())


PY26_BACKPORTS = ['importlib', 'ordereddict', 'Counter']


install_requires = ['hypothesis==%s' % (__version__,)]

if sys.version_info[:2] == (2, 6):
    install_requires.extend(PY26_BACKPORTS)

setup(
    name='hypothesislegacysupport',
    version=__version__,
    author='David R. MacIver',
    author_email='david@drmaciver.com',
    packages=find_packages(SOURCE),
    package_dir={'': SOURCE},
    url='https://github.com/HypothesisWorks/hypothesis-python',
    license='AGPL',
    install_requires=install_requires,
    extras_require={
        ":python_version == '2.6'": PY26_BACKPORTS,
    }
)
