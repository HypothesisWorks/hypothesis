RELEASE_TYPE: patch

This release fixes an issue where Hypothesis would raise a ``TypeError`` when
using the datetime-related strategies if running with ``PYTHONOPTIMIZE=2``.
This bug was introduced in v3.20.0.  (See :issue:`822`)
