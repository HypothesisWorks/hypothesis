RELEASE_TYPE: patch

This patch teaches our enhanced :func:`~typing.get_type_hints` function to
'see through' :obj:`~functools.partial` application, allowing inference
from type hints to work in a few more cases which aren't (yet!) supported
by the standard-library version.
