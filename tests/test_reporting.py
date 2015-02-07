from hypothesis import reporting, given
import pytest
from tests.common.utils import capture_out


def test_can_suppress_output():
    @given(int)
    def test_int(x):
        assert False

    with capture_out() as o:
        with reporting.with_reporter(reporting.silent):
            with pytest.raises(AssertionError):
                test_int()
    assert 'Falsifying example' not in o.getvalue()


def test_prints_output_by_default():
    @given(int)
    def test_int(x):
        assert False

    with capture_out() as o:
        with reporting.with_reporter(reporting.default):
            with pytest.raises(AssertionError):
                test_int()
    assert 'Falsifying example' in o.getvalue()
