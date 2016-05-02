=============================
Details and advanced features
=============================

This is an account of slightly less common Hypothesis features that you don't need
to get started but will nevertheless make your life easier.


----------------------
Additional test output
----------------------

Normally the output of a failing test will look something like:

.. code::

    Falsifying example: test_a_thing(x=1, y="foo")

With the ``repr`` of each keyword argument being printed.

Sometimes this isn't enough, either because you have values with a ``repr`` that
isn't very descriptive or because you need to see the output of some
intermediate steps of your test. That's where the ``note`` function comes in:

.. code:: pycon

    >>> from hypothesis import given, note, strategies as st
    >>> @given(st.lists(st.integers()), st.randoms())
    ... def test_shuffle_is_noop(ls, r):
    ...     ls2 = list(ls)
    ...     r.shuffle(ls2)
    ...     note("Shuffle: %r" % (ls2))
    ...     assert ls == ls2
    ...
    >>> test_shuffle_is_noop()
    Falsifying example: test_shuffle_is_noop(ls=[0, 0, 1], r=RandomWithSeed(0))
    Shuffle: [0, 1, 0]
    Traceback (most recent call last):
        ...
    AssertionError

The note is printed in the final run of the test in order to include any
additional information you might need in your test.

------------------
Making assumptions
------------------

Sometimes Hypothesis doesn't give you exactly the right sort of data you want - it's
mostly of the right shape, but some examples won't work and you don't want to care about
them. You *can* just ignore these by aborting the test early, but this runs the risk of
accidentally testing a lot less than you think you are. Also it would be nice to spend
less time on bad examples - if you're running 200 examples per test (the default) and
it turns out 150 of those examples don't match your needs, that's a lot of wasted time.

The way Hypothesis handles this is to let you specify things which you *assume* to be
true. This lets you abort a test in a way that marks the example as bad rather than
failing the test. Hypothesis will use this information to try to avoid similar examples
in future.

For example suppose had the following test:


.. code:: python

  from hypothesis import given
  from hypothesis.strategies import floats

  @given(floats())
  def test_negation_is_self_inverse(x):
      assert x == -(-x)


Running this gives us:

.. code::

  Falsifying example: test_negation_is_self_inverse(x=float('nan'))
  AssertionError

This is annoying. We know about NaN and don't really care about it, but as soon as Hypothesis
finds a NaN example it will get distracted by that and tell us about it. Also the test will
fail and we want it to pass.

So lets block off this particular example:

.. code:: python

  from hypothesis import given, assume
  from hypothesis.strategies import floats
  from math import isnan

  @given(floats())
  def test_negation_is_self_inverse_for_non_nan(x):
      assume(not isnan(x))
      assert x == -(-x)

And this passes without a problem.

:func:`~hypothesis.core.assume` throws an exception which
terminates the test when provided with a false argument.
It's essentially an :ref:`assert <python:assert>`, except that
the exception it throws is one that Hypothesis
identifies as meaning that this is a bad example, not a failing test.

In order to avoid the easy trap where you assume a lot more than you intended, Hypothesis
will fail a test when it can't find enough examples passing the assumption.

If we'd written:

.. code:: python

  from hypothesis import given, assume
  from hypothesis.strategies import floats

  @given(floats())
  def test_negation_is_self_inverse_for_non_nan(x):
      assume(False)
      assert x == -(-x)


Then on running we'd have got the exception:

.. code::

  Unsatisfiable: Unable to satisfy assumptions of hypothesis test_negation_is_self_inverse_for_non_nan. Only 0 examples found after 0.0791318 seconds

~~~~~~~~~~~~~~~~~~~
How good is assume?
~~~~~~~~~~~~~~~~~~~

Hypothesis has an adaptive exploration strategy to try to avoid things which falsify
assumptions, which should generally result in it still being able to find examples in
hard to find situations.

Suppose we had the following:


.. code:: python

  @given(lists(integers()))
  def test_sum_is_positive(xs):
    assert sum(xs) > 0

Unsurprisingly this fails and gives the falsifying example [].

Adding ``assume(xs)`` to this removes the trivial empty example and gives us [0].

Adding ``assume(all(x > 0 for x in xs))`` and it passes: A sum of a list of
positive integers is positive.

The reason that this should be surprising is not that it doesn't find a
counter-example, but that it finds enough examples at all.

In order to make sure something interesting is happening, suppose we wanted to
try this for long lists. e.g. suppose we added an assume(len(xs) > 10) to it.
This should basically never find an example: A naive strategy would find fewer
than one in a thousand examples, because if each element of the list is
negative with probability half, you'd have to have ten of these go the right
way by chance. In the default configuration Hypothesis gives up long before
it's tried 1000 examples (by default it tries 200).

Here's what happens if we try to run this:


.. code:: python

  @given(lists(integers()))
  def test_sum_is_positive(xs):
      assume(len(xs) > 10)
      assume(all(x > 0 for x in xs))
      print(xs)
      assert sum(xs) > 0

  In: test_sum_is_positive()
  [17, 12, 7, 13, 11, 3, 6, 9, 8, 11, 47, 27, 1, 31, 1]
  [6, 2, 29, 30, 25, 34, 19, 15, 50, 16, 10, 3, 16]
  [25, 17, 9, 19, 15, 2, 2, 4, 22, 10, 10, 27, 3, 1, 14, 17, 13, 8, 16, 9, 2...
  [17, 65, 78, 1, 8, 29, 2, 79, 28, 18, 39]
  [13, 26, 8, 3, 4, 76, 6, 14, 20, 27, 21, 32, 14, 42, 9, 24, 33, 9, 5, 15, ...
  [2, 1, 2, 2, 3, 10, 12, 11, 21, 11, 1, 16]

As you can see, Hypothesis doesn't find *many* examples here, but it finds some - enough to
keep it happy.

In general if you *can* shape your strategies better to your tests you should - for example
``integers_in_range(1, 1000)`` is a lot better than ``assume(1 <= x <= 1000)``, but assume will take
you a long way if you can't.

---------------------
Defining strategies
---------------------

The type of object that is used to explore the examples given to your test
function is called a :class:`~hypothesis.SearchStrategy`.
These are created using the functions
exposed in the :mod:`hypothesis.strategies` module.

Many of these strategies expose a variety of arguments you can use to customize
generation. For example for integers you can specify ``min`` and ``max`` values of
integers you want:

.. code:: python

  >>> from hypothesis.strategies import integers
  >>> integers()
  RandomGeometricIntStrategy() | WideRangeIntStrategy()
  >>> integers(min_value=0)
  IntegersFromStrategy(0)
  >>> integers(min_value=0, max_value=10)
  BoundedIntStrategy(0, 10)

If you want to see exactly what a strategy produces you can ask for an example:

.. code:: python

  >>> integers(min_value=0, max_value=10).example()
  7

Many strategies are build out of other strategies. For example, if you want
to define a tuple you need to say what goes in each element:

.. code:: python

  >>> from hypothesis.strategies import tuples
  >>> tuples(integers(), integers()).example()
  (-1953, 85733644253897814191482551773726674360154905303788466954)

Further details are :doc:`available in a separate document <data>`.

------------------------------------
The gory details of given parameters
------------------------------------

The :func:`@given <hypothesis.core.given>` decorator may be used
to specify what arguments of a function should
be parametrized over. You can use either positional or keyword arguments or a mixture
of the two.

For example all of the following are valid uses:

.. code:: python

  @given(integers(), integers())
  def a(x, y):
    pass

  @given(integers())
  def b(x, y):
    pass

  @given(y=integers())
  def c(x, y):
    pass

  @given(x=integers())
  def d(x, y):
    pass

  @given(x=integers(), y=integers())
  def e(x, **kwargs):
    pass

  @given(x=integers(), y=integers())
  def f(x, *args, **kwargs):
    pass


  class SomeTest(TestCase):
      @given(integers())
      def test_a_thing(self, x):
          pass

The following are not:

.. code:: python

  @given(integers(), integers(), integers())
  def g(x, y):
      pass

  @given(integers())
  def h(x, *args):
      pass

  @given(integers(), x=integers())
  def i(x, y):
      pass

  @given()
  def j(x, y):
      pass


The rules for determining what are valid uses of given are as follows:

1. You may pass any keyword argument to given.
2. Positional arguments to given are equivalent to the rightmost named
   arguments for the test function.
3. positional arguments may not be used if the underlying test function has
   varargs or arbitrary keywords.
4. Functions tested with given may not have any defaults.

The reason for the "rightmost named arguments" behaviour is so that
using :func:`@given <hypothesis.core.given>` with instance methods works: self
will be passed to the function as normal and not be parametrized over.

The function returned by given has all the arguments that the original test did
, minus the ones that are being filled in by given.

-------------------------
Custom function execution
-------------------------

Hypothesis provides you with a hook that lets you control how it runs
examples.

This lets you do things like set up and tear down around each example, run
examples in a subprocess, transform coroutine tests into normal tests, etc.

The way this works is by introducing the concept of an executor. An executor
is essentially a function that takes a block of code and run it. The default
executor is:

.. code:: python

    def default_executor(function):
        return function()

You define executors by defining a method execute_example on a class. Any
test methods on that class with :func:`@given <hypothesis.core.given>` used on them will use
``self.execute_example`` as an executor with which to run tests. For example,
the following executor runs all its code twice:


.. code:: python

    from unittest import TestCase

    class TestTryReallyHard(TestCase):
        @given(integers())
        def test_something(self, i):
            perform_some_unreliable_operation(i)

        def execute_example(self, f):
            f()
            return f()

Note: The functions you use in map, etc. will run *inside* the executor. i.e.
they will not be called until you invoke the function passed to setup\_example.

An executor must be able to handle being passed a function which returns None,
otherwise it won't be able to run normal test cases. So for example the following
executor is invalid:

.. code:: python

    from unittest import TestCase

    class TestRunTwice(TestCase):
        def execute_example(self, f):
            return f()()


and should be rewritten as:


.. code:: python

    from unittest import TestCase
    import inspect

    class TestRunTwice(TestCase):
        def execute_example(self, f):
            result = f()
            if inspect.isfunction(result):
                result = result()
            return result


Methods of a BasicStrategy however will typically be called whenever. This may
happen inside your executor or outside. This is why they have a "Warning you
have no control over the lifecycle of these values" attached.

-------------------------------
Using Hypothesis to find values
-------------------------------

You can use Hypothesis's data exploration features to find values satisfying
some predicate:

.. code:: python

  >>> from hypothesis import find
  >>> from hypothesis.strategies import sets, lists, integers
  >>> find(lists(integers()), lambda x: sum(x) >= 10)
  [10]
  >>> find(lists(integers()), lambda x: sum(x) >= 10 and len(x) >= 3)
  [0, 0, 10]
  >>> find(sets(integers()), lambda x: sum(x) >= 10 and len(x) >= 3)
  {0, 1, 9}

The first argument to :func:`~hypothesis.find` describes data in the usual way for an argument to
given, and supports :doc:`all the same data types <data>`. The second is a
predicate it must satisfy.

Of course not all conditions are satisfiable. If you ask Hypothesis for an
example to a condition that is always false it will raise an error:


.. code:: python

  >>> find(integers(), lambda x: False)
  Traceback (most recent call last):
  ...
  hypothesis.errors.NoSuchExample: No examples of condition lambda x: <unknown>
  >>> from hypothesis.strategies import booleans
  >>> find(booleans(), lambda x: False)
  Traceback (most recent call last):
  ...
  hypothesis.errors.NoSuchExample: No examples of condition lambda x: <unknown>



(The "lambda x: unknown" is because Hypothesis can't retrieve the source code
of lambdas from the interactive python console. It gives a better error message
most of the time which contains the actual condition)

The reason for the two different types of errors is that there are only a small
number of booleans, so it is feasible for Hypothesis to enumerate all of them
and simply check that your condition is never true.


.. _providing-explicit-examples:

---------------------------
Providing explicit examples
---------------------------

You can explicitly ask Hypothesis to try a particular example as follows:

.. code:: python

  from hypothesis import given, example
  from hypothesis.strategies import text

  @given(text())
  @example("Hello world")
  @example(x="Some very long string")
  def test_some_code(x):
      assert True

Hypothesis will run all examples you've asked for first. If any of them fail it
will not go on to look for more examples.

It doesn't matter whether you put the example decorator before or after given.
Any permutation of the decorators in the above will do the same thing.

Note that examples can be positional or keyword based. If they're positional then
they will be filled in from the right when calling, so things like the following
will also work:

.. code:: python

  from unittest import TestCase
  from hypothesis import given, example
  from hypothesis.strategies import text


  class TestThings(TestCase):
      @given(text())
      @example("Hello world")
      @example(x="Some very long string")
      def test_some_code(self, x):
          assert True

It is *not* permitted for a single example to be a mix of positional and
keyword arguments. Either are fine, and you can use one in one example and the
other in another example if for some reason you really want to, but a single
example must be consistent.

