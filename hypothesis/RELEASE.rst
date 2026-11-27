RELEASE_TYPE: patch

This patch speeds up startup for concurrent processes which do not yet have a :ref:`constants cache <v6.131.1>`, such as :pypi:`pytest-xdist` workers in CI.  Each process now scans local modules in a different order, so that they mostly share work instead of repeating it (:issue:`4978`).
