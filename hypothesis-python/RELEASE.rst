RELEASE_TYPE: patch

This patch adds filter rewriting for :func:`math.isfinite`, :func:`math.isinf`, and :func:`math.isnan`
on :func:`~hypothesis.strategies.integers` or :func:`~hypothesis.strategies.floats` (:issue:`2701`).

Thanks to Sam Clamons at the SciPy Sprints!