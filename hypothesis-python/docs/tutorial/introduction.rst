Introduction
============

Hypothesis is library for *property-based testing*. In a property-based test, you write something which should hold for all inputs of a certain type, and then let Hypothesis generate and check random inputs of that type. This randomized testing can catch bugs that manually constructed inputs may not have found.

Install Hypothesis
------------------

First, install Hypothesis:

.. code-block:: shell

    pip install hypothesis

A simple example
----------------

Let's get started with Hypothesis by writing a really simple test:

.. code-block:: python

    from hypothesis import given, strategies as st

    @given(st.integers())
    def test_trivial_property(n):
        assert isinstance(n, int)

This asks Hypothesis for random integers, and checks that we are in fact getting integers.

We can run this test in one of two ways:

* By letting a test runner (such as ``pytest``) pick up on it.
* By explicitly calling it.

Let's do the latter for now, and add a print statement so we can see what's going on:

.. code-block:: python

    # contents of example.py
    from hypothesis import given, strategies as st

    @given(st.integers())
    def test_trivial_property(n):
        print(f"called with {n}")
        assert isinstance(n, int)

    test_trivial_property()

Here's my output when running ``python example.py`` (yours will be different, since Hypothesis generates random values):

.. code-block:: none

    called with 0
    called with -18588
    called with -672780074
    called with 32616
    ...

Concretely, when you run a Hypothesis test, Hypothesis will:

* generate 100 random inputs,
* run the body of the function for each input, and
* report any exceptions that get raised.

.. note::

  The number of examples can be controlled with the |max_examples| setting. The default is 100.

Let's take a closer look at the two things from Hypothesis we used to write this test: the |st.integers| strategy, and the |@given| decorator.

Strategies
----------

A *strategy* tells Hypothesis what type of inputs to generate. When we said "Hypothesis generates 100 random inputs", what we really meant was "Hypothesis generates 100 random inputs, using the |st.integers| strategy".

Let's introduce a few more strategies with a slightly more complicated example. Suppose we have implemented a simple selection sort, and want to make sure it's correct. We can start by writing the following test using the |st.lists| strategy:

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

  @given(st.lists(st.integers()))
  def test_sort_correct(lst):
      print(f"called with {lst}")
      assert selection_sort(lst.copy()) == sorted(lst)

  test_sort_correct()

Because we're testing a sorting implementation, we've changed the strategy to ``lists(integers())``. When we run ``test_sort_correct``, Hypothesis looks at the strategy ``lists(integers())``, and generates random lists of integers as input. Feel free to run ``python example.py`` to get an idea of the kinds of lists Hypothesis generates (and to convince yourself that this test passes).

This is a good start at a test. But ``selection_sort`` should be able to sort lists with floats, too. If we wanted to generate lists of either integers or floats, we can change our strategy:

.. code-block:: python

  # changes to example.py
  @given(st.lists(st.integers() | st.floats()))
  def test_sort_correct(lst):
      ...

The pipe operator ``|`` takes two strategies, and returns a new strategy which can generate values from either of its strategies. So the strategy ``integers() | floats()`` can generate either an integer, or a float.

.. note::

  ``|`` is equivalent to (and is shorthand for) the |st.one_of| strategy.

Even though ``test_sort_correct`` passed when we used lists of integers, it actually fails now that we've added floats! If you run ``python example.py``, you'll likely (but not always; this is random testing, after all) find that Hypothesis reports a counterexample to ``test_sort_correct``. For me, that counterexample is ``[1.0, nan, 0]``. It might be different for you.

The issue is that sorting in the presence of ``nan`` is not well defined. As a result, we may decide that we don't want to generate them while testing. We can pass ``floats(allow_nan=False)`` to tell Hypothesis not to generate ``nan``:

.. code-block:: python

  # changes to example.py
  @given(st.lists(st.integers() | st.floats(allow_nan=False)))
  def test_sort_correct(lst):
      ...

And now this test passes without issues.

.. note::

  Hypothesis provides many different strategies. If you want to generate a standard Python type, Hypothesis almost certainly has a strategy for it. See the :ref:`strategies reference <strategies>` for a complete list.


``.example``
~~~~~~~~~~~~

You can use the ``.example`` method to get an idea of the kinds of things a strategy will generate:

.. code-block:: pycon

  >>> dictionaries(integers(), text()).example()
  {-87: '×\x18'}

.. warning::

  ``.example`` is intended for interactive use only (i.e., in a :term:`REPL <python:REPL>`). It is not intended to be used inside tests.


|@given|
--------

Now that we've talked about strategies, let's talk about how to pass them to a test using |@given|. |@given| is the standard entrypoint into Hypothesis, which converts the decorated function into a property-based test.

In order to talk about how to pass things to |@given|, let's start again with our really simple example:

.. code-block:: python

    from hypothesis import given, strategies as st

    @given(st.integers())
    def test_trivial_property(n):
        assert isinstance(n, int)

If we wanted to pass multiple arguments to ``test_trivial_property``, we can do this by passing multiple strategies to |@given|:

.. code-block:: python

    from hypothesis import given, strategies as st

    @given(st.integers(), st.lists(st.floats()))
    def test_trivial_property(n, lst):
        assert isinstance(n, int)
        assert isinstance(lst, list)
        for f in lst:
            assert isinstance(f, float)

We can also pass strategies using keyword arguments:

.. code-block:: python

    from hypothesis import given, strategies as st

    @given(lst=st.lists(st.floats()), n=st.integers())  #  <-- changed
    def test_trivial_property(n, lst):
        assert isinstance(n, int)
        assert isinstance(lst, list)
        for f in lst:
            assert isinstance(f, float)

Note that in the keyword example, even though we changed the order the parameters to |@given| appear, we also explicitly told it which parameters to pass to by using keyword arguments, so the meaning of the test hasn't changed.

In general, you can think of positional and keyword arguments to |@given| as being forwarded to the test arguments.

.. note::

  One exception is that |@given| does not support mixing positional and keyword arguments. Read more about how |@given| handles arguments in :doc:`its documentation </reference/given>`.

When to use property-based testing
----------------------------------

Property-based testing is a powerful *addition* to unit testing. It is not always a replacement.

Sometimes, the hardest part can be finding a property in your code to test. As a starting point, we recommend looking through your existing unit tests for hardcoded inputs whose value is not actually relevant. Can this value be abstracted into a generic strategy? If so, congratulations — replacing explicit values with a generic strategy is all you need to start writing property-based tests.

There is also an easy property that is always available: "the code does not crash when called with inputs of the proper type". You would be surprised how often simply calling your code with random inputs finds bugs!

Other examples of properties include:

* Serializing and then deserializing returns the value you started with.
* An optimized implementation is equivalent to a slower, but clearly correct, implementation.
* A sequence of transactions in a financial system always "balances"; money never gets lost.
* The derivative of a polynomial of order ``n`` has order ``n - 1``.
* A type-checker, linter, formatter, or compiler does not crash when called on syntactically valid code.
* `And more <https://fsharpforfunandprofit.com/posts/property-based-testing-2/>`_.


.. A more realistic example
.. ------------------------

.. For instance, suppose we have written a fast sorting implementation called ``fast_sort``, and want to make sure it is correct. We could write a standard unit test, by selecting a few inputs and checking the output is what we expect:

.. .. code-block:: python

..   def test_sort_correct():
..       assert fast_sort([1, 3.01, 2]) == sorted([1, 3.01, 2])
..       assert fast_sort([1.5, 2]) == sorted([1.5, 2])

.. But this test isn't particularly strong. ``my_sort`` might behave incorrectly when called with duplicate values, or with ``math.nan``, or with long runs of increasing or decreasing values, or any number of other unusual inputs. We could try to test each of these by writing manual test cases...or we could write a property-based test instead!

.. Here's a more powerful property-based test, written with Hypothesis:

.. .. code-block:: python

..   from hypothesis import given, strategies as st

..   @given(st.lists(st.integers() | st.floats()))
..   def test_sort_correct(lst):
..       assert fast_sort(lst) == sorted(lst)

.. When ``test_sort_correct`` is called, Hypothesis:

.. * generates 100 random inputs,
.. * runs the body of the function for each input, and
.. * reports any exceptions that get raised.
