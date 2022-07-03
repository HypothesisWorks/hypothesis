RELEASE_TYPE: patch

:func:`hypothesis.event` now works for hashable objects which do not
support weakrefs, such as integers and tuples.
