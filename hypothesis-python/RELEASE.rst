RELEASE_TYPE: minor

This release allows :func:`~hypothesis.strategies.register_type_strategy` to be used
with :obj:`python:typing.NewType` instances.  This may be useful to e.g. provide
only positive integers for :func:`from_type(UserId) <hypothesis.strategies.from_type>`
with a ``UserId = NewType('UserId', int)`` type.

Thanks to PJCampi for suggesting and writing the patch!
