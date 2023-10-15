RELEASE_TYPE: minor

This release allows strategy-generating functions registered with
:func:`~hypothesis.strategies.register_type_strategy` to conditionally not
return a strategy, by returning :data:`NotImplemented` (:issue:`3767`).
