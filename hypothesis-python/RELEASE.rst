RELEASE_TYPE: minor

This release simplifies the logic of the :attr:`~hypothesis.settings.print_blob` setting by removing the option to set it to ``PrintSettings.INFER``.
As a result the ``print_blob`` setting now takes a single boolean value, and the use of ``PrintSettings`` is deprecated.
