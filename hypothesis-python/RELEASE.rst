RELEASE_TYPE: patch

This release fixes a bug (:issue:`2160`) where decorators applied after
:func:`@settings <hypothesis.settings>` and before
:func:`@given <hypothesis.given>` were ignored.

Thanks to Tom Milligan for this bugfix!
