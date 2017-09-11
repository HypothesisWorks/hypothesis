RELEASE_TYPE: minor

This release introduces a :attr:`~hypothesis.settings.deadline`
setting to Hypothesis.

When set this turns slow tests into errors. By default it is unset but will
warn if you exceed 300ms, which will become the default value in a future
release.

This work was funded by `Smarkets <https://smarkets.com/>`_.
