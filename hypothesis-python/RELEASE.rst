RELEASE_TYPE: minor

This release adds :ref:`an interface <custom-function-execution>`
which can be used to insert a wrapper between the original test function and
:func:`@given <hypothesis.given>` (:issue:`1257`).  This will be particularly
useful for test runner extensions such as :pypi:`pytest-trio`, but is
not recommended for direct use by other users of Hypothesis.
