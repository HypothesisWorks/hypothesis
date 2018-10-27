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
import re
import sys
import subprocess
from tempfile import mkdtemp

import pytest

import hypothesis.strategies as st
from hypothesis import given, example, unlimited
from hypothesis.errors import InvalidState, InvalidArgument, \
    HypothesisDeprecationWarning
from tests.common.utils import validate_deprecation, \
    checks_deprecated_behaviour
from hypothesis.database import ExampleDatabase, \
    DirectoryBasedExampleDatabase
from hypothesis.stateful import GenericStateMachine, \
    RuleBasedStateMachine, rule
from hypothesis._settings import Verbosity, PrintSettings, settings, \
    default_variable, note_deprecation
from hypothesis.utils.conventions import not_set


def test_has_docstrings():
    assert settings.verbosity.__doc__


original_default = settings.get_profile('default').max_examples


def setup_function(fn):
    settings.load_profile('default')
    settings.register_profile('test_settings', settings())
    settings.load_profile('test_settings')


def test_cannot_set_non_settings():
    s = settings()
    with pytest.raises(AttributeError):
        s.databas_file = u'some_file'


def test_settings_uses_defaults():
    s = settings()
    assert s.max_examples == settings.default.max_examples


def test_raises_attribute_error():
    with pytest.raises(AttributeError):
        settings().kittens


def test_respects_none_database():
    assert settings(database=None).database is None


@checks_deprecated_behaviour
def test_settings_can_be_used_as_context_manager_to_change_defaults():
    with settings(max_examples=12):
        assert settings.default.max_examples == 12
    assert settings.default.max_examples == original_default


@checks_deprecated_behaviour
def test_can_repeatedly_push_the_same_thing():
    s = settings(max_examples=12)
    t = settings(max_examples=17)
    assert settings().max_examples == original_default
    with s:
        assert settings().max_examples == 12
        with t:
            assert settings().max_examples == 17
            with s:
                assert settings().max_examples == 12
                with t:
                    assert settings().max_examples == 17
                assert settings().max_examples == 12
            assert settings().max_examples == 17
        assert settings().max_examples == 12
    assert settings().max_examples == original_default


def test_cannot_create_settings_with_invalid_options():
    with pytest.raises(InvalidArgument):
        settings(a_setting_with_limited_options=u'spoon')


def test_cannot_register_with_parent_and_settings_args():
    with pytest.raises(InvalidArgument):
        settings.register_profile(
            'conflicted', settings.default, settings=settings.default)
    assert 'conflicted' not in settings._profiles


@checks_deprecated_behaviour
def test_register_profile_kwarg_settings_is_deprecated():
    settings.register_profile('test', settings=settings(max_examples=10))
    settings.load_profile('test')
    assert settings.default.max_examples == 10


@checks_deprecated_behaviour
def test_perform_health_check_setting_is_deprecated():
    s = settings(suppress_health_check=(), perform_health_check=False)
    assert s.suppress_health_check


@checks_deprecated_behaviour
@given(st.integers(0, 10000))
def test_max_shrinks_setting_is_deprecated(n):
    s = settings(max_shrinks=n)
    assert s.max_shrinks == n


def test_can_set_verbosity():
    settings(verbosity=Verbosity.quiet)
    settings(verbosity=Verbosity.normal)
    settings(verbosity=Verbosity.verbose)


def test_can_not_set_verbosity_to_non_verbosity():
    with pytest.raises(InvalidArgument):
        settings(verbosity='kittens')


@checks_deprecated_behaviour
@pytest.mark.parametrize('db', [None, ExampleDatabase()])
def test_inherits_an_empty_database(db):
    assert settings.default.database is not None
    s = settings(database=db)
    assert s.database is db
    with s:
        t = settings()
    assert t.database is db


@pytest.mark.parametrize('db', [None, ExampleDatabase()])
def test_can_assign_database(db):
    x = settings(database=db)
    assert x.database is db


def test_will_reload_profile_when_default_is_absent():
    original = settings.default
    default_variable.value = None
    assert settings.default is original


def test_load_profile():
    settings.load_profile('default')
    assert settings.default.max_examples == original_default
    assert settings.default.stateful_step_count == 50

    settings.register_profile(
        'test', settings(max_examples=10), stateful_step_count=5
    )
    settings.load_profile('test')

    assert settings.default.max_examples == 10
    assert settings.default.stateful_step_count == 5

    settings.load_profile('default')

    assert settings.default.max_examples == original_default
    assert settings.default.stateful_step_count == 50


@checks_deprecated_behaviour
def test_nonstring_profile_names_deprecated():
    settings.register_profile(5, stateful_step_count=5)
    settings.load_profile(5)
    assert settings.default.stateful_step_count == 5


@checks_deprecated_behaviour
def test_loading_profile_keeps_expected_behaviour():
    settings.register_profile('ci', settings(max_examples=10000))
    settings.load_profile('ci')
    assert settings().max_examples == 10000
    with settings(max_examples=5):
        assert settings().max_examples == 5
    assert settings().max_examples == 10000


def test_load_non_existent_profile():
    with pytest.raises(InvalidArgument):
        settings.get_profile('nonsense')


@pytest.mark.skipif(
    os.getenv('HYPOTHESIS_PROFILE') not in (None, 'default'),
    reason='Defaults have been overridden')
def test_runs_tests_with_defaults_from_conftest():
    assert settings.default.timeout == -1


def test_cannot_delete_a_setting():
    x = settings()
    with pytest.raises(AttributeError):
        del x.max_examples
    x.max_examples

    x = settings()
    with pytest.raises(AttributeError):
        del x.foo


def test_cannot_set_strict():
    with pytest.raises(HypothesisDeprecationWarning):
        settings(strict=True)


@checks_deprecated_behaviour
def test_set_deprecated_settings():
    assert settings(timeout=3).timeout == 3


def test_setting_to_future_value_gives_future_value_and_no_error():
    assert settings(timeout=unlimited).timeout == -1


def test_cannot_set_settings():
    x = settings()
    with pytest.raises(AttributeError):
        x.max_examples = 'foo'
    with pytest.raises(AttributeError):
        x.database = 'foo'
    assert x.max_examples != 'foo'
    assert x.database != 'foo'


def test_can_have_none_database():
    assert settings(database=None).database is None


@checks_deprecated_behaviour
@pytest.mark.parametrize('db', [None, ExampleDatabase(':memory:')])
def test_database_type_must_be_ExampleDatabase(db):
    with settings(database=db):
        settings_property_db = settings.database
        with pytest.raises(InvalidArgument):
            settings(database='.hypothesis/examples')
        assert settings.database is settings_property_db


@checks_deprecated_behaviour
def test_can_have_none_database_file():
    assert settings(database_file=None).database is None


@checks_deprecated_behaviour
def test_can_override_database_file():
    f = mkdtemp()
    x = settings(database_file=f)
    assert isinstance(x.database, DirectoryBasedExampleDatabase)
    assert x.database.path == f


def test_cannot_define_settings_once_locked():
    with pytest.raises(InvalidState):
        settings._define_setting('hi', 'there', 4)


def test_cannot_assign_default():
    with pytest.raises(AttributeError):
        settings.default = settings(max_examples=3)
    assert settings().max_examples != 3


def test_does_not_warn_if_quiet():
    with pytest.warns(None) as rec:
        note_deprecation('This is bad', settings(verbosity=Verbosity.quiet))
    assert len(rec) == 0


@settings(max_examples=7)
@given(st.builds(lambda: settings.default))
def test_settings_in_strategies_are_from_test_scope(s):
    assert s.max_examples == 7


@checks_deprecated_behaviour
def test_settings_alone():
    @settings()
    def test_nothing():
        pass
    test_nothing()


@checks_deprecated_behaviour
def test_settings_applied_twice_1():
    @given(st.integers())
    @settings()
    @settings()
    def test_nothing(x):
        pass
    test_nothing()


@checks_deprecated_behaviour
def test_settings_applied_twice_2():
    @settings()
    @given(st.integers())
    @settings()
    def test_nothing(x):
        pass
    test_nothing()


@checks_deprecated_behaviour
def test_settings_applied_twice_3():
    @settings()
    @settings()
    @given(st.integers())
    def test_nothing(x):
        pass
    test_nothing()


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
    script = tmpdir.join('assertlocation.py')
    script.write(ASSERT_DATABASE_PATH)

    subprocess.check_call([
        sys.executable, str(script)
    ])


def test_database_is_reference_preserved():
    s = settings(database=not_set)

    assert s.database is s.database


@pytest.mark.parametrize('value', [False, True])
def test_setting_use_coverage_is_deprecated(value):
    with validate_deprecation():
        settings(use_coverage=value)


@settings(verbosity=Verbosity.verbose)
@example(x=99)
@given(st.integers())
def test_settings_apply_for_explicit_examples(x):
    # Regression test for #1521
    assert settings.default.verbosity == Verbosity.verbose


def test_setattr_on_settings_singleton_is_error():
    # https://github.com/pandas-dev/pandas/pull/22679#issuecomment-420750921
    # Should be setting attributes on settings.default, not settings!
    with pytest.raises(AttributeError):
        settings.max_examples = 10


@pytest.mark.parametrize(('value', 'replacement', 'suggestion'), [
    (False, PrintSettings.NEVER, 'PrintSettings.NEVER'),
    (True, PrintSettings.ALWAYS, 'PrintSettings.ALWAYS'),
])
def test_can_set_print_blob_to_deprecated_bool(value, replacement, suggestion):
    with pytest.warns(
        HypothesisDeprecationWarning,
        match=re.escape(suggestion),
    ):
        s = settings(print_blob=value)

    assert s.print_blob == replacement


@pytest.mark.parametrize('value', [0, 1, 'always'])
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


test_settings_decorator_applies_to_rule_based_state_machine_class = \
    StepCounter.TestCase


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
    state_machine_instance.settings = 'any value'
