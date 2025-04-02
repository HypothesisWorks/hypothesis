Built-in strategies
===================

This page shows some of the strategies that Hypothesis provides for you.

Strategies provided by Hypothesis
---------------------------------

Here is a selection of strategies provided by Hypothesis that may be useful to know:

- |st.integers|. Generates integers.
- |st.floats|. Generates floats.
- |st.booleans|. Generates booleans.
- |st.text|. Generates unicode strings (i.e., instances of |str|).
- |st.lists|. Generates lists with elements from the strategy passed to it. ``st.lists(st.integers())`` generates lists of integers.
- |st.tuples|. Generates tuples of a fixed length. ``st.tuples(st.integers(), st.floats())`` generates tuples with two elements, where the first element is an integer and the second is a float.
- |st.one_of|. Generates from any of the strategies passed to it. ``st.one_of(st.integers(), st.floats())`` generates either integers or floats. You can also use ``|`` to construct |st.one_of|, like ``st.integers() | st.floats()``.
- |st.builds|. Generates instances of a class (or other callable) by specifying a strategy for each argument. ``st.builds(Person, name=st.text(), age=st.integers())``.
- |st.just|. Generates the exact value passed to it. ``st.just("a")`` generates the exact string ``"a"``. This is useful when something expects to be passed a strategy. For instance, ``st.lists(st.integers() | st.just("a"))`` generates lists whose elements are either integers or the string ``"a"``.
- |st.sampled_from|. Generates a random value from a list. ``st.sampled_from(["a", 1, True])`` is equivalent to ``st.just("a") | st.just(1) | st.just(True)``.
- |st.none|. Generates ``None``. Useful for parameters that can be optional, like ``st.integers() | st.none()``.

.. seealso::

    See the :doc:`strategies API reference </reference/strategies>` for a full list of strategies provided by Hypothesis.
