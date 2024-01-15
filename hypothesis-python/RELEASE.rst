RELEASE_TYPE: patch

This patch improves :doc:`observability <observability>` reports by moving
timing information from ``metadata`` to a new ``timing`` key, and supporting
conversion of additional argument types to json rather than string reprs
via a ``.to_json()`` method (including e.g. Pandas dataframes).
