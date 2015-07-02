=============================
Details and advanced features
=============================

This is an account of slightly less common Hypothesis features that you don't need
to get started but will nevertheless make your life easier.

------------------
Making assumptions
------------------

Sometimes hypothesis doesn't give you exactly the right sort of data you want - it's
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

.. 

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

assume throws an exception which terminates the test when provided with a false argument.
It's essentially an assert, except that the exception it throws is one that Hypothesis
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

.. 

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

Adding assume(xs) to this removes the trivial empty example and gives us [0].

Adding assume(all(x > 0 for x in xs)) and it passes: A sum of a list of
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
integers_in_range(1, 1000) is a lot better than assume(1 <= x <= 1000), but assume will take
you a long way if you can't.

--------
Settings
--------

Hypothesis tries to have good defaults for its behaviour, but sometimes that's
not enough and you need to tweak it.

The mechanism for doing this is the Settings object. You can pass this to a
@given invocation as follows:

.. code:: python

    from hypothesis import given, Settings

    @given(integers(), settings=Settings(max_examples=500))
    def test_this_thoroughly(x):
        pass

This uses a Settings object which causes the test to receive a much larger
set of examples than normal.

There is a Settings.default object. This is both a Settings object you can
use, but additionally any changes to the default object will be picked up as
the defaults for newly created settings objects.

.. code:: python

    >>> from hypothesis import Settings
    >>> s = Settings()
    >>> s.max_examples
    200
    >>> Settings.default.max_examples = 100
    >>> t = Settings()
    >>> t.max_examples
    100
    >>> s.max_examples
    200

You can also override the default locally by using a settings object as a context
manager:


.. code:: python

  >>> with Settings(max_examples=150):
  ...     print(Settings().max_examples)
  ... 
  150
  >>> Settings().max_examples
  200

Note that after the block exits the default is returned to normal.

You can use this by nesting test definitions inside the context:


.. code:: python

    from hypothesis import given, Settings

    with Settings(max_examples=500):
        @given(integers())
        def test_this_thoroughly(x):
            pass

All Settings objects created or tests defined inside the block will inherit their
defaults from the settings object used as the context. You can still override them
with custom defined settings of course.

As well as max_examples there are a variety of other settings you can use.
help(Settings) in an interactive environment will give you a full list of them.


.. _verbose-output:

~~~~~~~~~~~~~~~~~~~~~~~~~~
Seeing intermediate result
~~~~~~~~~~~~~~~~~~~~~~~~~~

To see what's going on while Hypothesis runs your tests, you can turn
up the verbosity setting. This works with both find and @given.

(The following examples are somewhat manually truncated because the results
of verbose output are, well, verbose, but they should convey the idea).

.. code:: python

    >>> from hypothesis import find, Settings, Verbosity
    >>> from hypothesis.strategies import lists, booleans
    >>> find(lists(booleans()), any, settings=Settings(verbosity=Verbosity.verbose))
    Found satisfying example [True, True, ...
    Shrunk example to [False, False, False, True, ...
    Shrunk example to [False, False, True, False, False, ...
    Shrunk example to [False, True, False, True, True, ...
    Shrunk example to [True, True, True]
    Shrunk example to [True, True]
    Shrunk example to [True]
    [True]

    >>> from hypothesis import given
    >>> from hypothesis.strategies import integers()
    >>> Settings.default.verbosity = Verbosity.verbose
    >>> @given(integers())
    ... def test_foo(x):
    ...     assert x > 0
    ... 
    >>> test_foo()
    Trying example: test_foo(x=-565872324465712963891750807252490657219)
    Traceback (most recent call last):
      ...
      File "<stdin>", line 3, in test_foo
    AssertionError

    Trying example: test_foo(x=565872324465712963891750807252490657219)
    Trying example: test_foo(x=0)
    Traceback (most recent call last):
    ...
    File "<stdin>", line 3, in test_foo
    AssertionError
    Falsifying example: test_foo(x=0)
    Traceback (most recent call last):
    ...
    AssertionError


The four levels are quiet, normal, verbose and debug. normal is the default,
while in quiet Hypothesis will not print anything out, even the final
falsifying example. debug is basically verbose but a bit more so. You probably
don't want it.

You can also override the default by setting the environment variable
HYPOTHESIS_VERBOSITY_LEVEL to the name of the level you want. So e.g.
setting HYPOTHESIS_VERBOSITY_LEVEL=verbose will run all your tests printing
intermediate results and errors.

---------------------
Defining strategies
---------------------

The type of object that is used to explore the examples given to your test
function is called a SearchStrategy. These are created using the functions
exposed in the hypothesis.strategies module.

Many of these strategies expose a variety of arguments you can use to customize
generation. For example for integers you can specify min and max values of
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

The @given decorator may be used to specify what arguments of a function should
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

  @given(x=integers(), y=integers())
  def d(x, **kwargs):
    pass


  class SomeTest(TestCase):
      @given(integers())
      def test_a_thing(self, x):
          pass

The following are not:

.. code:: python

  @given(integers(), integers(), integers())
  def e(x, y):
      pass

  @given(x=integers())
  def f(x, y):
      pass

  @given()
  def f(x, y):
      pass


The rules for determining what are valid uses of given are as follows:

1. Arguments passed as keyword arguments must cover the right hand side
   of the argument list. That is, if you provide an argument as a keyword
   you must also provide everything to the right of it.
2. Positional arguments fill up from the right, starting from the first
   argument not covered by a keyword argument. (Note: Mixing keyword and
   positional arguments is supported but deprecated as its semantics are
   highly confusing and difficult to support. You'll get a warning if you
   do). 
3. If the function has variable keywords, additional arguments will be
   added corresponding to any keyword arguments passed. These will be to
   the right of the normal argument list in an arbitrary order.
4. varargs are forbidden on functions used with @given.

If you don't have kwargs then the function returned by @given will have
the same argspec (i.e. same arguments, keyword arguments, etc) as the
original but with different defaults.

The reason for the "filling up from the right" behaviour is so that
using @given with instance methods works: self will be passed to the
function as normal and not be parametrized over.


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
test methods on that class with @given used on them will use
self.execute_example as an executor with which to run tests. For example,
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

Methods of a BasicStrategy however will typically be called whenever. This may
happen inside your executor or outside. This is why they have a "Warning you
have no control over the lifecycle of these values" attached.

~~~~~~~~~~~~~~~~~~~~~
Fork before each test
~~~~~~~~~~~~~~~~~~~~~

An obstacle you can run into if you want to use Hypothesis to test native code
is that your C code segfaults, or fails a C level assertion, and it causes the
whole process to exit hard and Hypothesis just cries a little and doesn't know
what is going on, so can't minimize an example for you.

The solution to this is to run your tests in a subprocess. The process can die
as messily as it likes and Hypothesis will be sitting happily in the
controlling process unaffected by the crash. Hypothesis provides a custom
executor for this:

.. code:: python

    from hypothesis.testrunners.forking import ForkingTestCase

    class TestForking(ForkingTestCase):

        @given(integers())
        def test_handles_abnormal_exit(self, i):
            os._exit(1)

        @given(integers())
        def test_normal_exceptions_work_too(self, i):
            assert False


Exceptions that occur in the child process will be seamlessly passed back to
the parent. Abnormal exits that do not throw an exception in the child process
will be turned into an AbnormalExit exception.

There are currently some limitations to this approach:

1. Exceptions which are not pickleable will be turned into abormal exits.
2. Tracebacks from exceptions are not properly recreated in the parent process.
3. Code called in the child process will not be recorded by coverage.
4. This is only supported on platforms with os.fork. e.g. it will not work on
   Windows.

Some of these limitations should be resolvable in time.

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

The first argument to find describes data in the usual way for an argument to
given, and supports :doc:`all the same data types <data>`. The second is a
predicate it must satisfy.

Of course not all conditions are satisfiable. If you ask Hypothesis for an
example to a condition that is always false it will raise an error:


.. code:: python

  >>> find(integers(), lambda x: False)
  Traceback (most recent call last):
  ...
  hypothesis.errors.NoSuchExample: No examples of conditition lambda x: <unknown>
  >>> from hypothesis.strategies import booleans
  >>> find(booleans(), lambda x: False)
  Traceback (most recent call last):
  ...
  hypothesis.errors.DefinitelyNoSuchExample: No examples of conditition lambda x: <unknown> (all 2 considered)



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

