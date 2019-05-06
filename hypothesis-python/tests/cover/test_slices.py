from hypothesis import strategies as st, given, seed 
from hypothesis.errors import InvalidArgument
import pytest

@given(st.slices(10))
def test_slices_strategy(cases_occurred_at_least_once, slicer):
    start, stop, step = slicer.indices(10)
    assert slicer.stop is None or (slicer.stop >=0 and slicer.stop <= 10)
    assert slicer.start is None or (slicer.start >=0 and slicer.start <= 9)
    assert start + step <= 10 and start + step >= 0

def test_slices_strategy_errors_on_invalid_size():
    with pytest.raises(InvalidArgument) as exc:
        st.slices(-1).example()
    with pytest.raises(InvalidArgument) as exc:
        st.slices(0).example()
    with pytest.raises(InvalidArgument) as exc:
        st.slices("what").example()
    with pytest.raises(InvalidArgument) as exc:
        st.slices(None).example()






