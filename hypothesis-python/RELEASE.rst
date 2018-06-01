RELEASE_TYPE: minor

Fix class xx(NamedTuple) introspection
======================================

.. code:: python

class AnnotatedNamedTuple(typing.NamedTuple):
    a: str
    i: int

is not buildble by :func:`@build <hypothesis.build>(AnnotedNamedTuple)` because
they don't have an `__init__` method to introspect and find the argument (field)
types. Fixed things so that introspection will happen in this case.

Thanks to James Uther for this bug fix
