RELEASE_TYPE: minor

This release adds a new health check that checks if the smallest "natural"
possible example of your test case is very large - this will tend to cause
Hypothesis to generate bad examples and be quite slow.

This work was funded by `Smarkets <https://smarkets.com/>`_.
