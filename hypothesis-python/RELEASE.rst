RELEASE_TYPE: patch

If multiple explicit examples (from :func:`@example() <hypothesis.example>`)
raise a Skip exception, for consistency with generated examples we now re-raise
the first instead of collecting them into an ExceptionGroup (:issue:`3453`).
