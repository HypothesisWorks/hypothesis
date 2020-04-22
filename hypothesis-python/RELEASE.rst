RELEASE_TYPE: patch

This patch fixes :issue:`2406`, where use of :obj:`pandas:pandas.Timestamp`
objects as bounds for the :func:`~hypothesis.strategies.datetimes` strategy
caused an internal error.  This bug was introduced in :ref:`version 5.8.1 <v5.8.2>`.
