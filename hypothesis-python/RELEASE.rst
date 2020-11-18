RELEASE_TYPE: patch

This patch adds a final fallback clause to :ref:`our plugin logic <entry-points>`
to fail with a warning rather than error on Python < 3.8 when neither the
:pypi:`importlib_metadata` (preferred) or :pypi:`setuptools` (fallback)
packages are available.
