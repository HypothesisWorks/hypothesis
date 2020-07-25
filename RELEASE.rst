RELEASE_TYPE: minor

The :func:`~hypothesis.strategies.slices` strategy can now generate slices for empty sequences,
slices with negative start and stop indices (from the end of the sequence),
and ``step=None`` in place of ``step=1``.

Thanks to Sangarshanan for implementing this feature at the EuroPython sprints!
