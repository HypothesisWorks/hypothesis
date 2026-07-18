RELEASE_TYPE: patch

This patch improves the performance of unique collections drawing from a fixed
pool of elements, such as :func:`~hypothesis.strategies.sets` of
:func:`~hypothesis.strategies.sampled_from`, under symbolic-execution backends
such as :pypi:`hypothesis-crosshair`.
