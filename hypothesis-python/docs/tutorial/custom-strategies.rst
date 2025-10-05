Custom strategies
==================

This page describes how to write a custom strategy, for when the built-in strategies don't quite fit your needs.

Writing helper functions
------------------------

Sometimes you might find it useful to write helper functions, to more concisely express a common pattern for your project. For example, it's much easier to write (and read!) ``response=json()`` than to have the whole implementation inline:

.. code-block:: python

    def json(*, finite_only=True):
        """Helper function to describe JSON objects, with optional inf and nan."""
        numbers = st.floats(allow_infinity=not finite_only, allow_nan=not finite_only)
        return st.recursive(
            st.none() | st.booleans() | st.integers() | numbers | st.text(),
            extend=lambda xs: st.lists(xs) | st.dictionaries(st.text(), xs),
        )

Writing your own strategy
-------------------------

If a strategy in Hypothesis doesn't match what you need, you can write your own strategy.

For instance, suppose we want to generate a list of floats which sum to ``1``. We might start implementing this by generating lists of integers between 0 and 1 with ``lists(floats(0, 1))``. But now we're a bit stuck, and can't go any further with the standard strategies.

One way to define a new strategy is using the |st.composite| decorator. |st.composite| lets you define a new strategy that uses arbitrary Python code. For instance, to implement the above:

.. code-block:: python

    from hypothesis import strategies as st

    @st.composite
    def sums_to_one(draw):
        l = draw(st.lists(st.floats(0, 1)))
        return [f / sum(l) for f in l]

|st.composite| passes a ``draw`` function to the decorated function as its first argument. ``draw`` is used to draw a random value from another strategy. We return from ``sums_to_one`` a value of the form we wanted to generate; in this case, a list that sums to one.

Let's see this new strategy in action:

.. code-block:: python

    import pytest

    from hypothesis import given, strategies as st

    @st.composite
    def sums_to_one(draw):
        lst = draw(st.lists(st.floats(0.001, 1), min_size=1))
        return [f / sum(lst) for f in lst]

    @given(sums_to_one())
    def test(lst):
        # ignore floating point errors
        assert sum(lst) == pytest.approx(1)

.. note::

    Just like all other strategies, we called ``sums_to_one`` before passing it to |@given|. |st.composite| should be thought of as turning its decorated function into a function which returns a stratgy when called. This is actually the same as existing strategies in Hypothesis; |st.integers| is really a function, which returns a strategy for integers when called.

Combining |st.composite| with parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can add parameters to functions decorated with |st.composite|, including keyword-only arguments. These work as you would normally expect.

For instance, suppose we wanted to generalize our ``sums_to_one`` function to ``sums_to_n``. We can add a parameter ``n``:

.. code-block:: python

    import pytest

    from hypothesis import assume, given, strategies as st

    @st.composite
    def sums_to_n(draw, n=1):  #  <-- changed
        lst = draw(st.lists(st.floats(0, 1), min_size=1))
        assume(sum(lst) > 0)
        return [f / sum(lst) * n for f in lst]  #  <-- changed

    @given(sums_to_n(10))
    def test(lst):
        assert sum(lst) == pytest.approx(10)

And we could just as easily have made ``n`` a keyword-only argument instead:

.. code-block:: python

    import pytest

    from hypothesis import assume, given, strategies as st

    @st.composite
    def sums_to_n(draw, *, n=1):  #  <-- changed
        lst = draw(st.lists(st.floats(0, 1), min_size=1))
        assume(sum(lst) > 0)
        return [f / sum(lst) * n for f in lst]

    @given(sums_to_n(n=10))  #  <-- changed
    def test(lst):
        assert sum(lst) == pytest.approx(10)

Dependent generation with |st.composite|
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Another scenario where |st.composite| is useful is when generating a value that depends on a value from another strategy. For instance, suppose we wanted to generate two integers ``n1`` and ``n2`` with ``n1 <= n2``. We can do this using |st.composite|:

.. code-block:: python

    @st.composite
    def ordered_pairs(draw):
        n1 = draw(st.integers())
        n2 = draw(st.integers(min_value=n1))
        return (n1, n2)

    @given(ordered_pairs())
    def test_pairs_are_ordered(pair):
        n1, n2 = pair
        assert n1 <= n2

.. note::

    We could also have written this particular strategy as ``st.tuples(st.integers(), st.integers()).map(sorted)`` (see :doc:`/tutorial/adapting-strategies`). Some prefer this inline approach, while others prefer defining well-named helper functions with |st.composite|. Our suggestion is simply that you prioritize ease of understanding when choosing which to use.

Mixing data generation and test code
------------------------------------

When using |st.composite|, you have to finish generating the entire input before running your test. But maybe you don't want to generate all of the input until you're sure some initial test assertions have passed. Or maybe you have some complicated control flow which makes it necessary to generate something in the middle of the test.

|st.data| lets you to do this. It's similar to |st.composite|, except it lets you mix test code and generation code.

.. note::

    The downside of this power is that |st.data| is incompatible |@example|, and that Hypothesis cannot print a nice representation of values generated from |st.data| when reporting failing examples, because the draws are spread out. Where possible, prefer |st.composite| to |st.data|.

For instance, here's how we would write our earlier |st.composite| example using |st.data|:

.. code-block:: python

    import pytest

    from hypothesis import given, strategies as st

    @given(st.data())
    def test(data):
        lst = data.draw(st.lists(st.floats(0.001, 1), min_size=1))
        lst = [f / sum(lst) for f in lst]
        # ignore floating point errors
        assert sum(lst) == pytest.approx(1)
