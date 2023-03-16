RELEASE_TYPE: minor

This release adds an optional ``domains=`` parameter to the
:func:`~hypothesis.strategies.emails` strategy, and excludes
the special-use :wikipedia:`.arpa` domain from the default
strategy (:issue:`3567`).

Thanks to Jens Tröger for reporting and fixing this bug!
