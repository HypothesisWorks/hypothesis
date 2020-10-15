RELEASE_TYPE: patch

This patch improves :func:`~hypothesis.strategies.builds` and
:func:`~hypothesis.strategies.from_type` support for explicitly defined ``__signature__``
attributes, from :ref:`version 5.8.3 <v5.8.3>`, to support generic types from the
:mod:`python:typing` module.

Thanks to Rónán Carrigan for identifying and fixing this problem!
