RELEASE_TYPE: minor

This release adds a new health check that checks if the smallest "natural"
possible example of your test case is very large - this will tend to cause
Hypothesis to generate bad examples and be quite slow.

In addition this release improves the documentation of how different
strategies shrink, as understanding that is useful for fixing the problem this
health check is pointing to.

This work was funded by `Smarkets <https://smarkets.com/>`_.
