# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from setuptools.command.test import test as TestCommand
from setuptools import find_packages, setup
import sys
import os


def local_file(name):
    return os.path.relpath(os.path.join(os.path.dirname(__file__), name))

SOURCE = local_file("src")
README = local_file("README.rst")


# Assignment to placate pyflakes. The actual version is from the exec that
# follows.
__version__ = None

with open(local_file("src/hypothesis/version.py")) as o:
    exec(o.read())

assert __version__ is not None


class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = ["tests"]
        self.test_suite = True

    def run_tests(self):
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)

extras = {
    'datetime':  ["pytz"],
    'fakefactory': ["fake-factory>=0.5.2,<=0.5.3"],
    'django': ['pytz', 'django>=1.7'],
    'numpy': ['numpy>=1.9.0'],
    'pytest': ['pytest>=2.7.0'],
}

extras['all'] = sum(extras.values(), [])
extras['django'].extend(extras['fakefactory'])
extras[":python_version == '2.6'"] = ['importlib', 'ordereddict', 'Counter']


setup(
    name='hypothesis',
    version=__version__,
    author='David R. MacIver',
    author_email='david@drmaciver.com',
    packages=find_packages(SOURCE),
    package_dir={"": SOURCE},
    url='https://github.com/DRMacIver/hypothesis',
    license='MPL v2',
    description='A library for property based testing',
    zip_safe=False,
    extras_require=extras,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
        "Operating System :: Unix",
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.2",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Software Development :: Testing",
    ],
    entry_points={
        'pytest11': ['hypothesispytest = hypothesis.extra.pytestplugin'],
    },
    long_description=open(README).read(),
    tests_require=[
        'pytest', 'flake8'],
    cmdclass={'test': PyTest},
)
