# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import sys
import warnings
from pathlib import Path

import setuptools

if sys.version_info[:2] < (3, 9):  # "unreachable" sanity check
    raise Exception(
        "You are trying to install Hypothesis using Python "
        f"{sys.version.split()[0]}, but it requires Python 3.9 or later."
        "Update `pip` and `setuptools`, try again, and you will automatically "
        "get the latest compatible version of Hypothesis instead.  "
        "See also https://python3statement.github.io/practicalities/"
    )


def local_file(name):
    return Path(__file__).absolute().parent.joinpath(name).relative_to(Path.cwd())


SOURCE = str(local_file("src"))

setuptools_version = tuple(map(int, setuptools.__version__.split(".")[:1]))

if setuptools_version < (42,):
    # Warning only - very bad if uploading bdist but fine if installing sdist.
    warnings.warn(
        "This version of setuptools is too old to handle license_files "
        "metadata key.  For more info, see:  "
        "https://setuptools.pypa.io/en/latest/userguide/declarative_config.html#metadata",
        stacklevel=1,
    )


# Assignment to placate pyflakes. The actual version is from the exec that follows.
__version__ = None
exec(local_file("src/hypothesis/version.py").read_text(encoding="utf-8"))
assert __version__ is not None


extras = {
    "cli": ["click>=7.0", "black>=19.10b0", "rich>=9.0.0"],
    "codemods": ["libcst>=0.3.16"],
    "ghostwriter": ["black>=19.10b0"],
    "pytz": ["pytz>=2014.1"],
    "dateutil": ["python-dateutil>=1.4"],
    "lark": ["lark>=0.10.1"],  # probably still works with old `lark-parser` too
    "numpy": ["numpy>=1.19.3"],  # oldest with wheels for non-EOL Python (for now)
    "pandas": ["pandas>=1.1"],
    "pytest": ["pytest>=4.6"],
    "dpcontracts": ["dpcontracts>=0.4"],
    "redis": ["redis>=3.0.0"],
    "crosshair": ["hypothesis-crosshair>=0.0.20", "crosshair-tool>=0.0.82"],
    # zoneinfo is an odd one: every dependency is platform-conditional.
    "zoneinfo": [
        "tzdata>=2025.1 ; sys_platform == 'win32' or sys_platform == 'emscripten'",
    ],
    # We only support Django versions with upstream support - see
    # https://www.djangoproject.com/download/#supported-versions
    # We also leave the choice of timezone library to the user, since it
    # might be zoneinfo or pytz depending on version and configuration.
    "django": ["django>=4.2"],
    "watchdog": ["watchdog>=4.0.0"],
}

extras["all"] = sorted(set(sum(extras.values(), [])))


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
    license="MPL-2.0",
    description="A library for property-based testing",
    zip_safe=False,
    extras_require=extras,
    install_requires=[
        "attrs>=22.2.0",
        "exceptiongroup>=1.0.0 ; python_version<'3.11'",
        "sortedcontainers>=2.1.0,<3.0.0",
    ],
    python_requires=">=3.9",
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
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Education :: Testing",
        "Topic :: Software Development :: Testing",
        "Typing :: Typed",
    ],
    py_modules=[
        "_hypothesis_pytestplugin",
        "_hypothesis_ftz_detector",
        "_hypothesis_globals",
    ],
    entry_points={
        "pytest11": ["hypothesispytest = _hypothesis_pytestplugin"],
        "console_scripts": ["hypothesis = hypothesis.extra.cli:main"],
    },
    long_description=local_file("README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    keywords="python testing fuzzing property-based-testing",
)
