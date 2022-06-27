RELEASE_TYPE: minor

This release raises :class:`~unittest.SkipTest` for which never executed any
examples, for example because the :obj:`~hypothesis.settings.phases` setting
excluded the :obj:`~hypothesis.Phase.explicit`, :obj:`~hypothesis.Phase.reuse`,
and :obj:`~hypothesis.Phase.generate` phases.  This helps to avoid cases where
broken tests appear to pass, because they didn't actually execute (:issue:`3328`).
