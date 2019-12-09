RELEASE_TYPE: minor

This release changes the ``stateful_step_count`` setting to raise an error if
set to ``0``. This is a backwards compatible change because a value of ``0``
would never have worked and attempting to run it would have resulted in an
internal assertion error.
