# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

"""Minimal setup.py to register an entrypoint."""

import setuptools

setuptools.setup(
    name="example_hypothesis_entrypoint",
    author="Example Author",
    email="author@example.com",
    license="MPL v2",
    description="Minimal setup.py to register an entrypoint.",
    packages=setuptools.find_packages(),
    install_requires=["hypothesis"],
    python_requires=">=3.7",
    entry_points={
        "hypothesis": ["_ = example_hypothesis_entrypoint:_hypothesis_setup_hook"]
    },
)
