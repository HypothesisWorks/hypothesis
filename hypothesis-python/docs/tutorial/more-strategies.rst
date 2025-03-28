More strategies
===============

We've seen several basic strategies so far: |st.lists|, |st.integers|, |st.floats|, etc. These are great for generating simple inputs. In this page, we'll introduce several useful strategies for generating more complicated inputs.

|st.composite|
--------------

|st.composite| lets you define a new strategy which can use arbitrary Python code. This is particularly useful when making complicated transformations, or when generating data that depends on earlier values.

For instance, suppose we want to generate a list of floats which sum to ``1``. We could start by generating lists of integers between 0 and 1 with ``lists(floats(0, 1))``. But now we're a bit stuck; we don't have a way to transform this list into what we want.

Here's how we can use |st.composite| to do this:

.. code-block:: python

    from hypothesis import strategies as st

    @st.composite
    def sums_to_one(draw):
        l = draw(st.lists(st.floats(0, 1)))
        return [f / sum(l) for f in l]

|st.composite| passes a ``draw`` function to the decorated function as its first argument, which can be used to draw a random value from any strategy. The return value from a function decorated with |st.composite| should be a value of the form you want to generate.

Let's see this new strategy in action:

.. code-block:: python

    from hypothesis import strategies as st, given
    import pytest

    @st.composite
    def sums_to_one(draw):
        lst = draw(st.lists(st.floats(0, 1), min_size=1))
        return [f / sum(lst) for f in lst]

    @given(sums_to_one())
    def test(lst):
        # ignore floating point errors
        assert sum(lst) == pytest.approx(1)

Notice that, just like all other strategies, we called ``sums_to_one`` before passing it to |@given|. |st.composite| should be thought of as turning its decorated function into a function which returns a stratgy when called. If that's confusing, just remember that strategies created by decorating a function with |st.composite| are exactly like regular Hypothesis strategies, and you should call it whenever you use it.

If we run this test, we get an error:

.. code-block:: none

        ...
        return [f / sum(lst) for f in lst]
                ~~^~~~~~~~~~
    ZeroDivisionError: float division by zero
    while generating 'lst' from sums_to_one()

Whoops. We forgot that we could generate lists filled with just zero. This case seems difficult to avoid by construction without sacrificing test power, so we can filter it out with |assume|:

.. code-block:: python

    from hypothesis import strategies as st, given, assume
    import pytest

    @st.composite
    def sums_to_one(draw):
        lst = draw(st.lists(st.floats(0, 1), min_size=1))
        assume(sum(lst) > 0)  #  <-- new
        return [f / sum(lst) for f in lst]

    @given(sums_to_one())
    def test(lst):
        # ignore floating point errors
        assert sum(lst) == pytest.approx(1)

|assume| works exactly the same when called inside |st.composite| as it does when called in a test.

Parameters with |st.composite|
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can add parameters to functions decorated with |st.composite|, including keyword-only arguments. These work as you would normally expect.

For instance, suppose we wanted to generalize our ``sums_to_one`` function to ``sums_to_n``. We can add a parameter ``n``:

.. code-block:: python

    from hypothesis import strategies as st, given, assume
    import pytest

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

    from hypothesis import strategies as st, given, assume
    import pytest

    @st.composite
    def sums_to_n(draw, *, n=1):  #  <-- changed
        lst = draw(st.lists(st.floats(0, 1), min_size=1))
        assume(sum(lst) > 0)
        return [f / sum(lst) * n for f in lst]

    @given(sums_to_n(n=10))  #  <-- changed
    def test(lst):
        assert sum(lst) == pytest.approx(10)

Dependent generation
~~~~~~~~~~~~~~~~~~~~

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

    We could also have written this particular strategy as ``st.tuples(st.integers(), st.integers()).map(sorted)`` (see :doc:`the tutorial on .map() <map-and-flatmap>`). Some prefer this inline approach, while others prefer defining well-named helper functions with |st.composite|. Our suggestion is simply that you prioritize ease of understanding when choosing which to use.

|st.data|
---------

When using |st.composite|, you have to finish generating the entire input before running your test. But maybe you don't want to generate all of the input until you're sure some initial test assertions have passed. Or maybe you have some complicated control flow which makes it necessary to generate something in the middle of the test.

|st.data| lets you to do this. It's similar to |st.composite|, except it lets you mix test code and generation code.

.. note::

    The downside of this power is that |st.data| is incompatible |@example|, and that Hypothesis cannot print a nice representation of values generated from |st.data| when reporting failing examples, because the draws are spread out. Where possible, prefer |st.composite| to |st.data|.

For instance, here's how we would write our earlier |st.composite| example using |st.data|:

.. code-block:: python

    from hypothesis import strategies as st, given, assume
    import pytest

    @given(st.data())
    def test(data):
        lst = data.draw(st.lists(st.floats(0, 1), min_size=1))
        assume(sum(lst) > 0)
        lst = [f / sum(lst) for f in lst]
        # ignore floating point errors
        assert sum(lst) == pytest.approx(1)

|st.builds|
-----------

|st.builds| is a strategy which lets you create instances of a class (or other callable) by passing strategies for each argument.

For example, suppose we have written a class:

.. code-block:: python

    class MyClass:
        def __init__(self, a, *, b):
            self.a = a
            self.b = b

|st.builds| lets us define a strategy which creates ``MyClass`` instances, by passing strategies for ``a`` and ``b``:

.. code-block:: python

    @given(st.builds(MyClass, st.integers(), b=st.floats()))
    def test_my_class(obj):
        assert isinstance(obj, MyClass)
        assert isinstance(obj.a, int)
        assert isinstance(obj.b, float)

Type inference
~~~~~~~~~~~~~~

|st.builds| automatically infers strategies based on type annotations. If the argument is annotated with ``x: int``, |st.builds| will use the |st.integers| strategy; if ``x: float`` then it will use the |st.floats| strategy; etc.

.. note::

    This type inference uses |st.from_type|. See the |st.from_type| and |st.register_type_strategy| documentation for how to control type inference in Hypothesis.

.. code-block:: python

    class MyClass:
        def __init__(self, a: int, *, b: float):
            self.a = a
            self.b = b

    @given(st.builds(MyClass))
    def test_my_class(obj):
        assert isinstance(obj, MyClass)
        assert isinstance(obj.a, int)
        assert isinstance(obj.b, float)

You can still override the automatic inference if you want. For instance, we can change the ``b`` parameter to only generate positive floats, while still leaving ``a`` inferred:

.. code-block:: python

    class MyClass:
        def __init__(self, a: int, *, b: float):
            self.a = a
            self.b = b

    # changed
    @given(st.builds(MyClass, b=st.floats(min_value=0.0)))
    def test_my_class(obj):
        assert isinstance(obj, MyClass)
        assert isinstance(obj.a, int)
        assert isinstance(obj.b, float)
        # added
        assert obj.b > 0.0

This type inference also works for |dataclasses| and :pypi:`attrs` classes.

|st.recursive|
--------------

Sometimes the data you want to generate has a recursive definition. e.g. if you wanted to generate JSON data, valid JSON is:

1. Any float, any boolean, any unicode string.
2. Any list of valid JSON data
3. Any dictionary mapping unicode strings to valid JSON data.

The problem is that you cannot call a strategy recursively and expect it to not just blow up and eat all your memory.  The other problem here is that not all unicode strings display consistently on different machines, so we'll restrict them in our doctest.

The way Hypothesis handles this is with the :func:`~hypothesis.strategies.recursive` strategy which you pass in a base case and a function that, given a strategy for your data type, returns a new strategy for it. So for example:

.. code-block:: pycon

    >>> from string import printable
    ... from pprint import pprint
    >>> json = recursive(
    ...     none() | booleans() | floats() | text(printable),
    ...     lambda children: lists(children) | dictionaries(text(printable), children),
    ... )
    >>> pprint(json.example())
    [[1.175494351e-38, ']', 1.9, True, False, '.M}Xl', ''], True]
    >>> pprint(json.example())
    {'de(l': None,
     'nK': {'(Rt)': None,
            '+hoZh1YU]gy8': True,
            '8z]EIFA06^li^': 'LFE{Q',
            '9,': 'l{cA=/'}}

That is, we start with our leaf data and then we augment it by allowing lists and dictionaries of anything we can generate as JSON data.

The size control of this works by limiting the maximum number of values that can be drawn from the base strategy. So for example if we wanted to only generate really small JSON we could do this as:

.. code-block:: pycon

    >>> small_lists = recursive(booleans(), lists, max_leaves=5)
    >>> small_lists.example()
    True
    >>> small_lists.example()
    [False]
