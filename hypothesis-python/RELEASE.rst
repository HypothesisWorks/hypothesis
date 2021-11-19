RELEASE_TYPE: minor

This release adds special filtering logic to make a few special cases
like ``s.map(lambda x: x)`` and ``lists().filter(len)`` more efficient
(:issue:`2701`).
