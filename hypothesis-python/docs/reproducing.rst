====================
Reproducing failures
====================

One of the things that is often concerning for people using randomized testing
is the question of how to reproduce failing test cases.

.. note::
    It is better to think about the data Hypothesis generates as being
    *arbitrary*, rather than *random*.  We deliberately generate any valid
    data that seems likely to cause errors, so you shouldn't rely on any
    expected distribution of or relationships between generated data.
    You can read about "swarm testing" and "coverage guided fuzzing" if
    you're interested, because you don't need to know for Hypothesis!

Fortunately Hypothesis has a number of features to support reproducing test failures. The one you
will use most commonly when developing locally is :doc:`the example database <database>`,
which means that you shouldn't have to think about the problem at all for local
use - test failures will just automatically reproduce without you having to do
anything.

The example database is perfectly suitable for sharing between machines, but
there currently aren't very good work flows for that, so Hypothesis provides a
number of ways to make examples reproducible by adding them to the source code
of your tests. This is particularly useful when e.g. you are trying to run an
example that has failed on your CI, or otherwise share them between machines.

.. _providing-explicit-examples:

---------------------------
Providing explicit examples
---------------------------

The simplest way to reproduce a failed test is to ask Hypothesis to run the
failing example it printed.  For example, if ``Falsifying example: test(n=1)``
was printed you can decorate ``test`` with ``@example(n=1)``.

``@example`` can also be used to ensure a specific example is *always* executed
as a regression test or to cover some edge case - basically combining a
Hypothesis test and a traditional parametrized test.

.. autoclass:: hypothesis.example

Hypothesis will run all examples you've asked for first. If any of them fail it
will not go on to look for more examples.

It doesn't matter whether you put the example decorator before or after given.
Any permutation of the decorators in the above will do the same thing.

Note that examples can be positional or keyword based. If they're positional then
they will be filled in from the right when calling, so either of the following
styles will work as expected:

.. code:: python

  @given(text())
  @example("Hello world")
  @example(x="Some very long string")
  def test_some_code(x):
      pass


  from unittest import TestCase


  class TestThings(TestCase):
      @given(text())
      @example("Hello world")
      @example(x="Some very long string")
      def test_some_code(self, x):
          pass

As with ``@given``, it is not permitted for a single example to be a mix of
positional and keyword arguments.
Either are fine, and you can use one in one example and the other in another
example if for some reason you really want to, but a single example must be
consistent.

.. automethod:: hypothesis.example.xfail

.. automethod:: hypothesis.example.via

.. _reproducing-with-seed:

-------------------------------------
Reproducing a test run with ``@seed``
-------------------------------------

.. autofunction:: hypothesis.seed

When a test fails unexpectedly, usually due to a health check failure,
Hypothesis will print out a seed that led to that failure, if the test is not
already running with a fixed seed. You can then recreate that failure using either
the ``@seed`` decorator or (if you are running :pypi:`pytest`) with
``--hypothesis-seed``.  For example, the following test function and
:class:`~hypothesis.stateful.RuleBasedStateMachine` will each check the
same examples each time they are executed, thanks to ``@seed()``:

.. code-block:: python

    @seed(1234)
    @given(x=...)
    def test(x): ...


    @seed(6789)
    class MyModel(RuleBasedStateMachine): ...

The seed will not be printed if you could simply use ``@example`` instead.

.. _reproduce_failure:

-------------------------------------------------------
Reproducing an example with ``@reproduce_failure``
-------------------------------------------------------

Hypothesis has an opaque binary representation that it uses for all examples it
generates. This representation is not intended to be stable across versions or
with respect to changes in the test, but can be used to to reproduce failures
with the ``@reproduce_failure`` decorator.

.. autofunction:: hypothesis.reproduce_failure

The intent is that you should never write this decorator by hand, but it is
instead provided by Hypothesis.
When a test fails with a falsifying example, Hypothesis may print out a
suggestion to use ``@reproduce_failure`` on the test to recreate the problem
as follows:

.. code-block:: pycon

    >>> from hypothesis import settings, given, PrintSettings
    >>> import hypothesis.strategies as st
    >>> @given(st.floats())
    ... @settings(print_blob=True)
    ... def test(f):
    ...     assert f == f
    ...
    >>> try:
    ...     test()
    ... except AssertionError:
    ...     pass
    ...
    Falsifying example: test(f=nan)

    You can reproduce this example by temporarily adding @reproduce_failure(..., b'AAAA//AAAAAAAAEA') as a decorator on your test case

Adding the suggested decorator to the test should reproduce the failure (as
long as everything else is the same - changing the versions of Python or
anything else involved, might of course affect the behaviour of the test! Note
that changing the version of Hypothesis will result in a different error -
each ``@reproduce_failure`` invocation is specific to a Hypothesis version).

By default these messages are not printed.
If you want to see these you must set the :attr:`~hypothesis.settings.print_blob` setting to ``True``.
