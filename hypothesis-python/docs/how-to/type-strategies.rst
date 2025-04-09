Write type hints for strategies
===============================

Hypothesis provides type hints for all strategies and functions which return a strategy:

.. code-block:: python

    from hypothesis import strategies as st

    reveal_type(st.integers())
    # SearchStrategy[int]

    reveal_type(st.lists(st.integers()))
    # SearchStrategy[list[int]]

|SearchStrategy| is the type of a strategy. It is parametrized by the type of the example it generates. You can use it to write type hints for your functions which return a strategy:

.. code-block:: python

    from hypothesis import strategies as st
    from hypothesis.strategies import SearchStrategy

    # returns a strategy for "normal" numbers
    def numbers() -> SearchStrategy[int | float]:
        return st.integers() | st.floats(allow_nan=False, allow_infinity=False)

It's worth pointing out the distinction between a strategy, and a function that returns a strategy. |st.integers| is a function which returns a strategy that has type ``SearchStrategy[int]``. The function ``st.integers`` therefore has type ``Callable[..., SearchStrategy[int]]``, while the value ``s = st.integers()`` has type ``SearchStrategy[int]``.


Type hints for |st.composite|
-----------------------------

When writing type hints for strategies defined with |st.composite|, use the type of the returned value (not ``SearchStrategy``):

.. code-block:: python

    @st.composite
    def ordered_pairs(draw) -> tuple[int, int]:
        n1 = draw(st.integers())
        n2 = draw(st.integers(min_value=n1))
        return (n1, n2)

Type variance of |SearchStrategy|
---------------------------------

|SearchStrategy| is covariant, meaning that if ``B < A`` then ``SearchStrategy[B] < SearchStrategy[A]``. In other words, the strategy ``st.from_type(Dog)`` is a subtype of the strategy ``st.from_type(Animal)``.
