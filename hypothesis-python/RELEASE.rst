RELEASE_TYPE: minor

:func:`~hypothesis.strategies.from_type` can now resolve :class:`~python:typing.TypeVar`
instances when the ``bound`` is a :class:`~python:typing.ForwardRef`, so long as that name
is in fact defined in the same module as the typevar (no ``TYPE_CHECKING`` tricks, sorry).
This feature requires Python 3.7 or later.

Thanks to Zac Hatfield-Dodds and Nikita Sobolev for this feature!
