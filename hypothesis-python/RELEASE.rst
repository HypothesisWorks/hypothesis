RELEASE_TYPE: minor

The :doc:`Ghostwritter <ghostwriter>` will now include type annotations on tests
for type-annotated code.  If you want to force this to happen (or not happen),
pass a boolean to the new ``annotate=`` argument to the Python functions, or
the ``--[no-]annotate`` CLI flag.

Thanks to Nicolas Ganz for this new feature!
