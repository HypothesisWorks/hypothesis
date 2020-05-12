RELEASE_TYPE: minor

This release fixes compatibility issues with Python 3.9; due to the removal of
NamedTuple's deprecated `_field_types` attribute, Hypothesis needs to also
check the newer `__annotations__` attribute to identify an object as a
NamedTuple.
