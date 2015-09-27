# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

"""A module controlling settings for Hypothesis to use in falsification.

Either an explicit Settings object can be used or the default object on
this module can be modified.

"""

from __future__ import division, print_function, absolute_import

import os
import inspect
import threading
from collections import namedtuple

from hypothesis.errors import InvalidArgument
from hypothesis.utils.conventions import not_set
from hypothesis.utils.dynamicvariables import DynamicVariable

__hypothesis_home_directory = None


def set_hypothesis_home_dir(directory):
    global __hypothesis_home_directory
    __hypothesis_home_directory = directory


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError:
        pass


def hypothesis_home_dir():
    global __hypothesis_home_directory
    if not __hypothesis_home_directory:
        __hypothesis_home_directory = os.getenv(
            'HYPOTHESIS_STORAGE_DIRECTORY')
    if not __hypothesis_home_directory:
        __hypothesis_home_directory = os.path.join(
            os.getcwd(), '.hypothesis'
        )
    mkdir_p(__hypothesis_home_directory)
    return __hypothesis_home_directory


def storage_directory(name):
    path = os.path.join(hypothesis_home_dir(), name)
    mkdir_p(path)
    return path

all_settings = {}


_db_cache = {}


def field_name(setting_name):
    return u'_' + setting_name


def get_class(obj, typ):
    if obj is not None:
        return type(obj)
    else:
        return typ


class SettingsProperty(object):

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        else:
            try:
                return obj.__dict__[self.name]
            except KeyError:
                raise AttributeError(self.name)

    def __set__(self, obj, value):
        obj.__dict__[self.name] = value

    def __delete__(self, obj):
        try:
            del obj.__dict__[self.name]
        except KeyError:
            raise AttributeError(self.name)

    @property
    def __doc__(self):
        return u'\n'.join((
            all_settings[self.name].description,
            u'default value: %r' % (getattr(Settings.default, self.name),)
        ))


class SettingsMeta(type):

    def __init__(self, *args, **kwargs):
        super(SettingsMeta, self).__init__(*args, **kwargs)
        self.default_variable = DynamicVariable(None)

    @property
    def default(self):
        return self.default_variable.value

    @default.setter
    def default(self, value):
        self.default_variable.value = value


class Settings(SettingsMeta('Settings', (object,), {})):

    """A settings object controls a variety of parameters that are used in
    falsification. These may control both the falsification strategy and the
    details of the data that is generated.

    Default values are picked up from the Settings.default object and
    changes made there will be picked up in newly created Settings.

    """

    def __getattr__(self, name):
        if name in all_settings:
            d = all_settings[name].default
            if inspect.isfunction(d):
                d = d()
            return d
        else:
            raise AttributeError(u'Settings has no attribute %s' % (name,))

    def __init__(
            self,
            **kwargs
    ):
        self._database = kwargs.pop(u'database', not_set)
        if Settings.default is not None:
            for setting in all_settings.values():
                if kwargs.get(setting.name, not_set) is not_set:
                    kwargs[setting.name] = getattr(
                        Settings.default, setting.name)
            if self._database is not_set:
                self._database = Settings.default.database
        for name, value in kwargs.items():
            if name not in all_settings:
                raise InvalidArgument(
                    u'Invalid argument %s' % (name,))
            setattr(self, name, value)
        self.storage = threading.local()

    def defaults_stack(self):
        try:
            return self.storage.defaults_stack
        except AttributeError:
            self.storage.defaults_stack = []
            return self.storage.defaults_stack

    @classmethod
    def define_setting(cls, name, description, default, options=None):
        """Add a new setting.

        - name is the name of the property that will be used to access the
          setting. This must be a valid python identifier.
        - description will appear in the property's docstring
        - default is the default value. This may be a zero argument
          function in which case it is evaluated and its result is stored
          the first time it is accessed on any given Settings object.

        """
        if options is not None:
            options = tuple(options)
            if default not in options:
                raise InvalidArgument(
                    u'Default value %r is not in options %r' % (
                        default, options
                    )
                )

        all_settings[name] = Setting(
            name, description.strip(), default, options)
        setattr(cls, name, SettingsProperty(name))

    def __setattr__(self, name, value):
        if name in all_settings:
            setting = all_settings[name]
            if setting.options is not None and value not in setting.options:
                raise InvalidArgument(
                    u'Invalid %s, %r. Valid options: %r' % (
                        name, value, setting.options
                    )
                )
        if name == 'database':
            return object.__setattr__(self, '_database', value)
        elif (
            name not in all_settings and
            name not in (u'storage', u'_database')
        ):
            raise AttributeError(u'No such setting %s' % (name,))
        else:
            return object.__setattr__(self, name, value)

    def __repr__(self):
        bits = []
        for name in all_settings:
            value = getattr(self, name)
            bits.append(u'%s=%r' % (name, value))
        bits.sort()
        return u'Settings(%s)' % u', '.join(bits)

    @property
    def database(self):
        """An ExampleDatabase instance to use for storage of examples. May be
        None.

        If this was explicitly set at Settings instantiation then that
        value will be used (even if it was None). If not and the
        database_file setting is not None this will be lazily loaded as
        an SQLite backed ExampleDatabase using that file the first time
        this property is accessed on a particular thread.

        """
        if self._database is not_set and self.database_file is not None:
            from hypothesis.database import ExampleDatabase
            from hypothesis.database.backend import SQLiteBackend
            if self.database_file not in _db_cache:
                _db_cache[self.database_file] = (
                    ExampleDatabase(backend=SQLiteBackend(self.database_file)))
            return _db_cache[self.database_file]
        if self._database is not_set:
            self._database = None
        return self._database

    def __enter__(self):
        default_context_manager = Settings.default_variable.with_value(self)
        self.defaults_stack().append(default_context_manager)
        default_context_manager.__enter__()
        return self

    def __exit__(self, *args, **kwargs):
        default_context_manager = self.defaults_stack().pop()
        return default_context_manager.__exit__(*args, **kwargs)

Setting = namedtuple(
    u'Setting', (u'name', u'description', u'default', u'options'))


Settings.define_setting(
    u'min_satisfying_examples',
    default=5,
    description="""
Raise Unsatisfiable for any tests which do not produce at least this many
values that pass all assume() calls and which have not exhaustively covered the
search space.
"""
)

Settings.define_setting(
    u'max_examples',
    default=200,
    description="""
Once this many satisfying examples have been considered without finding any
counter-example, falsification will terminate.
"""
)

Settings.define_setting(
    u'max_iterations',
    default=1000,
    description="""
Once this many iterations of the example loop have run, including ones which
failed to satisfy assumptions and ones which produced duplicates, falsification
will terminate.
"""
)

Settings.define_setting(
    u'max_shrinks',
    default=500,
    description="""
Once this many successful shrinks have been performed, Hypothesis will assume
something has gone a bit wrong and give up rather than continuing to try to
shrink the example.
"""
)

Settings.define_setting(
    u'timeout',
    default=60,
    description="""
Once this amount of time has passed, falsify will terminate even
if it has not found many examples. This is a soft rather than a hard
limit - Hypothesis won't e.g. interrupt execution of the called
function to stop it. If this value is <= 0 then no timeout will be
applied.
"""
)

Settings.define_setting(
    u'derandomize',
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

Settings.define_setting(
    u'strict',
    default=os.getenv(u'HYPOTHESIS_STRICT_MODE') == u'true',
    description="""
If set to True, anything that would cause Hypothesis to issue a warning will
instead raise an error.
"""
)

Settings.define_setting(
    u'database_file',
    default=lambda: (
        os.getenv(u'HYPOTHESIS_DATABASE_FILE') or
        os.path.join(hypothesis_home_dir(), u'examples.db')
    ),
    description="""
    database: An instance of hypothesis.database.ExampleDatabase that will be
used to save examples to and load previous examples from. May be None
in which case no storage will be used.
"""
)


class Verbosity(object):

    def __repr__(self):
        return u'Verbosity.%s' % (self.name,)

    def __init__(self, name, level):
        self.name = name
        self.level = level

    def __eq__(self, other):
        return isinstance(other, Verbosity) and (
            self.level == other.level
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return self.level

    def __lt__(self, other):
        return self.level < other.level

    def __le__(self, other):
        return self.level <= other.level

    def __gt__(self, other):
        return self.level > other.level

    def __ge__(self, other):
        return self.level >= other.level

    @classmethod
    def by_name(cls, key):
        result = getattr(cls, key, None)
        if isinstance(result, Verbosity):
            return result
        raise InvalidArgument(u'No such verbosity level %r' % (key,))

Settings.default = Settings()

Verbosity.quiet = Verbosity(u'quiet', 0)
Verbosity.normal = Verbosity(u'normal', 1)
Verbosity.verbose = Verbosity(u'verbose', 2)
Verbosity.debug = Verbosity(u'debug', 3)
Verbosity.all = [
    Verbosity.quiet, Verbosity.normal, Verbosity.verbose, Verbosity.debug
]


ENVIRONMENT_VERBOSITY_OVERRIDE = os.getenv(u'HYPOTHESIS_VERBOSITY_LEVEL')

if ENVIRONMENT_VERBOSITY_OVERRIDE:
    DEFAULT_VERBOSITY = Verbosity.by_name(ENVIRONMENT_VERBOSITY_OVERRIDE)
else:
    DEFAULT_VERBOSITY = Verbosity.normal

Settings.define_setting(
    u'verbosity',
    options=Verbosity.all,
    default=DEFAULT_VERBOSITY,
    description=u'Control the verbosity level of Hypothesis messages',
)
