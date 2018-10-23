RELEASE_TYPE: patch

This patch shortens tracebacks from Hypothesis, so you can see exactly
happened in your code without having to skip over irrelevant details
about our internals (:issue:`848`).

In the example test (see :pull:`1582`), this reduces tracebacks from
nine frames to just three - and for a test with multiple errors, from
seven frames per error to just one!

If you *do* want to see the internal details, you can disable frame
elision by setting :obj:`~hypothesis.settings.verbosity` to ``debug``.
