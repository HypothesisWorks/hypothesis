Flaky failures
==============

Have you ever had a test fail, and then you re-run it, only for the test to magically pass? That is a *flaky test*. A flaky test is one which might behave differently when called again. You can think of it as a test which is not deterministic.

Any test can be flaky, but because Hypothesis runs your test many times, Hypothesis tests are particularly likely to uncover flaky behavior.

Note that Hypothesis does not require tests to be fully deterministic. Only the sequence of calls to Hypothesis APIs like ``draw`` from |st.composite| and the outcome of the test (pass or fail) need to be deterministic. This means you can use randomness, threads, or nondeterminism in your test, as long as it doesn't impact anything Hypothesis can see.

Why is flakiness bad?
---------------------

Hypothesis raises an exception when it detects flakiness. This might seem extreme, relative to a simple warning. But there are good reasons to consider flakiness a fatal error.

.. TODO_DOCS: link to not-yet-written database page

* Hypothesis relies on deterministic behavior for the database to work.
* Flakiness makes debugging failures substantially harder if the failing input reported by Hypothesis only flakily reproduces.
* Flakiness makes effectively exploration of the test's behavior space by Hypothesis difficult or impossible.

Common sources of flakiness
---------------------------

Here is a quick and non-exhaustive enumeration of some reasons you might encounter flakiness:

* Decisions based on global state.
* Explicit dependencies between inputs.
* Test depends on filesystem or database state which isn't reset between inputs.
* Un-managed sources of randomness. This includes standard PRNGs (see also |register_random|), but also thread scheduling, network timing, etc.

.. note::

    If your tests depend on global state, consider replacing that state with |st.shared|. This is a common way to refactor your test to bring conceptually-global state under the control and visibility of Hypothesis.

Types of flakiness
------------------

When Hypothesis detects that a test is flaky, it will raise one of two |Flaky| exceptions.

Flaky failure
~~~~~~~~~~~~~

The most common form of flakiness is that Hypothesis finds a failure, but then replaying that input does not reproduce the failure. For example, here is a contrived test which only fails the first time it is called:

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

Flaky strategy definition
~~~~~~~~~~~~~~~~~~~~~~~~~

Each strategy must 'do the same thing' (again, as seen by Hypothesis) if we replay a previously-seen input.  Failing to do so is a more subtle but equally serious form of flakiness, which leaves us unable to shrink to a minimal failing input, or even reliably report the failure in future runs.

One easy way for this to occur is if a strategy depends on external state. For example, this strategy filters out previously-generated integers, including those seen in any previous test case:

.. code-block:: python

    seen = set()

    @st.composite
    def unique_ints(draw):
        while (n := draw(st.integers())) in seen:
            pass
        seen.add(n)
        return n

    @given(unique_ints(), unique_ints())
    def test_ints(x, y): ...

By using ``seen``, this test is relying on outside state! In the first test case where |st.integers| generates ``0``, ``unique_ints`` draws only one integer. But if in the next test case |st.integers| generates ``0``, ``unique_ints`` has to draw two integers because ``0`` is already in ``seen``. This means data generation is not deterministic.

As a result, running ``test_ints()`` will raise |FlakyStrategyDefinition|. The solution is to refactor the strategy to not depend on external state. One way to do this is using |st.shared|:

.. code-block:: python

    @st.composite
    def unique_ints(draw):
        seen_this_test = draw(st.shared(st.builds(set), key="seen_ints"))
        while (n := draw(st.integers())) in seen_this_test:
            pass
        seen_this_test.add(n)
        return n
