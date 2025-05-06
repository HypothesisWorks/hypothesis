How many times will Hypothesis run my test?
===========================================

This is a trickier question than you might expect. The short answer is "exactly |max_examples| times", with the following exceptions:

- Less than |max_examples| times, if Hypothesis exhausts the search space early.
- More than |max_examples| times, if Hypothesis retries some examples because either:

  - They failed an |assume| or |.filter| condition, or
  - They were too large to continue generating.

- Either less or more than |max_examples| times, if Hypothesis finds a failing example.

Read on for details.

Search space exhaustion
-----------------------

If Hypothesis detects that there are no more examples left to try, it may stop generating examples before it hits |max_examples|. For example:

.. code-block:: python

    from hypothesis import given, strategies as st

    calls = 0

    @given(st.integers(0, 19))
    def test_function(n):
        global calls
        calls += 1

    test_function()
    assert calls == 20

This runs ``test_function`` 20 times, not 100, since there are only 20 unique integers to try.

The search space tracking in Hypothesis is good, but not perfect. We treat this more as a bonus than something to strive for.

.. TODO_DOCS

.. .. note::

..     Search space tracking uses the :doc:`choice sequence <choice-sequence>` to determine uniqueness of inputs.

|assume| and |.filter|
----------------------

If an example fails to satisfy an |assume| or |.filter| condition, Hypothesis will retry generating that example and will not count it towards the |max_examples| limit. For instance:

.. code-block:: python

    from hypothesis import assume, given, strategies as st

    @given(st.integers())
    def test_function(n):
        assume(n % 2 == 0)

will run roughly 200 times, since half of the examples are discarded from the |assume|.

Note that while failing an |assume| triggers an immediate retry of the entire example, Hypothesis will try several times in the same example to satisfy a |.filter| condition. This makes expressing the same condition using |.filter| more efficient than |assume|.

Also note that even if your code does not explicitly use |assume| or |.filter|, a builtin strategy may still use them and cause retries. We try to directly satisfy conditions where possible instead of relying on rejection sampling, so this should be relatively uncommon.

Examples which are too large
----------------------------

For performance reasons, Hypothesis places an internal limit on the size of a single example. If an example exceeds this size limit, we will retry generating it and will not count it towards the |max_examples| limit. (And if we see too many of these large examples, we will raise |HealthCheck.data_too_large|, unless suppressed with |settings.suppress_health_check|).

The specific value of the size limit is an undocumented implementation detail. The majority of Hypothesis tests do not come close to hitting it.

Failing examples
----------------

If Hypothesis finds a failing example, it stops generation early, and may call the test function additional times during the |Phase.shrink| and |Phase.explain| phases. Sometimes, Hypothesis determines that the initial failing example was already as simple as possible, in which case |Phase.shrink| will not result in additional test executions (but |Phase.explain| might).

Regardless of whether Hypothesis runs the test during the shrinking and explain phases, it will always run the minimal failing example one additional time to check for flakiness. For instance, the following trivial test runs with ``n=0`` *twice*, even though it only uses the |Phase.generate| phase:

.. code-block:: python

    from hypothesis import Phase, given, settings, strategies as st

    @given(st.integers())
    @settings(phases=[Phase.generate])
    def test_function(n):
        print(f"called with {n}")
        assert n != 0

    test_function()

The first execution finds the initial failure with ``n=0``, and the second execution replays ``n=0`` to ensure the failure is not flaky.
