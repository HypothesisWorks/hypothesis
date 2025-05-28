RELEASE_TYPE: minor

Warn when :func:`~hypothesis.strategies.shared` strategies with the same ``key``
draw from different base strategies. This could lead to subtle failures or
lower-than-expected example coverage.
