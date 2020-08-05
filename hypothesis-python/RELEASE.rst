RELEASE_TYPE: patch

This patch improves the ``repr`` of the implementation details of certain
strategies, which could 'leak' out via some introspection tricks or via
events displayed with the ``--hypothesis-show-statistics`` option.
While not identical to our public reprs, this fixes :issue:`2404`.
