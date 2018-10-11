RELEASE_TYPE: minor

This release deprecates using floats for ``min_size`` and ``max_size``.

The type hint for ``average_size`` arguments has been changed from
``Optional[int]`` to None, because non-None values are always ignored and
deprecated.

