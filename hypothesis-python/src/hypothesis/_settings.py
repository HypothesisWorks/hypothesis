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

"""A module controlling settings for Hypothesis to use in falsification.

Either an explicit settings object can be used or the default object on
this module can be modified.
"""

import contextlib
import datetime
import inspect
import threading
import warnings
from enum import Enum, IntEnum, unique
from typing import Any, Dict, List

import attr

from hypothesis.errors import (
    HypothesisDeprecationWarning,
    InvalidArgument,
    InvalidState,
)
from hypothesis.internal.reflection import get_pretty_function_description
from hypothesis.internal.validation import check_type, try_convert
from hypothesis.utils.conventions import not_set
from hypothesis.utils.dynamicvariables import DynamicVariable

__all__ = ["settings"]

all_settings = {}  # type: Dict[str, Setting]


class settingsProperty:
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
        default = (
            repr(getattr(settings.default, self.name))
            if self.show_default
            else "(dynamically calculated)"
        )
        return "%s\n\ndefault value: ``%s``" % (description, default)


default_variable = DynamicVariable(None)


class settingsMeta(type):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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


class settings(metaclass=settingsMeta):
    """A settings object controls a variety of parameters that are used in
    falsification. These may control both the falsification strategy and the
    details of the data that is generated.

    Default values are picked up from the settings.default object and
    changes made there will be picked up in newly created settings.
    """

    _WHITELISTED_REAL_PROPERTIES = ["_construction_complete", "storage"]
    __definitions_are_locked = False
    _profiles = {}  # type: dict
    __module__ = "hypothesis"

    def __getattr__(self, name):
        if name in all_settings:
            return all_settings[name].default
        else:
            raise AttributeError("settings has no attribute %s" % (name,))

    def __init__(self, parent: "settings" = None, **kwargs: Any) -> None:
        if parent is not None and not isinstance(parent, settings):
            raise InvalidArgument(
                "Invalid argument: parent=%r is not a settings instance" % (parent,)
            )
        if kwargs.get("derandomize"):
            if kwargs.get("database") is not None:
                raise InvalidArgument(
                    "derandomize=True implies database=None, so passing "
                    "database=%r too is invalid." % (kwargs["database"],)
                )
            kwargs["database"] = None
        self._construction_complete = False
        defaults = parent or settings.default
        if defaults is not None:
            for setting in all_settings.values():
                if kwargs.get(setting.name, not_set) is not_set:
                    kwargs[setting.name] = getattr(defaults, setting.name)
                else:
                    if setting.validator:
                        kwargs[setting.name] = setting.validator(kwargs[setting.name])
        for name, value in kwargs.items():
            if name not in all_settings:
                raise InvalidArgument(
                    "Invalid argument: %r is not a valid setting" % (name,)
                )
            setattr(self, name, value)
        self.storage = threading.local()
        self._construction_complete = True

    def __call__(self, test):
        """Make the settings object (self) an attribute of the test.

        The settings are later discovered by looking them up on the test itself.
        """
        if not callable(test):
            raise InvalidArgument(
                "settings objects can be called as a decorator with @given, "
                "but decorated test=%r is not callable." % (test,)
            )
        if inspect.isclass(test):
            from hypothesis.stateful import RuleBasedStateMachine

            if issubclass(test, RuleBasedStateMachine):
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
                    "functions, or on subclasses of RuleBasedStateMachine."
                )
        if hasattr(test, "_hypothesis_internal_settings_applied"):
            # Can't use _hypothesis_internal_use_settings as an indicator that
            # @settings was applied, because @given also assigns that attribute.
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
        test._hypothesis_internal_settings_applied = True
        return test

    @classmethod
    def _define_setting(
        cls,
        name,
        description,
        default,
        options=None,
        validator=None,
        show_default=True,
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
        else:
            assert validator is not None

        all_settings[name] = Setting(
            name=name,
            description=description.strip(),
            default=default,
            options=options,
            validator=validator,
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
        bits = ("%s=%r" % (name, getattr(self, name)) for name in all_settings)
        return "settings(%s)" % ", ".join(sorted(bits))

    def show_changed(self):
        bits = []
        for name, setting in all_settings.items():
            value = getattr(self, name)
            if value != setting.default:
                bits.append("%s=%r" % (name, value))
        return ", ".join(sorted(bits, key=len))

    @staticmethod
    def register_profile(name: str, parent: "settings" = None, **kwargs: Any) -> None:
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
        check_type(str, name, "name")
        settings._profiles[name] = settings(parent=parent, **kwargs)

    @staticmethod
    def get_profile(name: str) -> "settings":
        """Return the profile with the given name."""
        check_type(str, name, "name")
        try:
            return settings._profiles[name]
        except KeyError:
            raise InvalidArgument("Profile %r is not registered" % (name,))

    @staticmethod
    def load_profile(name: str) -> None:
        """Loads in the settings defined in the profile provided.

        If the profile does not exist, InvalidArgument will be raised.
        Any setting not defined in the profile will be the library
        defined default for that setting.
        """
        check_type(str, name, "name")
        settings._current_profile = name
        settings._assign_default_internal(settings.get_profile(name))


@contextlib.contextmanager
def local_settings(s):
    default_context_manager = default_variable.with_value(s)
    with default_context_manager:
        yield s


@attr.s()
class Setting:
    name = attr.ib()
    description = attr.ib()
    default = attr.ib()
    options = attr.ib()
    validator = attr.ib()


def _max_examples_validator(x):
    check_type(int, x, name="max_examples")
    if x < 1:
        raise InvalidArgument(
            "max_examples=%r should be at least one. You can disable example "
            "generation with the `phases` setting instead." % (x,)
        )
    return x


settings._define_setting(
    "max_examples",
    default=100,
    validator=_max_examples_validator,
    description="""
Once this many satisfying examples have been considered without finding any
counter-example, falsification will terminate.

The default value is chosen to suit a workflow where the test will be part of
a suite that is regularly executed locally or on a CI server, balancing total
running time against the chance of missing a bug.

If you are writing one-off tests, running tens of thousands of examples is
quite reasonable as Hypothesis may miss uncommon bugs with default settings.
For very complex code, we have observed Hypothesis finding novel bugs after
*several million* examples while testing :pypi:`SymPy`.
""",
)


settings._define_setting(
    "derandomize",
    default=False,
    options=(True, False),
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
used to save examples to and load previous examples from. May be ``None``
in which case no storage will be used, ``":memory:"`` for an in-memory
database, or any path for a directory-based example database.
""",
    validator=_validate_database,
)


@unique
class Phase(IntEnum):
    explicit = 0
    reuse = 1
    generate = 2
    target = 3
    shrink = 4

    def __repr__(self):
        return "Phase.%s" % (self.name,)


@unique
class HealthCheck(Enum):
    """Arguments for :attr:`~hypothesis.settings.suppress_health_check`.

    Each member of this enum is a type of health check to suppress.
    """

    def __repr__(self):
        return "%s.%s" % (self.__class__.__name__, self.name)

    @classmethod
    def all(cls) -> List["HealthCheck"]:
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

    large_base_example = 7
    """Checks if the natural example to shrink towards is very large."""

    not_a_test_method = 8
    """Checks if :func:`@given <hypothesis.given>` has been applied to a
    method defined by :class:`python:unittest.TestCase` (i.e. not a test)."""


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
    phases = tuple(phases)
    for a in phases:
        if not isinstance(a, Phase):
            raise InvalidArgument("%r is not a valid phase" % (a,))
    return tuple(p for p in list(Phase) if p in phases)


settings._define_setting(
    "phases",
    default=tuple(Phase),
    description=(
        "Control which phases should be run. "
        "See :ref:`the full documentation for more details <phases>`"
    ),
    validator=_validate_phases,
)


def _validate_stateful_step_count(x):
    check_type(int, x, name="stateful_step_count")
    if x < 1:
        raise InvalidArgument("stateful_step_count=%r must be at least one." % (x,))
    return x


settings._define_setting(
    name="stateful_step_count",
    default=50,
    validator=_validate_stateful_step_count,
    description="""
Number of steps to run a stateful program for before giving up on it breaking.
""",
)

settings._define_setting(
    name="report_multiple_bugs",
    default=True,
    options=(True, False),
    description="""
Because Hypothesis runs the test many times, it can sometimes find multiple
bugs in a single run.  Reporting all of them at once is usually very useful,
but replacing the exceptions can occasionally clash with debuggers.
If disabled, only the exception with the smallest minimal example is raised.
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
    description="""A list of :class:`~hypothesis.HealthCheck` items to disable.""",
    validator=validate_health_check_suppressions,
)


class duration(datetime.timedelta):
    """A timedelta specifically measured in milliseconds."""

    def __repr__(self):
        ms = self.total_seconds() * 1000
        return "timedelta(milliseconds=%r)" % (int(ms) if ms == int(ms) else ms,)


def _validate_deadline(x):
    if x is None:
        return x
    invalid_deadline_error = InvalidArgument(
        "deadline=%r (type %s) must be a timedelta object, an integer or float "
        "number of milliseconds, or None to disable the per-test-case deadline."
        % (x, type(x).__name__)
    )
    if isinstance(x, (int, float)):
        if isinstance(x, bool):
            raise invalid_deadline_error
        try:
            x = duration(milliseconds=x)
        except OverflowError:
            raise InvalidArgument(
                "deadline=%r is invalid, because it is too large to represent "
                "as a timedelta. Use deadline=None to disable deadlines." % (x,)
            ) from None
    if isinstance(x, datetime.timedelta):
        if x <= datetime.timedelta(0):
            raise InvalidArgument(
                "deadline=%r is invalid, because it is impossible to meet a "
                "deadline <= 0. Use deadline=None to disable deadlines." % (x,)
            )
        return duration(seconds=x.total_seconds())
    raise invalid_deadline_error


settings._define_setting(
    "deadline",
    default=duration(milliseconds=200),
    validator=_validate_deadline,
    description="""
If set, a duration (as timedelta, or integer or float number of milliseconds)
that each individual example (i.e. each time your test
function is called, not the whole decorated test) within a test is not
allowed to exceed. Tests which take longer than that may be converted into
errors (but will not necessarily be if close to the deadline, to allow some
variability in test run time).

Set this to None to disable this behaviour entirely.
""",
)


settings._define_setting(
    "print_blob",
    default=False,
    options=(True, False),
    description="""
If set to ``True``, Hypothesis will print code for failing examples that can be used with
:func:`@reproduce_failure <hypothesis.reproduce_failure>` to reproduce the failing example.
""",
)

settings.lock_further_definitions()


def note_deprecation(message: str, *, since: str) -> None:
    if since != "RELEASEDAY":
        date = datetime.datetime.strptime(since, "%Y-%m-%d").date()
        assert datetime.date(2016, 1, 1) <= date
    warnings.warn(HypothesisDeprecationWarning(message), stacklevel=2)


settings.register_profile("default", settings())
settings.load_profile("default")
assert settings.default is not None
