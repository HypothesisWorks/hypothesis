# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
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

"""A module controlling settings for Hypothesis to use in falsification.

Either an explicit settings object can be used or the default object on
this module can be modified.
"""

from __future__ import absolute_import, division, print_function

import contextlib
import datetime
import inspect
import threading
import warnings
from enum import Enum, IntEnum, unique

import attr

from hypothesis.errors import (
    HypothesisDeprecationWarning,
    InvalidArgument,
    InvalidState,
)
from hypothesis.internal.compat import string_types
from hypothesis.internal.reflection import get_pretty_function_description, proxies
from hypothesis.internal.validation import check_type, try_convert
from hypothesis.utils.conventions import UniqueIdentifier, not_set
from hypothesis.utils.dynamicvariables import DynamicVariable

if False:
    from typing import Any, Dict, List  # noqa

__all__ = ["settings"]


unlimited = UniqueIdentifier("unlimited")


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
                if self.name == "database" and result is not_set:
                    from hypothesis.database import ExampleDatabase

                    result = ExampleDatabase(not_set)
                return result
            except KeyError:
                raise AttributeError(self.name)

    def __set__(self, obj, value):
        obj.__dict__[self.name] = value

    def __delete__(self, obj):
        raise AttributeError("Cannot delete attribute %s" % (self.name,))

    @property
    def __doc__(self):
        description = all_settings[self.name].description
        deprecation_message = all_settings[self.name].deprecation_message
        default = (
            repr(getattr(settings.default, self.name))
            if self.show_default
            else "(dynamically calculated)"
        )
        return "\n\n".join(
            [
                description,
                "default value: %s" % (default,),
                (deprecation_message or "").strip(),
            ]
        ).strip()


default_variable = DynamicVariable(None)


class settingsMeta(type):
    def __init__(self, *args, **kwargs):
        super(settingsMeta, self).__init__(*args, **kwargs)

    @property
    def default(self):
        v = default_variable.value
        if v is not None:
            return v
        if hasattr(settings, "_current_profile"):
            settings.load_profile(settings._current_profile)
            assert default_variable.value is not None
        return default_variable.value

    def _assign_default_internal(self, value):
        default_variable.value = value

    def __setattr__(self, name, value):
        if name == "default":
            raise AttributeError(
                "Cannot assign to the property settings.default - "
                "consider using settings.load_profile instead."
            )
        elif not (isinstance(value, settingsProperty) or name.startswith("_")):
            raise AttributeError(
                "Cannot assign hypothesis.settings.%s=%r - the settings "
                "class is immutable.  You can change the global default "
                "settings with settings.load_profile, or use @settings(...) "
                "to decorate your test instead." % (name, value)
            )
        return type.__setattr__(self, name, value)


class settings(settingsMeta("settings", (object,), {})):  # type: ignore
    """A settings object controls a variety of parameters that are used in
    falsification. These may control both the falsification strategy and the
    details of the data that is generated.

    Default values are picked up from the settings.default object and
    changes made there will be picked up in newly created settings.
    """

    _WHITELISTED_REAL_PROPERTIES = ["_construction_complete", "storage"]
    __definitions_are_locked = False
    _profiles = {}  # type: dict

    def __getattr__(self, name):
        if name in all_settings:
            return all_settings[name].default
        else:
            raise AttributeError("settings has no attribute %s" % (name,))

    def __init__(self, parent=None, **kwargs):
        # type: (settings, **Any) -> None
        if kwargs.get("derandomize"):
            if kwargs.get("database") is not None:
                raise InvalidArgument(
                    "derandomize=True implies database=None, so passing "
                    "database=%r too is invalid." % (kwargs["database"],)
                )
            kwargs["database"] = None
        self._construction_complete = False
        deprecations = []
        defaults = parent or settings.default
        if defaults is not None:
            for setting in all_settings.values():
                if kwargs.get(setting.name, not_set) is not_set:
                    kwargs[setting.name] = getattr(defaults, setting.name)
                else:
                    if setting.validator:
                        kwargs[setting.name] = setting.validator(kwargs[setting.name])
                    if setting.deprecation_message is not None:
                        deprecations.append(setting)
        for name, value in kwargs.items():
            if name not in all_settings:
                raise InvalidArgument(
                    "Invalid argument: %r is not a valid setting" % (name,)
                )
            setattr(self, name, value)
        self.storage = threading.local()
        self._construction_complete = True

        for d in deprecations:
            note_deprecation(
                d.deprecation_message,
                since=d.deprecated_since,
                verbosity=self.verbosity,
            )

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
                "settings objects can be called as a decorator with @given, "
                "but test=%r" % (test,)
            )
        if inspect.isclass(test):
            from hypothesis.stateful import GenericStateMachine

            if issubclass(test, GenericStateMachine):
                attr_name = "_hypothesis_internal_settings_applied"
                if getattr(test, attr_name, False):
                    raise InvalidArgument(
                        "Applying the @settings decorator twice would "
                        "overwrite the first version; merge their arguments "
                        "instead."
                    )
                setattr(test, attr_name, True)
                test.TestCase.settings = self
                return test
            else:
                raise InvalidArgument(
                    "@settings(...) can only be used as a decorator on "
                    "functions, or on subclasses of GenericStateMachine."
                )
        if hasattr(test, "_hypothesis_internal_settings_applied"):
            raise InvalidArgument(
                "%s has already been decorated with a settings object."
                "\n    Previous:  %r\n    This:  %r"
                % (
                    get_pretty_function_description(test),
                    test._hypothesis_internal_use_settings,
                    self,
                )
            )

        test._hypothesis_internal_use_settings = self

        # For double-@settings check:
        test._hypothesis_internal_settings_applied = True

        @proxies(test)
        def new_test(*args, **kwargs):
            raise InvalidArgument(
                "Using `@settings` on a test without `@given` is completely pointless."
            )

        # @given will get the test from this attribution (rather than use the
        # version with the deprecation warning)
        new_test._hypothesis_internal_test_function_without_warning = test

        # This means @given has been applied, so we don't need to worry about
        # warning for @settings alone.
        has_given_applied = getattr(test, "is_hypothesis_test", False)
        test_to_use = test if has_given_applied else new_test
        test_to_use._hypothesis_internal_use_settings = self
        # Can't use _hypothesis_internal_use_settings as an indicator that
        # @settings was applied, because @given also assigns that attribute.
        test._hypothesis_internal_settings_applied = True
        return test_to_use

    @classmethod
    def _define_setting(
        cls,
        name,
        description,
        default,
        options=None,
        validator=None,
        show_default=True,
        deprecation_message=None,
        deprecated_since=None,
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
                "settings have been locked and may no longer be defined."
            )
        if options is not None:
            options = tuple(options)
            assert default in options

        all_settings[name] = Setting(
            name=name,
            description=description.strip(),
            default=default,
            options=options,
            validator=validator,
            deprecation_message=deprecation_message,
            deprecated_since=deprecated_since,
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
                    "settings objects are immutable and may not be assigned to"
                    " after construction."
                )
            else:
                setting = all_settings[name]
                if setting.options is not None and value not in setting.options:
                    raise InvalidArgument(
                        "Invalid %s, %r. Valid options: %r"
                        % (name, value, setting.options)
                    )
                return object.__setattr__(self, name, value)
        else:
            raise AttributeError("No such setting %s" % (name,))

    def __repr__(self):
        bits = []
        for name, setting in all_settings.items():
            value = getattr(self, name)
            # The only settings that are not shown are those that are
            # deprecated and left at their default values.
            if value != setting.default or not setting.deprecation_message:
                bits.append("%s=%r" % (name, value))
        return "settings(%s)" % ", ".join(sorted(bits))

    def show_changed(self):
        bits = []
        for name, setting in all_settings.items():
            value = getattr(self, name)
            if value != setting.default:
                bits.append("%s=%r" % (name, value))
        return ", ".join(sorted(bits, key=len))

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
        check_type(string_types, name, "name")
        settings._profiles[name] = settings(parent=parent, **kwargs)

    @staticmethod
    def get_profile(name):
        # type: (str) -> settings
        """Return the profile with the given name."""
        check_type(string_types, name, "name")
        try:
            return settings._profiles[name]
        except KeyError:
            raise InvalidArgument("Profile %r is not registered" % (name,))

    @staticmethod
    def load_profile(name):
        # type: (str) -> None
        """Loads in the settings defined in the profile provided.

        If the profile does not exist, InvalidArgument will be raised.
        Any setting not defined in the profile will be the library
        defined default for that setting.
        """
        check_type(string_types, name, "name")
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
    deprecation_message = attr.ib()
    deprecated_since = attr.ib()


settings._define_setting(
    "max_examples",
    default=100,
    description="""
Once this many satisfying examples have been considered without finding any
counter-example, falsification will terminate.
""",
)

settings._define_setting(
    "buffer_size",
    default=8 * 1024,
    description="""
The size of the underlying data used to generate examples. If you need to
generate really large examples you may want to increase this, but it will make
your tests slower.
""",
)


def _validate_timeout(n):
    if n in (not_set, unlimited):
        return n
    raise InvalidArgument("The timeout setting has been removed.")


settings._define_setting(
    "timeout",
    default=not_set,
    description="The timeout setting has been deprecated and no longer does anything.",
    deprecation_message="The timeout setting can safely be removed with no effect.",
    deprecated_since="2017-11-02",
    validator=_validate_timeout,
)

settings._define_setting(
    "derandomize",
    default=False,
    description="""
If this is True then hypothesis will run in deterministic mode
where each falsification uses a random number generator that is seeded
based on the hypothesis to falsify, which will be consistent across
multiple runs. This has the advantage that it will eliminate any
randomness from your tests, which may be preferable for some situations.
It does have the disadvantage of making your tests less likely to
find novel breakages.
""",
)


def _validate_database(db):
    from hypothesis.database import ExampleDatabase

    if db is None or isinstance(db, ExampleDatabase):
        return db
    raise InvalidArgument(
        "Arguments to the database setting must be None or an instance of "
        "ExampleDatabase.  Try passing database=ExampleDatabase(%r), or "
        "construct and use one of the specific subclasses in "
        "hypothesis.database" % (db,)
    )


settings._define_setting(
    "database",
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
        return "%s.%s" % (self.__class__.__name__, self.name)

    @classmethod
    def all(cls):
        # type: () -> List[HealthCheck]
        return list(HealthCheck)

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

    def __repr__(self):
        return "Verbosity.%s" % (self.name,)


settings._define_setting(
    "verbosity",
    options=tuple(Verbosity),
    default=Verbosity.normal,
    description="Control the verbosity level of Hypothesis messages",
)


def _validate_phases(phases):
    if phases is None:
        return tuple(Phase)
    phases = tuple(phases)
    for a in phases:
        if not isinstance(a, Phase):
            raise InvalidArgument("%r is not a valid phase" % (a,))
    return phases


settings._define_setting(
    "phases",
    default=tuple(Phase),
    description=(
        "Control which phases should be run. "
        + "See :ref:`the full documentation for more details <phases>`"
    ),
    validator=_validate_phases,
)

settings._define_setting(
    name="stateful_step_count",
    default=50,
    description="""
Number of steps to run a stateful program for before giving up on it breaking.
""",
)


def validate_health_check_suppressions(suppressions):
    suppressions = try_convert(list, suppressions, "suppress_health_check")
    for s in suppressions:
        if not isinstance(s, HealthCheck):
            raise InvalidArgument(
                "Non-HealthCheck value %r of type %s is invalid in suppress_health_check."
                % (s, type(s).__name__)
            )
    return suppressions


settings._define_setting(
    "suppress_health_check",
    default=(),
    description="""A list of health checks to disable.""",
    validator=validate_health_check_suppressions,
)


def _validate_deadline(x):
    if x is None or isinstance(x, (int, float)):
        return x
    raise InvalidArgument(
        "deadline=%r (type %s) must be an integer or float number of milliseconds, "
        "or None to disable the per-test-case deadline." % (x, type(x).__name__)
    )


settings._define_setting(
    "deadline",
    default=200,
    validator=_validate_deadline,
    description=u"""
If set, a time in milliseconds (which may be a float to express
smaller units of time) that each individual example (i.e. each time your test
function is called, not the whole decorated test) within a test is not
allowed to exceed. Tests which take longer than that may be converted into
errors (but will not necessarily be if close to the deadline, to allow some
variability in test run time).

Set this to None to disable this behaviour entirely.
""",
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

    def __repr__(self):
        return "PrintSettings.%s" % (self.name,)


def _validate_print_blob(value):
    if isinstance(value, bool):
        if value:
            replacement = PrintSettings.ALWAYS
        else:
            replacement = PrintSettings.NEVER

        note_deprecation(
            "Setting print_blob=%r is deprecated and will become an error "
            "in a future version of Hypothesis. Use print_blob=%r instead."
            % (value, replacement),
            since="2018-09-30",
        )
        return replacement

    # Values that aren't bool or PrintSettings will be turned into hard errors
    # by the 'options' check.
    return value


settings._define_setting(
    "print_blob",
    default=PrintSettings.INFER,
    description="""
Determines whether to print blobs after tests that can be used to reproduce
failures.

See :ref:`the documentation on @reproduce_failure <reproduce_failure>` for
more details of this behaviour.
""",
    validator=_validate_print_blob,
    options=tuple(PrintSettings),
)

settings.lock_further_definitions()


def note_deprecation(message, since, verbosity=None):
    # type: (str, str, Verbosity) -> None
    if verbosity is None:
        verbosity = settings.default.verbosity
    assert verbosity is not None
    if since != "RELEASEDAY":
        date = datetime.datetime.strptime(since, "%Y-%m-%d").date()
        assert datetime.date(2016, 1, 1) <= date
    warning = HypothesisDeprecationWarning(message)
    if verbosity > Verbosity.quiet:
        warnings.warn(warning, stacklevel=2)


settings.register_profile("default", settings())
settings.load_profile("default")
assert settings.default is not None
