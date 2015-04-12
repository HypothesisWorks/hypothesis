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

  @given(float)
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
  from math import isnan

  @given(float)
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

  @given(float)
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

  @given([int])
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

  @given([int])
  def test_sum_is_positive(xs):
      assume(len(xs) > 10)
      assume(all(x > 0 for x in xs))
      print(xs)
      assert sum(xs) > 0

  In: test_sum_is_positive()
  [17, 12, 7, 13, 11, 3, 6, 9, 8, 11, 47, 27, 1, 31, 1]
  [6, 2, 29, 30, 25, 34, 19, 15, 50, 16, 10, 3, 16]
  [25, 17, 9, 19, 15, 2, 2, 4, 22, 10, 10, 27, 3, 1, 14, 17, 13, 8, 16, 9, 2, 26, 5, 18, 16, 4]
  [17, 65, 78, 1, 8, 29, 2, 79, 28, 18, 39]
  [13, 26, 8, 3, 4, 76, 6, 14, 20, 27, 21, 32, 14, 42, 9, 24, 33, 9, 5, 15, 30, 40, 58, 2, 2, 4, 40, 1, 42, 33, 22, 45, 51, 2, 8, 4, 11, 5, 35, 18, 1, 46]
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

    @given(int, settings=Settings(max_examples=500))
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
        @given(int)
        def test_this_thoroughly(x):
            pass

All Settings objects created or tests defined inside the block will inherit their
defaults from the settings object used as the context. You can still override them
with custom defined settings of course.

As well as max_examples there are a variety of other settings you can use.
help(Settings) in an interactive environment will give you a full list of them.

Settings are also extensible. You can add new settings if you want to extend
this. This is useful for adding additional parameters for customising your
strategies. These will be picked up by all settings objects.

.. code:: python

    >>> Settings.define_setting(
    ... name="some_custom_setting", default=3,
    ... description="This is a custom settings we've just added")
    >>> s.some_custom_setting
    3

---------------------------------------
SearchStrategy and converting arguments
---------------------------------------

The type of object that is used to explore the examples given to your test
function is called a SearchStrategy. The arguments to @given are passed to
the function *strategy*. This is used to convert arbitrary objects to
a SearchStrategy.

From most usage, strategy looks like a normal function:

.. code:: python

  >>> from hypothesis import strategy

  >>> strategy(int)
  RandomGeometricIntStrategy()

  >>> strategy((int, int))
  TupleStrategy((RandomGeometricIntStrategy(), RandomGeometricIntStrategy()), tuple) 

If you try to call it on something with no implementation defined you will
get a NotImplementedError:


.. code:: python

  >>> strategy(1)
  NotImplementedError: No implementation available for 1

Although we have a strategy for producing ints it doesn't make sense to convert
an *individual* int into a strategy.

Conversely there's no implementation for the type "tuple" because we need to know
the shape of the tuple and what sort of elements to put in it:

.. code:: python

  In[5]: strategy(tuple)
  NotImplementedError: No implementation available for <class 'tuple'>


The general idea is that arguments to strategy should "look like types" and
should generate things that are instances of that type. With collections and
similar you also need to specify the types of the elements. So e.g. the
strategy you get for (int, int, int) is a strategy for generating triples
of ints.

If you want to see the sort of data that a strategy produces you can ask it
for an example:

.. code:: python

  >>> strategy(int).example()
  192
 
  >>> strategy(str).example()
  '\U0009d5dc\U000989fc\U00106f82\U00033731'

  >>> strategy(float).example()
  -1.7551092389086e-308

  >>> strategy((int, int)).example()
  (548, 12)

Note: example is just a method that's available for this sort of interactive debugging.
It's not actually part of the process that Hypothesis uses to feed tests, though
it is of course built on the same basic mechanisms.


strategy can also accept a settings object which will customise the SearchStrategy
returned:

.. code:: python

    >>> strategy([[int]], Settings(average_list_length=0.5)).example()
    [[], [0]]

 
You can also generate lists (like tuples you generate lists from a list describing
what should be in the list rather than from the type):

.. code:: python

  >>> strategy([int]).example()
  [0, 0, -1, 0, -1, -2]


Details of what exactly you can generate are :doc:`available in a separate document <data>`.

------------------------------------
The gory details of given parameters
------------------------------------

The @given decorator may be used to specify what arguments of a function should
be parametrized over. You can use either positional or keyword arguments or a mixture
of the two.

For example all of the following are valid uses:

.. code:: python

  @given(int, int)
  def a(x, y):
    pass

  @given(int, y=int)
  def b(x, y):
    pass

  @given(int)
  def c(x, y):
    pass

  @given(y=int)
  def d(x, y):
    pass

  @given(x=int, y=int)
  def e(x, **kwargs):
    pass


  class SomeTest(TestCase):
      @given(int)
      def test_a_thing(self, x):
          pass

The following are not:

.. code:: python

  @given(int, int, int)
  def e(x, y):
      pass

  @given(x=int)
  def f(x, y):
      pass

  @given()
  def f(x, y):
      pass


The rules for determining what are valid uses of given are as follows:

1. Arguments passed as keyword arguments must cover the right hand side of the argument list.
2. Positional arguments fill up from the right, starting from the first argument not covered by a keyword argument.
3. If the function has kwargs, additional arguments will be added corresponding to any keyword arguments passed. These will be to the right of the normal argument list in an arbitrary order.
4. varargs are forbidden on functions used with @given.

If you don't have kwargs then the function returned by @given will have the same argspec (i.e. same arguments, keyword arguments, etc) as the original but with different defaults.

The reason for the "filling up from the right" behaviour is so that using @given with instance methods works: self will be passed to the function as normal and not be parametrized over.

If all this seems really confusing, my recommendation is to just not mix positional and keyword arguments. It will probably make your life easier.

-----------------------------------
Extending Hypothesis with new types
-----------------------------------

You can build new strategies out of other strategies. For example:

.. code:: python

  >>> s = strategy(int).map(Decimal)
  >>> s.example()
  Decimal('6029418')

map takes a function which takes a value produced by the original strategy and
returns a new value. It returns a strategy whose values are values from the
original strategy with that function applied to them, so here we have a strategy
which produces Decimals by first generating an int and then calling Decimal on
that int.

This is generally the encouraged way to define your own strategies: The details of how SearchStrategy
works are not currently considered part of the public API and may be liable to change.

If you want to register this so that strategy works for your custom types you
can do this by extending the strategy method:

.. code:: python

  >>> @strategy.extend_static(Decimal)
  ... def decimal_strategy(d, settings):
  ...   return strategy(int, settings).map(Decimal)
  >>> strategy(Decimal).example()
  Decimal('13')

You can also define types for your own custom data generation if you need something
more specific. For example here is a strategy that lets you specify the exact length
of list you want:

.. code:: python

  >>> from collections import namedtuple
  >>> ListsOfFixedLength = namedtuple('ListsOfFixedLength', ('length', 'elements'))
  >>> @strategy.extend(ListsOfFixedLength)
  ... def fixed_length_lists_strategy(specifier, settings):
  ...     return strategy((specifier.elements,) * specifier.length, settings).map(
  ...        pack=list)
  ... 
  >>> strategy(ListsOfFixedLength(5, int)).example()
  [0, 2190, 899, 2, -1326]

(You don't have to use namedtuple for this, but I tend to because they're
convenient)

Hypothesis also provides a standard test suite you can use for testing strategies
you've defined.


.. code:: python

  from hypothesis.strategytests import strategy_test_suite
  TestDecimal = strategy_test_suite(Decimal)

TestDecimal is a TestCase class (from unittest) that will run a bunch of tests against the
strategy you've provided for Decimal to make sure it works correctly.

~~~~~~~~~~~~~~~~~~~~~
Extending a function?
~~~~~~~~~~~~~~~~~~~~~

The way this works is that Hypothesis has something that looks suspiciously
like its own object system, called ExtMethod.

It mirrors the Python object system as closely as possible and has the
same method resolution order, but allows for methods that are defined externally
to the class that uses them. This allows extensibly doing different things
based on the type of an argument without worrying about the namespacing problems
caused by MonkeyPatching.

strategy is the main ExtMethod you are likely to interact with directly, but
there are a number of others that Hypothesis uses under the hood.


-------------------------
Custom function execution
-------------------------

Hypothesis provides you with a hook that lets you control how it runs examples.

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
        @given(int)
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

        @given(int)
        def test_handles_abnormal_exit(self, i):
            os._exit(1)

        @given(int)
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
