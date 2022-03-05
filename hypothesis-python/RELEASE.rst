RELEASE_TYPE: minor

This release changes the implementation of :const:`~hypothesis.infer` to be an alias 
for ``Ellipsis``. E.g. ``@given(a=infer)`` is now equivalent to ``@given(a=...)``. Furthermore, ``@given(...)`` can now be specified so that 
:func:`@given <hypothesis.given>` will infer the strategies for *all* arguments of the
decorated function based on its annotations.