|assume| and |strategy.filter|
==============================

Many strategies in Hypothesis offer some control over the kinds of values that get generated. For instance, ``integers(min_value=0)`` generates positive integers, and ``integers(100, 200)`` generates integers between ``100`` and ``200``.

Sometimes, you need more control than this. The inputs from a strategy may not match exactly what you need, and you just need to filter out a few bad cases.

For instance, suppose we have written a simple test involving the modulo operator ``%``:

.. code-block:: python

    from hypothesis import given, strategies as st

    @given(st.integers(), st.integers())
    def test_remainder_magnitude(a, b):
        # the remainder after division is always less than
        # the divisor
        assert abs(a % b) < abs(b)

Hypothesis will quickly report a failure for this test: ``ZeroDivisionError: integer modulo by zero``. Just like division, modulo isn't defined for 0. The case of ``b == 0`` isn't interesting for the test, and we would like to get rid of it.

Hypothesis has two ways to do this: |assume|, and |strategy.filter|.

|assume|
--------

The |assume| function tells Hypothesis to skip test cases where some condition evaluates to ``True``. You can use it anywhere in your test. Let's use |assume| to tell Hypothesis to skip the case where ``b == 0``:

.. code-block:: python

    from hypothesis import assume, given, strategies as st

    @given(st.integers(), st.integers())
    def test_remainder_magnitude(a, b):
        assume(b != 0)
        # b will be nonzero here
        assert abs(a % b) < abs(b)

This test now passes cleanly.

|assume| vs early-returning
~~~~~~~~~~~~~~~~~~~~~~~~~~~

One other way we could have avoided the divide-by-zero error is to early-return when ``b == 0``:

.. code-block:: python

    from hypothesis import assume, given, strategies as st

    @given(st.integers(), st.integers())
    def test_remainder_magnitude(a, b):
        if b == 0:
            return
        assert abs(a % b) < abs(b)

While this would have avoided the divide-by-zero, early-returning is not the same as using |assume|. With |assume|, Hypothesis knows that a test case has been filtered out, and will not count it towards the |max_examples| limit. In contrast, early-returns are counted as a valid example. In more complicted cases, this could end up testing your code less than you expect, because many test cases get discarded without Hypothesis knowing about it.

In addition, |assume| lets you skip the test case at any point in the test, even inside arbitrarily deep nestings of functions.

You should always use |assume| rather than early-returning. |assume| is more idiomatic and allows Hypothesis more insight into your test.

|strategy.filter|
-----------------

Calling |strategy.filter| on a strategy creates a new strategy with that filter applied at generation-time. For instance, ``integers().filter(lambda n: n != 0)`` is a strategy which generates nonzero integers.

We could have expresseed our |assume| example using |strategy.filter| as well:

.. code-block:: python

    from hypothesis import assume, given, strategies as st

    @given(st.integers(), st.integers().filter(lambda n: n != 0))
    def test_remainder_magnitude(a, b):
        # b is guaranteed to be nonzero here, thanks to the filter
        assert abs(a % b) < abs(b)


|assume| vs |strategy.filter|
-----------------------------

Where possible, you should use |strategy.filter|. Hypothesis can often rewrite simple filters into more efficient sampling methods than rejection sampling, and will retry filters several times instead of aborting the entire test case (as with |assume|).

For more complex relationships that can't be expressed with |strategy.filter|, use |assume|.

Here's an example of a test where we want to filter out two different types of examples:

.. code-block:: python

    from hypothesis import assume, given, strategies as st

    @given(st.integers(), st.integers())
    def test_floor_division_lossless_when_b_divides_a(a, b):
        # we want to assume that:
        # * b is nonzero, and
        # * b divides a
        assert (a // b) * b == a

We could start by using |assume| for both:

.. code-block:: python

    from hypothesis import assume, given, strategies as st

    @given(st.integers(), st.integers())
    def test_floor_division_lossless_when_b_divides_a(a, b):
        assume(b != 0)
        assume(a % b == 0)
        assert (a // b) * b == a

And then notice that the ``b != 0`` condition can be moved into the strategy definition as a |strategy.filter| call:

.. code-block:: python

    from hypothesis import assume, given, strategies as st

    @given(st.integers(), st.integers().filter(lambda n: n != 0))
    def test_floor_division_lossless_when_b_divides_a(a, b):
        assume(a % b == 0)
        assert (a // b) * b == a

However, the ``a % b == 0`` condition has to stay as an |assume|, because it expresses a more complicated relationship between ``a`` and ``b``.
