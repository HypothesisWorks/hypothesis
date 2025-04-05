Write type hints for strategies
===============================

Hypothesis provides type hints for all standard strategies:

.. code-block:: python

    from hypothesis import strategies as st

    # SearchStrategy[int]
    reveal_type(st.integers())

    # SearchStrategy[list[int]]
    reveal_type(st.lists(st.integers()))

|SearchStrategy| is the type of a strategy. You can use it to write type hints for your own strategies:

.. code-block:: python

    from hypothesis import strategies as st
    from hypothesis.strategies import SearchStrategy


    @st.composite
    def all_ints_or_floats(draw) -> SearchStrategy[int] | SearchStrategy[float]:
        all_integers = draw(st.booleans())
        return st.integers() if all_integers else st.floats()

Type variance of |SearchStrategy|
---------------------------------

|SearchStrategy| is generic in the type of examples it generates. It is covariant, meaning that if ``B < A`` then ``SearchStrategy[B] < SearchStrategy[A]``. In other words:

.. code-block:: python

    from hypothesis import given, strategies as st


    class A:
        pass


    class B(A):
        pass


    # accepts A, or any subtype of A
    def accepts_a(a: A) -> None:
        pass


    @given(st.from_type(B))
    def test_b(b: B) -> None:
        # this type checks, because accepts_a accepts any subtype of A,
        # and st.from_type(B) has type SearchStrategy[B] which provides
        # instances ``b: B`` to test_b.
        accepts_a(b)
