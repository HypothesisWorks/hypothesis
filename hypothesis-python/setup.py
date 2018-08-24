# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import os
import sys
import warnings

import setuptools


def local_file(name):
    return os.path.relpath(os.path.join(os.path.dirname(__file__), name))


SOURCE = local_file('src')
README = local_file('README.rst')

setuptools_version = tuple(map(int, setuptools.__version__.split('.')[:2]))

if setuptools_version < (36, 2):
    # Warning only - very bad if uploading bdist but fine if installing sdist.
    warnings.warn(
        'This version of setuptools is too old to correctly store '
        'conditional dependencies in binary wheels.  For more info, see:  '
        'https://hynek.me/articles/conditional-python-dependencies/'
    )


# Assignment to placate pyflakes. The actual version is from the exec that
# follows.
__version__ = None

with open(local_file('src/hypothesis/version.py')) as o:
    exec(o.read())

assert __version__ is not None


extras = {
    'datetime': ['pytz>=2014.1'],
    'pytz': ['pytz>=2014.1'],
    'dateutil': ['python-dateutil>=1.4'],
    'fakefactory': ['Faker>=0.7'],
    'numpy': ['numpy>=1.9.0'],
    'pytest': ['pytest>=3.0'],
    'dpcontracts': ['dpcontracts>=0.4'],
    # We only support Django versions with upstream support - see
    # https://www.djangoproject.com/download/#supported-versions
    'django': ['pytz', 'django>=1.11'],
}

extras['faker'] = extras['fakefactory']
extras['all'] = sorted(sum(extras.values(), []))


install_requires = ['attrs>=16.0.0']
# Using an environment marker on enum34 makes the dependency condition
# independent of the build environemnt, which is important for wheels.
# https://www.python.org/dev/peps/pep-0345/#environment-markers
if sys.version_info[0] < 3 and setuptools_version < (8, 0):
    # Except really old systems, where we give up and install unconditionally
    install_requires.append('enum34')
else:
    install_requires.append('enum34; python_version=="2.7"')


setuptools.setup(
    name='hypothesis',
    version=__version__,
    author='David R. MacIver',
    author_email='david@drmaciver.com',
    packages=setuptools.find_packages(SOURCE),
    package_dir={'': SOURCE},
    package_data={'hypothesis': ['py.typed']},
    url=(
        'https://github.com/HypothesisWorks/hypothesis/'
        'tree/master/hypothesis-python'
    ),
    license='MPL v2',
    description='A library for property based testing',
    zip_safe=False,
    extras_require=extras,
    install_requires=install_requires,
    python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
        'Operating System :: Unix',
        'Operating System :: POSIX',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Software Development :: Testing',
        'Framework :: Pytest',
    ],
    entry_points={
        'pytest11': ['hypothesispytest = hypothesis.extra.pytestplugin'],
    },
    long_description=open(README).read(),
    keywords='python testing fuzzing property-based-testing',
)
