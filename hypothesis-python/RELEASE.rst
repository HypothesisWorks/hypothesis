RELEASE_TYPE: patch

This patch fixes :issue:`2964`, where ``.map()`` and ``.filter()`` methods
were omitted from the ``repr()`` of :func:`~hypothesis.strategies.just` and
:func:`~hypothesis.strategies.sampled_from` strategies, since
:ref:`version 5.43.7 <v5.43.7>`.
