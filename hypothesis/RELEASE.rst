RELEASE_TYPE: minor

:func:`~hypothesis.strategies.datetimes` now generates "tricky" datetimes
more often: values on or near daylight-saving and other utc-offset
transitions of the drawn timezone - including imaginary wall times, and
ambiguous ones with each value of ``fold`` - as well as times adjacent to
leap seconds and to famous rollovers like the millennium and the end of
the signed 32-bit Unix epoch (:issue:`69`).

This release also fixes some rare internal errors, where an error raised
partway through updating an internal cache - for example by a deeply
recursive strategy exhausting the interpreter stack - could leave that
cache corrupted.
