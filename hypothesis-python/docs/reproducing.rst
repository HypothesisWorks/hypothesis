====================
Reproducing Failures
====================

One of the things that is often concerning for people using randomized testing
like Hypothesis is the question of how to reproduce failing test cases.

Fortunately Hypothesis has a number of features in support of this. The one you
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

You can explicitly ask Hypothesis to try a particular example, using

.. autofunction:: hypothesis.example

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
      assert True

  from unittest import TestCase

  class TestThings(TestCase):
      @given(text())
      @example("Hello world")
      @example(x="Some very long string")
      def test_some_code(self, x):
          assert True

As with ``@given``, it is not permitted for a single example to be a mix of
positional and keyword arguments.
Either are fine, and you can use one in one example and the other in another
example if for some reason you really want to, but a single example must be
consistent.

-------------------------------------
Reproducing a test run with ``@seed``
-------------------------------------

.. autofunction:: hypothesis.seed

When a test fails unexpectedly, usually due to a health check failure,
Hypothesis will print out a seed that led to that failure, if the test is not
already running with a fixed seed. You can then recreate that failure using either
the ``@seed`` decorator or (if you are running :pypi:`pytest`) with
``--hypothesis-seed``.

.. _reproduce_failure:

-------------------------------------------------------
Reproducing an example with with ``@reproduce_failure``
-------------------------------------------------------

Hypothesis has an opaque binary representation that it uses for all examples it
generates. This representation is not intended to be stable across versions or
with respect to changes in the test, but can be used to to reproduce failures
with the ``@reproduce_example`` decorator.

.. autofunction:: hypothesis.reproduce_failure

The intent is that you should never write this decorator by hand, but it is
instead provided by Hypothesis.
When a test fails with a falsifying example, Hypothesis may print out a
suggestion to use ``@reproduce_failure`` on the test to recreate the problem
as follows:

.. doctest::

    >>> from hypothesis import settings, given, PrintSettings
    >>> import hypothesis.strategies as st
    >>> @given(st.floats())
    ... @settings(print_blob=PrintSettings.ALWAYS)
    ... def test(f):
    ...     assert f == f
    ...
    >>> try:
    ...     test()
    ... except AssertionError:
    ...     pass
    Falsifying example: test(f=nan)
    <BLANKLINE>
    You can reproduce this example by temporarily adding @reproduce_failure(..., b'AAAA//AAAAAAAAEA') as a decorator on your test case

Adding the suggested decorator to the test should reproduce the failure (as
long as everything else is the same - changing the versions of Python or
anything else involved, might of course affect the behaviour of the test! Note
that changing the version of Hypothesis will result in a different error -
each ``@reproduce_failure`` invocation is specific to a Hypothesis version).

When to do this is controlled by the :attr:`~hypothesis.settings.print_blob`
setting, which may be one of the following values:

.. autoclass:: hypothesis.PrintSettings
  :members:
