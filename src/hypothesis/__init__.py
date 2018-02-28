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

"""Hypothesis is a library for writing unit tests which are parametrized by
some source of data.

It verifies your code against a wide range of input and minimizes any
failing examples it finds.
"""


from hypothesis._settings import settings, Verbosity, Phase, HealthCheck, \
    unlimited
from hypothesis.version import __version_info__, __version__
from hypothesis.control import assume, note, reject, event
from hypothesis.core import given, find, example, seed, reproduce_failure, \
    PrintSettings
from hypothesis.utils.conventions import infer


__all__ = [
    'settings',
    'Verbosity',
    'HealthCheck',
    'Phase',
    'PrintSettings',
    'assume',
    'reject',
    'seed',
    'given',
    'unlimited',
    'reproduce_failure',
    'find',
    'example',
    'note',
    'event',
    'infer',
    '__version__',
    '__version_info__',
]
