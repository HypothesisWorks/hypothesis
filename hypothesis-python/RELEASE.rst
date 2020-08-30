RELEASE_TYPE: minor

:func:`~hypothesis.strategies.register_type_strategy` now supports 
:class:`python:typing.TypeVar`, which was previously hard-coded, and allows a 
variety of types to be generated for unconstrained :class:`~python:typing.TypeVar`s 
instead of just :func:`~hypothesis.strategies.text`.

Thanks again to Nikita Sobolev for all your work on advanced types!
