RELEASE_TYPE: patch

Add a ``for_failure: bool = False`` parameter to ``provider.realize`` in :ref:`alternative backends <alternative-backends>`, so that symbolic-based backends can increase their timeouts when realizing failures, which are more important than regular examples.
