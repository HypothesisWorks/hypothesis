RELEASE_TYPE: minor

This release updates :func:`hypothesis.strategies.uuids` by introducing an
``allow_nil`` argument, defaulting to ``False``. If ``allow_nil=True``, 
nil UUID would be generated more often