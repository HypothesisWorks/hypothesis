RELEASE_TYPE: minor

This release avoids creating a ``.hypothesis`` directory when using
:func:`~hypothesis.strategies.register_type_strategy` (:issue:`3836`),
and adds warnings for plugins which do so by other means or have
other unintended side-effects.
