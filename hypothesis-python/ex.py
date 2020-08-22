from typing import TypeVar

from hypothesis import strategies as st

S = TypeVar('S', bound='st.SearchStrategy')

def some(x: S) -> None:
    x.example()
