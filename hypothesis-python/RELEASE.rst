RELEASE_TYPE: patch

This patch fixes a very rare overflow bug (:issue:`1748`) which could raise an
``InvalidArgument`` error in :func:`~hypothesis.strategies.complex_numbers`
even though the arguments were valid.
