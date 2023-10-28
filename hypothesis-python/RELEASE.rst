RELEASE_TYPE: patch

This patch improves the speed of the explain phase on python 3.12+, by using the new `sys.monitoring <https://docs.python.org/dev/library/sys.monitoring.html>`_ module to collect coverage instead of `sys.settrace <https://docs.python.org/dev/library/sys.html#sys.settrace>`_.
