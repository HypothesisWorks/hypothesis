RELEASE_TYPE: minor

This release checks that the value of the
:attr:`~hypothesis.settings.print_blob` setting is a
:class:`~hypothesis.PrintSettings` instance.

Being able to specify a boolean value was not intended, and is now deprecated.
In addition, specifying ``True`` will now cause the blob to always be printed,
instead of causing it to be suppressed.

Specifying any value that is not a :class:`~hypothesis.PrintSettings`
or a boolean is now an error.
