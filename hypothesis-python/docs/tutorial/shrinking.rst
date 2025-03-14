Shrinking
=========

When Hypothesis finds a failure, the reported failing input is often much simpler than we might expect from random generation. For instance, here is a test which clearly fails:

.. code-block:: python

    @given(st.integers())
    def test_boundary_fails(n):
        assert n < 100

When randomly generating inputs to this function, we would expect the first failing example to be some random integer well over 100. And yet, Hypothesis will consistently tell you that this test fails with ``Falsifying example: test_boundary_fails(n=100)`` — the simplest possible failure.

The internal process that ensures this is called shrinking. When Hypothesis finds a failing example, it first runs a shrinking phase where it tries to make the example as simple as possible before reporting it to you.

You can see the initial failure found by Hypothesis by disabling the shrinking phase:

.. code-block:: python

    @given(st.integers())
    @settings(phases=set(Phase) - {Phase.shrink})
    def test_boundary_fails(n):
        assert n < 100

For me, this reports:

.. code-block:: none

    Falsifying example: test_boundary_fails(
        n=31332,
    )

But your failing example will be different.

Details to know
---------------

.. note::

    If you want to understand the full details of how shrinking works in Hypothesis, see the :doc:`shrinking explanation </explanation/shrinking>` page. You do not need to understand the details of shrinking to use it in Hypothesis.

The Hypothesis shrinker is not magic. At a high level, the shrinker works by simplifying part of the failing example, and then trying to re-run the test with the simpler example. If the test still fails, it continues simplifying from the simpler example. The shrinker stops when it can no longer make progress.

A tangible consequence of this is that Hypothesis may call your test function many times while shrinking a failure. The shrinker will only run when Hypothesis finds a failing example, so it has no effect on regular example generation. We think that trading off increased test time for more comprehensible error reports is hugely beneficial, and that the shrinker is one of the strongest parts of Hypothesis.

Shrinking adds zero overhead in the case when Hypothesis does not find a failure. However, if Hypothesis does find a failure, shrinking might add significant overhead for tests which execute costly parts of your code. If you encounter this (and are willing to live with Hypothesis reporting more complicated failing examples), you can disable shrinking using the |settings.phases| setting:

.. code-block:: python

    @given(st.integers())
    @settings(phases=set(Phase) - {Phase.shrink})
    def will_not_shrink_failures(n):
        assert n < 100
