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

"""A module controlling settings for Hypothesis to use in falsification.

Either an explicit settings object can be used or the default object on
this module can be modified.
"""

from __future__ import division, print_function, absolute_import

import os
import warnings
import threading
import contextlib
from enum import Enum, IntEnum, unique

import attr

from hypothesis.errors import InvalidState, InvalidArgument, \
    HypothesisDeprecationWarning
from hypothesis.internal.compat import text_type
from hypothesis.utils.conventions import UniqueIdentifier, not_set
from hypothesis.internal.reflection import proxies, \
    get_pretty_function_description
from hypothesis.internal.validation import try_convert
from hypothesis.utils.dynamicvariables import DynamicVariable

if False:
    from typing import Any, Dict, List  # noqa

__all__ = [
    'settings',
]


unlimited = UniqueIdentifier('unlimited')


all_settings = {}  # type: Dict[str, Setting]


class settingsProperty(object):

    def __init__(self, name, show_default):
        self.name = name
        self.show_default = show_default

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        else:
            try:
                result = obj.__dict__[self.name]
                # This is a gross hack, but it preserves the old behaviour that
                # you can change the storage directory and it will be reflected
                # in the default database.
                if self.name == 'database' and result is not_set:
                    from hypothesis.database import ExampleDatabase
                    result = ExampleDatabase(not_set)
                return result
            except KeyError:
                raise AttributeError(self.name)

    def __set__(self, obj, value):
        obj.__dict__[self.name] = value

    def __delete__(self, obj):
        raise AttributeError('Cannot delete attribute %s' % (self.name,))

    @property
    def __doc__(self):
        description = all_settings[self.name].description
        deprecation_message = all_settings[self.name].deprecation_message
        default = repr(getattr(settings.default, self.name)) if \
            self.show_default else '(dynamically calculated)'
        return '\n\n'.join([description, 'default value: %s' % (default,),
                            (deprecation_message or '').strip()]).strip()


default_variable = DynamicVariable(None)


class settingsMeta(type):

    def __init__(self, *args, **kwargs):
        super(settingsMeta, self).__init__(*args, **kwargs)

    @property
    def default(self):
        v = default_variable.value
        if v is not None:
            return v
        if hasattr(settings, '_current_profile'):
            settings.load_profile(settings._current_profile)
            assert default_variable.value is not None
        return default_variable.value

    @default.setter
    def default(self, value):
        raise AttributeError('Cannot assign settings.default')

    def _assign_default_internal(self, value):
        default_variable.value = value


class settings(
    settingsMeta('settings', (object,), {})  # type: ignore
):
    """A settings object controls a variety of parameters that are used in
    falsification. These may control both the falsification strategy and the
    details of the data that is generated.

    Default values are picked up from the settings.default object and
    changes made there will be picked up in newly created settings.
    """

    _WHITELISTED_REAL_PROPERTIES = [
        '_construction_complete', 'storage'
    ]
    __definitions_are_locked = False
    _profiles = {}  # type: dict

    def __getattr__(self, name):
        if name in all_settings:
            return all_settings[name].default
        else:
            raise AttributeError('settings has no attribute %s' % (name,))

    def __init__(self, parent=None, **kwargs):
        # type: (settings, **Any) -> None
        if (
            kwargs.get('database', not_set) is not_set and
            kwargs.get('database_file', not_set) is not not_set
        ):
            if kwargs['database_file'] is None:
                kwargs['database'] = None
            else:
                from hypothesis.database import ExampleDatabase
                kwargs['database'] = ExampleDatabase(kwargs['database_file'])
        if not kwargs.get('perform_health_check', True):
            kwargs['suppress_health_check'] = HealthCheck.all()
        if kwargs.get('max_shrinks') == 0:
            kwargs['phases'] = tuple(
                p for p in _validate_phases(kwargs.get('phases'))
                if p != Phase.shrink
            )
        self._construction_complete = False
        deprecations = []
        defaults = parent or settings.default
        if defaults is not None:
            for setting in all_settings.values():
                if kwargs.get(setting.name, not_set) is not_set:
                    kwargs[setting.name] = getattr(defaults, setting.name)
                else:
                    if kwargs[setting.name] != setting.future_default:
                        if setting.deprecation_message is not None:
                            deprecations.append(setting)
                    if setting.validator:
                        kwargs[setting.name] = setting.validator(
                            kwargs[setting.name])
        for name, value in kwargs.items():
            if name not in all_settings:
                raise InvalidArgument(
                    'Invalid argument: %r is not a valid setting' % (name,))
            setattr(self, name, value)
        self.storage = threading.local()
        self._construction_complete = True

        for d in deprecations:
            note_deprecation(d.deprecation_message, self)

    def defaults_stack(self):
        try:
            return self.storage.defaults_stack
        except AttributeError:
            self.storage.defaults_stack = []
            return self.storage.defaults_stack

    def __call__(self, test):
        """Make the settings object (self) an attribute of the test.

        The settings are later discovered by looking them up on the test
        itself.

        Also, we want to issue a deprecation warning for settings used alone
        (without @given) so, note the deprecation in the new test, but also
        attach the version without the warning as an attribute, so that @given
        can unwrap it (since if @given is used, that means we don't want the
        deprecation warning).

        When it's time to turn the warning into an error, we'll raise an
        exception instead of calling note_deprecation (and can delete
        "test(*args, **kwargs)").
        """
        if not callable(test):
            raise InvalidArgument(
                'settings objects can be called as a decorator with @given, '
                'but test=%r' % (test,)
            )
        if hasattr(test, '_hypothesis_internal_settings_applied'):
            note_deprecation(
                '%s has already been decorated with a settings object, which '
                'will be overridden.  This will be an error in a future '
                'version of Hypothesis.\n    Previous:  %r\n    This:  %r' % (
                    get_pretty_function_description(test),
                    test._hypothesis_internal_use_settings,
                    self
                )
            )

        test._hypothesis_internal_use_settings = self

        # For double-@settings check:
        test._hypothesis_internal_settings_applied = True

        @proxies(test)
        def new_test(*args, **kwargs):
            note_deprecation(
                'Using `@settings` without `@given` does not make sense and '
                'will be an error in a future version of Hypothesis.'
            )
            test(*args, **kwargs)

        # @given will get the test from this attribution (rather than use the
        # version with the deprecation warning)
        new_test._hypothesis_internal_test_function_without_warning = test

        # This means @given has been applied, so we don't need to worry about
        # warning for @settings alone.
        has_given_applied = getattr(test, 'is_hypothesis_test', False)
        test_to_use = test if has_given_applied else new_test
        test_to_use._hypothesis_internal_use_settings = self
        # Can't use _hypothesis_internal_use_settings as an indicator that
        # @settings was applied, because @given also assigns that attribute.
        test._hypothesis_internal_settings_applied = True
        return test_to_use

    @classmethod
    def _define_setting(
        cls, name, description, default, options=None,
        validator=None, show_default=True, future_default=not_set,
        deprecation_message=None, hide_repr=not_set,
    ):
        """Add a new setting.

        - name is the name of the property that will be used to access the
          setting. This must be a valid python identifier.
        - description will appear in the property's docstring
        - default is the default value. This may be a zero argument
          function in which case it is evaluated and its result is stored
          the first time it is accessed on any given settings object.
        """
        if settings.__definitions_are_locked:
            raise InvalidState(
                'settings have been locked and may no longer be defined.'
            )
        if options is not None:
            options = tuple(options)
            assert default in options

        if future_default is not_set:
            future_default = default

        if hide_repr is not_set:
            hide_repr = bool(deprecation_message)

        all_settings[name] = Setting(
            name, description.strip(), default, options, validator,
            future_default, deprecation_message, hide_repr,
        )
        setattr(settings, name, settingsProperty(name, show_default))

    @classmethod
    def lock_further_definitions(cls):
        settings.__definitions_are_locked = True

    def __setattr__(self, name, value):
        if name in settings._WHITELISTED_REAL_PROPERTIES:
            return object.__setattr__(self, name, value)
        elif name in all_settings:
            if self._construction_complete:
                raise AttributeError(
                    'settings objects are immutable and may not be assigned to'
                    ' after construction.'
                )
            else:
                setting = all_settings[name]
                if (
                    setting.options is not None and
                    value not in setting.options
                ):
                    raise InvalidArgument(
                        'Invalid %s, %r. Valid options: %r' % (
                            name, value, setting.options
                        )
                    )
                return object.__setattr__(self, name, value)
        else:
            raise AttributeError('No such setting %s' % (name,))

    def __repr__(self):
        bits = []
        for name, setting in all_settings.items():
            value = getattr(self, name)
            # The only settings that are not shown are those that are
            # deprecated and left at their default values.
            if value != setting.default or not setting.hide_repr:
                bits.append('%s=%r' % (name, value))
        return 'settings(%s)' % ', '.join(sorted(bits))

    def show_changed(self):
        bits = []
        for name, setting in all_settings.items():
            value = getattr(self, name)
            if value != setting.default:
                bits.append('%s=%r' % (name, value))
        return ', '.join(sorted(bits, key=len))

    def __enter__(self):
        note_deprecation(
            'Settings should be determined only by global state or with the '
            '@settings decorator.'
        )
        default_context_manager = default_variable.with_value(self)
        self.defaults_stack().append(default_context_manager)
        default_context_manager.__enter__()
        return self

    def __exit__(self, *args, **kwargs):
        default_context_manager = self.defaults_stack().pop()
        return default_context_manager.__exit__(*args, **kwargs)

    @staticmethod
    def register_profile(name, parent=None, **kwargs):
        # type: (str, settings, **Any) -> None
        """Registers a collection of values to be used as a settings profile.

        Settings profiles can be loaded by name - for example, you might
        create a 'fast' profile which runs fewer examples, keep the 'default'
        profile, and create a 'ci' profile that increases the number of
        examples and uses a different database to store failures.

        The arguments to this method are exactly as for
        :class:`~hypothesis.settings`: optional ``parent`` settings, and
        keyword arguments for each setting that will be set differently to
        parent (or settings.default, if parent is None).
        """
        if not isinstance(name, (str, text_type)):
            note_deprecation('name=%r must be a string' % (name,))
        if 'settings' in kwargs:
            if parent is None:
                parent = kwargs.pop('settings')
                note_deprecation('The `settings` argument is deprecated - '
                                 'use `parent` instead.')
            else:
                raise InvalidArgument(
                    'The `settings` argument is deprecated, and has been '
                    'replaced by the `parent` argument.  Use `parent` only.'
                )
        settings._profiles[name] = settings(parent=parent, **kwargs)

    @staticmethod
    def get_profile(name):
        # type: (str) -> settings
        """Return the profile with the given name."""
        if not isinstance(name, (str, text_type)):
            note_deprecation('name=%r must be a string' % (name,))
        try:
            return settings._profiles[name]
        except KeyError:
            raise InvalidArgument('Profile %r is not registered' % (name,))

    @staticmethod
    def load_profile(name):
        # type: (str) -> None
        """Loads in the settings defined in the profile provided.

        If the profile does not exist, InvalidArgument will be raised.
        Any setting not defined in the profile will be the library
        defined default for that setting.
        """
        if not isinstance(name, (str, text_type)):
            note_deprecation('name=%r must be a string' % (name,))
        settings._current_profile = name
        settings._assign_default_internal(settings.get_profile(name))


@contextlib.contextmanager
def local_settings(s):
    default_context_manager = default_variable.with_value(s)
    with default_context_manager:
        yield s


@attr.s()
class Setting(object):
    name = attr.ib()
    description = attr.ib()
    default = attr.ib()
    options = attr.ib()
    validator = attr.ib()
    future_default = attr.ib()
    deprecation_message = attr.ib()
    hide_repr = attr.ib()


settings._define_setting(
    'min_satisfying_examples',
    default=not_set,
    description="""
This doesn't actually do anything, but remains for compatibility reasons.
""",
    deprecation_message="""
The min_satisfying_examples setting has been deprecated and disabled, due to
overlap with the filter_too_much healthcheck and poor interaction with the
max_examples setting.
"""
)

settings._define_setting(
    'max_examples',
    default=100,
    description="""
Once this many satisfying examples have been considered without finding any
counter-example, falsification will terminate.
"""
)

settings._define_setting(
    'max_iterations',
    default=not_set,
    description="""
This doesn't actually do anything, but remains for compatibility reasons.
""",
    deprecation_message="""
The max_iterations setting has been disabled, as internal heuristics are more
useful for this purpose than a user setting.  It no longer has any effect.
"""
)

settings._define_setting(
    'buffer_size',
    default=8 * 1024,
    description="""
The size of the underlying data used to generate examples. If you need to
generate really large examples you may want to increase this, but it will make
your tests slower.
"""
)


settings._define_setting(
    'max_shrinks',
    default=not_set,
    description="""
Passing ``max_shrinks=0`` disables the shrinking phase (see the ``phases``
setting), but any other value has no effect and uses a general heuristic.
""",
    deprecation_message="""
The max_shrinks setting has been disabled, as internal heuristics are more
useful for this purpose than a user setting.
"""
)


def _validate_timeout(n):
    if n is unlimited:
        return -1
    else:
        return n


settings._define_setting(
    'timeout',
    default=60,
    description="""
Once this many seconds have passed, falsify will terminate even
if it has not found many examples. This is a soft rather than a hard
limit - Hypothesis won't e.g. interrupt execution of the called
function to stop it. If this value is <= 0 then no timeout will be
applied.
""",
    hide_repr=False,  # Still affects behaviour at runtime
    deprecation_message="""
The timeout setting is deprecated and will be removed in a future version of
Hypothesis. To get the future behaviour set ``timeout=hypothesis.unlimited``
instead (which will remain valid for a further deprecation period after this
setting has gone away).
""",
    future_default=unlimited,
    validator=_validate_timeout
)

settings._define_setting(
    'derandomize',
    default=False,
    description="""
If this is True then hypothesis will run in deterministic mode
where each falsification uses a random number generator that is seeded
based on the hypothesis to falsify, which will be consistent across
multiple runs. This has the advantage that it will eliminate any
randomness from your tests, which may be preferable for some situations.
It does have the disadvantage of making your tests less likely to
find novel breakages.
"""
)

settings._define_setting(
    'strict',
    default=os.getenv('HYPOTHESIS_STRICT_MODE') == 'true',
    description="""
Strict mode has been deprecated in favor of Python's standard warnings
controls.  Ironically, enabling it is therefore an error - it only exists so
that users get the right *type* of error!
""",
    deprecation_message="""
Strict mode is deprecated and will go away in a future version of Hypothesis.
To get the same behaviour, use
warnings.simplefilter('error', HypothesisDeprecationWarning).
""",
    future_default=False,
)


def _validate_database(db, _from_db_file=False):
    from hypothesis.database import ExampleDatabase
    if db is None or isinstance(db, ExampleDatabase):
        return db
    if _from_db_file or db is not_set:
        return ExampleDatabase(db)
    raise InvalidArgument(
        'Arguments to the database setting must be None or an instance of '
        'ExampleDatabase.  Try passing database=ExampleDatabase(%r), or '
        'construct and use one of the specific subclasses in '
        'hypothesis.database' % (db,)
    )


settings._define_setting(
    'database',
    default=not_set,
    show_default=False,
    description="""
An instance of hypothesis.database.ExampleDatabase that will be
used to save examples to and load previous examples from. May be None
in which case no storage will be used, `:memory:` for an in-memory
database, or any path for a directory-based example database.
""",
    validator=_validate_database,
)

settings._define_setting(
    'database_file',
    default=not_set,
    show_default=False,
    description="""
The file or directory location to save and load previously tried examples;
`:memory:` for an in-memory cache or None to disable caching entirely.
""",
    validator=lambda f: _validate_database(f, _from_db_file=True),
    deprecation_message="""
The `database_file` setting is deprecated in favor of the `database`
setting, and will be removed in a future version.  It only exists at
all for complicated historical reasons and you should just use
`database` instead.
""",
)


@unique
class Phase(IntEnum):
    explicit = 0
    reuse = 1
    generate = 2
    shrink = 3


@unique
class HealthCheck(Enum):
    """Arguments for :attr:`~hypothesis.settings.suppress_health_check`.

    Each member of this enum is a type of health check to suppress.
    """

    def __repr__(self):
        return '%s.%s' % (self.__class__.__name__, self.name)

    @classmethod
    def all(cls):
        # type: () -> List[HealthCheck]
        bad = (HealthCheck.exception_in_generation, HealthCheck.random_module)
        return [h for h in list(cls) if h not in bad]

    exception_in_generation = 0
    """Deprecated and no longer does anything. It used to convert errors in
    data generation into FailedHealthCheck error."""

    data_too_large = 1
    """Check for when the typical size of the examples you are generating
    exceeds the maximum allowed size too often."""

    filter_too_much = 2
    """Check for when the test is filtering out too many examples, either
    through use of :func:`~hypothesis.assume()` or :ref:`filter() <filtering>`,
    or occasionally for Hypothesis internal reasons."""

    too_slow = 3
    """Check for when your data generation is extremely slow and likely to hurt
    testing."""

    random_module = 4
    """Deprecated and no longer does anything. It used to check for whether
    your tests used the global random module. Now @given tests automatically
    seed random so this is no longer an error."""

    return_value = 5
    """Checks if your tests return a non-None value (which will be ignored and
    is unlikely to do what you want)."""

    hung_test = 6
    """Checks if your tests have been running for a very long time."""

    large_base_example = 7
    """Checks if the natural example to shrink towards is very large."""

    not_a_test_method = 8
    """Checks if @given has been applied to a method of unittest.TestCase."""


@unique
class Statistics(IntEnum):
    never = 0
    interesting = 1
    always = 2


@unique
class Verbosity(IntEnum):
    quiet = 0
    normal = 1
    verbose = 2
    debug = 3

    @staticmethod
    def _get_default():
        # type: () -> Verbosity
        var = os.getenv('HYPOTHESIS_VERBOSITY_LEVEL')
        if var is not None:  # pragma: no cover
            try:
                result = Verbosity[var]
            except KeyError:
                raise InvalidArgument('No such verbosity level %r' % (var,))

            warnings.warn(HypothesisDeprecationWarning(
                'The HYPOTHESIS_VERBOSITY_LEVEL environment variable is '
                'deprecated, and will be ignored by a future version of '
                'Hypothesis.  Configure your verbosity level via a '
                'settings profile instead.'
            ))
            return result
        return Verbosity.normal

    def __repr__(self):
        return 'Verbosity.%s' % (self.name,)


settings._define_setting(
    'verbosity',
    options=tuple(Verbosity),
    default=Verbosity._get_default(),
    description='Control the verbosity level of Hypothesis messages',
)


def _validate_phases(phases):
    if phases is None:
        return tuple(Phase)
    phases = tuple(phases)
    for a in phases:
        if not isinstance(a, Phase):
            raise InvalidArgument('%r is not a valid phase' % (a,))
    return phases


settings._define_setting(
    'phases',
    default=tuple(Phase),
    description=(
        'Control which phases should be run. ' +
        'See :ref:`the full documentation for more details <phases>`'
    ),
    validator=_validate_phases,
)

settings._define_setting(
    name='stateful_step_count',
    default=50,
    description="""
Number of steps to run a stateful program for before giving up on it breaking.
"""
)

settings._define_setting(
    'perform_health_check',
    default=not_set,
    description=u"""
If set to True, Hypothesis will run a preliminary health check before
attempting to actually execute your test.
""",
    deprecation_message="""
This setting is deprecated, as `perform_health_check=False` duplicates the
effect of `suppress_health_check=HealthCheck.all()`.  Use that instead!
""",
)


def validate_health_check_suppressions(suppressions):
    suppressions = try_convert(list, suppressions, 'suppress_health_check')
    for s in suppressions:
        if not isinstance(s, HealthCheck):
            note_deprecation((
                'Non-HealthCheck value %r of type %s in suppress_health_check '
                'will be ignored, and will become an error in a future '
                'version of Hypothesis') % (
                s, type(s).__name__,
            ))
        elif s in (
            HealthCheck.exception_in_generation, HealthCheck.random_module
        ):
            note_deprecation((
                '%s is now ignored and suppressing it is a no-op. This will '
                'become an error in a future version of Hypothesis. Simply '
                'remove it from your list of suppressions to get the same '
                'effect.') % (s,))
    return suppressions


settings._define_setting(
    'suppress_health_check',
    default=(),
    description="""A list of health checks to disable.""",
    validator=validate_health_check_suppressions
)

settings._define_setting(
    'deadline',
    default=not_set,
    description=u"""
If set, a time in milliseconds (which may be a float to express
smaller units of time) that each individual example (i.e. each time your test
function is called, not the whole decorated test) within a test is not
allowed to exceed. Tests which take longer than that may be converted into
errors (but will not necessarily be if close to the deadline, to allow some
variability in test run time).

Set this to None to disable this behaviour entirely.

In future this will default to 200. For now, a
HypothesisDeprecationWarning will be emitted if you exceed that default
deadline and have not explicitly set a deadline yourself.
"""
)

settings._define_setting(
    'use_coverage',
    default=not_set,
    deprecation_message="""
use_coverage no longer does anything and can be removed from your settings.
""",
    description="""
A flag to enable a feature that no longer exists. This setting is present
only for backwards compatibility purposes.
"""
)


class PrintSettings(Enum):
    """Flags to determine whether or not to print a detailed example blob to
    use with :func:`~hypothesis.reproduce_failure` for failing test cases."""

    NEVER = 0
    """Never print a blob."""

    INFER = 1
    """Make an educated guess as to whether it would be appropriate to print
    the blob.

    The current rules are that this will print if:

    1. The output from Hypothesis appears to be unsuitable for use with
       :func:`~hypothesis.example`, and
    2. The output is not too long, and
    3. Verbosity is at least normal."""

    ALWAYS = 2
    """Always print a blob on failure."""


settings._define_setting(
    'print_blob',
    default=PrintSettings.INFER,
    description="""
Determines whether to print blobs after tests that can be used to reproduce
failures.

See :ref:`the documentation on @reproduce_failure <reproduce_failure>` for
more details of this behaviour.
"""
)

settings.lock_further_definitions()


def note_deprecation(message, s=None):
    # type: (str, settings) -> None
    if s is None:
        s = settings.default
    assert s is not None
    verbosity = s.verbosity
    warning = HypothesisDeprecationWarning(message)
    if verbosity > Verbosity.quiet:
        warnings.warn(warning, stacklevel=3)


settings.register_profile('default', settings())
settings.load_profile('default')
assert settings.default is not None
