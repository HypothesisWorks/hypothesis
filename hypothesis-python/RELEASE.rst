RELEASE_TYPE: minor

This release adds a ``fullmatch`` argument to
:func:`~hypothesis.strategies.from_regex`.  When ``fullmatch=True``, the
whole example will match the regex pattern as for :func:`python:re.fullmatch`.

Thanks to Jakub Nabaglo for writing this patch at the PyCon Australia sprints!
