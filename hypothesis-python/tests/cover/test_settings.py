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

from __future__ import absolute_import, division, print_function

import datetime
import subprocess
import sys
from unittest import TestCase

import pytest

import hypothesis.strategies as st
from hypothesis import example, given, unlimited
from hypothesis._settings import (
    Phase,
    Verbosity,
    default_variable,
    local_settings,
    note_deprecation,
    settings,
)
from hypothesis.database import ExampleDatabase
from hypothesis.errors import InvalidArgument, InvalidState
from hypothesis.stateful import GenericStateMachine, RuleBasedStateMachine, rule
from hypothesis.utils.conventions import not_set
from tests.common.utils import checks_deprecated_behaviour, counts_calls, fails_with


def test_has_docstrings():
    assert settings.verbosity.__doc__


original_default = settings.get_profile("default").max_examples


def setup_function(fn):
    settings.load_profile("default")
    settings.register_profile("test_settings", settings())
    settings.load_profile("test_settings")


def test_cannot_set_non_settings():
    s = settings()
    with pytest.raises(AttributeError):
        s.databas_file = u"some_file"


def test_settings_uses_defaults():
    s = settings()
    assert s.max_examples == settings.default.max_examples


def test_raises_attribute_error():
    with pytest.raises(AttributeError):
        settings().kittens


def test_respects_none_database():
    assert settings(database=None).database is None


def test_can_repeatedly_push_the_same_thing():
    s = settings(max_examples=12)
    t = settings(max_examples=17)
    assert settings().max_examples == original_default
    with local_settings(s):
        assert settings().max_examples == 12
        with local_settings(t):
            assert settings().max_examples == 17
            with local_settings(s):
                assert settings().max_examples == 12
                with local_settings(t):
                    assert settings().max_examples == 17
                assert settings().max_examples == 12
            assert settings().max_examples == 17
        assert settings().max_examples == 12
    assert settings().max_examples == original_default


def test_cannot_create_settings_with_invalid_options():
    with pytest.raises(InvalidArgument):
        settings(a_setting_with_limited_options=u"spoon")


def test_cannot_register_with_parent_and_settings_args():
    with pytest.raises(InvalidArgument):
        settings.register_profile(
            "conflicted", settings.default, settings=settings.default
        )
    assert "conflicted" not in settings._profiles


def test_can_set_verbosity():
    settings(verbosity=Verbosity.quiet)
    settings(verbosity=Verbosity.normal)
    settings(verbosity=Verbosity.verbose)
    settings(verbosity=Verbosity.debug)


def test_can_not_set_verbosity_to_non_verbosity():
    with pytest.raises(InvalidArgument):
        settings(verbosity="kittens")


@pytest.mark.parametrize("db", [None, ExampleDatabase()])
def test_inherits_an_empty_database(db):
    assert settings.default.database is not None
    s = settings(database=db)
    assert s.database is db
    with local_settings(s):
        t = settings()
    assert t.database is db


@pytest.mark.parametrize("db", [None, ExampleDatabase()])
def test_can_assign_database(db):
    x = settings(database=db)
    assert x.database is db


def test_will_reload_profile_when_default_is_absent():
    original = settings.default
    default_variable.value = None
    assert settings.default is original


def test_load_profile():
    settings.load_profile("default")
    assert settings.default.max_examples == original_default
    assert settings.default.stateful_step_count == 50

    settings.register_profile("test", settings(max_examples=10), stateful_step_count=5)
    settings.load_profile("test")

    assert settings.default.max_examples == 10
    assert settings.default.stateful_step_count == 5

    settings.load_profile("default")

    assert settings.default.max_examples == original_default
    assert settings.default.stateful_step_count == 50


def test_profile_names_must_be_strings():
    with pytest.raises(InvalidArgument):
        settings.register_profile(5)
    with pytest.raises(InvalidArgument):
        settings.get_profile(5)
    with pytest.raises(InvalidArgument):
        settings.load_profile(5)


def test_loading_profile_keeps_expected_behaviour():
    settings.register_profile("ci", settings(max_examples=10000))
    settings.load_profile("ci")
    assert settings().max_examples == 10000
    with local_settings(settings(max_examples=5)):
        assert settings().max_examples == 5
    assert settings().max_examples == 10000


def test_load_non_existent_profile():
    with pytest.raises(InvalidArgument):
        settings.get_profile("nonsense")


def test_cannot_delete_a_setting():
    x = settings()
    with pytest.raises(AttributeError):
        del x.max_examples
    x.max_examples

    x = settings()
    with pytest.raises(AttributeError):
        del x.foo


@checks_deprecated_behaviour
def test_setting_to_unlimited_is_not_error_yet():
    settings(timeout=unlimited)


def test_cannot_set_settings():
    x = settings()
    with pytest.raises(AttributeError):
        x.max_examples = "foo"
    with pytest.raises(AttributeError):
        x.database = "foo"
    assert x.max_examples != "foo"
    assert x.database != "foo"


def test_can_have_none_database():
    assert settings(database=None).database is None


@pytest.mark.parametrize("db", [None, ExampleDatabase(":memory:")])
def test_database_type_must_be_ExampleDatabase(db):
    with local_settings(settings(database=db)):
        settings_property_db = settings.database
        with pytest.raises(InvalidArgument):
            settings(database=".hypothesis/examples")
        assert settings.database is settings_property_db


def test_cannot_define_settings_once_locked():
    with pytest.raises(InvalidState):
        settings._define_setting("hi", "there", 4)


def test_cannot_assign_default():
    with pytest.raises(AttributeError):
        settings.default = settings(max_examples=3)
    assert settings().max_examples != 3


def test_does_not_warn_if_quiet():
    with pytest.warns(None) as rec:
        note_deprecation("This is bad", since="RELEASEDAY", verbosity=Verbosity.quiet)
    assert len(rec) == 0


@settings(max_examples=7)
@given(st.builds(lambda: settings.default))
def test_settings_in_strategies_are_from_test_scope(s):
    assert s.max_examples == 7


TEST_SETTINGS_ALONE = """
from hypothesis import settings
from hypothesis.strategies import integers

@settings()
def test_settings_alone():
    pass
"""


def test_settings_alone(testdir):
    script = testdir.makepyfile(TEST_SETTINGS_ALONE)
    result = testdir.runpytest(script)
    out = "\n".join(result.stdout.lines)
    assert (
        "Using `@settings` on a test without `@given` is completely pointless." in out
    )
    assert "InvalidArgument" in out
    assert result.ret == 1


@fails_with(InvalidArgument)
def test_settings_applied_twice_is_error():
    @given(st.integers())
    @settings()
    @settings()
    def test_nothing(x):
        pass


@settings()
@given(st.integers())
def test_outer_ok(x):
    pass


@given(st.integers())
@settings()
def test_inner_ok(x):
    pass


def test_settings_as_decorator_must_be_on_callable():
    with pytest.raises(InvalidArgument):
        settings()(1)


ASSERT_DATABASE_PATH = """
import tempfile
from hypothesis import settings
from hypothesis.configuration import set_hypothesis_home_dir
from hypothesis.database import DirectoryBasedExampleDatabase

settings.default.database

if __name__ == '__main__':
    new_home = tempfile.mkdtemp()
    set_hypothesis_home_dir(new_home)
    db = settings.default.database
    assert isinstance(db, DirectoryBasedExampleDatabase), db
    assert db.path.startswith(new_home), (db.path, new_home)
"""


def test_puts_the_database_in_the_home_dir_by_default(tmpdir):
    script = tmpdir.join("assertlocation.py")
    script.write(ASSERT_DATABASE_PATH)

    subprocess.check_call([sys.executable, str(script)])


def test_database_is_reference_preserved():
    s = settings(database=not_set)

    assert s.database is s.database


@settings(verbosity=Verbosity.verbose)
@example(x=99)
@given(st.integers())
def test_settings_apply_for_explicit_examples(x):
    # Regression test for #1521
    assert settings.default.verbosity == Verbosity.verbose


class TestGivenExampleSettingsExplicitCalled(TestCase):
    """Real nasty edge case here.

    in #2160, if ``example`` is after ``given`` but before ``settings``,
    it will be completely ignored.

    If we set phases to only ``explicit``, the test case will never be called!

    We have to run an assertion outside of the test case itself.
    """

    @counts_calls
    def call_target(self):
        pass

    @given(st.booleans())
    @example(True)
    @settings(phases=[Phase.explicit])
    def test_example_explicit(self, x):
        self.call_target()

    def tearDown(self):
        # In #2160, this is 0.
        assert self.call_target.calls == 1


def test_setattr_on_settings_singleton_is_error():
    # https://github.com/pandas-dev/pandas/pull/22679#issuecomment-420750921
    # Should be setting attributes on settings.default, not settings!
    with pytest.raises(AttributeError):
        settings.max_examples = 10


def test_deadline_given_none():
    x = settings(deadline=None).deadline
    assert x is None


def test_deadline_given_valid_int():
    x = settings(deadline=1000).deadline
    assert isinstance(x, datetime.timedelta)
    assert x.days == 0 and x.seconds == 1 and x.microseconds == 0


def test_deadline_given_valid_float():
    x = settings(deadline=2050.25).deadline
    assert isinstance(x, datetime.timedelta)
    assert x.days == 0 and x.seconds == 2 and x.microseconds == 50250


def test_deadline_given_valid_timedelta():
    x = settings(deadline=datetime.timedelta(days=1, microseconds=15030000)).deadline
    assert isinstance(x, datetime.timedelta)
    assert x.days == 1 and x.seconds == 15 and x.microseconds == 30000


@pytest.mark.parametrize(
    "x",
    [
        0,
        -0.7,
        -1,
        86400000000000000.2,
        datetime.timedelta(microseconds=-1),
        datetime.timedelta(0),
    ],
)
def test_invalid_deadline(x):
    with pytest.raises(InvalidArgument):
        settings(deadline=x)


@pytest.mark.parametrize("value", ["always"])
def test_can_not_set_print_blob_to_non_print_settings(value):
    with pytest.raises(InvalidArgument):
        settings(print_blob=value)


settings_step_count = 1


@settings(stateful_step_count=settings_step_count)
class StepCounter(RuleBasedStateMachine):
    def __init__(self):
        super(StepCounter, self).__init__()
        self.step_count = 0

    @rule()
    def count_step(self):
        self.step_count += 1

    def teardown(self):
        assert self.step_count <= settings_step_count


test_settings_decorator_applies_to_rule_based_state_machine_class = StepCounter.TestCase


def test_two_settings_decorators_applied_to_state_machine_class_raises_error():
    with pytest.raises(InvalidArgument):

        @settings()
        @settings()
        class StatefulTest(RuleBasedStateMachine):
            pass


def test_settings_decorator_applied_to_non_state_machine_class_raises_error():
    with pytest.raises(InvalidArgument):

        @settings()
        class NonStateMachine:
            pass


def test_assigning_to_settings_attribute_on_state_machine_raises_error():
    with pytest.raises(AttributeError):

        class StateMachine(GenericStateMachine):
            pass

        StateMachine.settings = settings()

    state_machine_instance = StateMachine()
    state_machine_instance.settings = "any value"


def test_can_not_set_timeout_to_time():
    with pytest.raises(InvalidArgument):
        settings(timeout=60)


def test_derandomise_with_explicit_database_is_invalid():
    with pytest.raises(InvalidArgument):
        settings(derandomize=True, database=ExampleDatabase(":memory:"))


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(max_examples=-1),
        dict(buffer_size=-1),
        dict(stateful_step_count=-1),
        dict(deadline=-1),
        dict(deadline=0),
    ],
)
def test_invalid_settings_are_errors(kwargs):
    with pytest.raises(InvalidArgument):
        settings(**kwargs)


@checks_deprecated_behaviour
def test_boolean_deadlines():
    settings(deadline=True)
    with pytest.raises(InvalidArgument):
        settings(deadline=False)


@checks_deprecated_behaviour
def test_non_boolean_derandomize():
    assert settings(derandomize=1).derandomize is True
    assert settings(derandomize=0).derandomize is False


@pytest.mark.parametrize("name", ["max_examples", "buffer_size", "stateful_step_count"])
@checks_deprecated_behaviour
def test_dubious_settings_deprecations(name):
    settings(**{name: 2.5})
    with pytest.raises(InvalidArgument):
        settings(**{name: "2.5"})  # deprecation warning, then type cast error.


@checks_deprecated_behaviour
def test_buffer_size_deprecated():
    assert settings(buffer_size=100).buffer_size == 100


@checks_deprecated_behaviour
def test_max_example_eq_0_warns_and_disables_generation():
    # Terrible way to disable generation, but did predate the phases setting
    # and existed in our test suite so it's not an error *just* yet.
    @example(None)
    @given(st.integers())
    @settings(max_examples=0)
    def inner(x):
        calls[0] += 1
        assert x is None

    calls = [0]
    inner()
    assert calls[0] == 1
