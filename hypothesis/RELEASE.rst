RELEASE_TYPE: patch

This patch rewrites the internal date- and time-drawing helper to use plain
arithmetic instead of branching on the values it draws.  The generated
distribution is unchanged, but :func:`~hypothesis.strategies.dates`,
:func:`~hypothesis.strategies.datetimes`, and
:func:`~hypothesis.strategies.times` are now much more efficient under
symbolic-execution backends such as :pypi:`crosshair-tool`, which can now
solve for a specific date directly rather than enumerating candidates
(:issue:`4759`).
