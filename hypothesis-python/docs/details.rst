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

Sometimes this isn't enough, either because you have a value with a
``__repr__()`` method that isn't very descriptive or because you need to see the output of some
intermediate steps of your test. That's where the ``note`` function comes in:

.. autofunction:: hypothesis.note

.. code-block:: pycon

    >>> from hypothesis import given, note, strategies as st
    >>> @given(st.lists(st.integers()), st.randoms())
    ... def test_shuffle_is_noop(ls, r):
    ...     ls2 = list(ls)
    ...     r.shuffle(ls2)
    ...     note(f"Shuffle: {ls2!r}")
    ...     assert ls == ls2
    ...
    >>> try:
    ...     test_shuffle_is_noop()
    ... except AssertionError:
    ...     print("ls != ls2")
    ...
    Falsifying example: test_shuffle_is_noop(ls=[0, 1], r=RandomWithSeed(1))
    Shuffle: [1, 0]
    ls != ls2

The note is printed for the minimal failing example of the test in order to include any
additional information you might need in your test.


.. _statistics:

---------------
Test statistics
---------------

If you are using :pypi:`pytest` you can see a number of statistics about the executed tests
by passing the command line argument ``--hypothesis-show-statistics``. This will include
some general statistics about the test:

For example if you ran the following with ``--hypothesis-show-statistics``:

.. code-block:: python

  from hypothesis import given, strategies as st


  @given(st.integers())
  def test_integers(i):
      pass


You would see:

.. code-block:: none

    - during generate phase (0.06 seconds):
        - Typical runtimes: < 1ms, ~ 47% in data generation
        - 100 passing examples, 0 failing examples, 0 invalid examples
    - Stopped because settings.max_examples=100

The final "Stopped because" line is particularly important to note: It tells you the
setting value that determined when the test should stop trying new examples. This
can be useful for understanding the behaviour of your tests. Ideally you'd always want
this to be :obj:`~hypothesis.settings.max_examples`.

In some cases (such as filtered and recursive strategies) you will see events mentioned
which describe some aspect of the data generation:

.. code-block:: python

  from hypothesis import given, strategies as st


  @given(st.integers().filter(lambda x: x % 2 == 0))
  def test_even_integers(i):
      pass

You would see something like:

.. code-block:: none

  test_even_integers:

    - during generate phase (0.08 seconds):
        - Typical runtimes: < 1ms, ~ 57% in data generation
        - 100 passing examples, 0 failing examples, 12 invalid examples
        - Events:
          * 51.79%, Retried draw from integers().filter(lambda x: x % 2 == 0) to satisfy filter
          * 10.71%, Aborted test because unable to satisfy integers().filter(lambda x: x % 2 == 0)
    - Stopped because settings.max_examples=100

You can also mark custom events in a test using the ``event`` function:

.. autofunction:: hypothesis.event

.. code:: python

  from hypothesis import event, given, strategies as st


  @given(st.integers().filter(lambda x: x % 2 == 0))
  def test_even_integers(i):
      event(f"i mod 3 = {i%3}")


You will then see output like:

.. code-block:: none

  test_even_integers:

    - during generate phase (0.09 seconds):
        - Typical runtimes: < 1ms, ~ 59% in data generation
        - 100 passing examples, 0 failing examples, 32 invalid examples
        - Events:
          * 54.55%, Retried draw from integers().filter(lambda x: x % 2 == 0) to satisfy filter
          * 31.06%, i mod 3 = 2
          * 28.79%, i mod 3 = 0
          * 24.24%, Aborted test because unable to satisfy integers().filter(lambda x: x % 2 == 0)
          * 15.91%, i mod 3 = 1
    - Stopped because settings.max_examples=100

Arguments to ``event`` can be any hashable type, but two events will be considered the same
if they are the same when converted to a string with :obj:`python:str`.

------------------
Making assumptions
------------------

Sometimes Hypothesis doesn't give you exactly the right sort of data you want - it's
mostly of the right shape, but some examples won't work and you don't want to care about
them. You *can* just ignore these by aborting the test early, but this runs the risk of
accidentally testing a lot less than you think you are. Also it would be nice to spend
less time on bad examples - if you're running 100 examples per test (the default) and
it turns out 70 of those examples don't match your needs, that's a lot of wasted time.

.. autofunction:: hypothesis.assume

For example suppose you had the following test:


.. code:: python

  @given(floats())
  def test_negation_is_self_inverse(x):
      assert x == -(-x)


Running this gives us:

.. code::

  Falsifying example: test_negation_is_self_inverse(x=float('nan'))
  AssertionError

This is annoying. We know about `NaN <https://docs.python.org/3/library/math.html>`__
and don't really care about it, but as soon as Hypothesis
finds a NaN example it will get distracted by that and tell us about it. Also
the test will fail and we want it to pass.

So let's block off this particular example:

.. code:: python

  from math import isnan


  @given(floats())
  def test_negation_is_self_inverse_for_non_nan(x):
      assume(not isnan(x))
      assert x == -(-x)

And this passes without a problem.

In order to avoid the easy trap where you assume a lot more than you intended, Hypothesis
will fail a test when it can't find enough examples passing the assumption.

If we'd written:

.. code:: python

  @given(floats())
  def test_negation_is_self_inverse_for_non_nan(x):
      assume(False)
      assert x == -(-x)

Then on running we'd have got the exception:

.. code::

  Unsatisfiable: Unable to satisfy assumptions of hypothesis test_negation_is_self_inverse_for_non_nan. Only 0 examples considered satisfied assumptions

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

Unsurprisingly this fails and gives the falsifying example ``[]``.

Adding ``assume(xs)`` to this removes the trivial empty example and gives us ``[0]``.

Adding ``assume(all(x > 0 for x in xs))`` and it passes: the sum of a list of
positive integers is positive.

The reason that this should be surprising is not that it doesn't find a
counter-example, but that it finds enough examples at all.

In general if you *can* shape your strategies better to your tests you should - for example
:py:func:`integers(1, 1000) <hypothesis.strategies.integers>` is a lot better than
``assume(1 <= x <= 1000)``, but ``assume`` will take you a long way if you can't.

---------------------
Defining strategies
---------------------

The type of object that is used to explore the examples given to your test
function is called a :class:`~hypothesis.strategies.SearchStrategy`.
These are created using the functions
exposed in the :mod:`hypothesis.strategies` module.

Many of these strategies expose a variety of arguments you can use to customize
generation. For example for integers you can specify ``min`` and ``max`` values of
integers you want.
If you want to see exactly what a strategy produces you can ask for an example:

.. code-block:: pycon

    >>> integers(min_value=0, max_value=10).example()
    1

Many strategies are built out of other strategies. For example, if you want
to define a tuple you need to say what goes in each element:

.. code-block:: pycon

    >>> from hypothesis.strategies import tuples
    >>> tuples(integers(), integers()).example()
    (-24597, 12566)

Further details are :doc:`available in a separate document <data>`.

------------------------------------
The gory details of given parameters
------------------------------------

.. autofunction:: hypothesis.given

The :func:`@given <hypothesis.given>` decorator may be used to specify
which arguments of a function should be parametrized over. You can use
either positional or keyword arguments, but not a mixture of both.

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


The rules for determining what are valid uses of ``given`` are as follows:

1. You may pass any keyword argument to ``given``.
2. Positional arguments to ``given`` are equivalent to the rightmost named
   arguments for the test function.
3. Positional arguments may not be used if the underlying test function has
   varargs, arbitrary keywords, or keyword-only arguments.
4. Functions tested with ``given`` may not have any defaults.

The reason for the "rightmost named arguments" behaviour is so that
using :func:`@given <hypothesis.given>` with instance methods works: ``self``
will be passed to the function as normal and not be parametrized over.

The function returned by given has all the same arguments as the original
test, minus those that are filled in by :func:`@given <hypothesis.given>`.
Check :ref:`the notes on framework compatibility <framework-compatibility>`
to see how this affects other testing libraries you may be using.


.. _targeted-search:

---------------------------
Targeted example generation
---------------------------

Targeted property-based testing combines the advantages of both search-based
and property-based testing.  Instead of being completely random, T-PBT uses
a search-based component to guide the input generation towards values that
have a higher probability of falsifying a property.  This explores the input
space more effectively and requires fewer tests to find a bug or achieve a
high confidence in the system being tested than random PBT.
(`Löscher and Sagonas <http://proper.softlab.ntua.gr/Publications.html>`__)

This is not *always* a good idea - for example calculating the search metric
might take time better spent running more uniformly-random test cases, or your
target metric might accidentally lead Hypothesis *away* from bugs - but if
there is a natural metric like "floating-point error", "load factor" or
"queue length", we encourage you to experiment with targeted testing.

.. autofunction:: hypothesis.target

.. code-block:: python

  from hypothesis import given, strategies as st, target


  @given(st.floats(0, 1e100), st.floats(0, 1e100), st.floats(0, 1e100))
  def test_associativity_with_target(a, b, c):
      ab_c = (a + b) + c
      a_bc = a + (b + c)
      difference = abs(ab_c - a_bc)
      target(difference)  # Without this, the test almost always passes
      assert difference < 2.0

We recommend that users also skim the papers introducing targeted PBT;
from `ISSTA 2017 <http://proper.softlab.ntua.gr/papers/issta2017.pdf>`__
and `ICST 2018 <http://proper.softlab.ntua.gr/papers/icst2018.pdf>`__.
For the curious, the initial implementation in Hypothesis uses hill-climbing
search via a mutating fuzzer, with some tactics inspired by simulated
annealing to avoid getting stuck and endlessly mutating a local maximum.


.. _custom-function-execution:

-------------------------
Custom function execution
-------------------------

Hypothesis provides you with a hook that lets you control how it runs
examples.

This lets you do things like set up and tear down around each example, run
examples in a subprocess, transform coroutine tests into normal tests, etc.
For example, :class:`~hypothesis.extra.django.TransactionTestCase` in the
Django extra runs each example in a separate database transaction.

The way this works is by introducing the concept of an executor. An executor
is essentially a function that takes a block of code and run it. The default
executor is:

.. code:: python

    def default_executor(function):
        return function()

You define executors by defining a method ``execute_example`` on a class. Any
test methods on that class with :func:`@given <hypothesis.given>` used on them will use
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
they will not be called until you invoke the function passed to ``execute_example``.

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


    class TestRunTwice(TestCase):
        def execute_example(self, f):
            result = f()
            if callable(result):
                result = result()
            return result


An alternative hook is provided for use by test runner extensions such as
:pypi:`pytest-trio`, which cannot use the ``execute_example`` method.
This is **not** recommended for end-users - it is better to write a complete
test function directly, perhaps by using a decorator to perform the same
transformation before applying :func:`@given <hypothesis.given>`.

.. code:: python

    @given(x=integers())
    @pytest.mark.trio
    async def test(x): ...


    # Illustrative code, inside the pytest-trio plugin
    test.hypothesis.inner_test = lambda x: trio.run(test, x)

For authors of test runners however, assigning to the ``inner_test`` attribute
of the ``hypothesis`` attribute of the test will replace the interior test.

.. note::
    The new ``inner_test`` must accept and pass through all the ``*args``
    and ``**kwargs`` expected by the original test.

If the end user has also specified a custom executor using the
``execute_example`` method, it - and all other execution-time logic - will
be applied to the *new* inner test assigned by the test runner.


--------------------------------
Making random code deterministic
--------------------------------

While Hypothesis' example generation can be used for nondeterministic tests,
debugging anything nondeterministic is usually a very frustrating exercise.
To make things worse, our example *shrinking* relies on the same input
causing the same failure each time - though we show the un-shrunk failure
and a decent error message if it doesn't.

By default, Hypothesis will handle the global ``random`` and ``numpy.random``
random number generators for you, and you can register others:

.. autofunction:: hypothesis.register_random


.. _type-inference:

-------------------
Inferred strategies
-------------------

In some cases, Hypothesis can work out what to do when you omit arguments.
This is based on introspection, *not* magic, and therefore has well-defined
limits.

:func:`~hypothesis.strategies.builds` will check the signature of the
``target`` (using :func:`~python:inspect.signature`).
If there are required arguments with type annotations and
no strategy was passed to :func:`~hypothesis.strategies.builds`,
:func:`~hypothesis.strategies.from_type` is used to fill them in.
You can also pass the value ``...`` (``Ellipsis``) as a keyword
argument, to force this inference for arguments with a default value.

.. code-block:: pycon

    >>> def func(a: int, b: str):
    ...     return [a, b]
    ...
    >>> builds(func).example()
    [-6993, '']

.. data:: hypothesis.infer

:func:`@given <hypothesis.given>` does not perform any implicit inference
for required arguments, as this would break compatibility with pytest fixtures.
``...`` (:obj:`python:Ellipsis`), can be used as a keyword argument to explicitly fill
in an argument from its type annotation.  You can also use the ``hypothesis.infer``
alias if writing a literal ``...`` seems too weird.

.. code:: python

    @given(a=...)  # or @given(a=infer)
    def test(a: int):
        pass


    # is equivalent to
    @given(a=from_type(int))
    def test(a):
        pass


``@given(...)`` can also be specified to fill all arguments from their type annotations.

.. code:: python

    @given(...)
    def test(a: int, b: str):
        pass


    # is equivalent to
    @given(a=..., b=...)
    def test(a, b):
        pass


~~~~~~~~~~~
Limitations
~~~~~~~~~~~

Hypothesis does not inspect :pep:`484` type comments at runtime.  While
:func:`~hypothesis.strategies.from_type` will work as usual, inference in
:func:`~hypothesis.strategies.builds` and :func:`@given <hypothesis.given>`
will only work if you manually create the ``__annotations__`` attribute
(e.g. by using ``@annotations(...)`` and ``@returns(...)`` decorators).

The :mod:`python:typing` module changes between different Python releases,
including at minor versions.  These
are all supported on a best-effort basis,
but you may encounter problems.  Please report them to us, and consider
updating to a newer version of Python as a workaround.


.. _our-type-hints:

------------------------------
Type annotations in Hypothesis
------------------------------

If you install Hypothesis and use :pypi:`mypy` 0.590+, or another
:PEP:`561`-compatible tool, the type checker should automatically pick
up our type hints.

.. note::
    Hypothesis' type hints may make breaking changes between minor releases.

    Upstream tools and conventions about type hints remain in flux - for
    example the :mod:`python:typing` module itself is provisional - and we plan to support the latest
    version of this ecosystem, as well as older versions where practical.

    We may also find more precise ways to describe the type of various
    interfaces, or change their type and runtime behaviour together in a way
    which is otherwise backwards-compatible.  We often omit type hints for
    deprecated features or arguments, as an additional form of warning.

There are known issues inferring the type of examples generated by
:func:`~hypothesis.strategies.deferred`, :func:`~hypothesis.strategies.recursive`,
:func:`~hypothesis.strategies.one_of`, :func:`~hypothesis.strategies.dictionaries`,
and :func:`~hypothesis.strategies.fixed_dictionaries`.
We will fix these, and require correspondingly newer versions of Mypy for type
hinting, as the ecosystem improves.

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Writing downstream type hints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Projects that :doc:`provide Hypothesis strategies <strategies>` and use
type hints may wish to annotate their strategies too.  This *is* a
supported use-case, again on a best-effort provisional basis.  For example:

.. code:: python

    def foo_strategy() -> SearchStrategy[Foo]: ...

.. class:: hypothesis.strategies.SearchStrategy

:class:`~hypothesis.strategies.SearchStrategy` is the type of all strategy
objects.  It is a generic type, and covariant in the type of the examples
it creates.  For example:

- ``integers()`` is of type ``SearchStrategy[int]``.
- ``lists(integers())`` is of type ``SearchStrategy[List[int]]``.
- ``SearchStrategy[Dog]`` is a subtype of ``SearchStrategy[Animal]``
  if ``Dog`` is a subtype of ``Animal`` (as seems likely).

.. warning::
    :class:`~hypothesis.strategies.SearchStrategy` **should only be used
    in type hints.**  Please do not inherit from, compare to, or otherwise
    use it in any way outside of type hints.  The only supported way to
    construct objects of this type is to use the functions provided by the
    :mod:`hypothesis.strategies` module!


.. _pytest-plugin:

----------------------------
The Hypothesis pytest plugin
----------------------------

Hypothesis includes a tiny plugin to improve integration with :pypi:`pytest`,
which is activated by default (but does not affect other test runners).
It aims to improve the integration between Hypothesis and Pytest by
providing extra information and convenient access to config options.

- ``pytest --hypothesis-show-statistics`` can be used to
  :ref:`display test and data generation statistics <statistics>`.
- ``pytest --hypothesis-profile=<profile name>`` can be used to
  :ref:`load a settings profile <settings_profiles>`.
- ``pytest --hypothesis-verbosity=<level name>`` can be used to
  :ref:`override the current verbosity level <verbose-output>`.
- ``pytest --hypothesis-seed=<an int>`` can be used to
  :ref:`reproduce a failure with a particular seed <reproducing-with-seed>`.
- ``pytest --hypothesis-explain`` can be used to
  :ref:`temporarily enable the explain phase <phases>`.

Finally, all tests that are defined with Hypothesis automatically have
``@pytest.mark.hypothesis`` applied to them.  See :ref:`here for information
on working with markers <pytest:mark examples>`.

.. note::
    Pytest will load the plugin automatically if Hypothesis is installed.
    You don't need to do anything at all to use it.

    If it causes problems, you can avoid loading the plugin with the
    ``-p no:hypothesispytest`` option.


.. _fuzz_one_input:

-------------------------
Use with external fuzzers
-------------------------

.. tip::

    | Want an integrated workflow for your team's local tests, CI, and continuous fuzzing?
    | Use `HypoFuzz <https://hypofuzz.com/>`__ to fuzz your whole test suite,
      and find more bugs without more tests!

Sometimes, you might want to point a traditional fuzzer such as
`python-afl <https://github.com/jwilk/python-afl>`__, :pypi:`pythonfuzz`,
or Google's :pypi:`atheris` (for Python *and* native extensions)
at your code. Wouldn't it be nice if you could use any of your
:func:`@given <hypothesis.given>` tests as fuzz targets, instead of
converting bytestrings into your objects by hand?

.. code:: python

    @given(st.text())
    def test_foo(s): ...


    # This is a traditional fuzz target - call it with a bytestring,
    # or a binary IO object, and it runs the test once.
    fuzz_target = test_foo.hypothesis.fuzz_one_input

    # For example:
    fuzz_target(b"\x00\x00\x00\x00\x00\x00\x00\x00")
    fuzz_target(io.BytesIO(...))

Depending on the input to ``fuzz_one_input``, one of three things will happen:

- If the bytestring was invalid, for example because it was too short or
  failed a filter or :func:`~hypothesis.assume` too many times,
  ``fuzz_one_input`` returns ``None``.

- If the bytestring was valid and the test passed, ``fuzz_one_input`` returns
  a canonicalised and pruned buffer which will replay that test case.  This
  is provided as an option to improve the performance of mutating fuzzers,
  but can safely be ignored.

- If the test *failed*, i.e. raised an exception, ``fuzz_one_input`` will add
  the pruned buffer to :doc:`the Hypothesis example database <database>`
  and then re-raise that exception.  All you need to do to reproduce, minimize,
  and de-duplicate all the failures found via fuzzing is run your test suite!

Note that the interpretation of both input and output bytestrings is specific
to the exact version of Hypothesis you are using and the strategies given to
the test, just like the :doc:`example database <database>` and
:func:`@reproduce_failure <hypothesis.reproduce_failure>` decorator.

.. tip::

  For usages of ``fuzz_one_input`` which expect to discover many failures, consider
  wrapping your database with :class:`~hypothesis.database.BackgroundWriteDatabase`
  for low-overhead writes of failures.

~~~~~~~~~~~~~~~~~~~~~~~~~
Interaction with settings
~~~~~~~~~~~~~~~~~~~~~~~~~

``fuzz_one_input`` uses just enough of Hypothesis' internals to drive your
test function with a fuzzer-provided bytestring, and most settings therefore
have no effect in this mode.  We recommend running your tests the usual way
before fuzzing to get the benefits of healthchecks, as well as afterwards to
replay, shrink, deduplicate, and report whatever errors were discovered.

- The :obj:`~hypothesis.settings.database` setting *is* used by fuzzing mode -
  adding failures to the database to be replayed when you next run your tests
  is our preferred reporting mechanism and response to
  `the 'fuzzer taming' problem <https://blog.regehr.org/archives/925>`__.
- The :obj:`~hypothesis.settings.verbosity` and
  :obj:`~hypothesis.settings.stateful_step_count` settings work as usual.

The ``deadline``, ``derandomize``, ``max_examples``, ``phases``, ``print_blob``,
``report_multiple_bugs``, and ``suppress_health_check`` settings do not affect
fuzzing mode.


--------------------
Thread-Safety Policy
--------------------

As discussed in :issue:`2719`, Hypothesis is not truly thread-safe and that's
unlikely to change in the future.  This policy therefore describes what you
*can* expect if you use Hypothesis with multiple threads.

**Running tests in multiple processes**, e.g. with ``pytest -n auto``, is fully
supported and we test this regularly in CI - thanks to process isolation, we only
need to ensure that :class:`~hypothesis.database.DirectoryBasedExampleDatabase`
can't tread on its own toes too badly.  If you find a bug here we will fix it ASAP.

**Running separate tests in multiple threads** is not something we design or test
for, and is not formally supported.  That said, anecdotally it does mostly work and
we would like it to keep working - we accept reasonable patches and low-priority
bug reports.  The main risks here are global state, shared caches, and cached strategies.

**Using multiple threads within a single test** , or running a single test simultaneously
in multiple threads, makes it pretty easy to trigger internal errors.  We usually accept
patches for such issues unless readability or single-thread performance suffer.

Hypothesis assumes that tests are single-threaded, or do a sufficiently-good job of
pretending to be single-threaded.  Tests that use helper threads internally should be OK,
but the user must be careful to ensure that test outcomes are still deterministic.
In particular it counts as nondeterministic if helper-thread timing changes the sequence
of dynamic draws using e.g. the :func:`~hypothesis.strategies.data`.

Interacting with any Hypothesis APIs from helper threads might do weird/bad things,
so avoid that too - we rely on thread-local variables in a few places, and haven't
explicitly tested/audited how they respond to cross-thread API calls.  While
:func:`~hypothesis.strategies.data` and equivalents are the most obvious danger,
other APIs might also be subtly affected.
