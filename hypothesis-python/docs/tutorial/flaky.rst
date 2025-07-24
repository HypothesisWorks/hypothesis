Flaky failures
==============

Have you ever had a test fail, and then you re-run it, only for the test to magically pass? That is a *flaky test*. A flaky test is one which behaves differently when called again; you can think of it as a test which is not deterministic.

Any test can be flaky, but because Hypothesis runs your test many times, Hypothesis tests are particularly likely to discover flakiness.

Types of flakiness
------------------

When Hypothesis detects that a test is flaky, it will tell you by raising one of two |Flaky| exceptions.

Flaky failure
~~~~~~~~~~~~~

The most common form of flakiness is that Hypothesis finds a failure, but then replaying it does not reproduce that failure. For example, here is a contrived test which only fails the first time it is called:

.. code-block:: python

    called = False

    @given(st.integers())
    def test_fails_flakily(n):
        global called
        if not called:
            called = True
            assert False

The first time Hypothesis generates an input, this test will fail. But when Hypothesis tries replaying that failure—by generating the same input—the test will succeed. This test is flaky.

As a result, running ``test_fails_flakily()`` will raise |FlakyFailure|. |FlakyFailure| is an ``ExceptionGroup``, which contains the origin failure as a sub-exception:

.. code-block:: none

  + Exception Group Traceback (most recent call last):
  | hypothesis.errors.FlakyFailure: Hypothesis test_fails_flakily(n=0) produces unreliable results: Falsified on the first call but did not on a subsequent one (1 sub-exception)
  | Falsifying example: test_fails_flakily(
  |     n=0,
  | )
  | Failed to reproduce exception. Expected:
  | Traceback (most recent call last):
  |   File "/Users/tybug/Desktop/sandbox2.py", line 13, in test_fails_flakily
  |     assert False
  |            ^^^^^
  | AssertionError
  +-+---------------- 1 ----------------
    | ...
    | Traceback (most recent call last):
    |   File "/Users/tybug/Desktop/sandbox2.py", line 13, in test_fails_flakily
    |     assert False
    |            ^^^^^
    | AssertionError
    +------------------------------------

The solution to seeing |FlakyFailure| is to refactor the test to not depend on external state. In this case, the external state is the variable ``called``.

Flaky strategy
~~~~~~~~~~~~~~

A more fundamental form of flakiness is if the strategy's data generation itself is flaky (or not deterministic). Since Hypothesis relies on this to replay and shrink failures, it requires that data generation is not flaky.

One easy way for this to occur is if a strategy depends on external state. For example, this strategy generates a unique integer each iteration:

.. code-block:: python

    seen = set()

    @st.composite
    def unique_ints(draw):
        while (n := draw(st.integers())) in seen:
            seen.add(n)
        return n

    @given(unique_ints())
    def test_ints(n): ...

By using ``seen``, this test is relying on outside state! On the first iteration where |st.integers| generates ``0``, ``unique_ints`` draws only one integer. But on the next iteration where |st.integers| generates ``0``, ``unique_ints`` draws two integers. This means data generation is not deterministic between generated inputs.

As a result, running ``test_ints()`` will raise |FlakyStrategyDefinition|. The solution is to refactor the strategy to not depend on external state. (in the case of ``unique_ints``, it can simply be replaced with |st.integers|, as Hypothesis already deduplicates generated inputs across iterations).
