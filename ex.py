from hypothesis import strategies as st
from typing import Final

def test_final_type():
    strategy = st.from_type(Final)
    strategy.example()
