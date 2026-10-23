RELEASE_TYPE: patch

This patch makes writing :ref:`observability <observability>` data to
``.hypothesis/observed`` cheaper when tests run in multiple threads, and
defers cleaning up old observation files from import time until
observations are first written.
