RELEASE_TYPE: patch

Pretty-printing of failing examples can now use functions registered with
:func:`IPython.lib.pretty.for_type` or :func:`~IPython.lib.pretty.for_type_by_name`,
as well as restoring compatibility with ``_repr_pretty_`` callback methods
which were accidentally broken in :ref:`version 6.61.2 <v6.61.2>` (:issue:`3721`).
