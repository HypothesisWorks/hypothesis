# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
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

from setuptools import setup, find_packages


def local_file(name):
    return os.path.relpath(os.path.join(os.path.dirname(__file__), name))


SOURCE = local_file('src')
README = local_file('README.rst')


# Assignment to placate pyflakes. The actual version is from the exec that
# follows.
__version__ = None

with open(local_file('src/hypothesis/version.py')) as o:
    exec(o.read())

assert __version__ is not None


extras = {
    'datetime':  ['pytz'],
    'pytz':  ['pytz'],
    'fakefactory': ['Faker>=0.7.0,<=0.7.1'],
    'django': ['pytz', 'django>=1.8,<2'],
    'numpy': ['numpy>=1.9.0'],
    'pytest': ['pytest>=2.8.0'],
}

extras['faker'] = extras['fakefactory']

extras['all'] = sorted(sum(extras.values(), []))

extras[":python_version == '2.7'"] = ['enum34']
extras[":python_version == '3.3'"] = ['enum34']

install_requires = []

if sys.version_info[0] < 3:
    install_requires.append('enum34')

setup(
    name='hypothesis',
    version=__version__,
    author='David R. MacIver',
    author_email='david@drmaciver.com',
    packages=find_packages(SOURCE),
    package_dir={'': SOURCE},
    url='https://github.com/HypothesisWorks/hypothesis-python',
    license='MPL v2',
    description='A library for property based testing',
    zip_safe=False,
    extras_require=extras,
    install_requires=install_requires,
    python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*',
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
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Software Development :: Testing',
    ],
    entry_points={
        'pytest11': ['hypothesispytest = hypothesis.extra.pytestplugin'],
    },
    long_description=open(README).read(),
)
