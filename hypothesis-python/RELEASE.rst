RELEASE_TYPE: minor

This release deprecates the :obj:`~hypothesis.settings.max_shrinks` setting
in favor of an internal heuristic.  If you need to avoid shrinking examples,
use the :obj:`~hypothesis.settings.phases` setting instead.  (:issue:`1235`)
