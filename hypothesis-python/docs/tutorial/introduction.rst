Introduction to Hypothesis
==========================

This page introduces two fundamental parts of Hypothesis (|@given|, and strategies) and shows how to test a selection sort implementation using Hypothesis.

Install Hypothesis
------------------

First, let's install Hypothesis:

.. code-block:: shell

    pip install hypothesis

Defining a simple test
----------------------

Hypothesis tests are defined using two things; |@given|, and a *strategy*, which is passed to |@given|. Here's a simple example:

.. code-block:: python

    from hypothesis import given, strategies as st

    @given(st.integers())
    def test_is_integer(n):
        assert isinstance(n, int)

Adding the |@given| decorator turns this function into a Hypothesis test. Passing |st.integers| to |@given| says that Hypothesis should generate random integers for the argument ``n`` when testing.

We can run this test by calling it:

.. code-block:: python

    from hypothesis import given, strategies as st

    @given(st.integers())
    def test_is_integer(n):
        print(f"called with {n}")
        assert isinstance(n, int)

    test_is_integer()

Note that we don't pass anything for ``n``; Hypothesis handles generating that value for us. The resulting output looks like this:

.. code-block:: none

    called with 0
    called with -18588
    called with -672780074
    called with 32616
    ...


Testing a sorting algorithm
---------------------------

Suppose we have implemented a simple selection sort:

.. code-block:: python

  # contents of example.py
  from hypothesis import given, strategies as st

  def selection_sort(lst):
      result = []
      while lst:
          smallest = min(lst)
          result.append(smallest)
          lst.remove(smallest)
      return result

and want to make sure it's correct. We can write the following test by combining the |st.integers| and |st.lists| strategies:

.. code-block:: python

  ...

  @given(st.lists(st.integers()))
  def test_sort_correct(lst):
      print(f"called with {lst}")
      assert selection_sort(lst.copy()) == sorted(lst)

  test_sort_correct()

When running ``test_sort_correct``, Hypothesis uses the ``lists(integers())`` strategy to generate randm lists of integers. Feel free to run ``python example.py`` to get an idea of the kinds of lists Hypothesis generates (and to convince yourself that this test passes).

Adding floats to our test
~~~~~~~~~~~~~~~~~~~~~~~~~

This test is a good start. But ``selection_sort`` should be able to sort lists with floats, too. If we wanted to generate lists of either integers or floats, we can change our strategy:

.. code-block:: python

  # changes to example.py
  @given(st.lists(st.integers() | st.floats()))
  def test_sort_correct(lst):
      pass

The pipe operator ``|`` takes two strategies, and returns a new strategy which generates values from either of its strategies. So the strategy ``integers() | floats()`` can generate either an integer, or a float.

.. note::

  ``strategy1 | strategy2`` is equivalent to :func:`st.one_of(strategy1, strategy2) <hypothesis.strategies.one_of>`.

Preventing |st.floats| from generating ``nan``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Even though ``test_sort_correct`` passed when we used lists of integers, it actually fails now that we've added floats! If you run ``python example.py``, you'll likely (but not always; this is random testing, after all) find that Hypothesis reports a counterexample to ``test_sort_correct``. For me, that counterexample is ``[1.0, nan, 0]``. It might be different for you.

The issue is that sorting in the presence of ``nan`` is not well defined. As a result, we may decide that we don't want to generate them while testing. We can pass ``floats(allow_nan=False)`` to tell Hypothesis not to generate ``nan``:

.. code-block:: python

  # changes to example.py
  @given(st.lists(st.integers() | st.floats(allow_nan=False)))
  def test_sort_correct(lst):
      pass

And now this test passes without issues.

.. note::

  You can use the ``.example()`` method to get an idea of the kinds of things a strategy will generate:

  .. code-block:: pycon

    >>> st.lists(st.integers() | st.floats(allow_nan=False)).example()
    [-5.969063e-08, 15283673678, 18717, -inf]

  Note that ``.example()`` is intended for interactive use only (i.e., in a :term:`REPL <python:REPL>`). It is not intended to be used inside tests.


Tests with multiple arguments
-----------------------------

If we wanted to pass multiple arguments to a test, we can do this by passing multiple strategies to |@given|:

.. code-block:: python

    from hypothesis import given, strategies as st

    @given(st.integers(), st.lists(st.floats()))
    def test_multiple_arguments(n, lst):
        assert isinstance(n, int)
        assert isinstance(lst, list)
        for f in lst:
            assert isinstance(f, float)

Keyword arguments
~~~~~~~~~~~~~~~~~

We can also pass strategies using keyword arguments:

.. code-block:: python

    @given(lst=st.lists(st.floats()), n=st.integers())  #  <-- changed
    def test_multiple_arguments(n, lst):
        pass

Note that even though we changed the order the parameters to |@given| appear, we also explicitly told it which parameters to pass to by using keyword arguments, so the meaning of the test hasn't changed.

In general, you can think of positional and keyword arguments to |@given| as being forwarded to the test arguments.

.. note::

  One exception is that |@given| does not support mixing positional and keyword arguments. See the |@given| documentation for more about how it handles arguments.


Running Hypothesis tests
------------------------

There are a few ways to run a Hypothesis test.

* Explicitly call it, like ``test_is_integer()``, as we've seen. Hypothesis tests are just normal functions, except |@given| handles generating and passing values for the function arguments.
* Let a test runner such as :pypi:`pytest` pick up on it (as long as the function name starts with ``test_``).

Concretely, when running a Hypothesis test, Hypothesis will:

* generate 100 random inputs,
* run the body of the function for each input, and
* report any exceptions that get raised.

.. note::

  The number of examples can be controlled with the |max_examples| setting. The default is 100.


When to use Hypothesis and property-based testing
-------------------------------------------------

Property-based testing is a powerful *addition* to unit testing. It is not always a replacement.

Sometimes, the biggest barrier to using property-based testing is finding a property in your code to test. As a starting point, we recommend looking through your existing unit tests for hardcoded inputs whose specific value does not actually matter. Can this value be abstracted into a generic strategy? If so, congratulations — replacing explicit values with a generic strategy is all you need to start writing a property-based test.

There is also an easy property that is always available: "the code does not crash when called with inputs of the proper type". You would be surprised how often simply calling your code with random inputs finds bugs!

Other examples of properties include:

* Serializing and then deserializing returns the value you started with.
* An optimized implementation is equivalent to a slower, but clearly correct, implementation.
* A sequence of transactions in a financial system always "balances"; money never gets lost.
* The derivative of a polynomial of order ``n`` has order ``n - 1``.
* A type-checker, linter, formatter, or compiler does not crash when called on syntactically valid code.
* `And more <https://fsharpforfunandprofit.com/posts/property-based-testing-2/>`_.
