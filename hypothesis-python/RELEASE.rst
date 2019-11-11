RELEASE_TYPE: patch

This patch fixes :issue:`2108`, where the first test using
:func:`~hypothesis.strategies.data` to draw from :func:`~hypothesis.strategies.characters`
or :func:`~hypothesis.strategies.text` would be flaky due to unreliable test timings.

Time taken by lazy instantiation of strategies is now counted towards drawing from
the strategy, rather than towards the deadline for the test function.
