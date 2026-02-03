RELEASE_TYPE: patch

This patch adds support for recursive forward references in
:func:`~hypothesis.strategies.from_type`, such as
``A = list[Union["A", str]]`` (:issue:`4542`).
Previously, such recursive type aliases would raise a ``ResolutionFailed``
error. Now, Hypothesis can automatically resolve the forward reference
by looking it up in the caller's namespace.
