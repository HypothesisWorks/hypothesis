RELEASE_TYPE: patch

This patch substantially improves our ability to avoid generating redundant
inputs when choosing between a non-power-of-two number of alternatives.
In certain circumstances, this was causing serious performance problems -
see :issue:`1864`, :issue:`1982`, and :issue:`2027`.
