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
import sys
import warnings

import setuptools

if sys.version_info[:2] < (3, 7):
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
    "cli": ["click>=7.0", "black>=19.10b0", "rich>=9.0.0"],
    "codemods": ["libcst>=0.3.16"],
    "ghostwriter": ["black>=19.10b0"],
    "pytz": ["pytz>=2014.1"],
    "dateutil": ["python-dateutil>=1.4"],
    "lark": ["lark-parser>=0.6.5"],
    "numpy": ["numpy>=1.9.0"],
    "pandas": ["pandas>=0.25"],
    "pytest": ["pytest>=4.6"],
    "dpcontracts": ["dpcontracts>=0.4"],
    "redis": ["redis>=3.0.0"],
    # zoneinfo is an odd one: every dependency is conditional, because they're
    # only necessary on old versions of Python or Windows systems.
    "zoneinfo": [
        "tzdata>=2021.5 ; sys_platform == 'win32'",
        "backports.zoneinfo>=0.2.1 ; python_version<'3.9'",
    ],
    # We only support Django versions with upstream support - see
    # https://www.djangoproject.com/download/#supported-versions
    # We also leave the choice of timezone library to the user, since it
    # might be zoneinfo or pytz depending on version and configuration.
    "django": ["django>=2.2"],
}

extras["all"] = sorted(
    set(sum(extras.values(), ["importlib_metadata>=3.6; python_version<'3.8'"]))
)


setuptools.setup(
    name="hypothesis",
    version=__version__,
    author="David R. MacIver and Zac Hatfield-Dodds",
    author_email="david@drmaciver.com",
    packages=setuptools.find_packages(SOURCE),
    package_dir={"": SOURCE},
    package_data={"hypothesis": ["py.typed", "vendor/tlds-alpha-by-domain.txt"]},
    url="https://hypothesis.works",
    project_urls={
        "Source": "https://github.com/HypothesisWorks/hypothesis/tree/master/hypothesis-python",
        "Changelog": "https://hypothesis.readthedocs.io/en/latest/changes.html",
        "Documentation": "https://hypothesis.readthedocs.io",
        "Issues": "https://github.com/HypothesisWorks/hypothesis/issues",
    },
    license="MPL v2",
    description="A library for property-based testing",
    zip_safe=False,
    extras_require=extras,
    install_requires=["attrs>=19.2.0", "sortedcontainers>=2.1.0,<3.0.0"],
    python_requires=">=3.7",
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
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Education :: Testing",
        "Topic :: Software Development :: Testing",
        "Typing :: Typed",
    ],
    py_modules=["_hypothesis_pytestplugin"],
    entry_points={
        "pytest11": ["hypothesispytest = _hypothesis_pytestplugin"],
        "console_scripts": ["hypothesis = hypothesis.extra.cli:main"],
    },
    long_description=open(README).read(),
    long_description_content_type="text/x-rst",
    keywords="python testing fuzzing property-based-testing",
)
