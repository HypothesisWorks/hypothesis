RELEASE_TYPE: minor

This release changes :func:`~hypothesis.strategies.register_type_strategy`
for compatibility with :pep:`585`: we now store only a single strategy or
resolver function which is used for both the builtin and the ``typing``
module version of each type (:issue:`3635`).

If you previously relied on registering separate strategies for e.g.
``list`` vs ``typing.List``, you may need to use explicit strategies
rather than inferring them from types.
