RELEASE_TYPE: minor

:obj:`~hypothesis.settings.register_profile` now accepts keyword arguments
for specific settings, and the parent settings object is now optional.
Using a ``name`` for a registered profile which is not a string was never
suggested, but it is now also deprecated and will eventually be an error.
