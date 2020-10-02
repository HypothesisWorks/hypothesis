RELEASE_TYPE: patch

This patch ensures that if the :ref:`"hypothesis" entry point <entry-points>`
is callable, we call it after importing it.  You can still use non-callable
entry points (like modules), which are only imported.
