from __future__ import absolute_import, division, print_function

import pytest

from hypothesis import given
from hypothesis.strategies import composite, integers


def test_keyboardinterrupt_no_rerun():
    runs = [0]
    interrupt = 3

    @given(integers())
    def test_raise_keyboardinterrupt(x):
        runs[0] += 1
        if runs[0] == interrupt:
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        test_raise_keyboardinterrupt()

    assert runs[0] == interrupt


def test_keyboardinterrupt_in_strategy_no_rerun():
    runs = [0]
    interrupt = 3

    @composite
    def interrupt_eventually(draw):
        runs[0] += 1
        if runs[0] == interrupt:
            # import pdb; pdb.set_trace()
            raise KeyboardInterrupt
        return draw(integers())

    @given(interrupt_eventually())
    def test_do_nothing(x):
        pass

    with pytest.raises(KeyboardInterrupt):
        test_do_nothing()

    assert runs[0] == interrupt


def test_systemexit_no_rerun():
    runs = [0]
    interrupt = 3

    @given(integers())
    def test_raise_systemexit(x):
        runs[0] += 1
        if runs[0] == interrupt:
            raise SystemExit

    with pytest.raises(SystemExit):
        test_raise_systemexit()

    assert runs[0] == interrupt
