RELEASE_TYPE: patch

``hypothesis.errors`` will now raise :py:exc:`AttributeError` when attempting
to access an undefined attribute, rather than returning :py:obj:`None`.
