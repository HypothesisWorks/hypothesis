RELEASE_TYPE: patch

This patch ensures that if the :ref:`"hypothesis" entry point <entry-points>`
is callable, we call it after importing it.  You can still use non-callable
entry points (like modules), which are only imported.

We also prefer `importlib.metadata <https://docs.python.org/3/library/importlib.metadata.html>`__
or :pypi:`the backport <importlib_metadata>` over `pkg_resources
<https://setuptools.readthedocs.io/en/latest/pkg_resources.html>`__,
which makes ``import hypothesis`` around 200 milliseconds faster
(:issue:`2571`).
