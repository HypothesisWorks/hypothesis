from hypothesis import strategies as st
from tests.common.debug import minimal, find_any, assert_all_examples


def test_stop_stays_within_bounds():
    size = 1000
    assert_all_examples(
        st.slices(size), 
        lambda x: x.stop is None or (x.stop >= 0 and x.stop <= size)
    )


def test_start_stay_within_bounds():
    size = 1000
    assert_all_examples(
        st.slices(size),
        lambda x: x.start is None or (x.start >= 0 and x.start <= size - 1),
    )


def test_step_stays_within_bounds():
    size = 1000
    # indices -> (start, stop, step)
    assert_all_examples(
        st.slices(size),
        lambda x: x.indices(size)[0] + x.indices(size)[2] <= size
        and x.indices(size)[0] + x.indices(size)[2] >= 0,
    )


def test_step_will_not_be_zero():
    size = 1000
    assert_all_examples(st.slices(size), lambda x: x.step != 0)


def test_step_will_be_negative():
    size = 10000
    find_any(st.slices(size), lambda x: x.step <= 0)


def test_step_will_be_positive():
    size = 10000
    find_any(st.slices(size), lambda x: x.step > 0)


def test_stop_will_equal_size():
    size = 10000
    find_any(st.slices(size), lambda x: x.stop == size)


def test_start_will_equal_size():
    size = 10000
    find_any(st.slices(size), lambda x: x.start == size - 1)


def test_start_will_equal_0():
    size = 10000
    find_any(st.slices(size), lambda x: x.start == 0)


def test_start_will_equal_stop():
    size = 10000
    find_any(st.slices(size), lambda x: x.start == x.stop)


def test_splices_will_shrink():
    size = 1000000
    sliced = minimal(st.slices(size))
    assert sliced.start == 0
    assert sliced.stop == 0 or sliced.stop is None
    assert sliced.step == 1

