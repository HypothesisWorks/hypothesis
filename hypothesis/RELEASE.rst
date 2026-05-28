RELEASE_TYPE: patch

This patch improves the type annotations of |st.fixed_dictionaries|, which now
accepts a :class:`~collections.abc.Mapping` rather than requiring an invariant
``dict``.  Because the value type is covariant, type-checkers can now infer the
generated type even when the strategies are heterogeneous, e.g. a ``mapping``
annotated as ``dict[str, SearchStrategy[int] | SearchStrategy[str]]`` (:issue:`4665`).

The ``mapping`` and ``optional`` arguments may now also have different key and
value types, which are unioned in the inferred result.
