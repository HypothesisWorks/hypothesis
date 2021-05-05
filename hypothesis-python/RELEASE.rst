RELEASE_TYPE: minor

:func:`hypothesis.target` now returns the ``observation`` value,
allowing it to be conveniently used inline in expressions such as
``assert target(abs(a - b)) < 0.1``.
