RELEASE_TYPE: minor

This release adds a warning for tests that set the global PRNG state, for example
by using :func:`python:random.seed` without appropriate cleanup (:issue:`1919`).
While convenient, this creates significant cross-test state and can substantially
reduce Hypothesis' chances of finding new bugs over multiple runs!

If you want deterministic Hypothesis tests - though we strongly recommend varied
generation and :doc:`reproducing` instead - you can use the
:obj:`~hypothesis.settings.derandomize` setting.  For other tests, the following
idiom may be useful in a decorator, fixture, or context manager:

.. code:: python

    state = random.getstate()
    random.seed(your_seed_here)
    try:
        yield
    finally:
        random.setstate(state)
