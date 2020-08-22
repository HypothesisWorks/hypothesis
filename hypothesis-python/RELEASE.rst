RELEASE_TYPE: minor

:func:`~hypothesis.strategies.register_type_strategy` now handles ``TypeVar`` bound to a ``ForwardRef`` differently.

It now tries to resolve the ``ForwardRef`` bound argument
inside the module's namespace. Just like the regular ``typing`` module does.

Thanks to Zac Hatfield-Dodds and Nikita Sobolev for this feature!
