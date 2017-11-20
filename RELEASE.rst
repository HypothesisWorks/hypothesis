RELEASE_TYPE: patch

This release changes the behaviour of the :attr:`~hypothesis.settings.deadline`
setting when used with :func:`~hypothesis.strategies.data`: Time spent inside
calls to ``data.draw`` will no longer be counted towards the deadline time.

As a side effect of some refactoring required for this work, the way flaky
tests are handled has changed slightly. You are unlikely to see much difference
from this, but some error messages will have changed.

This work was funded by `Smarkets <https://smarkets.com/>`_.
