RELEASE_TYPE: minor

Deprecate :func:`~hypothesis.strategies.shared` strategies with the same ``key``
drawing from different base strategies. This could lead to subtle failures or
lower-than-expected example coverage.
