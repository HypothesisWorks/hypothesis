import pytest

from hypothesis import assume, given, infer, reject, settings
from hypothesis.errors import InvalidArgument, Unsatisfiable
from hypothesis.strategies import integers, composite
from tests.common.utils import fails_with


def test_keyboardinterrupt_no_rerun():
    runs = 0
    interrupt = 3
    @given(integers())
    def test_raise_keyboardinterrupt(x):
        nonlocal runs
        runs += 1
        if runs == interrupt:
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        test_raise_keyboardinterrupt()

    assert runs == interrupt


def test_keyboardinterrupt_in_strategy_no_rerun():
    runs = 0
    interrupt = 3

    @composite
    def interrupt_eventually(draw):
        nonlocal runs
        runs += 1
        if runs == interrupt:
            # import pdb; pdb.set_trace()
            raise KeyboardInterrupt
        return draw(integers())

    @given(interrupt_eventually())
    def test_do_nothing(x):
        pass

    with pytest.raises(KeyboardInterrupt):
        test_do_nothing()

    assert runs == interrupt


def test_systemexit_no_rerun():
    runs = 0
    interrupt = 3
    @given(integers())
    def test_raise_systemexit(x):
        nonlocal runs
        runs += 1
        if runs == interrupt:
            raise SystemExit

    with pytest.raises(SystemExit):
        test_raise_systemexit()

    assert runs == interrupt
