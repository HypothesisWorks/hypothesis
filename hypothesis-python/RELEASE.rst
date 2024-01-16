RELEASE_TYPE: minor

Warns when constructing a `repr` that is overly long. This can
happen by accident if stringifying arbitrary strategies, and
is expensive in time and memory.
