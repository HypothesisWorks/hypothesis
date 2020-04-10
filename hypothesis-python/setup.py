# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

import os
import sys
import warnings

import setuptools

if sys.version_info[:3] < (3, 5, 2):
    raise Exception(
        "This version of Python is too old to install new versions of Hypothesis.  "
        "Update `pip` and `setuptools`, try again, and you will automatically "
        "get the latest compatible version of Hypothesis instead.  "
        "See also https://python3statement.org/practicalities/"
    )


def local_file(name):
    return os.path.relpath(os.path.join(os.path.dirname(__file__), name))


SOURCE = local_file("src")
README = local_file("README.rst")

setuptools_version = tuple(map(int, setuptools.__version__.split(".")[:2]))

if setuptools_version < (36, 2):
    # Warning only - very bad if uploading bdist but fine if installing sdist.
    warnings.warn(
        "This version of setuptools is too old to correctly store "
        "conditional dependencies in binary wheels.  For more info, see:  "
        "https://hynek.me/articles/conditional-python-dependencies/"
    )


# Assignment to placate pyflakes. The actual version is from the exec that
# follows.
__version__ = None

with open(local_file("src/hypothesis/version.py")) as o:
    exec(o.read())

assert __version__ is not None


extras = {
    "pytz": ["pytz>=2014.1"],
    "dateutil": ["python-dateutil>=1.4"],
    "lark": ["lark-parser>=0.6.5"],
    "numpy": ["numpy>=1.9.0"],
    "pandas": ["pandas>=0.19"],
    "pytest": ["pytest>=4.3"],
    "dpcontracts": ["dpcontracts>=0.4"],
    # We only support Django versions with upstream support - see
    # https://www.djangoproject.com/download/#supported-versions
    "django": ["pytz>=2014.1", "django>=2.2"],
}

extras["all"] = sorted(set(sum(extras.values(), [])))


setuptools.setup(
    name="hypothesis",
    version=__version__,
    author="David R. MacIver",
    author_email="david@drmaciver.com",
    packages=setuptools.find_packages(SOURCE),
    package_dir={"": SOURCE},
    package_data={"hypothesis": ["py.typed", "vendor/tlds-alpha-by-domain.txt"]},
    url="https://github.com/HypothesisWorks/hypothesis/tree/master/hypothesis-python",
    project_urls={
        "Website": "https://hypothesis.works",
        "Documentation": "https://hypothesis.readthedocs.io",
        "Issues": "https://github.com/HypothesisWorks/hypothesis/issues",
    },
    license="MPL v2",
    description="A library for property-based testing",
    zip_safe=False,
    extras_require=extras,
    install_requires=["attrs>=19.2.0", "sortedcontainers>=2.1.0,<3.0.0"],
    python_requires=">=3.5.2",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Framework :: Hypothesis",
        "Framework :: Pytest",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
        "Operating System :: Unix",
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Education :: Testing",
        "Topic :: Software Development :: Testing",
        "Typing :: Typed",
    ],
    entry_points={"pytest11": ["hypothesispytest = hypothesis.extra.pytestplugin"]},
    long_description=open(README).read(),
    long_description_content_type="text/x-rst",
    keywords="python testing fuzzing property-based-testing",
)
