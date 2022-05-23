RELEASE_TYPE: patch

This patch by Phillip Schanely makes changes to the
:func:`~hypothesis.strategies.floats` strategy when ``min_value`` or ``max_value`` is
present.
Hypothesis will now be capable of generating every representable value in the bounds.
You may notice that hypothesis is more likely to test values near boundaries, and values
that are very close to zero.

These changes also support future integrations with symbolic execution tools and fuzzers
(:issue:`3086`).
