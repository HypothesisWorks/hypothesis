RELEASE_TYPE: patch

This patch improves our error detection and message when Hypothesis is run
on a Python implementation without support for ``-0.0``, which is required
for the :func:`~hypothesis.strategies.floats` strategy but can be disabled by
`unsafe compiler options <https://simonbyrne.github.io/notes/fastmath/>`__
(:issue:`3265`).
