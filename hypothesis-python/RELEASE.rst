RELEASE_TYPE: patch

This patch disables part of the :mod:`typing`-based inference for the
:pypi:`attrs` package under Python 3.5.0, which has some incompatible
internal details (:issue:`2095`).
