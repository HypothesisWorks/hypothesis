RELEASE_TYPE: patch

This release fixes an issue where the decorator used to rename arguments could
throw a ``TypeError`` if used on a function without a docstring.  This was
causing issues in the pytest build system (see :issue:`822`), but in practice
most users should see no change.
