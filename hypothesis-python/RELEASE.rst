RELEASE_TYPE: minor

This release enables deprecation warnings even when the
:obj:`~hypothesis.settings.verbosity` setting is ``quiet``,
in preparation for Hypothesis 5.0 (:issue:`2218`).

Warnings can still be filtered by the standard mechanisms
provided in the standard-library :mod:`python:warnings` module.
