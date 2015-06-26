# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by other. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from distutils.core import setup
from setuptools.command.test import test as TestCommand
from setuptools import find_packages
import sys
import os


class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)


def local_file(name):
    return os.path.join(os.path.dirname(__file__), name)

SOURCE = local_file("src")
REQUIREMENTS = local_file("requirements.txt")
README = local_file("README.rst")

setup(
    name='hypothesis-django',
    version='0.9.0',
    author='David R. MacIver',
    author_email='david@drmaciver.com',
    packages=find_packages(SOURCE),
    package_dir={"": SOURCE},
    url='https://github.com/DRMacIver/hypothesis',
    license='MPL v2',
    description='Adds support for Django testing to Hypothesis',
    install_requires=[
        "hypothesis>=1.7.0,<1.7.99",
        "hypothesis-datetime>=1.7.0,<1.7.99",
        "hypothesis-fakefactory>=0.10.0,<0.10.99",
        "django>=1.7",
    ],
    long_description=open(README).read(),
    entry_points={
        'hypothesis.extra': 'hypothesisdjango = hypothesisdjango'
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
        "Operating System :: Unix",
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: Software Development :: Testing",
    ],
    tests_require=['pytest'],
    cmdclass={'test': PyTest},
)
