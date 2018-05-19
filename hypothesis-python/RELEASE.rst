RELEASE_TYPE: minor

Using an unordered collection with the :func:`~hypothesis.strategies.permutations`
strategy has been deprecated because the order in which e.g. a set shrinks is
arbitrary. This may cause different results between runs.
