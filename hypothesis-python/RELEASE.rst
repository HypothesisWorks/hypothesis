RELEASE_TYPE: patch

This patch fixes a bug where :func:`~hypothesis.target` was accidentally
disabled if :attr:`~hypothesis.settings.database` setting was ``None``.
