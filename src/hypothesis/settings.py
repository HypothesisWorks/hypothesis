# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

"""A module controlling settings for Hypothesis to use in falsification.

Either an explicit Settings object can be used or the default object on
this module can be modified.

"""
from __future__ import division, print_function, absolute_import, \
    unicode_literals

import os
from collections import namedtuple

from hypothesis.conventions import not_set

all_settings = {}


class Settings(object):

    """A settings object controls a variety of parameters that are used in
    falsification. There is a single default settings object that all other
    Settings will use as its values s defaults.

    Not all settings parameters are guaranteed to be stable. However the
    following are:

    """
    # pylint: disable=too-many-arguments

    def __getattr__(self, name):
        if name in all_settings:
            return all_settings[name].default

        else:
            raise AttributeError('Settings has no attribute %s' % (name,))

    def __init__(
            self,
            **kwargs
    ):
        for setting in all_settings.values():
            value = kwargs.pop(setting.name, not_set)
            if value == not_set:
                value = getattr(default, setting.name)
            setattr(self, setting.name, value)
        if kwargs:
            raise TypeError('Invalid arguments %s' % (', '.join(kwargs),))

    def __repr__(self):
        bits = []
        for name in all_settings:
            value = getattr(self, name)
            if value != getattr(default, name):
                bits.append('%s=%r' % (name, value))
        bits.sort()
        return 'Settings(%s)' % ', '.join(bits)

default = Settings()

Setting = namedtuple('Setting', ('name', 'description', 'default'))


def _default():
    return default


def define_setting(name, description, default):
    all_settings[name] = Setting(name, description.strip(), default)


define_setting(
    'min_satisfying_examples',
    default=5,
    description="""
Raise Unsatisfiable for any tests which do not produce at least this many
values that pass all assume() calls and which have not exhaustively covered the
search space.
"""
)

define_setting(
    'max_examples',
    default=200,
    description="""
Once this many examples have been considered without finding any counter-
example, falsify will terminate
"""
)

define_setting(
    'timeout',
    default=60,
    description="""
Once this amount of time has passed, falsify will terminate even
if it has not found many examples. This is a soft rather than a hard
limit - Hypothesis won't e.g. interrupt execution of the called
function to stop it. If this value is <= 0 then no timeout will be
applied.
"""
)

define_setting(
    'derandomize',
    default=False,
    description="""
If this is True then hypothesis will run in deterministic mode
where each falsification uses a random number generator that is seeded
based on the hypothesis to falsify, which will be consistent across
multiple runs. This has the advantage that it will eliminate any
randomness from your tests, which may be preferable for some situations
. It does have the disadvantage of making your tests less likely to
find novel breakages.
"""
)

define_setting(
    'database',
    default=None,
    description="""
    database: An instance of hypothesis.database.ExampleDatabase that will be
used to save examples to and load previous examples from. May be None
in which case no storage will be used.
"""
)

DATABASE_OVERRIDE = os.getenv('HYPOTHESIS_DATABASE_FILE')

if DATABASE_OVERRIDE:
    from hypothesis.database import ExampleDatabase
    from hypothesis.database.backend import SQLiteBackend
    default.database = ExampleDatabase(
        backend=SQLiteBackend(DATABASE_OVERRIDE)
    )
