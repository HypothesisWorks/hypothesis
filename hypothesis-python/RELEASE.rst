RELEASE_TYPE: minor

This release fixes :issue:`3133` and :issue:`3144`, where attempting
to generate Pandas series of lists or sets would fail with confusing
errors if you did not specify ``dtype=object``.
