RELEASE_TYPE: patch

This patch fixes :issue:`2696`, an internal error triggered when the
:func:`@example <hypothesis.example>` decorator was used and the
:obj:`~hypothesis.settings.verbosity` setting was ``quiet``.
