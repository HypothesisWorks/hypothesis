RELEASE_TYPE: patch

This patch updates :func:`<hypothesis._settings._validate_deadline>` to accept
timedeltas and numbers and returns a timedelta. This patch also updates the
runtime variable in :func:`<hypothesis.core.StateForActualGivenExecution.test>`
to use a timedelta to make the comparison work (:issue:`1900`).
