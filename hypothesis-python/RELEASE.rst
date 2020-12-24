RELEASE_TYPE: patch

This change fixes a documentation error in the
:obj:`~hypothesis.settings.database` setting.

The previous documentation suggested that callers could specify a database
path string, or the special string ``":memory:"``, but this setting has
never actually allowed string arguments.

Permitted values are ``None``, and instances of
:class:`~hypothesis.database.ExampleDatabase`.
