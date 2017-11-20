RELEASE_TYPE: patch

This release changes the behaviour of the :attr:`~hypothesis.settings.deadline`
setting when used with :func:`~hypothesis.strategies.data`: Time spent inside
calls to ``data.draw`` will no longer be counted towards the deadline time.

This work was funded by `Smarkets <https://smarkets.com/>`_.
