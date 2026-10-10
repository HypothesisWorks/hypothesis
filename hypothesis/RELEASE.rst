RELEASE_TYPE: patch

This release fixes an error when applying :func:`@given <hypothesis.given>`
on Python 3.14 to functions with annotations referring to types that are only
available during type checking, when explicit strategies are supplied
(:issue:`4897`).

Thanks to Arjun Aravind for this fix!
