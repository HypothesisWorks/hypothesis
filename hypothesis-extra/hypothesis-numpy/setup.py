# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from distutils.core import setup
from setuptools import find_packages
import os
import platform


def local_file(name):
    return os.path.join(os.path.dirname(__file__), name)

SOURCE = local_file("src")
REQUIREMENTS = local_file("requirements.txt")
README = local_file("README.rst")

install_requires = [
    "hypothesis>=1.6,<1.6.99",
]
if platform.python_implementation() == 'CPython':
    install_requires.append("numpy>=1.9.0,<1.9.99")

setup(
    name='hypothesis-numpy',
    version='0.4.1',
    author='David R. MacIver',
    author_email='david@drmaciver.com',
    packages=find_packages(SOURCE),
    package_dir={"": SOURCE},
    url='https://github.com/DRMacIver/hypothesis',
    license='MPL v2',
    description='Adds support for generating datetime to Hypothesis',
    install_requires=install_requires,
    long_description=open(README).read(),
    entry_points={
        'hypothesis.extra': 'hypothesisnumpy = hypothesisnumpy'
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
)
