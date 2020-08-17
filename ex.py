from hypothesis import given, strategies as st
from typing import TypeVar

_T = TypeVar('_T', bound='X')

def some(x: _T) -> int:
    return x.arg

class X:
    def __init__(self, arg: int) -> None:
        self.arg = arg


@given(st.builds(some))
def test_forward_ref(built):
    assert isinstance(built, int)
