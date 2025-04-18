# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import datetime
import os
import subprocess
import sys
from contextlib import contextmanager
from unittest import TestCase

import pytest

from hypothesis import example, given, strategies as st
from hypothesis._settings import (
    HealthCheck,
    Phase,
    Verbosity,
    default_variable,
    local_settings,
    note_deprecation,
    settings,
)
from hypothesis.database import InMemoryExampleDatabase
from hypothesis.errors import (
    HypothesisDeprecationWarning,
    InvalidArgument,
)
from hypothesis.stateful import RuleBasedStateMachine, rule
from hypothesis.utils.conventions import not_set

from tests.common.utils import (
    checks_deprecated_behaviour,
    counts_calls,
    fails_with,
    skipif_emscripten,
    validate_deprecation,
)

original_default = settings.get_profile("default").max_examples


@contextmanager
def temp_register_profile(name, parent, **kwargs):
    try:
        settings.register_profile(name, parent, **kwargs)
        yield
    finally:
        settings._profiles.pop(name)


def setup_function(fn):
    settings.load_profile("default")
    settings.register_profile("test_settings", settings())
    settings.load_profile("test_settings")


def test_cannot_set_non_settings():
    s = settings()
    with pytest.raises(AttributeError):
        s.databas_file = "some_file"


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


def test_can_set_verbosity():
    settings(verbosity=Verbosity.quiet)
    settings(verbosity=Verbosity.normal)
    settings(verbosity=Verbosity.verbose)
    settings(verbosity=Verbosity.debug)


def test_can_not_set_verbosity_to_non_verbosity():
    with pytest.raises(InvalidArgument):
        settings(verbosity="kittens")


@pytest.mark.parametrize("db", [None, InMemoryExampleDatabase()])
def test_inherits_an_empty_database(db):
    with local_settings(settings(database=InMemoryExampleDatabase())):
        assert settings.default.database is not None
        s = settings(database=db)
        assert s.database is db
        with local_settings(s):
            t = settings()
        assert t.database is db


@pytest.mark.parametrize("db", [None, InMemoryExampleDatabase()])
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


@pytest.mark.parametrize("db", [None, InMemoryExampleDatabase()])
@pytest.mark.parametrize("bad_db", [":memory:", ".hypothesis/examples"])
def test_database_type_must_be_ExampleDatabase(db, bad_db):
    with local_settings(settings(database=db)):
        settings_property_db = settings.database
        with pytest.raises(InvalidArgument):
            settings(database=bad_db)
        assert settings.database is settings_property_db


def test_cannot_assign_default():
    with pytest.raises(AttributeError):
        settings.default = settings(max_examples=3)
    assert settings().max_examples != 3


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


def test_settings_alone(pytester):
    # Disable cacheprovider, since we don't need it and it's flaky on pyodide
    script = pytester.makepyfile(TEST_SETTINGS_ALONE)
    result = pytester.runpytest_inprocess(script, "-p", "no:cacheprovider")
    out = "\n".join(result.stdout.lines)
    msg = "Using `@settings` on a test without `@given` is completely pointless."
    assert msg in out
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

settings.load_profile("default")
settings.default.database

if __name__ == '__main__':
    new_home = tempfile.mkdtemp()
    set_hypothesis_home_dir(new_home)
    db = settings.default.database
    assert isinstance(db, DirectoryBasedExampleDatabase), db
    assert db.path.is_relative_to(new_home), (db.path, new_home)
"""


@skipif_emscripten
def test_puts_the_database_in_the_home_dir_by_default(tmp_path):
    script = tmp_path / "assertlocation.py"
    script.write_text(ASSERT_DATABASE_PATH, encoding="utf-8")
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
    assert x.days == 0
    assert x.seconds == 1
    assert x.microseconds == 0


def test_deadline_given_valid_float():
    x = settings(deadline=2050.25).deadline
    assert isinstance(x, datetime.timedelta)
    assert x.days == 0
    assert x.seconds == 2
    assert x.microseconds == 50250


def test_deadline_given_valid_timedelta():
    x = settings(deadline=datetime.timedelta(days=1, microseconds=15030000)).deadline
    assert isinstance(x, datetime.timedelta)
    assert x.days == 1
    assert x.seconds == 15
    assert x.microseconds == 30000


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
        super().__init__()
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
    class StateMachine(RuleBasedStateMachine):
        @rule(x=st.none())
        def a_rule(self, x):
            assert x is None

    with pytest.raises(AttributeError):
        StateMachine.settings = settings()

    state_machine_instance = StateMachine()
    state_machine_instance.settings = "any value"


def test_derandomise_with_explicit_database_is_invalid():
    with pytest.raises(InvalidArgument):
        settings(derandomize=True, database=InMemoryExampleDatabase())


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_examples": -1},
        {"max_examples": 2.5},
        {"stateful_step_count": -1},
        {"stateful_step_count": 2.5},
        {"deadline": -1},
        {"deadline": 0},
        {"deadline": True},
        {"deadline": False},
        {"backend": "this_backend_does_not_exist"},
    ],
)
def test_invalid_settings_are_errors(kwargs):
    with pytest.raises(InvalidArgument):
        settings(**kwargs)


def test_invalid_parent():
    class NotSettings:
        def __repr__(self):
            return "(not settings repr)"

    not_settings = NotSettings()

    with pytest.raises(InvalidArgument) as excinfo:
        settings(not_settings)

    assert "parent=(not settings repr)" in str(excinfo.value)


def test_default_settings_do_not_use_ci():
    assert settings.get_profile("default").suppress_health_check == ()


def test_show_changed():
    s = settings(settings.get_profile("default"), max_examples=999, database=None)
    assert s.show_changed() == "database=None, max_examples=999"


def test_note_deprecation_checks_date():
    with pytest.warns(HypothesisDeprecationWarning) as rec:
        note_deprecation("This is bad", since="RELEASEDAY", has_codemod=False)
    assert len(rec) == 1
    with pytest.raises(AssertionError):
        note_deprecation("This is way too old", since="1999-12-31", has_codemod=False)


def test_note_deprecation_checks_has_codemod():
    with pytest.warns(
        HypothesisDeprecationWarning,
        match="The `hypothesis codemod` command-line tool",
    ):
        note_deprecation("This is bad", since="2021-01-01", has_codemod=True)


def test_deprecated_settings_warn_on_set_settings():
    with validate_deprecation():
        settings(suppress_health_check=[HealthCheck.return_value])
    with validate_deprecation():
        settings(suppress_health_check=[HealthCheck.not_a_test_method])


@checks_deprecated_behaviour
def test_deprecated_settings_not_in_settings_all_list():
    al = HealthCheck.all()
    ls = list(HealthCheck)
    assert al == ls
    assert HealthCheck.return_value not in ls
    assert HealthCheck.not_a_test_method not in ls


@skipif_emscripten
def test_check_defaults_to_derandomize_when_running_on_ci():
    env = dict(os.environ)
    env["CI"] = "true"

    assert (
        subprocess.check_output(
            [
                sys.executable,
                "-c",
                "from hypothesis import settings\nprint(settings().derandomize)",
            ],
            env=env,
            text=True,
            encoding="utf-8",
        ).strip()
        == "True"
    )


@skipif_emscripten
def test_check_defaults_to_randomize_when_not_running_on_ci():
    env = dict(os.environ)
    env.pop("CI", None)
    env.pop("TF_BUILD", None)
    assert (
        subprocess.check_output(
            [
                sys.executable,
                "-c",
                "from hypothesis import settings\nprint(settings().derandomize)",
            ],
            env=env,
            text=True,
            encoding="utf-8",
        ).strip()
        == "False"
    )


def test_reloads_the_loaded_profile_if_registered_again():
    prev_profile = settings._current_profile
    try:
        test_profile = "some nonsense profile purely for this test"
        test_value = 123456
        settings.register_profile(test_profile, settings(max_examples=test_value))
        settings.load_profile(test_profile)
        assert settings.default.max_examples == test_value
        test_value_2 = 42
        settings.register_profile(test_profile, settings(max_examples=test_value_2))
        assert settings.default.max_examples == test_value_2
    finally:
        if prev_profile is not None:
            settings.load_profile(prev_profile)


CI_TESTING_SCRIPT = """
from hypothesis import settings

if __name__ == '__main__':
    settings.register_profile("ci", settings(max_examples=42))
    assert settings.default.max_examples == 42
"""


@skipif_emscripten
def test_will_automatically_pick_up_changes_to_ci_profile_in_ci():
    env = dict(os.environ)
    env["CI"] = "true"
    subprocess.check_call(
        [sys.executable, "-c", CI_TESTING_SCRIPT],
        env=env,
        text=True,
        encoding="utf-8",
    )


def test_register_profile_avoids_intermediate_profiles():
    parent = settings()
    s = settings(parent, max_examples=10)
    with temp_register_profile("for_intermediate_test", s):
        assert settings.get_profile("for_intermediate_test")._fallback is parent
