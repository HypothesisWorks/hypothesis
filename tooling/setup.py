# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import os

import setuptools


def local_file(name):
    return os.path.relpath(os.path.join(os.path.dirname(__file__), name))


SOURCE = local_file("src")
README = local_file("README.md")

setuptools.setup(
    name="hypothesis-tooling",
    # We don't actually ship this, it just has a setup.py for convenience.
    version="0.0.0",
    author="David R. MacIver",
    author_email="david@drmaciver.com",
    packages=setuptools.find_packages(SOURCE),
    package_dir={"": SOURCE},
    url="https://github.com/HypothesisWorks/hypothesis-python/tree/master/tooling",
    license="MPL v2",
    description="A library for property-based testing",
    python_requires=">=3.7",
    long_description=open(README).read(),  # noqa
)
