RELEASE_TYPE: patch

This patch ensures that we check that ``black`` is installed
before actually using it in CLI.
Previously, it was raising an ``ImportError``.

Thanks to Nikita Sobolev for fixing :issue:`2604`!
