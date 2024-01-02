RELEASE_TYPE: patch

This introduces the rewriting of length filters in :func:`~hypothesis.strategies.text` strategies, utilizing ``partial`` and ``lambda`` functions for efficient handling of length constraints (:issue:`3791`).

Thanks to Reagan Lee for implementing this feature!