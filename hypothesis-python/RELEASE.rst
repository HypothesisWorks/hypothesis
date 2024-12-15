RELEASE_TYPE: patch

This release improves shrinking in some cases, especially for strategies using :func:`~hypothesis.strategies.one_of`.
This will typically improve shrinking speed and may in some cases improve the end result.
